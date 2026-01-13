"""Tests for GET /scans/active endpoint."""

from contextlib import contextmanager
from typing import Iterator
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._recorder.active_scans_store import ActiveScanInfo, ActiveScansStore
from inspect_scout._recorder.summary import Summary
from inspect_scout._view._api_v2 import v2_api_app


@contextmanager
def _mock_active_scans_store(
    data: dict[str, ActiveScanInfo],
) -> Iterator[None]:
    """Mock active_scans_store context manager."""
    mock_store = MagicMock(spec=ActiveScansStore)
    mock_store.read_all.return_value = data

    @contextmanager
    def mock_cm() -> Iterator[ActiveScansStore]:
        yield mock_store

    with patch("inspect_scout._view._api_v2.active_scans_store", mock_cm):
        yield


class TestActiveScansEndpoint:
    """Tests for GET /scans/active endpoint."""

    def test_active_scans_empty(self) -> None:
        """No active scans returns empty items dict."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with _mock_active_scans_store({}):
            response = client.get("/scans/active")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == {}

    def test_active_scans_with_single_scan(self) -> None:
        """Single active scan returned correctly."""
        client = TestClient(v2_api_app(results_dir="/tmp"))
        metrics = ScanMetrics(
            process_count=4,
            task_count=8,
            completed_scans=100,
            memory_usage=1024 * 1024,
        )
        scan_info = ActiveScanInfo(
            scan_id="scan-abc-123",
            summary=Summary(),
            metrics=metrics,
            last_updated=1704067200.0,
            title="scan: test.py (100 transcripts)",
            config="model: gpt-4",
            total_scans=100,
            start_time=1704067100.0,
            scanner_names=["scanner1", "scanner2"],
        )

        with _mock_active_scans_store({"scan-abc-123": scan_info}):
            response = client.get("/scans/active")

        assert response.status_code == 200
        data = response.json()
        assert "scan-abc-123" in data["items"]

        item = data["items"]["scan-abc-123"]
        assert item["scan_id"] == "scan-abc-123"
        assert item["metrics"]["process_count"] == 4
        assert item["metrics"]["task_count"] == 8
        assert item["metrics"]["completed_scans"] == 100
        assert item["metrics"]["memory_usage"] == 1024 * 1024
        assert item["last_updated"] == 1704067200.0

    def test_active_scans_multiple(self) -> None:
        """Multiple active scans returned correctly."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        scan1 = ActiveScanInfo(
            scan_id="scan-1",
            summary=Summary(),
            metrics=ScanMetrics(completed_scans=50),
            last_updated=1000.0,
            title="scan-1",
            config="",
            total_scans=100,
            start_time=900.0,
            scanner_names=["s1"],
        )
        scan2 = ActiveScanInfo(
            scan_id="scan-2",
            summary=Summary(),
            metrics=ScanMetrics(completed_scans=75),
            last_updated=2000.0,
            title="scan-2",
            config="",
            total_scans=100,
            start_time=1900.0,
            scanner_names=["s1"],
        )
        scan3 = ActiveScanInfo(
            scan_id="scan-3",
            summary=Summary(),
            metrics=ScanMetrics(completed_scans=25),
            last_updated=3000.0,
            title="scan-3",
            config="",
            total_scans=100,
            start_time=2900.0,
            scanner_names=["s1"],
        )

        store_data = {
            "scan-1": scan1,
            "scan-2": scan2,
            "scan-3": scan3,
        }

        with _mock_active_scans_store(store_data):
            response = client.get("/scans/active")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert set(data["items"].keys()) == {"scan-1", "scan-2", "scan-3"}

        assert data["items"]["scan-1"]["metrics"]["completed_scans"] == 50
        assert data["items"]["scan-2"]["metrics"]["completed_scans"] == 75
        assert data["items"]["scan-3"]["metrics"]["completed_scans"] == 25

    def test_active_scans_all_metrics_fields(self) -> None:
        """All ScanMetrics fields serialized correctly."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        metrics = ScanMetrics(
            process_count=2,
            task_count=4,
            tasks_idle=1,
            tasks_parsing=1,
            tasks_scanning=2,
            buffered_scanner_jobs=10,
            completed_scans=500,
            memory_usage=2048,
            batch_pending=5,
            batch_failures=1,
            batch_oldest_created=1704000000,
        )
        scan_info = ActiveScanInfo(
            scan_id="full-metrics-scan",
            summary=Summary(),
            metrics=metrics,
            last_updated=1704067200.0,
            title="full-metrics-scan",
            config="max_connections: 10",
            total_scans=1000,
            start_time=1704000000.0,
            scanner_names=["scanner1"],
        )

        with _mock_active_scans_store({"full-metrics-scan": scan_info}):
            response = client.get("/scans/active")

        assert response.status_code == 200
        m = response.json()["items"]["full-metrics-scan"]["metrics"]

        assert m["process_count"] == 2
        assert m["task_count"] == 4
        assert m["tasks_idle"] == 1
        assert m["tasks_parsing"] == 1
        assert m["tasks_scanning"] == 2
        assert m["buffered_scanner_jobs"] == 10
        assert m["completed_scans"] == 500
        assert m["memory_usage"] == 2048
        assert m["batch_pending"] == 5
        assert m["batch_failures"] == 1
        assert m["batch_oldest_created"] == 1704000000


