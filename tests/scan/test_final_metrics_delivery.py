"""Final metrics delivery at strategy teardown (issue #569).

A strategy zeroes its counts and issues one last metrics update as it
finishes. These tests pin down that the update lands in the store.
"""

from pathlib import Path

import inspect_scout._scan as scan_module
import pytest
from inspect_ai.util import throttle
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._concurrency import single_process
from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._recorder.active_scans_store import ActiveScansStore
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

from tests.helpers import active_scans_store_spy, temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


@scanner(name="final_metrics_scanner", messages="all")
def final_metrics_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan_transcript


def _run_scan_recording_metrics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, max_processes: int
) -> list[int | None]:
    # read back what the store kept, not what the callback was handed, so a
    # write swallowed by a closed store cannot pass for a delivered one
    process_counts: list[int | None] = []

    def record(store: ActiveScansStore, scan_id: str, metrics: ScanMetrics) -> None:
        info = store.read_all().get(scan_id)
        process_counts.append(info.metrics.process_count if info else None)

    monkeypatch.setattr(
        scan_module, "active_scans_store", active_scans_store_spy("put_metrics", record)
    )

    with temp_active_scans_store():
        status = scan(
            scanners=[final_metrics_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=str(tmp_path),
            limit=2,
            max_processes=max_processes,
            display="none",
        )

    assert status.complete
    return process_counts


def test_completed_scan_delivers_final_metrics_single_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The strategy's zeroed teardown update reaches the store.

    A widened throttle window leaves every later call pending, so the final
    update is only observed if the strategy delivers it synchronously.
    """
    monkeypatch.setattr(single_process, "throttle", lambda _seconds: throttle(3600))

    process_counts = _run_scan_recording_metrics(monkeypatch, tmp_path, 1)

    assert process_counts, "no metrics updates reached the store"
    assert process_counts[-1] == 0, (
        "final zeroed metrics update was dropped. the last delivered update "
        f"still reported process_count={process_counts[-1]}"
    )


def test_completed_scan_delivers_final_metrics_multiprocess(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Each MP worker's final zeroed metrics snapshot reaches the parent.

    Spawned workers keep the real 1s window, so the update is only observed if
    the worker delivers it synchronously and the upstream queue has room.
    """
    process_counts = _run_scan_recording_metrics(monkeypatch, tmp_path, 2)

    assert process_counts, "no metrics updates reached the store"
    assert process_counts[-1] == 0, (
        "final zeroed worker metrics never reached the parent. the last "
        f"combined update still reported process_count={process_counts[-1]}"
    )
