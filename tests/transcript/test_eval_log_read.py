"""Tests for EvalLogTranscriptsView.read() with legacy JSON format logs."""

from pathlib import Path

import pytest
from inspect_ai.log import read_eval_log, write_eval_log
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptTooLargeError,
)

TEST_EVAL_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
EVAL_LOG = (
    TEST_EVAL_LOGS_DIR
    / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
)


@pytest.fixture(scope="module")
def json_log(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Legacy JSON-format copy of the .eval fixture."""
    json_path = tmp_path_factory.mktemp("logs") / EVAL_LOG.with_suffix(".json").name
    write_eval_log(read_eval_log(str(EVAL_LOG)), str(json_path))
    return json_path


async def _read_first_transcript(
    log_path: Path, content: TranscriptContent, max_bytes: int | None = None
) -> Transcript:
    """Read the first transcript from a log file."""
    async with EvalLogTranscriptsView(str(log_path)) as view:
        async for info in view.select():
            return await view.read(info, content, max_bytes)
    raise AssertionError("No transcripts found")


@pytest.mark.asyncio
async def test_read_json_log_matches_eval_log(json_log: Path) -> None:
    """Reading a legacy JSON log yields the same content as the .eval log."""
    content = TranscriptContent(messages="all", events="all")

    eval_transcript = await _read_first_transcript(EVAL_LOG, content)
    json_transcript = await _read_first_transcript(json_log, content)

    assert json_transcript.messages == eval_transcript.messages
    assert json_transcript.events == eval_transcript.events


@pytest.mark.asyncio
async def test_read_json_log_builds_timeline_and_refilters_events(
    json_log: Path,
) -> None:
    """Timeline requests build timelines from events and re-filter events after."""
    content = TranscriptContent(messages="all", events=["model"], timeline="all")

    eval_transcript = await _read_first_transcript(EVAL_LOG, content)
    json_transcript = await _read_first_transcript(json_log, content)

    assert json_transcript.timelines
    assert json_transcript.timelines == eval_transcript.timelines
    assert all(event.event == "model" for event in json_transcript.events)
    assert json_transcript.events == eval_transcript.events


@pytest.mark.asyncio
async def test_read_json_log_respects_max_bytes(json_log: Path) -> None:
    """A JSON sample larger than max_bytes raises TranscriptTooLargeError."""
    content = TranscriptContent(messages="all", events="all")

    with pytest.raises(TranscriptTooLargeError):
        await _read_first_transcript(json_log, content, max_bytes=10)
