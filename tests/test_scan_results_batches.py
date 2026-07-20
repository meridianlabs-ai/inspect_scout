"""Tests for scan_results_batches and streaming parquet reads."""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any

import pandas as pd
import pyarrow.fs as pafs
import pyarrow.parquet as pq
import pytest
from fsspec.implementations.local import LocalFileSystem  # type: ignore[import-untyped]
from inspect_scout import (
    Result,
    Scanner,
    scan,
    scan_results_arrow,
    scan_results_batches,
    scan_results_batches_async,
    scan_results_df,
    scanner,
)
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

# Test data locations
LOGS_DIR = Path(__file__).parent.parent / "examples" / "scanner" / "logs"
FIXTURE_SCAN = (
    Path(__file__).parent / "recorder" / "scans" / "scan_id=JzvEPBFB4aVpCU93FFbiFT"
)


@scanner(name="resultset_scanner", messages="all")
def resultset_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns a resultset (expands across batch boundaries)."""

    async def scan_transcript(transcript: Transcript) -> list[Result]:
        return [
            Result(label="deception", value=True, explanation="one"),
            Result(label="deception", value=False, explanation="two"),
            Result(label="misconfiguration", value="high", answer="HIGH"),
        ]

    return scan_transcript


@scanner(name="bool_scanner", messages="all")
def bool_scanner_factory() -> Scanner[Transcript]:
    """Scanner with uniform boolean value_type (casting applied)."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=len(transcript.messages) > 2)

    return scan_transcript


@scanner(name="mixed_scanner", messages="all")
def mixed_scanner_factory() -> Scanner[Transcript]:
    """Scanner with mixed value_type across transcripts (no casting)."""
    calls: list[int] = []

    async def scan_transcript(transcript: Transcript) -> Result:
        calls.append(1)
        if len(calls) % 2 == 1:
            return Result(value=True)
        else:
            return Result(value="a string")

    return scan_transcript


