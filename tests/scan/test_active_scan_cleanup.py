import os
from pathlib import Path

import anyio
import pytest
from inspect_scout import Result, Scanner, Status, scan, scanner
from inspect_scout._recorder.active_scans_store import active_scans_store
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


@scanner(name="cleanup_probe_scanner", messages="all")
def cleanup_probe_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan_transcript


@scanner(name="failing_probe_scanner", messages="all")
def failing_probe_scanner() -> Scanner[Transcript]:
    first_transcript = True

    async def scan_transcript(transcript: Transcript) -> Result:
        nonlocal first_transcript
        if first_transcript:
            first_transcript = False
            return Result(value=True)
        # let the first result get recorded before failing (the test docstring
        # explains why this ordering leaves a trailing write pending)
        await anyio.sleep(0.3)
        raise ValueError("injected scanner failure")

    return scan_transcript


def assert_no_active_scan_entry() -> None:
    """The active-scans entry for this process must be gone after a scan.

    Checked by PID rather than by an empty store: under pytest-xdist other
    worker processes have live entries of their own.
    """
    with active_scans_store() as store:
        assert store.read_by_pid(os.getpid()) is None


def test_scan_completes_with_a_metrics_write_still_throttled(tmp_path: Path) -> None:
    """A scan short enough to end while a throttled metrics write is pending.

    The scan issues its metrics updates within a few tens of milliseconds and
    finishes well inside the one second throttle window, so the trailing-edge
    write is still pending when the scan ends. It must not fire against the
    closed store, and the scan must leave no active-scans entry behind.
    """
    status = scan(
        scanners=[cleanup_probe_scanner()],
        transcripts=transcripts_from(LOGS_DIR),
        scans=str(tmp_path),
        limit=2,
        # the deferred write only exists on the single-process path, where
        # metrics reporting goes through a throttled callback
        max_processes=1,
        display="none",
    )

    assert status.complete
    assert_no_active_scan_entry()


def test_interrupted_scan_survives_a_late_metrics_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A trailing-edge metrics write coming due after the store has closed.

    When a scanner error interrupts the scan, the active-scans store is closed
    and its entry deleted, then handle_scan_interrupted awaits a final sync.
    A pending trailing-edge metrics write whose throttle window expires during
    that sync must not run: the store's sqlite connection is closed and the
    write would raise (and resurrect the deleted entry if it got further).

    Holding the interrupted-path sync open past the one second throttle window
    makes the write come due inside that gap deterministically, no wall-clock
    aiming involved.
    """
    real_sync = FileRecorder.sync

    async def slow_sync(scan_location: str, complete: bool) -> Status:
        await anyio.sleep(2)
        return await real_sync(scan_location, complete)

    monkeypatch.setattr(FileRecorder, "sync", staticmethod(slow_sync))

    status = scan(
        scanners=[failing_probe_scanner()],
        transcripts=transcripts_from(LOGS_DIR),
        scans=str(tmp_path),
        limit=2,
        max_processes=1,
        fail_on_error=True,
        display="none",
    )

    assert not status.complete
    assert_no_active_scan_entry()
