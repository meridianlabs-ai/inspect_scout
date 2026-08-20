"""Tests for the parquet page reader."""

import builtins
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import zstandard
from fsspec.implementations.memory import (  # type: ignore[import-untyped]
    MemoryFileSystem,
)
from inspect_scout._transcript.database.parquet import page_reader
from inspect_scout._transcript.database.parquet.page_reader import (
    _PAGE_TYPE_DATA,
    _PAGE_TYPE_DICTIONARY,
    DEFAULT_STREAM_CHUNK_SIZE,
    CellLocation,
    PageReaderUnsupportedError,
    ParquetContentReader,
    _ChunkSource,
    _decode_rle_hybrid,
    _decompressed_stream,
    _PageInfo,
    _parse_page_header,
    _read_def_levels,
    _StreamCursor,
    _walk_pages,
)
from upath import UPath


def sample_values() -> list[str | None]:
    """Content cells covering NULL, empty, tiny, non-BMP, and multi-page sizes."""
    return [
        '[{"role":"user","content":"héllo→世界😀 ' + "a" * 50_000 + '"}]',
        None,
        "",
        '[{"big":"' + "b" * 2_000_000 + '"}]',
        "[]",
        '[{"role":"assistant","content":"' + "c" * 300_000 + '"}]',
        None,
        '[{"seq":7}]',
        '[{"role":"user","content":"' + "d" * 1_200_000 + '"}]',
    ]


def build_content_table(events: list[str | None]) -> pa.Table:
    n = len(events)
    return pa.table(
        {
            "transcript_id": pa.array(
                [f"tr_{i:04d}" for i in range(n)], pa.large_string()
            ),
            "events": pa.array(events, pa.large_string()),
        }
    )


def write_content_file(
    path: str,
    events: list[str | None],
    *,
    row_group_size: int = 4,
    **write_kwargs: Any,
) -> pa.Table:
    """Write a two-column file mimicking Scout's writer defaults."""
    table = build_content_table(events)
    defaults: dict[str, Any] = {
        "compression": "zstd",
        "use_dictionary": True,
        "write_statistics": True,
    }
    defaults.update(write_kwargs)
    pq.write_table(table, path, row_group_size=row_group_size, **defaults)
    return table


def first_page_offset(md: pq.FileMetaData, row_group: int, column: int) -> int:
    cc = md.row_group(row_group).column(column)
    offsets = [
        o
        for o in (cc.dictionary_page_offset, cc.data_page_offset)
        if o is not None and o > 0
    ]
    return min(offsets)


def first_header_slice(path: str, size: int = 8 * 1024) -> tuple[bytes, int]:
    """Raw bytes at the first page header of row group 0, column 1."""
    md = pq.ParquetFile(path).metadata
    offset = first_page_offset(md, 0, 1)
    with open(path, "rb") as f:
        f.seek(offset)
        return f.read(size), offset


def test_parse_dictionary_page_header(tmp_path: Path) -> None:
    path = str(tmp_path / "dict.parquet")
    write_content_file(path, sample_values())
    buf, offset = first_header_slice(path)
    page = _parse_page_header(buf, offset)
    assert page.page_type == _PAGE_TYPE_DICTIONARY
    assert page.header_offset == offset
    assert page.data_offset > offset
    assert page.compressed_size > 0
    assert page.uncompressed_size > 0
    assert page.num_values > 0


def test_parse_plain_data_page_header(tmp_path: Path) -> None:
    path = str(tmp_path / "plain.parquet")
    write_content_file(path, sample_values(), use_dictionary=False)
    buf, offset = first_header_slice(path)
    page = _parse_page_header(buf, offset)
    assert page.page_type == _PAGE_TYPE_DATA
    # a 4-row group with dictionary off = one PLAIN page holding all rows
    assert page.num_values == 4


