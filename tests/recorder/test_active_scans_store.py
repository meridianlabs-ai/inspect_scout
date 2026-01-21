"""Tests for the active scans KV store."""

import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

from inspect_ai._util.kvstore import inspect_kvstore
from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._recorder.active_scans_store import (
    ActiveScanInfo,
    active_scans_store,
)
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanspec import ScannerSpec, ScanSpec


def _make_spec(scan_id: str) -> ScanSpec:
    """Create minimal ScanSpec for testing."""
    return ScanSpec(
        scan_id=scan_id,
        scan_name="test",
        scanners={"test_scanner": ScannerSpec(name="test_scanner")},
    )


@contextmanager
def _temp_store_name() -> Iterator[str]:
    """Override store name for isolated testing."""
    name = f"__testing_active_scans_{secrets.token_hex(4)}__"
    with patch("inspect_scout._recorder.active_scans_store._STORE_NAME", name):
        try:
            yield name
        finally:
            with inspect_kvstore(name) as kvstore:
                path = kvstore.filename
            Path(path).unlink(missing_ok=True)


def test_put_and_read_all() -> None:
    """Store metrics and verify read returns them."""
    with _temp_store_name():
        metrics = ScanMetrics(process_count=2, task_count=4, completed_scans=10)
        scan_id = "test-scan-123"

        with active_scans_store() as store:
            store.put_spec(scan_id, _make_spec(scan_id), total_scans=100, location="")
            store.put_metrics(scan_id, metrics)
            result = store.read_all()

        assert scan_id in result
        info = result[scan_id]
        assert info.scan_id == scan_id
        assert info.metrics.process_count == 2
        assert info.metrics.task_count == 4
        assert info.metrics.completed_scans == 10
        assert info.last_updated > 0


def test_mark_completed() -> None:
    """Store metrics, mark completed, verify running becomes False."""
    with _temp_store_name():
        metrics = ScanMetrics(completed_scans=5)
        scan_id = "mark-test"

        with active_scans_store() as store:
            store.put_spec(scan_id, _make_spec(scan_id), total_scans=100, location="")
            store.put_metrics(scan_id, metrics)
            info = store.read_all()[scan_id]
            assert info.running is True
            store.mark_completed()
            info = store.read_all()[scan_id]
            assert info.running is False
            assert info.error_message is None


def test_mark_interrupted() -> None:
    """Store metrics, mark interrupted, verify running=False and error_message."""
    with _temp_store_name():
        scan_id = "interrupt-test"

        with active_scans_store() as store:
            store.put_spec(scan_id, _make_spec(scan_id), total_scans=100, location="")
            store.mark_interrupted(scan_id, "Test error message")
            info = store.read_all()[scan_id]
            assert info.running is False
            assert info.error_message == "Test error message"


def test_mark_interrupted_without_put_spec() -> None:
    """mark_interrupted creates minimal entry if called before put_spec."""
    with _temp_store_name():
        scan_id = "prereq-error-test"

        with active_scans_store() as store:
            store.mark_interrupted(scan_id, "No transcripts")
            info = store.read_all()[scan_id]
            assert info.scan_id == scan_id
            assert info.running is False
            assert info.error_message == "No transcripts"
            assert info.title == ""
            assert info.total_scans == 0


def test_multiple_scans_same_process() -> None:
    """Put twice replaces entry since keyed by PID."""
    with _temp_store_name():
        scan_id_1 = "scan-1"
        scan_id_2 = "scan-2"

        with active_scans_store() as store:
            store.put_spec(
                scan_id_1, _make_spec(scan_id_1), total_scans=100, location=""
            )
            store.put_metrics(scan_id_1, ScanMetrics(completed_scans=1))
            store.put_spec(
                scan_id_2, _make_spec(scan_id_2), total_scans=100, location=""
            )
            store.put_metrics(scan_id_2, ScanMetrics(completed_scans=2))
            result = store.read_all()

        # Same PID overwrites, so only last scan_id present
        assert len(result) == 1
        assert scan_id_2 in result
        assert result[scan_id_2].metrics.completed_scans == 2


def test_overwrite_updates_metrics_and_timestamp() -> None:
    """Put twice with same scan_id updates metrics and timestamp."""
    with _temp_store_name():
        scan_id = "update-test"

        with active_scans_store() as store:
            store.put_spec(scan_id, _make_spec(scan_id), total_scans=100, location="")
            store.put_metrics(scan_id, ScanMetrics(completed_scans=5))
            first_result = store.read_all()[scan_id]
            first_timestamp = first_result.last_updated

            time.sleep(0.01)  # Ensure timestamp changes
            store.put_metrics(scan_id, ScanMetrics(completed_scans=10))
            second_result = store.read_all()[scan_id]

        assert second_result.metrics.completed_scans == 10
        assert second_result.last_updated > first_timestamp


def test_entries_persist_after_process_exit() -> None:
    """Entries persist even if process no longer exists (cleared on server restart)."""
    with _temp_store_name() as name:
        # Manually insert entry with fake dead PID
        fake_pid = 99999999  # Unlikely to exist
        with inspect_kvstore(name) as kvstore:
            kvstore.put(
                str(fake_pid),
                '{"scan_id": "persisted", "metrics": {}, "last_updated": 0, '
                '"summary": {}, "title": "", "config": "", "total_scans": 0, '
                '"start_time": 0, "scanner_names": [], "location": "", '
                '"running": false, "error_message": null}',
            )

        # Opening store should NOT clean the entry (entries persist until server restart)
        with active_scans_store() as store:
            result = store.read_all()

        assert "persisted" in result


def test_read_all_returns_empty_when_no_entries() -> None:
    """Fresh store returns empty dict."""
    with _temp_store_name():
        with active_scans_store() as store:
            result = store.read_all()

        assert result == {}


def test_active_scan_info_dataclass() -> None:
    """ActiveScanInfo holds expected fields."""
    metrics = ScanMetrics(memory_usage=1024)
    info = ActiveScanInfo(
        scan_id="test",
        summary=Summary(),
        metrics=metrics,
        last_updated=123.456,
        title="Test Title",
        config="test-config",
        total_scans=5,
        start_time=100.0,
        scanner_names=["scanner1"],
        location="",
        running=True,
    )

    assert info.scan_id == "test"
    assert info.metrics.memory_usage == 1024
    assert info.last_updated == 123.456
    assert info.running is True
    assert info.error_message is None
