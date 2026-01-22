"""Tests for nan/inf float handling in API v2 JSON responses."""

from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import ScannerSummary, Summary
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2 import v2_api_app


def _create_status_with_nan_metrics() -> Status:
    """Create a Status with nan values in scanner metrics."""
    spec = ScanSpec(
        scan_id="test-nan-scan",
        scan_name="nan_test",
        timestamp=datetime.now(),
        model=None,
        scanners={"test_scanner": ScannerSpec(name="test_scanner")},
    )

    summary = Summary(scanners={})
    summary.scanners["test_scanner"] = ScannerSummary(
        scans=10,
        results=5,
        errors=0,
        metrics={
            "accuracy": {"mean": 0.8, "stderr": float("nan")},
            "precision": {"mean": float("nan"), "stderr": float("nan")},
        },
    )

    return Status(
        complete=True,
        spec=spec,
        location="/path/to/scan",
        summary=summary,
        errors=[],
    )


class TestNanHandling:
    """Tests for nan/inf float handling in JSON responses."""

    def test_scans_with_nan_metrics(self) -> None:
        """POST /scans should handle nan values in metrics without crashing."""
        client = TestClient(v2_api_app(results_dir="/tmp"))
        status_with_nan = _create_status_with_nan_metrics()

        async def select_with_nan(query: object = None) -> AsyncIterator[Status]:
            yield status_with_nan

        with patch("inspect_scout._view._api_scans.scan_jobs_view") as mock_factory:
            mock_view = AsyncMock()
            mock_view.select = select_with_nan
            mock_view.count = AsyncMock(return_value=1)
            mock_view.__aenter__ = AsyncMock(return_value=mock_view)
            mock_view.__aexit__ = AsyncMock(return_value=None)
            mock_factory.return_value = mock_view

            response = client.post("/scans", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
