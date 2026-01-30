"""Tests for POST /scans/{dir}/distinct endpoint."""

import base64
from datetime import datetime
from typing import AsyncIterator
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanjobs.duckdb import DuckDBScanJobsView
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2 import v2_api_app


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _create_test_status(
    scan_id: str,
    scan_name: str = "test_scan",
    complete: bool = True,
    scanners: list[str] | None = None,
    timestamp: datetime | None = None,
) -> Status:
    """Create a test Status object."""
    if scanners is None:
        scanners = ["refusal"]
    if timestamp is None:
        timestamp = datetime.now()

    spec = ScanSpec(
        scan_id=scan_id,
        scan_name=scan_name,
        timestamp=timestamp,
        model=None,
        scanners={s: ScannerSpec(name=s) for s in scanners},
    )

    return Status(
        complete=complete,
        spec=spec,
        location=f"/path/to/scans/scan_id={scan_id}",
        summary=Summary(scanners=scanners),
        errors=[],
    )


@pytest_asyncio.fixture
async def mock_scan_jobs_view() -> AsyncIterator[DuckDBScanJobsView]:
    """Create a mock ScanJobsView with test data."""
    statuses = [
        _create_test_status("scan-001", scan_name="math_eval", scanners=["refusal"]),
        _create_test_status("scan-002", scan_name="math_eval", scanners=["deception"]),
        _create_test_status("scan-003", scan_name="coding_eval", scanners=["refusal"]),
        _create_test_status("scan-004", scan_name="coding_eval", scanners=["efficiency"]),
        _create_test_status("scan-005", scan_name="qa_eval", scanners=["refusal"]),
    ]
    view = DuckDBScanJobsView(statuses)
    await view.connect()
    yield view
    await view.disconnect()


class TestScansDistinctEndpoint:
    """Tests for POST /scans/{dir}/distinct endpoint."""

    @pytest.mark.asyncio
    async def test_distinct_no_filter(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Get distinct values without filter."""
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_scans.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                f"/scans/{_base64url('/tmp')}/distinct",
                json={"column": "scan_name"},
            )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"coding_eval", "math_eval", "qa_eval"}
        # Verify sorted ascending
        assert values == sorted(values)

    @pytest.mark.asyncio
    async def test_distinct_with_filter(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Get distinct values with filter condition."""
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_scans.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                f"/scans/{_base64url('/tmp')}/distinct",
                json={
                    "column": "scan_name",
                    "filter": {
                        "is_compound": False,
                        "left": "scanners",
                        "operator": "=",
                        "right": "refusal",
                    },
                },
            )

        assert response.status_code == 200
        values = response.json()
        # Only scan_names with refusal scanner
        assert set(values) == {"coding_eval", "math_eval", "qa_eval"}

    @pytest.mark.asyncio
    async def test_distinct_empty_result(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Get distinct values with no matching results."""
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_scans.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                f"/scans/{_base64url('/tmp')}/distinct",
                json={
                    "column": "scan_name",
                    "filter": {
                        "is_compound": False,
                        "left": "scanners",
                        "operator": "=",
                        "right": "nonexistent_scanner",
                    },
                },
            )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_distinct_no_body(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Request with no body returns empty list."""
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_scans.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(f"/scans/{_base64url('/tmp')}/distinct")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_distinct_different_column(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Get distinct values for different column."""
        client = TestClient(v2_api_app())

        with patch(
            "inspect_scout._view._api_v2_scans.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                f"/scans/{_base64url('/tmp')}/distinct",
                json={"column": "scanners"},
            )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"deception", "efficiency", "refusal"}
        assert values == sorted(values)
