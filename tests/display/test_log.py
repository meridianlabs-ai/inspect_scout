import logging
import time

import pytest
from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._display.log import ScanDisplayLog, TextProgressLog


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

    with caplog.at_level(logging.INFO):
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

    with caplog.at_level(logging.INFO):
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

    with caplog.at_level(logging.INFO):
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

    with caplog.at_level(logging.INFO):
        display._log_metrics(metrics)

    record = caplog.records[0]
    assert record.__dict__["scan_progress"]["percent"] == expected_percent


def test_text_progress_log_first_update_logs_immediately(
    caplog: pytest.LogCaptureFixture,
) -> None:
    progress = TextProgressLog(caption="Loading", count=10)

    with caplog.at_level(logging.INFO):
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

    with caplog.at_level(logging.INFO):
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

    with caplog.at_level(logging.INFO):
        progress._log_update("item")

    record = caplog.records[0]
    assert record.__dict__["progress"] == 5
    assert "total" not in record.__dict__


def test_text_progress_log_update_with_int_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    progress = TextProgressLog(caption="Loading", count=100)
    progress._total = 25

    with caplog.at_level(logging.INFO):
        progress._log_update("item")

    record = caplog.records[0]
    assert record.__dict__["progress"] == 25
    assert record.__dict__["total"] == 100


@pytest.mark.parametrize(
    (
        "per_scanner_total",
        "per_scanner_skipped",
        "results_scanners",
        "expected_completed_scanners",
    ),
    [
        (
            {"scanner_a": 3},
            {},
            ["scanner_a", "scanner_a", "scanner_a"],
            ["scanner_a"],
        ),
        (
            {"scanner_a": 3},
            {"scanner_a": 2},
            ["scanner_a"],
            ["scanner_a"],
        ),
        (
            {"scanner_a": 2, "scanner_b": 3},
            {},
            ["scanner_a", "scanner_a", "scanner_b", "scanner_b", "scanner_b"],
            ["scanner_a", "scanner_b"],
        ),
        (
            {"scanner_a": 2},
            {"scanner_a": 2},
            [],
            ["scanner_a"],
        ),
        (
            {"scanner_a": 3, "scanner_b": 2},
            {"scanner_a": 1},
            ["scanner_a", "scanner_b", "scanner_b", "scanner_a"],
            ["scanner_b", "scanner_a"],
        ),
    ],
)
def test_scan_display_log_scanner_completion(
    per_scanner_total: dict[str, int],
    per_scanner_skipped: dict[str, int],
    results_scanners: list[str],
    expected_completed_scanners: list[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    from unittest import mock

    with caplog.at_level(logging.INFO):
        display = ScanDisplayLog(
            total=sum(per_scanner_total.values()),
            skipped=sum(per_scanner_skipped.values()),
            per_scanner_total=per_scanner_total,
            per_scanner_skipped=per_scanner_skipped,
        )

        for scanner in results_scanners:
            display.results(mock.Mock(), scanner, [], None)

    completion_logs = [
        r for r in caplog.records if "complete" in r.message and "Scanner" in r.message
    ]
    completed_scanner_names = [r.__dict__["scanner"] for r in completion_logs]

    assert completed_scanner_names == expected_completed_scanners


def test_scan_display_log_scanner_completion_logs_correct_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from unittest import mock

    with caplog.at_level(logging.INFO):
        display = ScanDisplayLog(
            total=5,
            skipped=0,
            per_scanner_total={"scanner_a": 2, "scanner_b": 3},
            per_scanner_skipped={},
        )

        display.results(mock.Mock(), "scanner_a", [], None)
        display.results(mock.Mock(), "scanner_a", [], None)

    completion_logs = [
        r for r in caplog.records if "complete" in r.message and "Scanner" in r.message
    ]
    assert len(completion_logs) == 1
    record = completion_logs[0]
    assert record.__dict__["scanner"] == "scanner_a"
    assert record.__dict__["scanners_complete"] == 1
    assert record.__dict__["scanners_total"] == 2
    assert record.__dict__["transcripts_completed"] == 2


def test_scan_display_log_scanner_completion_already_complete_at_init(
    caplog: pytest.LogCaptureFixture,
) -> None:
    display = ScanDisplayLog(
        total=2,
        skipped=2,
        per_scanner_total={"scanner_a": 2},
        per_scanner_skipped={"scanner_a": 2},
    )

    assert "scanner_a" in display._scanners_completed


def test_scan_display_log_no_duplicate_completion_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from unittest import mock

    with caplog.at_level(logging.INFO):
        display = ScanDisplayLog(
            total=2,
            skipped=0,
            per_scanner_total={"scanner_a": 2},
            per_scanner_skipped={},
        )

        display.results(mock.Mock(), "scanner_a", [], None)
        display.results(mock.Mock(), "scanner_a", [], None)
        display.results(mock.Mock(), "scanner_a", [], None)

    completion_logs = [
        r for r in caplog.records if "complete" in r.message and "Scanner" in r.message
    ]
    assert len(completion_logs) == 1