def test_parse_v2_page_header_unsupported(tmp_path: Path) -> None:
    path = str(tmp_path / "v2.parquet")
    write_content_file(
        path, sample_values(), use_dictionary=False, data_page_version="2.0"
    )
    buf, offset = first_header_slice(path)
    with pytest.raises(PageReaderUnsupportedError, match="page type"):
        _parse_page_header(buf, offset)


def test_truncated_header_raises_index_error(tmp_path: Path) -> None:
    path = str(tmp_path / "trunc.parquet")
    write_content_file(path, sample_values())
    buf, offset = first_header_slice(path, size=3)  # far too short for any header
    with pytest.raises(IndexError):
        _parse_page_header(buf, offset)


# --- crafted page headers (thrift compact wire format) ---


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | 0x80 if value else byte)
        if not value:
            return bytes(out)


def encode_zigzag(value: int) -> bytes:
    return encode_varint((value << 1) ^ (value >> 63))


def encode_field(field_id: int, ftype: int, payload: bytes) -> bytes:
    """One struct field in long form (delta 0 + explicit zigzag field id)."""
    return bytes([ftype]) + encode_zigzag(field_id) + payload


def encode_i32(field_id: int, value: int) -> bytes:
    return encode_field(field_id, 5, encode_zigzag(value))


def encode_page_header(
    *,
    page_type: int = _PAGE_TYPE_DATA,
    uncompressed: int = 64,
    compressed: int = 32,
    num_values: int = 4,
    encoding: int = 0,
    extra: bytes = b"",
) -> bytes:
    data_page = (
        encode_i32(1, num_values)
        + encode_i32(2, encoding)
        + encode_i32(3, 3)  # definition_level_encoding = RLE
        + encode_i32(4, 3)  # repetition_level_encoding = RLE
        + b"\x00"
    )
    return (
        encode_i32(1, page_type)
        + encode_i32(2, uncompressed)
        + encode_i32(3, compressed)
        + encode_field(5, 12, data_page)
        + extra
        + b"\x00"
    )


def test_crafted_header_encoder_round_trips() -> None:
    """Sanity-checks the test encoder itself before it is used adversarially."""
    page = _parse_page_header(encode_page_header(), 100)
    assert page.page_type == _PAGE_TYPE_DATA
    assert page.header_offset == 100
    assert page.data_offset == 100 + len(encode_page_header())
    assert (page.uncompressed_size, page.compressed_size) == (64, 32)
    assert (page.num_values, page.encoding) == (4, 0)


@pytest.mark.parametrize(
    "header",
    [
        encode_page_header(compressed=-18),
        encode_page_header(uncompressed=-1),
        encode_page_header(num_values=-5),
        encode_page_header(page_type=-1),
        encode_page_header(encoding=-2),
    ],
    ids=["compressed", "uncompressed", "num-values", "page-type", "encoding"],
)
def test_negative_header_sizes_raise(header: bytes) -> None:
    """A negative compressed_size would make _walk_pages spin forever."""
    with pytest.raises(PageReaderUnsupportedError, match="invalid thrift field"):
        _parse_page_header(header, 0)


def test_missing_data_page_header_raises() -> None:
    """A DATA page whose nested header is absent must not KeyError."""
    header = (
        encode_i32(1, _PAGE_TYPE_DATA) + encode_i32(2, 64) + encode_i32(3, 32) + b"\x00"
    )
    with pytest.raises(PageReaderUnsupportedError, match="invalid thrift field 5"):
        _parse_page_header(header, 0)


def test_thrift_collection_bomb_raises() -> None:
    """Bool list elements consume no bytes, so a declared 2**34 would hang."""
    bomb = encode_field(9, 9, bytes([0xF0 | 1]) + encode_varint(2**34))
    with pytest.raises(PageReaderUnsupportedError, match="thrift collection"):
        _parse_page_header(encode_page_header(extra=bomb), 0)


def walk_column_pages(path: str, row_group: int, column: int) -> list[_PageInfo]:
    md = pq.ParquetFile(path).metadata
    cc = md.row_group(row_group).column(column)
    with open(path, "rb") as f:
        chunk = _ChunkSource(
            f, first_page_offset(md, row_group, column), cc.total_compressed_size
        )
        return list(_walk_pages(chunk))


