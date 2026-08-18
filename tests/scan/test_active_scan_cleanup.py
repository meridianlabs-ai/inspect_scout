import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

import anyio
import inspect_scout._scan as scan_module
import pytest
from inspect_ai.util import throttle
from inspect_scout import Result, Scanner, Status, scan, scanner
from inspect_scout._concurrency import single_process
from inspect_scout._recorder.active_scans_store import (
    ActiveScansStore,
    active_scans_store,
)
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

from tests.helpers import temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"

# the strategy hardcodes @throttle(1); shrinking the window keeps the same
# trailing-edge mechanics while the test holds the vulnerable gap open for
# fractions of a second instead of multiples of it. the window must still be
# generous enough that the strategy's teardown metrics call lands inside it
# even on a loaded CI machine, or no trailing-edge fire gets scheduled.
THROTTLE_WINDOW = 0.3


@scanner(name="cleanup_probe_scanner", messages="all")
def cleanup_probe_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan_transcript


@scanner(name="failing_probe_scanner", messages="all")
def failing_probe_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        raise ValueError("injected scanner failure")

    return scan_transcript


def test_completed_scan_leaves_no_active_scan_entry(tmp_path: Path) -> None:
    """Cleanup smoke test for the success path.

    A completed scan must delete its active-scans entry. (The late
    metrics-write hazard is only reachable on the interrupted path -- on
    completion the pending trailing-edge write is cancelled with the scan's
    task group -- so this test pins only the cleanup behavior.)
    """
    with temp_active_scans_store():
        status = scan(
            scanners=[cleanup_probe_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=str(tmp_path),
            limit=2,
            # single-process path: the strategy whose metrics callback and
            # store cleanup are under test here
            max_processes=1,
            display="none",
        )

        assert status.complete
        with active_scans_store() as store:
            assert store.read_all() == {}


def test_interrupted_scan_survives_a_late_metrics_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A trailing-edge metrics write coming due after the store has closed.

    When a scanner error interrupts the scan, the active-scans store is closed
    and its entry deleted, then handle_scan_interrupted awaits a final sync.
    A pending trailing-edge metrics write whose throttle window expires during
    that sync must not run: the store's sqlite connection is closed and the
    write would raise (and resurrect the deleted entry if it got further).

    Holding the interrupted-path sync open past the throttle window makes the
    write come due inside that gap deterministically. The test records when
    throttled fires happen and when the scan deletes its store entry, and
    asserts a fire actually came due after the delete -- so it fails loudly
    if the vulnerable window ever stops opening, rather than passing
    vacuously. (Without the guards, that post-delete fire raises
    sqlite3.ProgrammingError out of scan() itself, failing the test with the
    original error.)
    """
    # shrink the throttle window and record when the throttled function fires
    fire_times: list[float] = []

    def recording_throttle(_seconds: float) -> Callable[..., Any]:
        def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
            def recorded(*args: Any, **kwargs: Any) -> Any:
                fire_times.append(time.monotonic())
                return fn(*args, **kwargs)

            return throttle(THROTTLE_WINDOW)(recorded)

        return decorate

    monkeypatch.setattr(single_process, "throttle", recording_throttle)

    # record when the scan deletes its active-scans entry
    deleted_at: list[float] = []

    @contextmanager
    def tracking_store() -> Iterator[ActiveScansStore]:
        with active_scans_store() as store:
            real_delete = store.delete_current

            def tracked_delete() -> None:
                deleted_at.append(time.monotonic())
                real_delete()

            store.delete_current = tracked_delete  # type: ignore[method-assign]
            yield store

    monkeypatch.setattr(scan_module, "active_scans_store", tracking_store)

    # hold the interrupted-path sync open past the throttle window
    real_sync = FileRecorder.sync

    async def slow_sync(scan_location: str, complete: bool) -> Status:
        await anyio.sleep(THROTTLE_WINDOW * 2)
        return await real_sync(scan_location, complete)

    monkeypatch.setattr(FileRecorder, "sync", staticmethod(slow_sync))

    with temp_active_scans_store():
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
        assert deleted_at, "scan never deleted its active-scans entry"
        assert fire_times and max(fire_times) > deleted_at[0], (
            "no trailing-edge metrics write came due after the store entry "
            "was deleted -- the vulnerable window this test exercises did "
            "not open"
        )
        with active_scans_store() as store:
            assert store.read_all() == {}
