"""Page-level parquet reader for transcript content columns.

Streams individual content cells (large JSON strings) directly from parquet
pages without ever materializing a cell in memory. Peak memory is bounded by
the zstd streaming window plus one read chunk, regardless of cell or
row-group size.

Supported shapes (everything Scout's writer produces):

- ZSTD-compressed or uncompressed column chunks
- v1 data pages with PLAIN, RLE_DICTIONARY, or PLAIN_DICTIONARY encoding
- flat optional BYTE_ARRAY columns (no repetition, max definition level <= 1)

Anything else raises :class:`PageReaderUnsupportedError`; callers fall back to the
DuckDB read path.
"""

from __future__ import annotations

import contextlib
import struct
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass
from types import TracebackType
from typing import IO, Any, cast

import pyarrow.parquet as pq
import zstandard
from inspect_ai._util.file import filesystem

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


class PageReaderUnsupportedError(Exception):
    """A parquet shape the page reader does not support; callers fall back."""


@dataclass(frozen=True)
class CellLocation:
    """Position of one transcript's row within a parquet file."""

    row_group: int
    row_in_group: int


_LOCATION_CACHE_MAX_FILES = 256
_location_cache: OrderedDict[str, dict[str, CellLocation]] = OrderedDict()
"""id -> position maps, keyed by file path.

Store files are immutable once written: every write generates a fresh
uuid-suffixed filename and compaction produces new files rather than
rewriting existing ones, so a path identifies its contents for the life of
the process. Decoding the whole transcript_id column per lookup instead made
locate() the dominant cost of read() on files with many rows.
"""