@pytest.mark.parametrize("coalesce", [True, False], ids=["whole-chunk", "ranged"])
def test_walk_accounts_for_full_chunk(tmp_path: Path, coalesce: bool) -> None:
    path = str(tmp_path / "walk.parquet")
    write_content_file(path, sample_values(), use_dictionary=False, write_batch_size=1)
    md = pq.ParquetFile(path).metadata
    for row_group in range(md.num_row_groups):
        cc = md.row_group(row_group).column(1)
        with open(path, "rb") as f:
            chunk = _ChunkSource(
                f,
                first_page_offset(md, row_group, 1),
                cc.total_compressed_size,
                coalesce_threshold=(2**40 if coalesce else 0),
            )
            pages = list(_walk_pages(chunk))
        walked = sum(p.data_offset - p.header_offset + p.compressed_size for p in pages)
        assert walked == cc.total_compressed_size
        data_rows = sum(p.num_values for p in pages if p.page_type == _PAGE_TYPE_DATA)
        assert data_rows == md.row_group(row_group).num_rows


def test_walk_dictionary_layout_is_dict_plus_data(tmp_path: Path) -> None:
    path = str(tmp_path / "dictionary.parquet")
    write_content_file(path, sample_values())
    pages = walk_column_pages(path, 0, 1)
    assert [p.page_type for p in pages] == [_PAGE_TYPE_DICTIONARY, _PAGE_TYPE_DATA]


def test_walk_batch1_layout_splits_pages(tmp_path: Path) -> None:
    path = str(tmp_path / "batch1.parquet")
    # two values that each cross the 1MiB data_page_size must land in
    # separate pages under write_batch_size=1 (the flush check runs per
    # value); the trailing small rows coalesce into a final page.
    values: list[str | None] = ["x" * 2_000_000, "y" * 2_000_000, "small", None]
    write_content_file(path, values, use_dictionary=False, write_batch_size=1)
    pages = walk_column_pages(path, 0, 1)
    assert all(p.page_type == _PAGE_TYPE_DATA for p in pages)
    assert len(pages) >= 2
    assert sum(p.num_values for p in pages) == 4


@pytest.mark.parametrize(
    ("data", "bit_width", "count", "expected"),
    [
        # RLE run: header = count << 1, then a ceil(bit_width/8)-byte value
        (b"\x32\x01", 1, 25, [1] * 25),
        (b"\x08\x02", 2, 4, [2, 2, 2, 2]),
        # bit width 0 (single dictionary entry): no bytes at all
        (b"", 0, 3, [0, 0, 0]),
        # bit-packed: header = (groups << 1) | 1; one group of 8, byte 0x55
        (b"\x03\x55", 1, 8, [1, 0, 1, 0, 1, 0, 1, 0]),
        # run of 3 zeros then the bit-packed group, truncated to count
        (b"\x06\x00\x03\x55", 1, 11, [0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0]),
        # multi-byte varint header: run of 100 -> header 200 -> b"\xc8\x01"
        (b"\xc8\x01\x01", 1, 100, [1] * 100),
        # corrupt run length (2**30) is capped to count rather than
        # materializing 2**30 elements before truncating
        (b"\x80\x80\x80\x80\x08\x09", 8, 5, [9] * 5),
    ],
    ids=[
        "rle-run-bw1",
        "rle-run-bw2",
        "bit-width-0",
        "bit-packed",
        "mixed-runs",
        "multibyte-varint-header",
        "corrupt-run-capped",
    ],
)
def test_rle_hybrid_decodes(
    data: bytes, bit_width: int, count: int, expected: list[int]
) -> None:
    assert _decode_rle_hybrid(data, bit_width, count) == expected


