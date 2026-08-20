"""Tests for the parquet page reader."""

import builtins
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._transcript.database.parquet.page_reader import (
    _PAGE_TYPE_DATA,
    _PAGE_TYPE_DICTIONARY,
    PageReaderUnsupported,
    _parse_page_header,
)


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


def test_parse_dictionary_page_header(tmp_path: Path) -> None:
    path = str(tmp_path / "dict.parquet")
    write_content_file(path, sample_values())
    md = pq.ParquetFile(path).metadata
    offset = first_page_offset(md, 0, 1)
    with open(path, "rb") as f:
        f.seek(offset)
        buf = f.read(8 * 1024)
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
    md = pq.ParquetFile(path).metadata
    offset = first_page_offset(md, 0, 1)
    with open(path, "rb") as f:
        f.seek(offset)
        buf = f.read(8 * 1024)
    page = _parse_page_header(buf, offset)
    assert page.page_type == _PAGE_TYPE_DATA
    # a 4-row group with dictionary off = one PLAIN page holding all rows
    assert page.num_values == 4


def test_parse_v2_page_header_unsupported(tmp_path: Path) -> None:
    path = str(tmp_path / "v2.parquet")
    write_content_file(
        path, sample_values(), use_dictionary=False, data_page_version="2.0"
    )
    md = pq.ParquetFile(path).metadata
    offset = first_page_offset(md, 0, 1)
    with open(path, "rb") as f:
        f.seek(offset)
        buf = f.read(8 * 1024)
    with pytest.raises(PageReaderUnsupported, match="page type"):
        _parse_page_header(buf, offset)


def test_truncated_header_raises_index_error(tmp_path: Path) -> None:
    path = str(tmp_path / "trunc.parquet")
    write_content_file(path, sample_values())
    md = pq.ParquetFile(path).metadata
    offset = first_page_offset(md, 0, 1)
    with open(path, "rb") as f:
        f.seek(offset)
        buf = f.read(3)  # far too short for any header
    with pytest.raises(IndexError):
        _parse_page_header(buf, offset)


def walk_column_pages(path: str, row_group: int, column: int) -> list[Any]:
    from inspect_scout._transcript.database.parquet.page_reader import (
        _ChunkSource,
        _walk_pages,
    )

    md = pq.ParquetFile(path).metadata
    cc = md.row_group(row_group).column(column)
    with open(path, "rb") as f:
        chunk = _ChunkSource(
            f, first_page_offset(md, row_group, column), cc.total_compressed_size
        )
        return list(_walk_pages(chunk))


@pytest.mark.parametrize("coalesce", [True, False], ids=["whole-chunk", "ranged"])
def test_walk_accounts_for_full_chunk(tmp_path: Path, coalesce: bool) -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        _ChunkSource,
        _walk_pages,
    )

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


def test_walk_legacy_layout_is_dict_plus_data(tmp_path: Path) -> None:
    path = str(tmp_path / "legacy.parquet")
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


def test_rle_run_decodes() -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        _decode_rle_hybrid,
    )

    # RLE run: header = count << 1; 25 values of 1 at bit width 1
    assert _decode_rle_hybrid(b"\x32\x01", 1, 25) == [1] * 25
    # bit width 2, run of 4 values of 2
    assert _decode_rle_hybrid(b"\x08\x02", 2, 4) == [2, 2, 2, 2]
    # bit width 0 (single dictionary entry): no bytes at all
    assert _decode_rle_hybrid(b"", 0, 3) == [0, 0, 0]


def test_rle_bitpacked_decodes() -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        _decode_rle_hybrid,
    )

    # bit-packed: header = (groups << 1) | 1; one group of 8, byte 0x55
    assert _decode_rle_hybrid(b"\x03\x55", 1, 8) == [1, 0, 1, 0, 1, 0, 1, 0]
    # mixed: run of 3 zeros then the bit-packed group, truncated to count
    assert _decode_rle_hybrid(b"\x06\x00\x03\x55", 1, 11) == [
        0,
        0,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
    ]


def test_stream_cursor_reads_across_chunks() -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        PageReaderUnsupported,
        _StreamCursor,
    )

    cursor = _StreamCursor(iter([b"ab", b"", b"cdef", b"g"]))
    assert cursor.read(3) == b"abc"
    cursor.skip(2)
    assert cursor.bytes_read == 5
    assert b"".join(cursor.iter_read(2, chunk_size=1)) == b"fg"
    with pytest.raises(PageReaderUnsupported, match="end of page"):
        cursor.read(1)


def test_decompressed_stream_zstd_roundtrip() -> None:
    import zstandard
    from inspect_scout._transcript.database.parquet.page_reader import (
        _decompressed_stream,
    )

    payload = ("héllo→世界😀" * 10_000).encode("utf-8")
    frame = zstandard.ZstdCompressor().compress(payload)
    pieces = [frame[i : i + 100] for i in range(0, len(frame), 100)]
    assert b"".join(_decompressed_stream(iter(pieces), "ZSTD")) == payload
    assert b"".join(_decompressed_stream(iter([payload]), "UNCOMPRESSED")) == payload


def test_read_def_levels() -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        _read_def_levels,
        _StreamCursor,
    )

    # 4-byte length prefix + RLE run of 25 ones (the Task-1 test vector)
    cursor = _StreamCursor(iter([b"\x02\x00\x00\x00\x32\x01"]))
    assert _read_def_levels(cursor, 25, 1) == [1] * 25
    assert cursor.bytes_read == 6
    # required column (max_def_level 0): nothing consumed, all defined
    cursor2 = _StreamCursor(iter([b""]))
    assert _read_def_levels(cursor2, 3, 0) == [1, 1, 1]
    assert cursor2.bytes_read == 0


