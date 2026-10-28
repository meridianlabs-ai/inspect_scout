"""Claude Code imports keep Claude Code's own message and call IDs."""

from pathlib import Path

import pytest
from inspect_scout import Transcript
from inspect_scout.sources import claude_code

from tests.sources.message_id_checks import assert_message_ids_consistent, ids

FIXTURES = Path(__file__).parent / "fixtures"


async def _import(name: str) -> list[Transcript]:
    return [t async for t in claude_code(path=FIXTURES / name)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture,messages,messages_from",
    [
        (
            "tool_call_conversation.jsonl",
            ["tool-001", "msg_assistant_010", "tool-003", "msg_assistant_011"],
            ["tool-004"],
        ),
        (
            # Spliced across a compaction: one source call per segment.
            "compaction_session.jsonl",
            [
                "compact-001",
                "msg_assistant_040",
                "compact-004",
                "compact-005",
                "msg_assistant_041",
            ],
            ["compact-002", "compact-006"],
        ),
    ],
)
async def test_ids_come_from_the_session_file(
    fixture: str, messages: list[str], messages_from: list[str]
) -> None:
    [transcript] = await _import(fixture)
    assert ids(transcript.messages) == messages
    assert transcript.messages_from == messages_from


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture",
    [
        "simple_conversation.jsonl",
        "tool_call_conversation.jsonl",
        "compaction_session.jsonl",
        "agent_session.jsonl",
        "clear_split_session.jsonl",
    ],
)
async def test_ids_agree_with_events(fixture: str) -> None:
    transcripts = await _import(fixture)
    assert transcripts
    for transcript in transcripts:
        assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_merged_slug_sessions_record_each_sessions_call(
    tmp_path: Path,
) -> None:
    for name in ["slug_session_1.jsonl", "slug_session_2.jsonl"]:
        (tmp_path / name).write_text((FIXTURES / name).read_text())

    [merged] = [t async for t in claude_code(path=tmp_path)]

    assert merged.messages_from == ["s1-002", "s2-002"]
    assert_message_ids_consistent(merged)