@pytest.mark.parametrize(
    ("data", "bit_width"),
    [(b"\x08", 2), (b"\x03", 1)],
    ids=["run-value-missing", "group-bytes-missing"],
)
def test_rle_truncated_payload_raises(data: bytes, bit_width: int) -> None:
    with pytest.raises(PageReaderUnsupportedError, match="truncated"):
        _decode_rle_hybrid(data, bit_width, 8)


def test_rle_short_data_raises_rather_than_returning_short() -> None:
    """Data that runs out before `count` values must not silently return short."""
    with pytest.raises(PageReaderUnsupportedError, match="RLE data ended"):
        _decode_rle_hybrid(b"\x06\x01", 1, 10)  # a run of 3, 10 requested


def test_stream_cursor_reads_across_chunks() -> None:
    cursor = _StreamCursor(iter([b"ab", b"", b"cdef", b"g"]))
    assert cursor.read(3) == b"abc"
    cursor.skip(2)
    assert cursor.bytes_read == 5
    assert b"".join(cursor.iter_read(2, chunk_size=1)) == b"fg"
    with pytest.raises(PageReaderUnsupportedError, match="end of page"):
        cursor.read(1)


def test_decompressed_stream_zstd_roundtrip() -> None:
    payload = ("héllo→世界😀" * 10_000).encode("utf-8")
    frame = zstandard.ZstdCompressor().compress(payload)
    pieces = [frame[i : i + 100] for i in range(0, len(frame), 100)]
    assert b"".join(_decompressed_stream(iter(pieces), "ZSTD")) == payload
    assert b"".join(_decompressed_stream(iter([payload]), "UNCOMPRESSED")) == payload


def test_decompressed_stream_output_is_bounded() -> None:
    """One tiny compressed piece must not decompress into one huge chunk."""
    payload = b"x" * (32 * 1024 * 1024)
    frame = zstandard.ZstdCompressor().compress(payload)
    assert len(frame) < 64 * 1024  # the whole frame arrives as one piece
    sizes = [len(piece) for piece in _decompressed_stream(iter([frame]), "ZSTD")]
    assert max(sizes) <= DEFAULT_STREAM_CHUNK_SIZE
    assert sum(sizes) == len(payload)


def test_read_def_levels() -> None:
    # 4-byte length prefix + RLE run of 25 ones
    cursor = _StreamCursor(iter([b"\x02\x00\x00\x00\x32\x01"]))
    assert _read_def_levels(cursor, 25, 1) == [1] * 25
    assert cursor.bytes_read == 6
    # required column (max_def_level 0): nothing consumed, all defined
    cursor2 = _StreamCursor(iter([b""]))
    assert _read_def_levels(cursor2, 3, 0) == [1, 1, 1]
    assert cursor2.bytes_read == 0


PLAIN_LAYOUTS: dict[str, dict[str, Any]] = {
    "plain_batch1": {"use_dictionary": False, "write_batch_size": 1},
    "plain_single_page": {"use_dictionary": False},
    "uncompressed": {"use_dictionary": False, "compression": "NONE"},
}

ALL_LAYOUTS: dict[str, dict[str, Any]] = {
    **PLAIN_LAYOUTS,
    # one dictionary page holds every distinct value for the row group
    "dict_single_page": {"use_dictionary": True},
    # dictionary overflow fallback: dict page + RLE_DICTIONARY + PLAIN pages
    "mixed_dict_plain": {"use_dictionary": True, "write_batch_size": 1},
}


def assert_reader_matches_source(
    path: str,
    values: list[str | None],
    *,
    coalesce_threshold: int | None = None,
) -> None:
    kwargs: dict[str, int] = (
        {} if coalesce_threshold is None else {"coalesce_threshold": coalesce_threshold}
    )
    with ParquetContentReader(path, **kwargs) as reader:
        assert reader.column_names() == {"transcript_id", "events"}
        for i, expected in enumerate(values):
            location = reader.locate(f"tr_{i:04d}")
            assert location is not None, f"row {i} not located"
            cell = reader.stream_cell(location, "events")
            if expected is None:
                assert cell is None, f"row {i} should be NULL"
            else:
                assert cell is not None, f"row {i} should not be NULL"
                assert b"".join(cell) == expected.encode("utf-8"), f"row {i}"
            expected_size = 0 if expected is None else len(expected.encode("utf-8"))
            assert reader.cell_size(location, "events") == expected_size, f"row {i}"


