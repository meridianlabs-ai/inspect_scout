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

import zstandard

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


def _decode_rle_hybrid(data: bytes, bit_width: int, count: int) -> list[int]:
    """Decode a parquet RLE/bit-packed hybrid run of `count` values."""
    if bit_width == 0:
        return [0] * count
    byte_width = (bit_width + 7) // 8
    mask = (1 << bit_width) - 1
    out: list[int] = []
    pos = 0
    while pos < len(data) and len(out) < count:
        header = 0
        shift = 0
        while True:
            b = data[pos]
            pos += 1
            header |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        if header & 1:  # bit-packed: (header >> 1) groups of 8 values
            n_groups = header >> 1
            n_bytes = n_groups * bit_width
            packed = int.from_bytes(data[pos : pos + n_bytes], "little")
            pos += n_bytes
            for j in range(n_groups * 8):
                out.append((packed >> (j * bit_width)) & mask)
        else:  # RLE run
            run = header >> 1
            value = int.from_bytes(data[pos : pos + byte_width], "little")
            pos += byte_width
            out.extend([value] * run)
    return out[:count]


class _StreamCursor:
    """Pull-based reader over an iterator of byte chunks.

    read() accumulates, skip() discards, iter_read() re-yields — the three
    verbs the page decoders need, none of which hold more than one chunk.
    """

    def __init__(self, chunks: Iterator[bytes]) -> None:
        self._chunks = chunks
        self._current = b""
        self._pos = 0
        self.bytes_read = 0

    def _refill(self) -> None:
        try:
            self._current = next(self._chunks)
        except StopIteration:
            raise PageReaderUnsupported("unexpected end of page data") from None
        self._pos = 0

    def read(self, n: int) -> bytes:
        parts: list[bytes] = []
        need = n
        while need > 0:
            available = len(self._current) - self._pos
            if available == 0:
                self._refill()
                continue
            take = min(available, need)
            parts.append(self._current[self._pos : self._pos + take])
            self._pos += take
            need -= take
        self.bytes_read += n
        return b"".join(parts)

    def skip(self, n: int) -> None:
        remaining = n
        while remaining > 0:
            available = len(self._current) - self._pos
            if available == 0:
                self._refill()
                continue
            take = min(available, remaining)
            self._pos += take
            remaining -= take
        self.bytes_read += n

    def iter_read(self, n: int, chunk_size: int) -> Iterator[bytes]:
        remaining = n
        while remaining > 0:
            piece = self.read(min(chunk_size, remaining))
            remaining -= len(piece)
            yield piece


def _decompressed_stream(compressed: Iterator[bytes], codec: str) -> Iterator[bytes]:
    """Stream-decompress one page. Codec is pre-validated by the caller."""
    if codec == "UNCOMPRESSED":
        yield from compressed
        return
    decompressor = zstandard.ZstdDecompressor().decompressobj()
    for piece in compressed:
        out = decompressor.decompress(piece)
        if out:
            yield out


def _read_def_levels(
    cursor: _StreamCursor, num_values: int, max_def_level: int
) -> list[int]:
    """Read a v1 data page's definition levels (RLE, 4-byte length prefix)."""
    if max_def_level == 0:
        return [1] * num_values
    (levels_len,) = struct.unpack("<I", cursor.read(4))
    return _decode_rle_hybrid(cursor.read(levels_len), 1, num_values)
