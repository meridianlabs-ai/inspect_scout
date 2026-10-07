"""Tests for import command completion messaging in import_command."""

from pathlib import Path
from typing import Any, AsyncIterator, Callable

import pytest
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._cli.import_command import _run_import
from inspect_scout._query import Query
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.types import Transcript, TranscriptContent


def _sample_transcript(id: str) -> Transcript:
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id="source-001",
        source_uri=f"test://{id}",
        metadata={},
        messages=[ChatMessageUser(content="Test message")],
        events=[],
    )


def _sample_transcript_with_message(id: str, message: str) -> Transcript:
    return _sample_transcript(id).model_copy(
        update={"messages": [ChatMessageUser(content=message)]}
    )


def _source_with(
    transcripts: list[Transcript],
) -> Callable[..., AsyncIterator[Transcript]]:
    """Create a source function yielding the given transcripts."""

    async def source(**kwargs: Any) -> AsyncIterator[Transcript]:
        for transcript in transcripts:
            yield transcript

    return source


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("transcripts", "expected", "not_expected"),
    [
        pytest.param(
            [],
            ["No transcripts were imported"],
            ["scout view"],
            id="empty_source",
        ),
        pytest.param(
            [_sample_transcript("t-001")],
            ["Import complete", "scout view"],
            ["No transcripts were imported"],
            id="non_empty_source",
        ),
    ],
)
async def test_run_import_completion_message(
    transcripts: list[Transcript],
    expected: list[str],
    not_expected: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transcripts_dir = str(tmp_path / "transcripts")

    await _run_import(_source_with(transcripts), "test-source", {}, transcripts_dir)

    output = capsys.readouterr().out
    for fragment in expected:
        assert fragment in output
    for fragment in not_expected:
        assert fragment not in output


@pytest.mark.asyncio
async def test_run_import_does_not_reimport_existing_transcripts(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Repeated imports are additive: existing transcript IDs are not rewritten."""
    transcripts_dir = str(tmp_path / "transcripts")
    initial = _sample_transcript_with_message("thread-001", "initial turn")
    resumed = _sample_transcript_with_message("thread-001", "resumed turn")

    await _run_import(_source_with([initial]), "test-source", {}, transcripts_dir)
    await _run_import(_source_with([resumed]), "test-source", {}, transcripts_dir)

    caplog.clear()
    async with transcripts_db(transcripts_dir) as db:
        infos = [info async for info in db.select(Query())]
        assert len(infos) == 1
        transcript = await db.read(
            infos[0], TranscriptContent(messages="all", events="all")
        )

    assert transcript.messages[0].text == "initial turn"
    assert len(list(Path(transcripts_dir).glob("*.parquet"))) == 1
    assert "Index is stale" not in caplog.text