@pytest.mark.parametrize("layout", sorted(ALL_LAYOUTS))
def test_all_layouts_match_source(tmp_path: Path, layout: str) -> None:
    path = str(tmp_path / f"{layout}.parquet")
    values = sample_values()
    write_content_file(path, values, **ALL_LAYOUTS[layout])
    assert_reader_matches_source(path, values)


def test_locate_maps_row_groups(tmp_path: Path) -> None:
    path = str(tmp_path / "locate.parquet")
    write_content_file(path, sample_values(), use_dictionary=False)
    with ParquetContentReader(path) as reader:
        # 9 rows at row_group_size=4 -> groups of 4, 4, 1
        assert reader.locate("tr_0000") == CellLocation(0, 0)
        assert reader.locate("tr_0005") == CellLocation(1, 1)
        assert reader.locate("tr_0008") == CellLocation(2, 0)
        assert reader.locate("no-such-id") is None


def test_absent_column_raises_value_error(tmp_path: Path) -> None:
    path = str(tmp_path / "absent.parquet")
    write_content_file(path, sample_values(), use_dictionary=False)
    with ParquetContentReader(path) as reader:
        location = reader.locate("tr_0000")
        assert location is not None
        with pytest.raises(ValueError, match="messages"):
            reader.stream_cell(location, "messages")


def test_init_failure_closes_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = str(tmp_path / "garbage.parquet")
    Path(path).write_bytes(b"not a parquet file")
    opened: list[Any] = []
    original_open = builtins.open

    def tracking_open(*args: Any, **kwargs: Any) -> Any:
        handle = original_open(*args, **kwargs)
        if args and args[0] == path:
            opened.append(handle)
        return handle

    monkeypatch.setattr(builtins, "open", tracking_open)
    with pytest.raises(Exception):  # noqa: B017
        ParquetContentReader(path)
    assert opened, "raw handle was never opened"
    assert all(handle.closed for handle in opened)


def test_duplicate_cells_share_dictionary_entry(tmp_path: Path) -> None:
    """Legacy dict pages hold DISTINCT values; rows may share an entry."""
    path = str(tmp_path / "dup.parquet")
    values: list[str | None] = ["[]", '{"a":1}', "[]", None, "[]", '{"a":1}']
    write_content_file(path, values)
    # confirm the fixture really deduplicates: dict page has 2 entries
    pages = walk_column_pages(path, 0, 1)
    assert pages[0].page_type == _PAGE_TYPE_DICTIONARY
    assert pages[0].num_values == 2
    assert_reader_matches_source(path, values)


@pytest.mark.parametrize(
    "write_kwargs,match",
    [
        ({"compression": "snappy", "use_dictionary": False}, "codec SNAPPY"),
        ({"compression": "gzip", "use_dictionary": False}, "codec GZIP"),
        (
            {"data_page_version": "2.0", "use_dictionary": False},
            "page type",
        ),
    ],
    ids=["snappy", "gzip", "data-page-v2"],
)
def test_unsupported_shapes_raise(
    tmp_path: Path, write_kwargs: dict[str, Any], match: str
) -> None:
    path = str(tmp_path / "unsupported.parquet")
    write_content_file(path, sample_values(), **write_kwargs)
    with ParquetContentReader(path) as reader:
        location = reader.locate("tr_0000")
        assert location is not None
        with pytest.raises(PageReaderUnsupportedError, match=match):
            reader.stream_cell(location, "events")
        with pytest.raises(PageReaderUnsupportedError, match=match):
            reader.cell_size(location, "events")


