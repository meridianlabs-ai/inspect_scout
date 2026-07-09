"""End-to-end tests for the `results_buffer` periodic-sync option.

`results_buffer=N` asks the scan to sync in-progress results to the final
scan location every N recorded results, so partial results are visible while
the scan is still running. These tests verify:

1. Partial results become visible at the scan location *before* the scan
   completes (the whole point of the feature).
2. Setting `results_buffer` does not change the final results.
3. Leaving it unset (the default) writes nothing to the scan location until
   completion.
"""

from pathlib import Path

import pandas as pd
import pytest
from inspect_scout import Result, Scanner, scan, scanner, transcripts_db
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout.aio import scan_async


def _make_transcript(index: int) -> Transcript:
    return Transcript(
        transcript_id=f"rb-{index:05d}",
        source_type="test",
        source_id="source-0",
        source_uri=f"test://uri/{index}",
        metadata={"index": index},
        messages=[],
        events=[],
    )


async def _insert_transcripts(db_path: Path, count: int) -> None:
    async with transcripts_db(str(db_path)) as db:
        await db.insert([_make_transcript(i) for i in range(count)])


@scanner(name="rb_probe_scanner", messages="all")
def _probe_scanner_factory(scan_location: str) -> Scanner[Transcript]:
    """Scanner that records how many rows are visible at the scan location.

    Each invocation reads the compacted parquet already written to the final
    scan location (if any) and stashes the row count in the result metadata,
    letting the test observe how partial results grow while the scan runs.
    """

    parquet = Path(scan_location) / "rb_probe_scanner.parquet"

    async def scan_transcript(transcript: Transcript) -> Result:
        if parquet.exists():
            visible = len(pd.read_parquet(parquet))
        else:
            visible = 0
        return Result(value=True, metadata={"visible_at_scan_location": visible})

    return scan_transcript


def test_results_buffer_syncs_partial_results(tmp_path: Path) -> None:
    """With results_buffer set, partial results appear at the scan location
    while the scan is still running."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 20

    import asyncio

    asyncio.run(_insert_transcripts(db_path, transcript_count))

    # scan_id is derived when the scan is created, so the concrete scan
    # directory isn't known up-front. Run the scan and then inspect the
    # metadata the probe recorded during execution.
    status = scan(
        scanners=[_probe_scanner_factory(str(scans_path))],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        results_buffer=5,
        display="none",
    )

    assert status.complete
    assert status.location is not None

    df = scan_results_df(status.location, scanner="rb_probe_scanner").scanners[
        "rb_probe_scanner"
    ]
    assert len(df) == transcript_count

    # The probe reads the scan-location parquet, which is only written by a
    # periodic sync. If periodic syncing works, at least one later invocation
    # must have observed partial results (> 0 rows) before the scan finished.
    visible_counts = [
        int(m["visible_at_scan_location"])
        for m in df["metadata"].apply(_load_metadata)
    ]
    assert max(visible_counts) > 0, (
        "expected partial results to be visible at the scan location mid-scan, "
        f"but saw counts {visible_counts}"
    )


def test_results_buffer_does_not_change_final_results(tmp_path: Path) -> None:
    """A scan with results_buffer set produces the same final results as one
    without it."""

    @scanner(name="rb_value_scanner", messages="all")
    def value_scanner_factory() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            return Result(value=transcript.metadata.get("index", 0))

        return scan_transcript

    transcript_count = 12

    import asyncio

    def run(results_buffer: int | None) -> pd.DataFrame:
        db_path = tmp_path / f"db_{results_buffer}"
        scans_path = tmp_path / f"scans_{results_buffer}"
        db_path.mkdir()
        scans_path.mkdir()
        asyncio.run(_insert_transcripts(db_path, transcript_count))
        status = scan(
            scanners=[value_scanner_factory()],
            transcripts=transcripts_from(str(db_path)),
            scans=str(scans_path),
            max_processes=1,
            results_buffer=results_buffer,
            display="none",
        )
        assert status.complete
        assert status.location is not None
        return scan_results_df(status.location, scanner="rb_value_scanner").scanners[
            "rb_value_scanner"
        ]

    buffered = run(3)
    unbuffered = run(None)

    assert sorted(buffered["value"].tolist()) == sorted(unbuffered["value"].tolist())
    assert len(buffered) == transcript_count == len(unbuffered)


def test_no_results_buffer_writes_nothing_until_complete(tmp_path: Path) -> None:
    """Without results_buffer, no scanner parquet is written to the scan
    location until the scan completes."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 10

    import asyncio

    asyncio.run(_insert_transcripts(db_path, transcript_count))

    status = scan(
        scanners=[_probe_scanner_factory(str(scans_path))],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        display="none",
    )

    assert status.complete
    assert status.location is not None

    df = scan_results_df(status.location, scanner="rb_probe_scanner").scanners[
        "rb_probe_scanner"
    ]
    visible_counts = [
        int(m["visible_at_scan_location"])
        for m in df["metadata"].apply(_load_metadata)
    ]
    # No periodic sync => nothing visible at the scan location during the scan.
    assert visible_counts == [0] * transcript_count


@pytest.mark.anyio
async def test_results_buffer_async(tmp_path: Path) -> None:
    """The option is also honored via scan_async."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 8
    await _insert_transcripts(db_path, transcript_count)

    status = await scan_async(
        scanners=[_probe_scanner_factory(str(scans_path))],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        results_buffer=2,
        display="none",
    )

    assert status.complete
    assert status.spec.options.results_buffer == 2


def _load_metadata(value: object) -> dict[str, object]:
    """Normalize a metadata cell (JSON string or dict) to a dict."""
    import json

    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        loaded = json.loads(value)
        assert isinstance(loaded, dict)
        return loaded
    return {}
