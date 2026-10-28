"""Claude Code imports keep Claude Code's own message and call IDs."""

import json
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import Event, ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources import claude_code
from inspect_scout.sources._claude_code.events import process_parsed_events
from inspect_scout.sources._claude_code.message_ids import apply_source_ids
from inspect_swe._claude_code._events.models import parse_events

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


def _lines(name: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (FIXTURES / name).read_text().splitlines()]


async def _import_lines(path: Path, lines: list[dict[str, Any]]) -> Transcript:
    path.parent.mkdir()
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    [transcript] = [t async for t in claude_code(path=path)]
    return transcript


@pytest.mark.asyncio
async def test_repeated_tool_call_id_on_one_line_gets_two_ids(tmp_path: Path) -> None:
    lines = _lines("tool_call_conversation.jsonl")
    result = lines[2]
    assert result["uuid"] == "tool-003"
    result["message"]["content"].append(
        {**result["message"]["content"][0], "content": "A second result."}
    )

    transcript = await _import_lines(tmp_path / "session" / "session.jsonl", lines)

    assert ids(transcript.messages) == [
        "tool-001",
        "msg_assistant_010",
        "tool-003",
        "tool-003-1",
        "msg_assistant_011",
    ]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_user_line_dropped_by_compaction_lends_no_id(tmp_path: Path) -> None:
    first, reply = _lines("simple_conversation.jsonl")[:2]
    boundary = _lines("compaction_session.jsonl")[2]
    boundary.update(uuid="boundary", parentUuid="msg-001", sessionId=first["sessionId"])
    again = {**first, "uuid": "after-compact", "parentUuid": "boundary"}
    reply["parentUuid"] = "after-compact"

    transcript = await _import_lines(
        tmp_path / "session" / "session.jsonl", [first, boundary, again, reply]
    )

    assert ids(transcript.messages) == ["after-compact", "msg_assistant_001"]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_reply_without_message_id_takes_its_line_uuid(tmp_path: Path) -> None:
    lines = _lines("simple_conversation.jsonl")
    for line in lines:
        if line["type"] == "assistant":
            del line["message"]["id"]

    first = await _import_lines(tmp_path / "first" / "session.jsonl", lines)
    second = await _import_lines(tmp_path / "second" / "session.jsonl", lines)

    assert ids(first.messages) == ["msg-001", "msg-002", "msg-003", "msg-004"]
    assert first.messages_from == ["msg-004"]
    assert ids(second.messages) == ids(first.messages)
    assert_message_ids_consistent(first)


@pytest.mark.asyncio
async def test_response_split_by_another_line_gets_distinct_ids(
    tmp_path: Path,
) -> None:
    prompt, response, result, final = _lines("tool_call_conversation.jsonl")
    text, tool_use = (
        response["message"]["content"][:2],
        response["message"]["content"][2:],
    )
    first = {**response, "uuid": "part-1", "message": {**response["message"]}}
    first["message"]["content"] = text
    second = {**response, "uuid": "part-2", "message": {**response["message"]}}
    second["message"]["content"] = tool_use
    between = {
        **prompt,
        "uuid": "between",
        "parentUuid": "part-1",
        "message": {"role": "user", "content": "go on"},
    }
    second["parentUuid"] = "between"
    result["parentUuid"] = "part-2"

    transcript = await _import_lines(
        tmp_path / "session" / "session.jsonl",
        [prompt, first, between, second, result, final],
    )

    message_ids = ids(transcript.messages)
    split = message_ids.pop(3)
    assert message_ids == [
        "tool-001",
        "msg_assistant_010",
        "between",
        "tool-003",
        "msg_assistant_011",
    ]
    assert split is not None and split.startswith("msg_assistant_010.")
    assert transcript.messages[3].metadata == transcript.messages[1].metadata
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_unpaired_model_events_are_an_error() -> None:
    lines = parse_events(_lines("simple_conversation.jsonl"))
    events: list[Event] = [e async for e in process_parsed_events(lines)]
    first_call = next(i for i, e in enumerate(events) if isinstance(e, ModelEvent))
    del events[first_call]

    with pytest.raises(RuntimeError, match="1 model events from 2 assistant lines"):
        apply_source_ids(lines, events)