def test_memory_filesystem_matches_source() -> None:
    url = UPath("memory://page-reader-tests/data.parquet")
    values = sample_values()
    table = build_content_table(values)
    with url.fs.open(str(url), "wb") as f:
        pq.write_table(
            table,
            f,
            compression="zstd",
            use_dictionary=False,
            write_batch_size=1,
            row_group_size=4,
            write_statistics=True,
        )
    assert_reader_matches_source(str(url), values)
    # coalesce_threshold=0 forces per-page ranged reads (rather than one
    # whole-chunk read) through a non-POSIX (fsspec) filesystem.
    assert_reader_matches_source(str(url), values, coalesce_threshold=0)


def test_reader_opens_only_its_own_path(monkeypatch: pytest.MonkeyPatch) -> None:
    target = UPath("memory://page-reader-spy/target.parquet")
    other = UPath("memory://page-reader-spy/other.parquet")
    for url in (target, other):
        with url.fs.open(str(url), "wb") as f:
            pq.write_table(
                build_content_table(sample_values()),
                f,
                compression="zstd",
                use_dictionary=False,
                write_batch_size=1,
                row_group_size=4,
                write_statistics=True,
            )

    opened: list[str] = []
    original_open = MemoryFileSystem._open

    def spy(self: MemoryFileSystem, path: str, *args: Any, **kwargs: Any) -> Any:
        opened.append(path)
        return original_open(self, path, *args, **kwargs)

    monkeypatch.setattr(MemoryFileSystem, "_open", spy)
    with ParquetContentReader(str(target)) as reader:
        location = reader.locate("tr_0000")
        assert location is not None
        cell = reader.stream_cell(location, "events")
        assert cell is not None
        b"".join(cell)
    expected = MemoryFileSystem._strip_protocol(str(target))
    assert set(opened) == {expected}


@pytest.mark.parametrize(
    "coalesce_threshold", [0, 2**40], ids=["ranged", "whole-chunk"]
)
def test_read_before_chunk_start_raises(
    tmp_path: Path, coalesce_threshold: int
) -> None:
    """Reads below the chunk start are illegal in both coalesce modes."""
    path = str(tmp_path / "before.parquet")
    Path(path).write_bytes(b"0123456789")
    with open(path, "rb") as f:
        chunk = _ChunkSource(f, 4, 6, coalesce_threshold=coalesce_threshold)
        assert chunk.read_at(4, 2) == b"45"
        with pytest.raises(PageReaderUnsupportedError, match="before chunk start"):
            chunk.read_at(2, 2)


def test_second_open_reuses_cached_metadata(tmp_path: Path) -> None:
    """A reader built from a cached footer must decode identically."""
    path = str(tmp_path / "reopen.parquet")
    values = sample_values()
    write_content_file(path, values, use_dictionary=False, write_batch_size=1)
    with ParquetContentReader(path) as first:
        names = first.column_names()
    assert path in page_reader._metadata_cache, "first open did not cache the footer"
    # every subsequent open now constructs from the cached footer
    with ParquetContentReader(path) as second:
        assert second.column_names() == names
    assert_reader_matches_source(path, values)


def test_metadata_cache_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(page_reader, "_LOCATION_CACHE_MAX_FILES", 2)
    paths: list[str] = []
    for i in range(3):
        path = str(tmp_path / f"cap{i}.parquet")
        write_content_file(path, sample_values(), use_dictionary=False)
        paths.append(path)
        ParquetContentReader(path).close()
    assert len(page_reader._metadata_cache) == 2
    assert list(page_reader._metadata_cache) == paths[1:]  # oldest evicted first


def test_coalescing_modes_agree(tmp_path: Path) -> None:
    path = str(tmp_path / "coalesce.parquet")
    values = sample_values()
    write_content_file(path, values, use_dictionary=False, write_batch_size=1)
    assert_reader_matches_source(path, values, coalesce_threshold=0)
    assert_reader_matches_source(path, values, coalesce_threshold=2**40)