# --- thrift compact protocol (just enough for PageHeader) ---


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read one LEB128 varint at `pos`; returns (value, position after it).

    Raises IndexError when the varint runs past the end of `data`.
    """
    result = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


class _ThriftReader:
    def __init__(self, buf: bytes) -> None:
        self.buf = buf
        self.pos = 0

    def byte(self) -> int:
        b = self.buf[self.pos]
        self.pos += 1
        return b

    def varint(self) -> int:
        result, self.pos = _read_varint(self.buf, self.pos)
        return result

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


def _check_collection_size(r: _ThriftReader, size: int) -> None:
    """Reject collections that cannot fit in the remaining buffer.

    Bool elements consume no bytes at all, so an 18-byte header can otherwise
    declare 2**34 elements and hang the parse.
    """
    if size > len(r.buf) - r.pos:
        raise PageReaderUnsupportedError(
            f"thrift collection of {size} elements exceeds the remaining buffer"
        )


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
        _check_collection_size(r, size)
        return [_parse_value(r, elem_type) for _ in range(size)]
    if ftype == 11:  # map
        size = r.varint()
        if size == 0:
            return {}
        _check_collection_size(r, size)
        header = r.byte()
        key_type, value_type = header >> 4, header & 0x0F
        result: dict[Any, Any] = {}
        for _ in range(size):
            key = _parse_value(r, key_type)
            result[key] = _parse_value(r, value_type)
        return result
    if ftype == 12:
        return _parse_struct(r)
    raise PageReaderUnsupportedError(f"unknown thrift compact type {ftype}")


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


def _int_field(fields: dict[int, Any], field_id: int, *, minimum: int = 0) -> int:
    """Read a non-negative int field, rejecting missing/wrong/negative values.

    Corrupt headers otherwise reach the walk as negative sizes, where they
    send it backwards forever, or as absent fields, where they KeyError.
    """
    value = fields.get(field_id)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise PageReaderUnsupportedError(f"invalid thrift field {field_id}: {value!r}")
    return value


def _struct_field(fields: dict[int, Any], field_id: int) -> dict[int, Any]:
    value = fields.get(field_id)
    if not isinstance(value, dict):
        raise PageReaderUnsupportedError(f"invalid thrift field {field_id}: {value!r}")
    return value


def _parse_page_header(buf: bytes, header_offset: int) -> _PageInfo:
    """Parse one PageHeader from buf.

    Raises IndexError when buf is too short (callers re-read with a larger
    slice) and PageReaderUnsupportedError for page types the reader cannot decode
    (DATA_PAGE_V2, INDEX_PAGE, ...) and for structurally invalid fields.
    """
    r = _ThriftReader(buf)
    fields = _parse_struct(r)
    page_type = _int_field(fields, 1)
    if page_type == _PAGE_TYPE_DATA:
        header = _struct_field(fields, 5)  # DataPageHeader
        num_values = _int_field(header, 1)
        encoding = _int_field(header, 2)
        def_level_encoding = _int_field(header, 3)
    elif page_type == _PAGE_TYPE_DICTIONARY:
        header = _struct_field(fields, 7)  # DictionaryPageHeader
        num_values = _int_field(header, 1)
        encoding = _int_field(header, 2)
        def_level_encoding = _ENC_RLE
    else:
        raise PageReaderUnsupportedError(f"unsupported page type {page_type}")
    return _PageInfo(
        header_offset=header_offset,
        data_offset=header_offset + r.pos,
        page_type=page_type,
        compressed_size=_int_field(fields, 3),
        uncompressed_size=_int_field(fields, 2),
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
        # Without this the coalesced branch would slice with a negative index
        # and silently return the wrong bytes, where the ranged branch reads
        # outside the chunk. Neither is a legal request.
        if offset < self.start:
            raise PageReaderUnsupportedError("read before chunk start")
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
                raise PageReaderUnsupportedError("truncated column chunk")
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
                    raise PageReaderUnsupportedError(
                        "page header parse ran past column chunk end"
                    ) from None
                slice_size *= 4
        next_position = page.data_offset + page.compressed_size
        if next_position <= position:
            raise PageReaderUnsupportedError("page does not advance")
        yield page
        position = next_position


def _decode_rle_hybrid(data: bytes, bit_width: int, count: int) -> list[int]:
    """Decode a parquet RLE/bit-packed hybrid run of `count` values."""
    if bit_width == 0:
        return [0] * count
    byte_width = (bit_width + 7) // 8
    mask = (1 << bit_width) - 1
    out: list[int] = []
    pos = 0
    while pos < len(data) and len(out) < count:
        header, pos = _read_varint(data, pos)
        if header & 1:  # bit-packed: (header >> 1) groups of 8 values
            n_groups = header >> 1
            n_bytes = n_groups * bit_width
            group_bytes = data[pos : pos + n_bytes]
            if len(group_bytes) != n_bytes:
                raise PageReaderUnsupportedError("truncated RLE bit-packed group")
            packed = int.from_bytes(group_bytes, "little")
            pos += n_bytes
            for j in range(n_groups * 8):
                out.append((packed >> (j * bit_width)) & mask)
        else:  # RLE run
            # Cap to what's still needed: a corrupt varint could otherwise
            # demand a huge allocation, and MemoryError is not fallback-able.
            run = min(header >> 1, count - len(out))
            value_bytes = data[pos : pos + byte_width]
            if len(value_bytes) != byte_width:
                raise PageReaderUnsupportedError("truncated RLE run value")
            value = int.from_bytes(value_bytes, "little")
            pos += byte_width
            out.extend([value] * run)
    if len(out) < count:
        # Returning short here surfaced later as an unrelated IndexError.
        raise PageReaderUnsupportedError(
            "RLE data ended before producing requested values"
        )
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
            raise PageReaderUnsupportedError("unexpected end of page data") from None
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


class _IteratorReader:
    """Minimal read(n) adapter over an iterator of byte chunks."""

    def __init__(self, chunks: Iterator[bytes]) -> None:
        self._chunks = chunks
        self._buffer = b""

    def read(self, n: int) -> bytes:
        while len(self._buffer) < n:
            piece = next(self._chunks, None)
            if piece is None:
                break
            self._buffer += piece
        out = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return out


def _decompressed_stream(
    compressed: Iterator[bytes],
    codec: str,
    chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE,
) -> Iterator[bytes]:
    """Stream-decompress one page, bounding each yielded chunk.

    zstandard's decompressobj returns ALL output for the input consumed —
    one tiny piece of a highly-compressible frame can decompress to the
    whole cell — so pull bounded reads through stream_reader instead.
    Codec is pre-validated by the caller.
    """
    if codec == "UNCOMPRESSED":
        yield from compressed
        return
    # stream_reader only ever calls read(n) on its source, so the minimal
    # adapter is sufficient despite the stubs asking for a full IO[bytes].
    reader = zstandard.ZstdDecompressor().stream_reader(
        cast(IO[bytes], _IteratorReader(compressed))
    )
    while True:
        piece = reader.read(chunk_size)
        if not piece:
            return
        yield piece


def _read_def_levels(
    cursor: _StreamCursor, num_values: int, max_def_level: int
) -> list[int]:
    """Read a v1 data page's definition levels (RLE, 4-byte length prefix)."""
    if max_def_level == 0:
        return [1] * num_values
    (levels_len,) = struct.unpack("<I", cursor.read(4))
    return _decode_rle_hybrid(cursor.read(levels_len), 1, num_values)