def test_rle_multibyte_header_and_truncation() -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        PageReaderUnsupported,
        _decode_rle_hybrid,
    )

    # multi-byte varint header: run of 100 -> header 200 -> varint b"\xc8\x01"
    assert _decode_rle_hybrid(b"\xc8\x01\x01", 1, 100) == [1] * 100
    # RLE header present but run value byte missing
    with pytest.raises(PageReaderUnsupported, match="truncated"):
        _decode_rle_hybrid(b"\x08", 2, 4)
    # bit-packed header present but group bytes missing
    with pytest.raises(PageReaderUnsupported, match="truncated"):
        _decode_rle_hybrid(b"\x03", 1, 8)


def test_rle_run_capped_to_remaining_count() -> None:
    """A corrupt/adversarial run length must not balloon the allocation.

    header = (run << 1); run = 2**30 -> header = 2**31, varint-encoded below
    as a 5-byte little-endian-group varint. With bit_width=8, one value byte
    follows. Decoding with a small count must return exactly [value] * count
    rather than materializing 2**30 elements before truncating.
    """
    from inspect_scout._transcript.database.parquet.page_reader import (
        _decode_rle_hybrid,
    )

    payload = b"\x80\x80\x80\x80\x08" + b"\x09"
    assert _decode_rle_hybrid(payload, 8, 5) == [9] * 5


PLAIN_LAYOUTS: dict[str, dict[str, Any]] = {
    "plain_batch1": {"use_dictionary": False, "write_batch_size": 1},
    "plain_single_page": {"use_dictionary": False},
    "uncompressed": {"use_dictionary": False, "compression": "NONE"},
}


def assert_reader_matches_source(
    path: str,
    values: list[str | None],
    *,
    coalesce_threshold: int | None = None,
) -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        ParquetContentReader,
    )

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


@pytest.mark.parametrize("layout", sorted(PLAIN_LAYOUTS))
def test_plain_cells_match_source(tmp_path: Path, layout: str) -> None:
    path = str(tmp_path / f"{layout}.parquet")
    values = sample_values()
    write_content_file(path, values, **PLAIN_LAYOUTS[layout])
    assert_reader_matches_source(path, values)


def test_locate_maps_row_groups(tmp_path: Path) -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        CellLocation,
        ParquetContentReader,
    )

    path = str(tmp_path / "locate.parquet")
    write_content_file(path, sample_values(), use_dictionary=False)
    with ParquetContentReader(path) as reader:
        # 9 rows at row_group_size=4 -> groups of 4, 4, 1
        assert reader.locate("tr_0000") == CellLocation(0, 0)
        assert reader.locate("tr_0005") == CellLocation(1, 1)
        assert reader.locate("tr_0008") == CellLocation(2, 0)
        assert reader.locate("no-such-id") is None


def test_absent_column_raises_value_error(tmp_path: Path) -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        ParquetContentReader,
    )

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
    from inspect_scout._transcript.database.parquet.page_reader import (
        ParquetContentReader,
    )

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


ALL_LAYOUTS: dict[str, dict[str, Any]] = {
    **PLAIN_LAYOUTS,
    # today's writer flags: one dictionary page holds every value
    "legacy_dict": {"use_dictionary": True},
    # dictionary overflow fallback: dict page + RLE_DICTIONARY + PLAIN pages
    "mixed_dict_plain": {"use_dictionary": True, "write_batch_size": 1},
}


@pytest.mark.parametrize("layout", sorted(ALL_LAYOUTS))
def test_all_layouts_match_source(tmp_path: Path, layout: str) -> None:
    path = str(tmp_path / f"{layout}.parquet")
    values = sample_values()
    write_content_file(path, values, **ALL_LAYOUTS[layout])
    assert_reader_matches_source(path, values)


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
    from inspect_scout._transcript.database.parquet.page_reader import (
        PageReaderUnsupported,
        ParquetContentReader,
    )

    path = str(tmp_path / "unsupported.parquet")
    write_content_file(path, sample_values(), **write_kwargs)
    with ParquetContentReader(path) as reader:
        location = reader.locate("tr_0000")
        assert location is not None
        with pytest.raises(PageReaderUnsupported, match=match):
            reader.stream_cell(location, "events")
        with pytest.raises(PageReaderUnsupported, match=match):
            reader.cell_size(location, "events")


def test_memory_filesystem_matches_source() -> None:
    from upath import UPath

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
    from fsspec.implementations.memory import (  # type: ignore[import-untyped]
        MemoryFileSystem,
    )
    from inspect_scout._transcript.database.parquet.page_reader import (
        ParquetContentReader,
    )
    from upath import UPath

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


def test_coalescing_modes_agree(tmp_path: Path) -> None:
    from inspect_scout._transcript.database.parquet.page_reader import (
        ParquetContentReader,
    )

    path = str(tmp_path / "coalesce.parquet")
    values = sample_values()
    write_content_file(path, values, use_dictionary=False, write_batch_size=1)
    for threshold in (0, 2**40):
        with ParquetContentReader(path, coalesce_threshold=threshold) as reader:
            for i, expected in enumerate(values):
                location = reader.locate(f"tr_{i:04d}")
                assert location is not None
                cell = reader.stream_cell(location, "events")
                got = None if cell is None else b"".join(cell)
                want = None if expected is None else expected.encode("utf-8")
                assert got == want, f"threshold={threshold} row={i}"
