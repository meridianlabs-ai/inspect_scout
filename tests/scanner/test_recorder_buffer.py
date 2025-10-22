from __future__ import annotations

import tempfile
from typing import Generator

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._recorder.buffer import RecorderBuffer, scanner_table
from inspect_scout._scanner.result import Reference, Result, ResultReport
from inspect_scout._scanspec import ScanScanner, ScanSpec, ScanTranscripts
from inspect_scout._transcript.types import TranscriptInfo


@pytest.fixture
def recorder_buffer() -> Generator[RecorderBuffer]:
    """Create a temporary RecorderBuffer for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = ScanSpec(
            scan_name="myscan",
            transcripts=ScanTranscripts(
                type="eval_log",
                fields=[],
                count=0,
                data="",
            ),
            scanners={
                "test_scanner": ScanScanner(name="test_scanner"),
                "test-scanner.with:special/chars": ScanScanner(
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
        id="test-transcript-123",
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
            input_id="",
            result=Result(
                value="correct",
                answer="42",
                explanation="The answer to everything",
                metadata={"confidence": 0.95},
                references=[Reference(type="message", id="msg-1")],
            ),
            error=None,
            events=[],
            model_usage={},
        ),
        ResultReport(
            input_type="transcript",
            input_id="",
            result=Result(
                value=True,
                answer="yes",
                explanation="Affirmative response",
                metadata={"confidence": 0.88},
                references=[Reference(type="event", id="evt-1")],
            ),
            error=None,
            events=[],
            model_usage={},
        ),
        ResultReport(
            input_type="transcript",
            input_id="",
            result=Result(
                value=3.14159,
                answer=None,
                explanation="Pi value",
                metadata=None,
                references=[],
            ),
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
    is_recorded = await recorder_buffer.is_recorded(sample_transcript, scanner_name)
    assert is_recorded is False

    # Record data
    await recorder_buffer.record(sample_transcript, scanner_name, sample_results)

    # Check after recording
    is_recorded = await recorder_buffer.is_recorded(sample_transcript, scanner_name)
    assert is_recorded is True

    # Check with different transcript ID
    other_transcript = TranscriptInfo(
        id="other-transcript-456", source_id="42", source_uri="/other/source.log"
    )
    is_recorded = await recorder_buffer.is_recorded(other_transcript, scanner_name)
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
    await recorder_buffer.record(sample_transcript, scanner_name, sample_results)

    # Should still be able to retrieve
    scanner_table(recorder_buffer._buffer_dir, scanner_name)
