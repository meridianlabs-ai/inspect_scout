"""Tests for the parquet page reader."""

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
    write_content_file(path, sample_values(), use_dictionary=False, write_batch_size=1)
    # row group 0 holds rows 0-3 incl. the 2MB cell: > 1 data page, no dict
    pages = walk_column_pages(path, 0, 1)
    assert all(p.page_type == _PAGE_TYPE_DATA for p in pages)
    assert len(pages) >= 2
