"""Tests that FileRecorder.list returns locations in the caller's format."""

from pathlib import Path

import pytest
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._recorder.recorder import Status
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


@pytest.mark.asyncio
async def test_list_skips_scan_that_vanished_after_listing(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """A scan that disappears between listing and read is skipped, not fatal.

    Listing and then reading each scan is inherently racy on a remote store,
    so a scan can go away in between. That must cost one entry rather than the
    whole listing.
    """
    scans_dir = tmp_path / "scans"
    kept_spec = _make_spec(["s"])
    await FileRecorder().init(kept_spec, scans_dir.as_posix())
    vanished_spec = _make_spec(["s"])
    await FileRecorder().init(vanished_spec, scans_dir.as_posix())
    (scans_dir / f"scan_id={vanished_spec.scan_id}" / "_scan.json").unlink()

    statuses = await FileRecorder.list(scans_dir.as_posix())

    assert {s.spec.scan_id for s in statuses} == {kept_spec.scan_id}


@pytest.mark.asyncio
async def test_list_returns_every_readable_scan_when_one_is_missing(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """One missing scan must not cancel the reads of its siblings.

    Concurrent reads share a task group, so a failure that isn't contained
    would cancel the scans queued alongside it. Three scans with the failure
    in the middle also pins that results stay aligned with their scans.
    """
    scans_dir = tmp_path / "scans"
    specs = [_make_spec(["s"]) for _ in range(3)]
    for spec in specs:
        await FileRecorder().init(spec, scans_dir.as_posix())
    (scans_dir / f"scan_id={specs[1].scan_id}" / "_scan.json").unlink()

    statuses = await FileRecorder.list(scans_dir.as_posix())

    assert {s.spec.scan_id for s in statuses} == {specs[0].scan_id, specs[2].scan_id}


@pytest.mark.asyncio
async def test_list_propagates_error_other_than_missing_scan(
    tmp_path: Path, scout_buffer_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read error that isn't a missing scan surfaces, naming that scan."""
    scans_dir = tmp_path / "scans"
    kept_spec = _make_spec(["s"])
    await FileRecorder().init(kept_spec, scans_dir.as_posix())
    denied_spec = _make_spec(["s"])
    await FileRecorder().init(denied_spec, scans_dir.as_posix())

    real_status = FileRecorder.status

    async def status(scan_location: str) -> Status:
        if f"scan_id={denied_spec.scan_id}" in scan_location:
            raise PermissionError(scan_location)
        return await real_status(scan_location)

    monkeypatch.setattr(FileRecorder, "status", staticmethod(status))

    with pytest.raises(PermissionError, match=denied_spec.scan_id):
        await FileRecorder.list(scans_dir.as_posix())
