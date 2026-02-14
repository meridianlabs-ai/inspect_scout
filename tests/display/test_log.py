import logging
import time

import pytest
from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._display.log import DisplayLog, ScanDisplayLog, TextProgressLog
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanner.result import Error
from inspect_scout._scanspec import ScanSpec


def test_scan_display_log_metrics_logs_progress(
    caplog: pytest.LogCaptureFixture,
) -> None:
    display = ScanDisplayLog(total=100, skipped=10)
    metrics = ScanMetrics(
        process_count=1,
        task_count=4,
        tasks_idle=1,
        tasks_parsing=1,
        tasks_scanning=2,
        buffered_scanner_jobs=5,
        completed_scans=50,
    )

    display._completed_scans = 60

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display._log_metrics(metrics)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Scan progress: 60%" in record.message
    assert "(60/100)" in record.message
    assert record.__dict__["scan_progress"]["completed"] == 60
    assert record.__dict__["scan_progress"]["total"] == 100
    assert record.__dict__["scan_metrics"]["completed_scans"] == 50


def test_scan_display_log_metrics_with_batch_info(
    caplog: pytest.LogCaptureFixture,
) -> None:
    display = ScanDisplayLog(total=100, skipped=0)
    display._completed_scans = 25
    current_time = int(time.time())
    metrics = ScanMetrics(
        completed_scans=25,
        batch_pending=10,
        batch_oldest_created=current_time - 120,
    )

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display._log_metrics(metrics)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "batch:" in record.message
    assert "10/" in record.message


def test_scan_display_log_metrics_updates_completed_count() -> None:
    display = ScanDisplayLog(total=100, skipped=10)

    assert display._completed_scans == 10

    metrics = ScanMetrics(completed_scans=50)
    display.metrics(metrics)

    assert display._completed_scans == 60


def test_scan_display_log_metrics_handles_zero_total(
    caplog: pytest.LogCaptureFixture,
) -> None:
    display = ScanDisplayLog(total=0, skipped=0)
    metrics = ScanMetrics(completed_scans=0)

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display._log_metrics(metrics)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "0%" in record.message


def test_scan_display_log_results_is_noop() -> None:
    from unittest import mock

    display = ScanDisplayLog(total=100, skipped=0)
    display.results(mock.Mock(), "scanner", [], None)


@pytest.mark.parametrize(
    ("total", "skipped", "completed_scans", "expected_percent"),
    [
        (100, 0, 50, 50.0),
        (100, 10, 40, 50.0),
        (1000, 100, 400, 50.0),
        (100, 0, 100, 100.0),
        (0, 0, 0, 0.0),
    ],
)
def test_scan_display_log_progress_percentage_calculation(
    total: int,
    skipped: int,
    completed_scans: int,
    expected_percent: float,
    caplog: pytest.LogCaptureFixture,
) -> None:
    display = ScanDisplayLog(total=total, skipped=skipped)
    metrics = ScanMetrics(completed_scans=completed_scans)
    display._completed_scans = skipped + completed_scans

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display._log_metrics(metrics)

    record = caplog.records[0]
    assert record.__dict__["scan_progress"]["percent"] == expected_percent


def test_text_progress_log_first_update_logs_immediately(
    caplog: pytest.LogCaptureFixture,
) -> None:
    progress = TextProgressLog(caption="Loading", count=10)

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        progress._log_update("item 1")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Loading: item 1" in record.message
    assert record.__dict__["caption"] == "Loading"
    assert record.__dict__["text"] == "item 1"


def test_text_progress_log_update_increments_total() -> None:
    progress = TextProgressLog(caption="Loading", count=True)

    assert progress._total == 0

    progress.update("item 1")
    assert progress._total == 1

    progress.update("item 2")
    assert progress._total == 2


def test_text_progress_log_update_without_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    progress = TextProgressLog(caption="Processing", count=False)

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        progress._log_update("file.txt")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "progress" not in record.__dict__
    assert "total" not in record.__dict__


def test_text_progress_log_update_with_bool_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    progress = TextProgressLog(caption="Loading", count=True)
    progress._total = 5

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        progress._log_update("item")

    record = caplog.records[0]
    assert record.__dict__["progress"] == 5
    assert "total" not in record.__dict__


def test_text_progress_log_update_with_int_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    progress = TextProgressLog(caption="Loading", count=100)
    progress._total = 25

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        progress._log_update("item")

    record = caplog.records[0]
    assert record.__dict__["progress"] == 25
    assert record.__dict__["total"] == 100


def _make_error(traceback: str = "Traceback (most recent call last):\n  ...") -> Error:
    return Error(
        transcript_id="t1",
        scanner="test_scanner",
        error="something failed",
        traceback=traceback,
        refusal=False,
    )


def _make_status(*, complete: bool = True, errors: list[Error] | None = None) -> Status:
    return Status(
        complete=complete,
        spec=ScanSpec(scan_name="test", scanners={}, transcripts=None),
        location="/tmp/test",
        summary=Summary(),
        errors=errors or [],
    )


def test_scan_complete_strips_tracebacks_from_logged_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    errors = [_make_error("long traceback\nline 2\nline 3")]
    status = _make_status(complete=False, errors=errors)
    display = DisplayLog()

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display.scan_complete(status)

    assert len(caplog.records) == 1
    logged_status: Status = caplog.records[0].__dict__["status"]
    assert len(logged_status.errors) == 1
    assert logged_status.errors[0].traceback == ""


def test_scan_complete_no_errors_logs_normally(
    caplog: pytest.LogCaptureFixture,
) -> None:
    status = _make_status(complete=True)
    display = DisplayLog()

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display.scan_complete(status)

    assert len(caplog.records) == 1
    logged_status: Status = caplog.records[0].__dict__["status"]
    assert logged_status.errors == []


def test_scan_status_strips_tracebacks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    errors = [_make_error(), _make_error()]
    status = _make_status(complete=False, errors=errors)
    display = DisplayLog()

    with caplog.at_level(logging.INFO, logger="inspect_scout._display.log"):
        display.scan_status(status)

    assert len(caplog.records) == 1
    logged_status: Status = caplog.records[0].__dict__["status"]
    assert all(e.traceback == "" for e in logged_status.errors)


def test_scan_interrupted_strips_tracebacks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    errors = [_make_error("tb")]
    status = _make_status(complete=False, errors=errors)
    display = DisplayLog()

    with caplog.at_level(logging.WARNING, logger="inspect_scout._display.log"):
        display.scan_interrupted("interrupted!", status)

    assert len(caplog.records) == 1
    logged_status: Status = caplog.records[0].__dict__["status"]
    assert logged_status.errors[0].traceback == ""


def test_strip_tracebacks_does_not_mutate_original_status() -> None:
    original_tb = "Traceback (most recent call last):\n  File ..."
    errors = [_make_error(original_tb)]
    status = _make_status(complete=False, errors=errors)
    display = DisplayLog()

    display.scan_complete(status)

    assert status.errors[0].traceback == original_tb
