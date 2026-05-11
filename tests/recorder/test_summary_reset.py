"""Tests that FileRecorder init/resume/attach manage summary and errors correctly."""

from pathlib import Path

import pytest
from inspect_scout._recorder.buffer import (
    SCAN_ERRORS,
    SCAN_SUMMARY,
    RecorderBuffer,
    cleanup_buffer_dir,
)
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
async def test_init_resets_summary(tmp_path: Path, scout_buffer_dir: Path) -> None:
    """A second `init` with the same scan_id wipes stale buffer state."""
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)
    rec1._scan_buffer.scan_summary().scanners["s"].scans = 10
    rec1._scan_buffer.scan_summary().scanners["s"].results = 50

    rec2 = FileRecorder()
    await rec2.init(spec, scans_location)
    assert rec2._scan_buffer.scan_summary().scanners["s"].scans == 0
    assert rec2._scan_buffer.scan_summary().scanners["s"].results == 0


@pytest.mark.asyncio
async def test_resume_preserves_summary(tmp_path: Path, scout_buffer_dir: Path) -> None:
    """`resume` seeds the buffer summary from the scan dir."""
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)
    rec1._scan_buffer.scan_summary().scanners["s"].scans = 10
    rec1._scan_buffer.scan_summary().scanners["s"].results = 50

    # mimic FileRecorder.sync persisting the summary into the scan dir
    summary_path = rec1.scan_dir / SCAN_SUMMARY
    with open(str(summary_path), "w") as f:
        f.write(rec1._scan_buffer.scan_summary().model_dump_json(indent=2))

    # simulate post-sync(complete=True) state where the buffer was cleaned
    cleanup_buffer_dir(RecorderBuffer.buffer_dir(rec1.scan_dir.as_posix()))

    rec2 = FileRecorder()
    await rec2.resume(rec1.scan_dir.as_posix())
    assert rec2._scan_buffer.scan_summary().scanners["s"].scans == 10
    assert rec2._scan_buffer.scan_summary().scanners["s"].results == 50


@pytest.mark.asyncio
async def test_init_truncates_errors(tmp_path: Path, scout_buffer_dir: Path) -> None:
    """`init` cleans the buffer dir, including the errors file."""
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)
    with open(str(rec1._scan_buffer._error_file), "w") as f:
        f.write('{"error": "test"}\n')

    rec2 = FileRecorder()
    await rec2.init(spec, scans_location)
    # buffer dir is wiped by init, so the prior error file is gone
    assert not rec2._scan_buffer._error_file.exists()


@pytest.mark.asyncio
async def test_resume_truncates_errors(tmp_path: Path, scout_buffer_dir: Path) -> None:
    """`resume` truncates the errors file.

    Previously-errored transcripts are re-processed (is_recorded returns
    False for errored parquets). Stale error entries must not persist or
    they incorrectly mark the scan as incomplete when the retry succeeds.
    """
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)
    with open(str(rec1._scan_buffer._error_file), "w") as f:
        f.write('{"error": "test"}\n')

    rec2 = FileRecorder()
    await rec2.resume(rec1.scan_dir.as_posix())
    assert rec2._scan_buffer._error_file.read_text() == ""


@pytest.mark.asyncio
async def test_attach_preserves_errors(tmp_path: Path, scout_buffer_dir: Path) -> None:
    """`attach` seeds errors from the scan dir so prior runs aren't clobbered."""
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)

    # write errors into the scan dir as if a prior run had completed
    error_content = '{"error": "test"}\n'
    scan_errors = rec1.scan_dir / SCAN_ERRORS
    with open(str(scan_errors), "w") as f:
        f.write(error_content)

    # mimic post-sync(complete=True) state where the buffer was cleaned
    cleanup_buffer_dir(RecorderBuffer.buffer_dir(rec1.scan_dir.as_posix()))

    rec2 = FileRecorder()
    await rec2.attach(rec1.scan_dir.as_posix())
    assert rec2._scan_buffer._error_file.read_text() == error_content
