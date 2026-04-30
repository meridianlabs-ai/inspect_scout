"""Tests for unconditional per-transcript scanner gating.

The first scanner for each transcript runs alone; followers are only released
after it completes. This lets the prompt cache populate from the lead's
generate call so followers hit the warm cache. Always-on; no opt-out.
"""

import asyncio
import time
from pathlib import Path

import pytest
from inspect_scout import Result, Scanner, scan, scanner, transcripts_db
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

from tests.scan.test_scan_e2e import create_minimal_transcript


@scanner(name="ts_recorder", messages="all")
def ts_recorder_factory(label: str, sleep_s: float = 0.05) -> Scanner[Transcript]:
    """Scanner that records its start/end times into a per-process registry."""

    async def scan_transcript(transcript: Transcript) -> Result:
        start = time.monotonic()
        await asyncio.sleep(sleep_s)
        end = time.monotonic()
        TIMINGS.setdefault(transcript.transcript_id, []).append((label, start, end))
        return Result(value=True, explanation=label)

    return scan_transcript


# Module-level registry; tests run in single-process mode so this is sufficient.
TIMINGS: dict[str, list[tuple[str, float, float]]] = {}


def _setup_transcripts(db_path: Path, count: int) -> None:
    async def _insert() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert(
                [create_minimal_transcript(f"t-{i:03d}", i) for i in range(count)]
            )

    asyncio.run(_insert())


@pytest.fixture(autouse=True)
def _clear_timings() -> None:
    TIMINGS.clear()


def test_first_scanner_runs_before_followers(tmp_path: Path) -> None:
    """Follower starts only after lead completes."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    _setup_transcripts(db_path, count=1)

    status = scan(
        scanners=[
            ("lead", ts_recorder_factory("lead", sleep_s=0.1)),
            ("follower", ts_recorder_factory("follower", sleep_s=0.01)),
        ],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        display="none",
    )

    assert status.complete

    events = TIMINGS["t-000"]
    assert len(events) == 2
    by_label = {label: (start, end) for label, start, end in events}
    lead_start, lead_end = by_label["lead"]
    follower_start, _ = by_label["follower"]
    assert follower_start >= lead_end, (
        f"follower started at {follower_start} but lead ended at {lead_end}"
    )


@scanner(name="raising_scanner", messages="all")
def raising_scanner_factory() -> Scanner[Transcript]:
    """Scanner that always raises — to verify follower release on lead failure."""

    async def scan_transcript(transcript: Transcript) -> Result:
        raise RuntimeError("boom")

    return scan_transcript


def test_followers_release_when_lead_fails(tmp_path: Path) -> None:
    """If the lead raises, followers must still run."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    _setup_transcripts(db_path, count=1)

    scan(
        scanners=[
            ("lead", raising_scanner_factory()),
            ("follower", ts_recorder_factory("follower", sleep_s=0.01)),
        ],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        display="none",
    )

    # Lead's exception is recorded as an error, but the follower must still run.
    assert "t-000" in TIMINGS
    labels = [label for label, _, _ in TIMINGS["t-000"]]
    assert "follower" in labels


def test_single_scanner_completes(tmp_path: Path) -> None:
    """Single-scanner config: gate is effectively a no-op, scan completes."""
    db_path = tmp_path / "db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()
    _setup_transcripts(db_path, count=2)

    status = scan(
        scanners=[("only", ts_recorder_factory("only", sleep_s=0.01))],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        display="none",
    )

    assert status.complete
    assert len(TIMINGS) == 2