@pytest.fixture(scope="module")
def scan_location() -> Iterator[str]:
    """Run a single scan with all test scanners over two transcripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[
                resultset_scanner_factory(),
                bool_scanner_factory(),
                mixed_scanner_factory(),
            ],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=2,
            max_processes=1,
        )
        yield status.location


def assert_batches_match_df(
    scan_location: str,
    scanner_name: str,
    *,
    rows: str = "results",
    exclude_columns: list[str] | None = None,
    batch_size: int = 1,
) -> list[pd.DataFrame]:
    """Assert concatenated batches equal the scan_results_df DataFrame."""
    expected = scan_results_df(
        scan_location,
        scanner=scanner_name,
        rows=rows,  # type: ignore[arg-type]
        exclude_columns=exclude_columns,
    ).scanners[scanner_name]
    batches = list(
        scan_results_batches(
            scan_location,
            scanner_name,
            batch_size=batch_size,
            rows=rows,  # type: ignore[arg-type]
            exclude_columns=exclude_columns,
        )
    )
    assert len(batches) > 1, "expected multiple batches"
    actual = pd.concat(batches, ignore_index=True)
    assert set(actual.columns) == set(expected.columns)
    pd.testing.assert_frame_equal(
        expected.reset_index(drop=True),
        actual[list(expected.columns)],
        check_dtype=True,
    )
    return batches


def test_parity_uniform_number_fixture() -> None:
    """Uniform value_type 'number' fixture: numeric cast matches, incl. dtypes."""
    location = FIXTURE_SCAN.as_posix()
    expected = scan_results_df(location, scanner="word_counter").scanners[
        "word_counter"
    ]
    batches = list(scan_results_batches(location, "word_counter", batch_size=1))
    assert len(batches) == len(expected)
    actual = pd.concat(batches, ignore_index=True)
    pd.testing.assert_frame_equal(
        expected.reset_index(drop=True), actual[list(expected.columns)]
    )
    # numeric cast applied (values are ints, not strings)
    assert pd.api.types.is_numeric_dtype(actual["value"].dtype)


def test_parity_uniform_boolean(scan_location: str) -> None:
    batches = assert_batches_match_df(scan_location, "bool_scanner")
    for batch in batches:
        for value in batch["value"].tolist():
            assert isinstance(value, bool)


def test_parity_mixed_value_type(scan_location: str) -> None:
    batches = assert_batches_match_df(scan_location, "mixed_scanner")
    # mixed types: values stay as (string) parquet representation
    values = pd.concat(batches, ignore_index=True)["value"].tolist()
    assert set(values) == {"true", "a string"}


def test_parity_resultset_expansion(scan_location: str) -> None:
    batches = assert_batches_match_df(scan_location, "resultset_scanner")
    # each parquet row is a resultset that expands to 3 result rows
    assert all(len(batch) == 3 for batch in batches)
    total = sum(len(batch) for batch in batches)
    assert total == 6


def test_parity_rows_transcripts(scan_location: str) -> None:
    batches = assert_batches_match_df(
        scan_location, "resultset_scanner", rows="transcripts"
    )
    # no expansion: one row per transcript
    assert sum(len(batch) for batch in batches) == 2


def test_exclude_columns(scan_location: str) -> None:
    batches = assert_batches_match_df(
        scan_location,
        "bool_scanner",
        exclude_columns=["scan_events", "eval_metadata"],
    )
    for batch in batches:
        assert "scan_events" not in batch.columns
        assert "eval_metadata" not in batch.columns


@pytest.mark.asyncio
async def test_scan_results_batches_async(scan_location: str) -> None:
    expected = scan_results_df(scan_location, scanner="bool_scanner").scanners[
        "bool_scanner"
    ]
    batches = [
        batch
        async for batch in scan_results_batches_async(
            scan_location, "bool_scanner", batch_size=1
        )
    ]
    assert len(batches) > 1
    actual = pd.concat(batches, ignore_index=True)
    pd.testing.assert_frame_equal(
        expected.reset_index(drop=True),
        actual[list(expected.columns)],
        check_dtype=True,
    )


class _CountingFile:
    """File wrapper that counts bytes read."""

    def __init__(self, f: IO[bytes], counter: dict[str, int]) -> None:
        self._f = f
        self._counter = counter

    def read(self, nbytes: int = -1) -> bytes:
        data = self._f.read(nbytes)
        self._counter["bytes_read"] += len(data)
        return data

    def __getattr__(self, name: str) -> Any:
        return getattr(self._f, name)


class _CountingLocalFileSystem(LocalFileSystem):  # type: ignore[misc]
    """fsspec local filesystem that counts bytes read from opened files."""

    def __init__(self, counter: dict[str, int], **kwargs: Any) -> None:
        super().__init__(skip_instance_cache=True, **kwargs)
        self.counter = counter

    def _open(self, path: str, mode: str = "rb", **kwargs: Any) -> Any:
        return _CountingFile(super()._open(path, mode=mode, **kwargs), self.counter)


def test_arrow_reader_streams_remote_filesystem(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """reader() on a remote-style filesystem must not read the file eagerly."""
    # copy the fixture scan, rewriting the parquet with many small row groups
    scan_dir = tmp_path / "scan_id=JzvEPBFB4aVpCU93FFbiFT"
    shutil.copytree(FIXTURE_SCAN, scan_dir)
    parquet_path = scan_dir / "word_counter.parquet"
    table = pq.ParquetFile(parquet_path).read()
    pq.write_table(table, parquet_path, row_group_size=2)
    file_size = parquet_path.stat().st_size

    # remote-style filesystem that counts bytes read
    counter = {"bytes_read": 0}
    counting_fs = pafs.PyFileSystem(
        # concrete at runtime; pyarrow stubs mark inherited methods abstract
        pafs.FSSpecHandler(_CountingLocalFileSystem(counter))  # type: ignore[abstract]
    )

    import inspect_scout._recorder.file as scout_file

    def resolve(scanner_path: Any) -> Any:
        return str(scanner_path), counting_fs

    monkeypatch.setattr(scout_file, "_resolve_parquet_source", resolve)

    results = scan_results_arrow(scan_dir.as_posix())
    reader = results.reader("word_counter", streaming_batch_size=2)

    # reading the first batch should not have read the whole file (the
    # reader does prefetch a bounded number of row groups ahead, so this
    # is a coarse bound rather than a single-row-group bound)
    first = next(iter(reader))
    assert len(first) == 2
    bytes_after_first = counter["bytes_read"]
    assert bytes_after_first < file_size

    # consuming the rest reads more data (i.e. reads were lazy)
    total_rows = len(first) + sum(len(b) for b in reader)
    assert total_rows == len(table)
    assert counter["bytes_read"] > bytes_after_first
