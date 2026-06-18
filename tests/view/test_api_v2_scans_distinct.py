"""Tests for POST /scans/{dir}/distinct endpoint."""

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


@pytest.fixture
def scans_dir(tmp_path: Path) -> Path:
    """Create a real scans directory with test data mirroring the prior fixture."""
    d = tmp_path / "scans"
    d.mkdir()
    _write_scan(
        d,
        scan_id="scan-001",
        scan_name="math_eval",
        complete=True,
        timestamp=datetime(2025, 1, 1, 1, 0, 0),
        scanners=["refusal"],
    )
    _write_scan(
        d,
        scan_id="scan-002",
        scan_name="math_eval",
        complete=True,
        timestamp=datetime(2025, 1, 1, 2, 0, 0),
        scanners=["deception"],
    )
    _write_scan(
        d,
        scan_id="scan-003",
        scan_name="coding_eval",
        complete=True,
        timestamp=datetime(2025, 1, 1, 3, 0, 0),
        scanners=["refusal"],
    )
    _write_scan(
        d,
        scan_id="scan-004",
        scan_name="coding_eval",
        complete=True,
        timestamp=datetime(2025, 1, 1, 4, 0, 0),
        scanners=["efficiency"],
    )
    _write_scan(
        d,
        scan_id="scan-005",
        scan_name="qa_eval",
        complete=True,
        timestamp=datetime(2025, 1, 1, 5, 0, 0),
        scanners=["refusal"],
    )
    return d


class TestScansDistinctEndpoint:
    """Tests for POST /scans/{dir}/distinct endpoint."""

    def test_distinct_no_filter(self, scans_dir: Path) -> None:
        """Get distinct values without filter."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}/distinct",
            json={"column": "scan_name"},
        )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"coding_eval", "math_eval", "qa_eval"}
        # Verify sorted ascending
        assert values == sorted(values)

    def test_distinct_with_filter(self, scans_dir: Path) -> None:
        """Get distinct values with filter condition."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}/distinct",
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

    def test_distinct_empty_result(self, scans_dir: Path) -> None:
        """Get distinct values with no matching results."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}/distinct",
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

    def test_distinct_no_body(self, scans_dir: Path) -> None:
        """Request with no body returns empty list."""
        client = TestClient(v2_api_app())

        response = client.post(f"/scans/{_base64url(str(scans_dir))}/distinct")

        assert response.status_code == 200
        assert response.json() == []

    def test_distinct_different_column(self, scans_dir: Path) -> None:
        """Get distinct values for different column."""
        client = TestClient(v2_api_app())

        response = client.post(
            f"/scans/{_base64url(str(scans_dir))}/distinct",
            json={"column": "scanners"},
        )

        assert response.status_code == 200
        values = response.json()
        assert set(values) == {"deception", "efficiency", "refusal"}
        assert values == sorted(values)
