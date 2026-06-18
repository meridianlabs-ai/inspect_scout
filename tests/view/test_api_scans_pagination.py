"""Tests for /scans endpoint pagination support."""

import base64
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2 import v2_api_app


def _base64url(s: str) -> str:
    """Encode string as base64url (URL-safe base64 without padding)."""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _write_scan(
    scans_dir: Path,
    *,
    scan_id: str,
    scan_name: str,
    complete: bool,
    timestamp: datetime,
    scanners: list[str],
) -> None:
    """Write a real on-disk scan dir using real model serialization."""
    scan_dir = scans_dir / f"scan_id={scan_id}"
    scan_dir.mkdir(parents=True)
    spec = ScanSpec(
        scan_id=scan_id,
        scan_name=scan_name,
        timestamp=timestamp,
        model=None,
        scanners={s: ScannerSpec(name=s) for s in scanners},
    )
    (scan_dir / "_scan.json").write_text(spec.model_dump_json())
    summary = Summary(scanners=scanners)
    summary.complete = complete
    (scan_dir / "_summary.json").write_text(summary.model_dump_json())


def _write_test_scans(scans_dir: Path, count: int = 10) -> None:
    """Write test scans to disk mirroring the prior _create_test_statuses data."""
    scanner_sets = [["refusal"], ["reward_hacking"], ["deception"]]
    for i in range(count):
        _write_scan(
            scans_dir,
            scan_id=f"scan-{i:03d}",
            scan_name=f"job_{i % 3}",
            complete=i % 4 != 0,
            timestamp=datetime(2025, 1, 1, i, 0, 0),
            scanners=scanner_sets[i % 3],
        )


@pytest.fixture
def scans_dir(tmp_path: Path) -> Path:
    """Create a real scans directory with test data."""
    d = tmp_path / "scans"
    d.mkdir()
    _write_test_scans(d, 10)
    return d


class TestScansEndpointPagination:
    """Tests for /scans endpoint with pagination support."""

    def test_scans_post_returns_response_structure(self, tmp_path: Path) -> None:
        """Verify POST /scans returns items, total_count, next_cursor."""
        client = TestClient(v2_api_app())
        empty_dir = tmp_path / "empty_scans"
        empty_dir.mkdir()

        response = client.post(f"/scans/{_base64url(str(empty_dir))}", json={})

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_count" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)
        assert data["total_count"] == 0
        assert data["next_cursor"] is None

    def test_scans_post_returns_all_without_pagination(self, scans_dir: Path) -> None:
        """Returns all scans when no pagination specified."""
        client = TestClient(v2_api_app())

        response = client.post(f"/scans/{_base64url(str(scans_dir))}", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10
        assert len(data["items"]) == 10
        assert data["next_cursor"] is None

    def test_scans_post_with_filter(self, scans_dir: Path) -> None:
        """Filter reduces results."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}",
            json={"filter": {"left": "status", "operator": "=", "right": "complete"}},
        )

        assert response.status_code == 200
        data = response.json()
        # 75% complete (i % 4 != 0)
        assert data["total_count"] in [7, 8]
        assert len(data["items"]) == data["total_count"]

    def test_scans_post_with_order_by(self, scans_dir: Path) -> None:
        """Results are sorted by specified column."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}",
            json={"order_by": {"column": "timestamp", "direction": "DESC"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10

        # Verify descending order by timestamp
        timestamps = [item["timestamp"] for item in data["items"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_scans_post_with_pagination_limit(self, scans_dir: Path) -> None:
        """Pagination limit restricts returned items."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}",
            json={"pagination": {"limit": 3, "cursor": None, "direction": "forward"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 10  # Total unchanged
        assert len(data["items"]) == 3  # Limited
        assert data["next_cursor"] is not None  # More available

    def test_scans_post_pagination_next_cursor(self, scans_dir: Path) -> None:
        """Next cursor allows fetching next page."""
        client = TestClient(v2_api_app())

        # First page
        response1 = client.post(
            f"/scans/{_base64url(str(scans_dir))}",
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
            f"/scans/{_base64url(str(scans_dir))}",
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
        ids1 = {item["scan_id"] for item in data1["items"]}
        ids2 = {item["scan_id"] for item in data2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_scans_post_filter_and_pagination(self, scans_dir: Path) -> None:
        """Filter and pagination work together."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}",
            json={
                "filter": {"left": "status", "operator": "=", "right": "complete"},
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
            assert item["status"] == "complete"
