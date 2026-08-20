"""Page-level parquet reader for transcript content columns.

Streams individual content cells (large JSON strings) directly from parquet
pages without ever materializing a cell in memory. Peak memory is bounded by
the zstd streaming window plus one read chunk, regardless of cell or
row-group size.

Supported shapes (everything Scout's writer produces):

- ZSTD-compressed or uncompressed column chunks
- v1 data pages with PLAIN, RLE_DICTIONARY, or PLAIN_DICTIONARY encoding
- flat optional BYTE_ARRAY columns (no repetition, max definition level <= 1)

Anything else raises :class:`PageReaderUnsupported`; callers fall back to the
DuckDB read path.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from dataclasses import dataclass
from typing import IO, Any

WHOLE_CHUNK_READ_THRESHOLD = 4 * 1024 * 1024
"""Column chunks at or below this compressed size are fetched in one read."""

DEFAULT_STREAM_CHUNK_SIZE = 64 * 1024

_PAGE_TYPE_DATA = 0
_PAGE_TYPE_DICTIONARY = 2
_ENC_PLAIN = 0
_ENC_PLAIN_DICTIONARY = 2
_ENC_RLE = 3
_ENC_RLE_DICTIONARY = 8
_DICT_DATA_ENCODINGS = frozenset({_ENC_PLAIN_DICTIONARY, _ENC_RLE_DICTIONARY})
_DICT_PAGE_ENCODINGS = frozenset({_ENC_PLAIN, _ENC_PLAIN_DICTIONARY})


class PageReaderUnsupported(Exception):
    """A parquet shape the page reader does not support; callers fall back."""


@dataclass(frozen=True)
class CellLocation:
    """Position of one transcript's row within a parquet file."""

    row_group: int
    row_in_group: int


# --- thrift compact protocol (just enough for PageHeader) ---


class _ThriftReader:
    def __init__(self, buf: bytes) -> None:
        self.buf = buf
        self.pos = 0

    def byte(self) -> int:
        b = self.buf[self.pos]
        self.pos += 1
        return b

    def varint(self) -> int:
        result = 0
        shift = 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result
            shift += 7

    def zigzag(self) -> int:
        n = self.varint()
        return (n >> 1) ^ -(n & 1)

    def binary(self) -> bytes:
        n = self.varint()
        value = self.buf[self.pos : self.pos + n]
        if len(value) != n:
            raise IndexError("binary field extends past buffer")
        self.pos += n
        return value


def _parse_value(r: _ThriftReader, ftype: int) -> Any:
    if ftype == 1:
        return True
    if ftype == 2:
        return False
    if ftype == 3:
        return struct.unpack("b", bytes([r.byte()]))[0]
    if ftype in (4, 5, 6):
        return r.zigzag()
    if ftype == 7:
        if r.pos + 8 > len(r.buf):
            raise IndexError("double field extends past buffer")
        value = struct.unpack("<d", r.buf[r.pos : r.pos + 8])[0]
        r.pos += 8
        return value
    if ftype == 8:
        return r.binary()
    if ftype in (9, 10):  # list / set
        header = r.byte()
        size = header >> 4
        elem_type = header & 0x0F
        if size == 15:
            size = r.varint()
        return [_parse_value(r, elem_type) for _ in range(size)]
    if ftype == 11:  # map
        size = r.varint()
        if size == 0:
            return {}
        header = r.byte()
        key_type, value_type = header >> 4, header & 0x0F
        result: dict[Any, Any] = {}
        for _ in range(size):
            key = _parse_value(r, key_type)
            result[key] = _parse_value(r, value_type)
        return result
    if ftype == 12:
        return _parse_struct(r)
    raise PageReaderUnsupported(f"unknown thrift compact type {ftype}")


def _parse_struct(r: _ThriftReader) -> dict[int, Any]:
    fields: dict[int, Any] = {}
    field_id = 0
    while True:
        b = r.byte()
        if b == 0:
            return fields
        delta = b >> 4
        ftype = b & 0x0F
        if delta == 0:
            field_id = r.zigzag()
        else:
            field_id += delta
        fields[field_id] = _parse_value(r, ftype)


# --- page headers ---


@dataclass(frozen=True)
class _PageInfo:
    header_offset: int
    data_offset: int
    page_type: int
    compressed_size: int
    uncompressed_size: int
    num_values: int
    encoding: int
    def_level_encoding: int


def _parse_page_header(buf: bytes, header_offset: int) -> _PageInfo:
    """Parse one PageHeader from buf.

    Raises IndexError when buf is too short (callers re-read with a larger
    slice) and PageReaderUnsupported for page types the reader cannot decode
    (DATA_PAGE_V2, INDEX_PAGE, ...).
    """
    r = _ThriftReader(buf)
    fields = _parse_struct(r)
    page_type = fields[1]
    if page_type == _PAGE_TYPE_DATA:
        header = fields[5]  # DataPageHeader
        num_values = header[1]
        encoding = header[2]
        def_level_encoding = header[3]
    elif page_type == _PAGE_TYPE_DICTIONARY:
        header = fields[7]  # DictionaryPageHeader
        num_values = header[1]
        encoding = header[2]
        def_level_encoding = _ENC_RLE
    else:
        raise PageReaderUnsupported(f"unsupported page type {page_type}")
    return _PageInfo(
        header_offset=header_offset,
        data_offset=header_offset + r.pos,
        page_type=page_type,
        compressed_size=fields[3],
        uncompressed_size=fields[2],
        num_values=num_values,
        encoding=encoding,
        def_level_encoding=def_level_encoding,
    )


_HEADER_SLICE = 8 * 1024


class _ChunkSource:
    """Byte access within one column chunk.

    Chunks at or below the coalesce threshold are read whole in one ranged
    read (matching DuckDB's I/O pattern on small chunks); larger chunks are
    read with explicit per-range seeks so non-target pages are never fetched.
    """

    def __init__(
        self,
        fileobj: IO[bytes],
        start: int,
        total_compressed: int,
        coalesce_threshold: int = WHOLE_CHUNK_READ_THRESHOLD,
    ) -> None:
        self._fileobj = fileobj
        self.start = start
        self.end = start + total_compressed
        self._buf: bytes | None = None
        if total_compressed <= coalesce_threshold:
            fileobj.seek(start)
            self._buf = fileobj.read(total_compressed)

    def read_at(self, offset: int, size: int) -> bytes:
        size = min(size, self.end - offset)
        if size <= 0:
            return b""
        if self._buf is not None:
            rel = offset - self.start
            return self._buf[rel : rel + size]
        self._fileobj.seek(offset)
        return self._fileobj.read(size)

    def iter_range(
        self,
        offset: int,
        size: int,
        chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE,
    ) -> Iterator[bytes]:
        position = offset
        remaining = size
        while remaining > 0:
            piece = self.read_at(position, min(chunk_size, remaining))
            if not piece:
                raise PageReaderUnsupported("truncated column chunk")
            yield piece
            position += len(piece)
            remaining -= len(piece)


def _walk_pages(chunk: _ChunkSource) -> Iterator[_PageInfo]:
    """Yield page infos in file order, reading only page headers."""
    position = chunk.start
    while position < chunk.end:
        slice_size = _HEADER_SLICE
        while True:
            buf = chunk.read_at(position, slice_size)
            try:
                page = _parse_page_header(buf, position)
                break
            except (IndexError, struct.error):
                if slice_size >= chunk.end - position:
                    raise PageReaderUnsupported(
                        "page header parse ran past column chunk end"
                    ) from None
                slice_size *= 4
        yield page
        position = page.data_offset + page.compressed_size
