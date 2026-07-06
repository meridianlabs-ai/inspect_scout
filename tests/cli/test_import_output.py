"""Tests for import command completion messaging in import_command."""

from pathlib import Path
from typing import Any, AsyncIterator, Callable

import pytest
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._cli.import_command import _run_import
from inspect_scout._transcript.types import Transcript


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
