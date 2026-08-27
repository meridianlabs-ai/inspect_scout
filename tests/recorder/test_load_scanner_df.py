"""Tests for column projection when loading scanner result DataFrames.

_load_scanner_df projects `exclude_columns` at the parquet source (so excluded
columns are never read/downloaded). These tests pin that the projection is
behavior-preserving relative to a full read, both for local paths and for
remote protocols that _parquet_source downloads via fsspec.
"""

import io
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest
from inspect_scout._recorder.file import _load_scanner_df, _parquet_source
from inspect_scout._recorder.recorder import HEAVY_COLUMNS
from inspect_scout._scanresults import scan_results_df
from upath import UPath

SCAN_DIR = Path(__file__).parent / "scans" / "scan_id=JzvEPBFB4aVpCU93FFbiFT"
SCANNERS = ["message_length", "word_counter"]
EXCLUDED = ["explanation", "scan_events"]


@pytest.fixture
def memory_scan_dir() -> Iterator[UPath]:
    """Fixture scan's parquet files copied to an fsspec memory filesystem."""
    mem_dir = UPath("memory://load_scanner_df_test")
    for parquet in sorted(SCAN_DIR.glob("*.parquet")):
        (mem_dir / parquet.name).write_bytes(parquet.read_bytes())
    yield mem_dir
    mem_dir.rmdir(recursive=True)


@pytest.mark.parametrize("scanner_name", SCANNERS)
def test_exclude_columns_matches_full_read(scanner_name: str) -> None:
    """Excluding columns drops them and leaves all other data unchanged."""
    scan_dir = UPath(SCAN_DIR.as_posix())
    full = _load_scanner_df(scan_dir, scanner_name, exclude_columns=[])
    excluded = _load_scanner_df(scan_dir, scanner_name, exclude_columns=EXCLUDED)

    assert len(full) > 0
    assert list(excluded.columns) == [c for c in full.columns if c not in EXCLUDED]
    pd.testing.assert_frame_equal(excluded, full[excluded.columns])


@pytest.mark.parametrize(
    "exclude_columns",
    [[], ["not_a_column"]],
    ids=["empty", "nonexistent"],
)
def test_exclude_columns_noop_variants(exclude_columns: list[str]) -> None:
    """Empty and non-existent exclusions both yield the full read."""
    scan_dir = UPath(SCAN_DIR.as_posix())
    full = _load_scanner_df(scan_dir, "word_counter", exclude_columns=[])
    df = _load_scanner_df(scan_dir, "word_counter", exclude_columns=exclude_columns)
    pd.testing.assert_frame_equal(df, full)


def test_value_cast_applied_after_exclusion() -> None:
    """The value column is still cast per value_type when other columns are excluded."""
    scan_dir = UPath(SCAN_DIR.as_posix())
    df = _load_scanner_df(scan_dir, "word_counter", exclude_columns=EXCLUDED)
    assert pd.api.types.is_numeric_dtype(df["value"])


def test_value_cast_skipped_when_value_type_excluded() -> None:
    """Excluding value_type leaves value as the raw strings stored in parquet."""
    scan_dir = UPath(SCAN_DIR.as_posix())
    with pq.ParquetFile(str(SCAN_DIR / "word_counter.parquet")) as parquet_file:
        raw = parquet_file.read(columns=["value"])
    df = _load_scanner_df(scan_dir, "word_counter", exclude_columns=["value_type"])
    assert "value_type" not in df.columns
    assert df["value"].tolist() == raw.column("value").to_pylist()


@pytest.mark.parametrize("scanner_name", SCANNERS)
def test_scan_results_df_exclude_columns(scanner_name: str) -> None:
    """exclude_columns via the public scan_results_df API matches a full read."""
    location = SCAN_DIR.as_posix()
    full = scan_results_df(location, scanner=scanner_name, exclude_columns=[]).scanners[
        scanner_name
    ]
    results = scan_results_df(location, scanner=scanner_name, exclude_columns=EXCLUDED)
    df = results.scanners[scanner_name]

    assert len(full) > 0
    assert list(df.columns) == [c for c in full.columns if c not in EXCLUDED]
    pd.testing.assert_frame_equal(df, full[df.columns])


@pytest.mark.parametrize("scanner_name", SCANNERS)
def test_scan_results_df_default_excludes_heavy_columns(scanner_name: str) -> None:
    """Default (None) excludes heavy columns; [] includes everything."""
    location = SCAN_DIR.as_posix()
    full = scan_results_df(location, scanner=scanner_name, exclude_columns=[]).scanners[
        scanner_name
    ]
    default = scan_results_df(location, scanner=scanner_name).scanners[scanner_name]

    assert len(default) > 0
    # input_data is dropped from the full read too (by event expansion)
    assert list(default.columns) == [c for c in full.columns if c not in HEAVY_COLUMNS]
    pd.testing.assert_frame_equal(default, full[default.columns])


def test_load_scanner_df_from_fsspec_only_protocol(memory_scan_dir: UPath) -> None:
    """Loading from a protocol without native pyarrow support matches a local read."""
    local = _load_scanner_df(
        UPath(SCAN_DIR.as_posix()), "word_counter", exclude_columns=EXCLUDED
    )
    remote = _load_scanner_df(memory_scan_dir, "word_counter", exclude_columns=EXCLUDED)
    pd.testing.assert_frame_equal(remote, local)


def test_parquet_source_local_path() -> None:
    """Local paths pass through as (path, None) for direct pyarrow reads."""
    parquet_path = SCAN_DIR / "word_counter.parquet"
    source, pa_fs = _parquet_source(UPath(parquet_path.as_posix()))
    assert source == parquet_path.as_posix()
    assert pa_fs is None


def test_parquet_source_fsspec_download(memory_scan_dir: UPath) -> None:
    """Protocols without native pyarrow support are downloaded to a buffer."""
    source, pa_fs = _parquet_source(memory_scan_dir / "word_counter.parquet")
    assert isinstance(source, io.BytesIO)
    assert pa_fs is None
    metadata = pq.read_metadata(str(SCAN_DIR / "word_counter.parquet"))
    assert pq.read_table(source).num_rows == metadata.num_rows
