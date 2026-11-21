"""Tests that FileRecorder init/resume/attach manage summary and errors correctly."""

from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result
from inspect_scout._recorder.buffer import (
    SCAN_ERRORS,
    RecorderBuffer,
    cleanup_buffer_dir,
)
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._scanner.result import Error, ResultReport
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._transcript.types import TranscriptInfo


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
    """`resume` restores the summary of the results synced to the scan dir."""
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)
    for transcript_id, value in [("t1", 1), ("t2", 0)]:
        await rec1.record(
            TranscriptInfo(
                transcript_id=transcript_id,
                source_type="test",
                source_id="src",
                source_uri=f"test://{transcript_id}",
            ),
            "s",
            [
                ResultReport(
                    input_type="message",
                    input_ids=[],
                    input=ChatMessageUser(content=""),
                    result=Result(value=value),
                    validation=None,
                    error=None,
                    events=[],
                    model_usage={},
                )
            ],
            None,
        )
    # syncing as complete also cleans the buffer
    await FileRecorder.sync(rec1.scan_dir.as_posix(), complete=True)

    rec2 = FileRecorder()
    await rec2.resume(rec1.scan_dir.as_posix())
    assert rec2._scan_buffer.scan_summary().scanners["s"].scans == 2
    assert rec2._scan_buffer.scan_summary().scanners["s"].results == 1


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
async def test_resume_drops_errors_without_errored_results(
    tmp_path: Path, scout_buffer_dir: Path
) -> None:
    """`resume` keeps only the errors of transcripts whose results are errors.

    Errored transcripts are re-processed (is_recorded returns False for
    errored results). An error entry with no errored result behind it is
    stale and would incorrectly mark the scan as incomplete.
    """
    scans_location = str(tmp_path / "scans")
    spec = _make_spec(["s"])

    rec1 = FileRecorder()
    await rec1.init(spec, scans_location)
    stale = Error(
        transcript_id="t1", scanner="s", error="test", traceback="", refusal=False
    )
    with open(str(rec1._scan_buffer._error_file), "w") as f:
        f.write(stale.model_dump_json() + "\n")

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
