from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._recorder.buffer import RecorderBuffer, scanner_table
from inspect_scout._scanner.result import Reference, Result, ResultReport
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._transcript.types import TranscriptInfo


@pytest.fixture
def recorder_buffer() -> Generator[RecorderBuffer]:
    """Create a temporary RecorderBuffer for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = ScanSpec(
            scan_name="myscan",
            scanners={
                "test_scanner": ScannerSpec(name="test_scanner"),
                "test-scanner.with:special/chars": ScannerSpec(
                    name="test-scanner.with:special/chars"
                ),
            },
        )
        buffer = RecorderBuffer(tmpdir, spec)
        yield buffer
        buffer.cleanup()


@pytest.fixture
def sample_transcript() -> TranscriptInfo:
    """Create a sample TranscriptInfo for testing."""
    return TranscriptInfo(
        transcript_id="test-transcript-123",
        source_type="test",
        source_id="source-42",
        source_uri="/path/to/source.log",
        metadata={"model": "gpt-4", "temperature": 0.7},
    )


@pytest.fixture
def sample_results() -> list[ResultReport]:
    """Create sample Results for testing."""
    return [
        ResultReport(
            input_type="transcript",
            input_ids=[],
            input=ChatMessageUser(content=""),
            result=Result(
                value="correct",
                explanation="The answer to everything",
                metadata={"confidence": 0.95},
                references=[Reference(type="message", id="msg-1")],
            ),
            validation=None,
            error=None,
            events=[],
            model_usage={},
        ),
        ResultReport(
            input_type="transcript",
            input_ids=[],
            input=ChatMessageUser(content=""),
            result=Result(
                value=True,
                explanation="Affirmative response",
                metadata={"confidence": 0.88},
                references=[Reference(type="event", id="evt-1")],
            ),
            validation=None,
            error=None,
            events=[],
            model_usage={},
        ),
        ResultReport(
            input_type="transcript",
            input_ids=[],
            input=ChatMessageUser(content=""),
            result=Result(
                value=3.14159,
                explanation="Pi value",
                metadata=None,
                references=[],
            ),
            validation=None,
            error=None,
            events=[],
            model_usage={},
        ),
    ]


@pytest.mark.asyncio
async def test_is_recorded(
    recorder_buffer: RecorderBuffer,
    sample_transcript: TranscriptInfo,
    sample_results: list[ResultReport],
) -> None:
    """Test is_recorded method."""
    scanner_name = "test_scanner"

    # Check before recording
    is_recorded = await recorder_buffer.is_recorded(
        sample_transcript.transcript_id, scanner_name
    )
    assert is_recorded is False

    # Record data
    await recorder_buffer.record(sample_transcript, scanner_name, sample_results, None)

    # Check after recording
    is_recorded = await recorder_buffer.is_recorded(
        sample_transcript.transcript_id, scanner_name
    )
    assert is_recorded is True

    # Check with different transcript ID
    other_transcript = TranscriptInfo(
        transcript_id="other-transcript-456",
        source_type="test",
        source_id="42",
        source_uri="/other/source.log",
    )
    is_recorded = await recorder_buffer.is_recorded(
        other_transcript.transcript_id, scanner_name
    )
    assert is_recorded is False


@pytest.mark.asyncio
async def test_sanitize_table_names(
    recorder_buffer: RecorderBuffer,
    sample_transcript: TranscriptInfo,
    sample_results: list[ResultReport],
) -> None:
    """Test that table names with special characters are sanitized."""
    scanner_name = "test-scanner.with:special/chars"

    # Record with special characters in scanner name
    await recorder_buffer.record(sample_transcript, scanner_name, sample_results, None)

    # Should still be able to retrieve
    scanner_table(recorder_buffer._buffer_dir, scanner_name)


def test_buffer_dir_respects_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that SCOUT_SCANBUFFER_DIR env var overrides the default buffer location."""
    custom_dir = tmp_path / "custom_buffer"
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(custom_dir))
    result = RecorderBuffer.buffer_dir("/some/scan/location")
    assert result.parent == custom_dir


def test_buffer_dir_expands_tilde(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that ~ in SCOUT_SCANBUFFER_DIR is expanded to the home directory."""
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", "~/my_scout_buffer")
    monkeypatch.setenv("HOME", str(tmp_path))
    result = RecorderBuffer.buffer_dir("/some/scan/location")
    assert result.parent == tmp_path / "my_scout_buffer"
