"""End-to-end tests for the `results_buffer` periodic-sync option.

`results_buffer=N` asks the scan to sync in-progress results to the scan
location every N recorded results (in a background task), so partial results
are visible while the scan is still running. These tests verify:

1. Partial results become visible at the scan location *before* the scan
   completes (the whole point of the feature).
2. Setting `results_buffer` does not change the final results.
3. Leaving it unset (the default) writes nothing to the scan location until
   completion.
4. The option is honored via `scan_async` and recorded on the scan spec.
"""

import asyncio
import json
from pathlib import Path

import anyio
import pandas as pd
import pyarrow.parquet as pq
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


def _synced_parquet(scans_path: Path, scanner_name: str) -> Path | None:
    """Find the compacted parquet for `scanner_name` at the scan location."""
    matches = list(scans_path.glob(f"scan_id=*/{scanner_name}.parquet"))
    assert len(matches) <= 1
    return matches[0] if matches else None


def _make_probe_scanner(
    name: str, scans_path: Path, wait_at_invocation: int | None
) -> Scanner[Transcript]:
    """Scanner that observes the compacted parquet at the scan location.

    Each invocation records (via result metadata) how many rows are visible
    in the scanner's parquet at the scan location. Periodic syncs run in the
    background, so at `wait_at_invocation` the scanner waits (bounded) for
    the parquet to appear, making the positive-case assertion deterministic.
    """
    invocations = 0

    @scanner(name=name, messages="all")
    def probe_scanner_factory() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            nonlocal invocations
            invocations += 1
            parquet = _synced_parquet(scans_path, name)
            if (
                parquet is None
                and wait_at_invocation is not None
                and invocations >= wait_at_invocation
            ):
                with anyio.move_on_after(10):
                    while parquet is None:
                        await anyio.sleep(0.05)
                        parquet = _synced_parquet(scans_path, name)
            visible = pq.read_table(parquet.as_posix()).num_rows if parquet else 0
            return Result(value=True, metadata={"visible": visible})

        return scan_transcript

    return probe_scanner_factory()


def _visible_counts(location: str, scanner_name: str) -> list[int]:
    df = scan_results_df(location, scanner=scanner_name).scanners[scanner_name]
    counts: list[int] = []
    for metadata in df["metadata"]:
        # metadata cells round-trip through parquet as JSON strings
        loaded = json.loads(metadata) if isinstance(metadata, str) else metadata
        assert isinstance(loaded, dict)
        counts.append(int(loaded["visible"]))
    return counts


def test_results_buffer_syncs_partial_results(tmp_path: Path) -> None:
    """Partial results appear at the scan location while the scan runs."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 20
    results_buffer = 5
    asyncio.run(_insert_transcripts(db_path, transcript_count))

    # max_processes=1 + max_transcripts=1 => transcripts processed serially,
    # so invocation 15 runs with at most 14 results recorded and at least two
    # syncs (at 5 and 10 recorded results) triggered before it.
    status = scan(
        scanners=[_make_probe_scanner("rb_probe_sync", scans_path, 15)],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        results_buffer=results_buffer,
        display="none",
    )

    assert status.complete
    assert status.location is not None

    # some invocation must have observed a partial (non-empty, incomplete)
    # snapshot at the scan location before the scan finished
    visible = _visible_counts(status.location, "rb_probe_sync")
    assert len(visible) == transcript_count
    assert max(visible) >= results_buffer, (
        f"expected partial results at the scan location mid-scan, saw {visible}"
    )
    assert max(visible) < transcript_count

    # the final sync still reflects every result
    final = _synced_parquet(scans_path, "rb_probe_sync")
    assert final is not None
    assert pq.read_table(final.as_posix()).num_rows == transcript_count


def test_no_results_buffer_writes_nothing_until_complete(tmp_path: Path) -> None:
    """Without results_buffer, nothing is written until the scan completes."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 10
    asyncio.run(_insert_transcripts(db_path, transcript_count))

    status = scan(
        scanners=[_make_probe_scanner("rb_probe_nosync", scans_path, None)],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        display="none",
    )

    assert status.complete
    assert status.location is not None
    assert _visible_counts(status.location, "rb_probe_nosync") == [0] * transcript_count


@pytest.mark.parametrize(
    ("results_buffer", "max_processes"),
    [(3, 1), (None, 1), (3, 2)],
)
def test_results_buffer_does_not_change_final_results(
    tmp_path: Path, results_buffer: int | None, max_processes: int
) -> None:
    """Periodic syncs must not duplicate or drop rows in the final results."""

    @scanner(name="rb_value_scanner", messages="all")
    def value_scanner_factory() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            return Result(value=transcript.metadata.get("index", 0))

        return scan_transcript

    transcript_count = 12
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    asyncio.run(_insert_transcripts(db_path, transcript_count))

    status = scan(
        scanners=[value_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=max_processes,
        results_buffer=results_buffer,
        display="none",
    )
    assert status.complete
    assert status.location is not None
    df: pd.DataFrame = scan_results_df(
        status.location, scanner="rb_value_scanner"
    ).scanners["rb_value_scanner"]
    assert sorted(int(v) for v in df["value"].tolist()) == list(range(transcript_count))


def test_results_buffer_async(tmp_path: Path) -> None:
    """The option is also honored via scan_async and recorded on the spec."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    async def run() -> None:
        await _insert_transcripts(db_path, 8)
        status = await scan_async(
            scanners=[_make_probe_scanner("rb_probe_async", scans_path, None)],
            transcripts=transcripts_from(str(db_path)),
            scans=str(scans_path),
            max_processes=1,
            max_transcripts=1,
            results_buffer=2,
        )
        assert status.complete
        assert status.spec.options.results_buffer == 2

    asyncio.run(run())
