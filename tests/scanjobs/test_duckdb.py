"""Tests for DuckDB ScanJobsView implementation."""

from datetime import datetime
from typing import AsyncIterator

import pytest
import pytest_asyncio
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanjobs.columns import scan_job_columns as c
from inspect_scout._scanjobs.duckdb import DuckDBScanJobsView
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2_types import OrderBy


def create_test_status(
    scan_id: str = "test-scan-001",
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
        model=None,  # ModelConfig not simple str
        scanners={s: ScannerSpec(name=s) for s in scanners},
    )

    return Status(
        complete=complete,
        spec=spec,
        location=f"/path/to/scans/scan_id={scan_id}",
        summary=Summary(scanners=scanners),
        errors=[],
    )


def create_test_statuses(count: int = 10) -> list[Status]:
    """Create multiple test Status objects with varied data."""
    statuses = []
    models = ["openai/gpt-4", "openai/gpt-3.5-turbo", "anthropic/claude-3-opus"]
    scanner_sets = [
        ["refusal"],
        ["reward_hacking", "efficiency"],
        ["refusal", "deception"],
    ]

    for i in range(count):
        statuses.append(
            create_test_status(
                scan_id=f"scan-{i:03d}",
                scan_name=f"job_{i % 3}",
                complete=i % 4 != 0,  # 25% incomplete
                model=models[i % 3],
                scanners=scanner_sets[i % 3],
                timestamp=datetime(2025, 1, 1, i, 0, 0),
            )
        )

    return statuses


@pytest.fixture
def sample_statuses() -> list[Status]:
    """Create sample Status objects for testing."""
    return create_test_statuses(10)


@pytest_asyncio.fixture
async def duckdb_view(
    sample_statuses: list[Status],
) -> AsyncIterator[DuckDBScanJobsView]:
    """Create and connect to a DuckDBScanJobsView with test data."""
    view = DuckDBScanJobsView(sample_statuses)
    await view.connect()
    yield view
    await view.disconnect()


# Basic Operations Tests
@pytest.mark.asyncio
async def test_connect_disconnect(sample_statuses: list[Status]) -> None:
    """Test view connection lifecycle."""
    view = DuckDBScanJobsView(sample_statuses)

    # Initially not connected
    assert view._conn is None

    # Connect
    await view.connect()
    assert view._conn is not None

    # Disconnect
    await view.disconnect()
    assert view._conn is None


@pytest.mark.asyncio
async def test_select_all(duckdb_view: DuckDBScanJobsView) -> None:
    """Test selecting all scan jobs."""
    results = [status async for status in duckdb_view.select()]
    assert len(results) == 10

    # Verify Status structure
    first = results[0]
    assert isinstance(first, Status)
    assert first.spec.scan_id is not None
    assert first.location is not None


@pytest.mark.asyncio
async def test_select_with_filter(duckdb_view: DuckDBScanJobsView) -> None:
    """Test filtering by condition."""
    condition = c.complete == True  # noqa: E712
    results = [status async for status in duckdb_view.select(where=[condition])]

    # 75% should be complete (i % 4 != 0)
    assert len(results) == 7 or len(results) == 8

    # Verify all results match condition
    for status in results:
        assert status.complete is True


@pytest.mark.asyncio
async def test_select_with_filter_by_scan_name(duckdb_view: DuckDBScanJobsView) -> None:
    """Test filtering by scan_name."""
    condition = c.scan_name == "job_0"
    results = [status async for status in duckdb_view.select(where=[condition])]

    # Should have ~3-4 results (10 total / 3 names)
    assert 3 <= len(results) <= 4

    for status in results:
        assert status.spec.scan_name == "job_0"


@pytest.mark.asyncio
async def test_select_with_order_by(duckdb_view: DuckDBScanJobsView) -> None:
    """Test ordering results."""
    results = [
        status
        async for status in duckdb_view.select(order_by=[OrderBy("timestamp", "ASC")])
    ]

    timestamps = [status.spec.timestamp for status in results]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_select_with_order_by_desc(duckdb_view: DuckDBScanJobsView) -> None:
    """Test ordering results descending."""
    results = [
        status
        async for status in duckdb_view.select(order_by=[OrderBy("timestamp", "DESC")])
    ]

    timestamps = [status.spec.timestamp for status in results]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_select_with_limit(duckdb_view: DuckDBScanJobsView) -> None:
    """Test limiting results."""
    results = [status async for status in duckdb_view.select(limit=5)]
    assert len(results) == 5


@pytest.mark.asyncio
async def test_select_with_filter_and_limit(duckdb_view: DuckDBScanJobsView) -> None:
    """Test filtering and limiting together."""
    condition = c.complete == True  # noqa: E712
    results = [
        status async for status in duckdb_view.select(where=[condition], limit=3)
    ]
    assert len(results) == 3

    for status in results:
        assert status.complete is True


@pytest.mark.asyncio
async def test_count(duckdb_view: DuckDBScanJobsView) -> None:
    """Test counting all scan jobs."""
    count = await duckdb_view.count()
    assert count == 10


@pytest.mark.asyncio
async def test_count_with_filter(duckdb_view: DuckDBScanJobsView) -> None:
    """Test counting with filter condition."""
    condition = c.complete == True  # noqa: E712
    count = await duckdb_view.count(where=[condition])

    # 75% should be complete
    assert count == 7 or count == 8


@pytest.mark.asyncio
async def test_count_with_scan_name_filter(duckdb_view: DuckDBScanJobsView) -> None:
    """Test counting with scan_name filter."""
    count = await duckdb_view.count(where=[c.scan_name == "job_0"])
    assert 3 <= count <= 4