@dataclass
class _OpenCell:
    """A located, validated cell.

    A cursor positioned after the def levels plus the number of preceding
    values to skip.
    """

    cursor: _StreamCursor
    values_to_skip: int

    def _seek_target(self) -> int:
        for _ in range(self.values_to_skip):
            (value_len,) = struct.unpack("<I", self.cursor.read(4))
            self.cursor.skip(value_len)
        (value_len,) = struct.unpack("<I", self.cursor.read(4))
        return int(value_len)

    def stream(self, chunk_size: int) -> Iterator[bytes]:
        value_len = self._seek_target()
        yield from self.cursor.iter_read(value_len, chunk_size)

    def size(self) -> int:
        return self._seek_target()


class ParquetContentReader:
    """Streams individual content cells from one transcript parquet file.

    Opens exactly the one path it is given (local or fsspec URL). Streams
    returned by stream_cell are only valid while the reader is open.
    """

    def __init__(
        self, path: str, *, coalesce_threshold: int = WHOLE_CHUNK_READ_THRESHOLD
    ) -> None:
        self._path = path
        self._coalesce_threshold = coalesce_threshold
        raw: Any = None
        meta: Any = None
        try:
            if "://" in path:
                fs = filesystem(path).fs
                # cache_type="none": fsspec readahead would turn each ~30-byte
                # header read into a multi-MB block fetch. pyarrow does its
                # own buffering for the metadata handle too, so "none" is
                # correct there as well.
                raw = fs.open(path, "rb", cache_type="none")
                meta = fs.open(path, "rb", cache_type="none")
                parquet_file = pq.ParquetFile(meta)
            else:
                raw = open(path, "rb")
                parquet_file = pq.ParquetFile(path)
            metadata = parquet_file.metadata
            self._column_index = {
                metadata.schema.column(i).name: i for i in range(metadata.num_columns)
            }
        except Exception:
            with contextlib.suppress(Exception):
                if meta is not None:
                    meta.close()
            with contextlib.suppress(Exception):
                if raw is not None:
                    raw.close()
            raise
        self._raw: Any = raw
        self._meta_file: Any = meta
        self._parquet_file = parquet_file

    @property
    def path(self) -> str:
        """The single file this reader was opened on."""
        return self._path

    def __enter__(self) -> "ParquetContentReader":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._parquet_file.close()
        if self._meta_file is not None:
            self._meta_file.close()
        self._raw.close()

    def column_names(self) -> set[str]:
        return set(self._parquet_file.schema_arrow.names)

    def locate(self, transcript_id: str) -> CellLocation | None:
        return self._locations().get(transcript_id)

    def _locations(self) -> dict[str, CellLocation]:
        """The file's whole id -> position map, built once and cached by path."""
        cached = _location_cache.get(self._path)
        if cached is not None:
            return cached
        if "transcript_id" not in self._column_index:
            raise PageReaderUnsupportedError("file has no transcript_id column")
        ids = self._parquet_file.read(columns=["transcript_id"]).column("transcript_id")
        all_ids = ids.to_pylist()
        metadata = self._parquet_file.metadata
        locations: dict[str, CellLocation] = {}
        row = 0
        for row_group in range(metadata.num_row_groups):
            group_rows = metadata.row_group(row_group).num_rows
            for row_in_group in range(group_rows):
                identifier = all_ids[row + row_in_group]
                if identifier is not None:
                    # first occurrence wins, matching the previous index() lookup
                    locations.setdefault(
                        identifier, CellLocation(row_group, row_in_group)
                    )
            row += group_rows
        if row != len(all_ids):
            raise PageReaderUnsupportedError("rows extend beyond all row groups")
        _location_cache[self._path] = locations
        while len(_location_cache) > _LOCATION_CACHE_MAX_FILES:
            _location_cache.popitem(last=False)
        return locations

    def stream_cell(
        self,
        location: CellLocation,
        column: str,
        chunk_size: int = DEFAULT_STREAM_CHUNK_SIZE,
    ) -> Iterator[bytes] | None:
        cell = self._open_cell(location, column)
        return None if cell is None else cell.stream(chunk_size)

    def cell_size(self, location: CellLocation, column: str) -> int:
        cell = self._open_cell(location, column)
        return 0 if cell is None else cell.size()

    def _open_cell(self, location: CellLocation, column: str) -> _OpenCell | None:
        if column not in self._column_index:
            raise ValueError(f"column {column!r} not in {self._path}")
        metadata = self._parquet_file.metadata
        column_i = self._column_index[column]
        schema_column = metadata.schema.column(column_i)
        if schema_column.physical_type != "BYTE_ARRAY":
            raise PageReaderUnsupportedError(
                f"physical type {schema_column.physical_type}"
            )
        if (
            schema_column.max_repetition_level != 0
            or schema_column.max_definition_level > 1
        ):
            raise PageReaderUnsupportedError("nested or repeated column")
        max_def_level = schema_column.max_definition_level
        chunk_meta = metadata.row_group(location.row_group).column(column_i)
        codec = chunk_meta.compression
        if codec not in ("ZSTD", "UNCOMPRESSED"):
            raise PageReaderUnsupportedError(f"codec {codec}")
        starts = [
            offset
            for offset in (
                chunk_meta.dictionary_page_offset,
                chunk_meta.data_page_offset,
            )
            if offset is not None and offset > 0
        ]
        chunk = _ChunkSource(
            self._raw,
            min(starts),
            chunk_meta.total_compressed_size,
            self._coalesce_threshold,
        )
        dictionary_page: _PageInfo | None = None
        rows_seen = 0
        for page in _walk_pages(chunk):
            if page.page_type == _PAGE_TYPE_DICTIONARY:
                if page.encoding not in _DICT_PAGE_ENCODINGS:
                    raise PageReaderUnsupportedError(
                        f"dictionary page encoding {page.encoding}"
                    )
                dictionary_page = page
                continue
            if rows_seen + page.num_values <= location.row_in_group:
                rows_seen += page.num_values
                continue
            if max_def_level > 0 and page.def_level_encoding != _ENC_RLE:
                raise PageReaderUnsupportedError(
                    f"definition level encoding {page.def_level_encoding}"
                )
            row_in_page = location.row_in_group - rows_seen
            return self._open_data_page(
                chunk, codec, page, dictionary_page, max_def_level, row_in_page
            )
        raise PageReaderUnsupportedError(
            f"row {location.row_in_group} beyond pages of row group "
            f"{location.row_group}"
        )

    def _open_data_page(
        self,
        chunk: _ChunkSource,
        codec: str,
        page: _PageInfo,
        dictionary_page: _PageInfo | None,
        max_def_level: int,
        row_in_page: int,
    ) -> _OpenCell | None:
        if page.encoding in _DICT_DATA_ENCODINGS:
            return self._open_dictionary_cell(
                chunk, codec, page, dictionary_page, max_def_level, row_in_page
            )
        if page.encoding != _ENC_PLAIN:
            raise PageReaderUnsupportedError(f"data page encoding {page.encoding}")
        cursor = _StreamCursor(
            _decompressed_stream(
                chunk.iter_range(page.data_offset, page.compressed_size), codec
            )
        )
        def_levels = _read_def_levels(cursor, page.num_values, max_def_level)
        if def_levels[row_in_page] == 0:
            return None
        values_before = sum(1 for level in def_levels[:row_in_page] if level)
        return _OpenCell(cursor=cursor, values_to_skip=values_before)

    def _open_dictionary_cell(
        self,
        chunk: _ChunkSource,
        codec: str,
        page: _PageInfo,
        dictionary_page: _PageInfo | None,
        max_def_level: int,
        row_in_page: int,
    ) -> _OpenCell | None:
        if dictionary_page is None:
            raise PageReaderUnsupportedError(
                "dictionary-encoded page without a dictionary page"
            )
        # The index page is small (indices, not values): decode it in memory.
        cursor = _StreamCursor(
            _decompressed_stream(
                chunk.iter_range(page.data_offset, page.compressed_size), codec
            )
        )
        def_levels = _read_def_levels(cursor, page.num_values, max_def_level)
        if def_levels[row_in_page] == 0:
            return None
        values_before = sum(1 for level in def_levels[:row_in_page] if level)
        bit_width = cursor.read(1)[0]
        remaining = page.uncompressed_size - cursor.bytes_read
        indices = _decode_rle_hybrid(
            cursor.read(remaining), bit_width, values_before + 1
        )
        dictionary_index = indices[values_before]
        # Stream the dictionary page, skipping entries before the target.
        dictionary_cursor = _StreamCursor(
            _decompressed_stream(
                chunk.iter_range(
                    dictionary_page.data_offset, dictionary_page.compressed_size
                ),
                codec,
            )
        )
        return _OpenCell(cursor=dictionary_cursor, values_to_skip=dictionary_index)
