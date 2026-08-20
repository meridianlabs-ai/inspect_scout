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
