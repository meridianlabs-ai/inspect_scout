"""Tests that FileRecorder.list returns locations in the caller's format."""

from pathlib import Path

import pytest
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._scanspec import ScannerSpec, ScanSpec


def _make_spec(scanners: list[str]) -> ScanSpec:
    """Create a minimal ScanSpec for testing."""
    return ScanSpec(
        scan_name="test",
        scanners={s: ScannerSpec(name=s) for s in scanners},
    )


@pytest.fixture
def scout_buffer_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point SCOUT_SCANBUFFER_DIR at an isolated temp dir."""
    buf_dir = tmp_path / "buffer"
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(buf_dir))
    return buf_dir


@pytest.mark.asyncio
async def test_list_preserves_file_uri_locations(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """Listing a file:// location yields file:// scan locations.

    Callers (e.g. the VS Code extension) relativize Status.location against
    the scans location they requested, so the protocol must round-trip.
    """
    scans_dir = tmp_path / "scans"
    spec = _make_spec(["s"])
    rec = FileRecorder()
    await rec.init(spec, scans_dir.as_posix())

    statuses = await FileRecorder.list(scans_dir.as_uri())

    assert [s.location for s in statuses] == [
        f"{scans_dir.as_uri()}/scan_id={spec.scan_id}"
    ]


@pytest.mark.asyncio
async def test_list_plain_path_locations_unchanged(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """Listing a plain path location yields plain path scan locations."""
    scans_dir = tmp_path / "scans"
    spec = _make_spec(["s"])
    rec = FileRecorder()
    await rec.init(spec, scans_dir.as_posix())

    statuses = await FileRecorder.list(scans_dir.as_posix())

    assert [s.location for s in statuses] == [
        (scans_dir / f"scan_id={spec.scan_id}").as_posix()
    ]
