"""Tests for /scans endpoint pagination support."""

from datetime import datetime
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanjobs.duckdb import DuckDBScanJobsView
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2 import v2_api_app


def _create_test_status(
    scan_id: str,
    scan_name: str = "test_scan",
    complete: bool = True,
    model: str | None = "openai/gpt-4",
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


def _create_test_statuses(count: int = 10) -> list[Status]:
    """Create multiple test Status objects."""
    statuses = []
    models = ["openai/gpt-4", "openai/gpt-3.5-turbo", "anthropic/claude-3-opus"]
    scanner_sets = [["refusal"], ["reward_hacking"], ["deception"]]

    for i in range(count):
        statuses.append(
            _create_test_status(
                scan_id=f"scan-{i:03d}",
                scan_name=f"job_{i % 3}",
                complete=i % 4 != 0,  # 25% incomplete
                model=models[i % 3],
                scanners=scanner_sets[i % 3],
                timestamp=datetime(2025, 1, 1, i, 0, 0),
            )
        )

    return statuses


@pytest_asyncio.fixture
async def mock_scan_jobs_view() -> AsyncIterator[DuckDBScanJobsView]:
    """Create a mock ScanJobsView with test data."""
    statuses = _create_test_statuses(10)
    view = DuckDBScanJobsView(statuses)
    await view.connect()
    yield view
    await view.disconnect()


class TestScansEndpointPagination:
    """Tests for /scans endpoint with pagination support."""

    def test_scans_post_returns_response_structure(self, tmp_path: str) -> None:
        """Verify POST /scans returns items, total_count, next_cursor."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        async def empty_select(**kwargs: object) -> AsyncIterator[Status]:
            return
            yield  # makes this an async generator

        with patch("inspect_scout._view._api_v2.scan_jobs_view") as mock_factory:
            # Create mock view
            mock_view = AsyncMock()
            mock_view.connect = AsyncMock()
            mock_view.disconnect = AsyncMock()
            mock_view.select = empty_select
            mock_view.count = AsyncMock(return_value=0)
            mock_view.__aenter__ = AsyncMock(return_value=mock_view)
            mock_view.__aexit__ = AsyncMock(return_value=None)
            mock_factory.return_value = mock_view

            response = client.post("/scans", json={})

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_count" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
        assert data["total_count"] == 0
        assert data["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_scans_post_returns_all_without_pagination(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Returns all scans when no pagination specified."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post("/scans", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10
        assert len(data["items"]) == 10
        assert data["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_scans_post_with_filter(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Filter reduces results."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                "/scans",
                json={"filter": {"left": "complete", "operator": "=", "right": True}},
            )

        assert response.status_code == 200
        data = response.json()
        # 75% complete (i % 4 != 0)
        assert data["total_count"] in [7, 8]
        assert len(data["items"]) == data["total_count"]

    @pytest.mark.asyncio
    async def test_scans_post_with_order_by(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Results are sorted by specified column."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                "/scans",
                json={"order_by": {"column": "timestamp", "direction": "DESC"}},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10

        # Verify descending order by timestamp
        timestamps = [item["spec"]["timestamp"] for item in data["items"]]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_scans_post_with_pagination_limit(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Pagination limit restricts returned items."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                "/scans",
                json={
                    "pagination": {"limit": 3, "cursor": None, "direction": "forward"}
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10  # Total unchanged
        assert len(data["items"]) == 3  # Limited
        assert data["next_cursor"] is not None  # More available

    @pytest.mark.asyncio
    async def test_scans_post_pagination_next_cursor(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Next cursor allows fetching next page."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            # First page
            response1 = client.post(
                "/scans",
                json={
                    "pagination": {"limit": 3, "cursor": None, "direction": "forward"},
                    "order_by": {"column": "scan_id", "direction": "ASC"},
                },
            )

            assert response1.status_code == 200
            data1 = response1.json()
            assert len(data1["items"]) == 3
            cursor = data1["next_cursor"]
            assert cursor is not None

            # Second page using cursor
            response2 = client.post(
                "/scans",
                json={
                    "pagination": {
                        "limit": 3,
                        "cursor": cursor,
                        "direction": "forward",
                    },
                    "order_by": {"column": "scan_id", "direction": "ASC"},
                },
            )

            assert response2.status_code == 200
            data2 = response2.json()
            assert len(data2["items"]) == 3

            # Items should be different (next page)
            ids1 = {item["spec"]["scan_id"] for item in data1["items"]}
            ids2 = {item["spec"]["scan_id"] for item in data2["items"]}
            assert ids1.isdisjoint(ids2)

    @pytest.mark.asyncio
    async def test_scans_post_filter_and_pagination(
        self, mock_scan_jobs_view: DuckDBScanJobsView
    ) -> None:
        """Filter and pagination work together."""
        client = TestClient(v2_api_app(results_dir="/tmp"))

        with patch(
            "inspect_scout._view._api_v2.scan_jobs_view",
            return_value=mock_scan_jobs_view,
        ):
            response = client.post(
                "/scans",
                json={
                    "filter": {"left": "complete", "operator": "=", "right": True},
                    "pagination": {"limit": 2, "cursor": None, "direction": "forward"},
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Total reflects filter, not pagination
        assert data["total_count"] in [7, 8]
        assert len(data["items"]) == 2
        # All returned items match filter
        for item in data["items"]:
            assert item["complete"] is True
