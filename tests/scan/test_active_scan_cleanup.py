import time
from pathlib import Path
from typing import Any, Callable

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

from tests.helpers import active_scans_store_spy, temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"

# shrinks the strategy's hardcoded @throttle(1) window, but stays generous
# enough that the strategy's teardown metrics call lands inside it on a
# loaded CI machine (otherwise no trailing-edge fire gets scheduled at all)
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
    """Cleanup smoke test: a completed scan deletes its active-scans entry.

    The late-write hazard is only reachable on the interrupted path (on
    completion the pending write is cancelled with the scan's task group).
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

    Holds the interrupted-path sync open past the throttle window and asserts
    a fire came due after the entry delete (fails loudly if the window closes).
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

    def record_delete(store: ActiveScansStore) -> None:
        deleted_at.append(time.monotonic())

    monkeypatch.setattr(
        scan_module,
        "active_scans_store",
        active_scans_store_spy("delete_current", record_delete),
    )

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
            "was deleted, so the vulnerable window this test exercises "
            "never opened"
        )
        with active_scans_store() as store:
            assert store.read_all() == {}
