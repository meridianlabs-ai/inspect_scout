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


def _split_response_lines() -> list[dict[str, Any]]:
    """A response (`msg_assistant_010`) split in two by a user line."""
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
    return [prompt, first, between, second, result, final]


@pytest.mark.asyncio
async def test_response_split_by_another_line_gets_distinct_ids(
    tmp_path: Path,
) -> None:
    transcript = await _import_lines(
        tmp_path / "session" / "session.jsonl", _split_response_lines()
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
async def test_split_response_id_gives_way_to_a_reply_with_that_id(
    tmp_path: Path,
) -> None:
    lines = _split_response_lines()
    split = ids(
        (await _import_lines(tmp_path / "first" / "session.jsonl", lines)).messages
    )[3]
    assert split is not None
    lines[-1]["message"]["id"] = split

    transcript = await _import_lines(tmp_path / "second" / "session.jsonl", lines)

    assert ids(transcript.messages) == [
        "tool-001",
        "msg_assistant_010",
        "between",
        f"{split}.1",
        "tool-003",
        split,
    ]
    assert_message_ids_consistent(transcript)


def _split_reply(lines: list[dict[str, Any]], index: int) -> list[dict[str, Any]]:
    """Split the one-text-block reply at `index` in two around a user line."""
    reply = lines[index]
    text = reply["message"]["content"][0]["text"]
    first, second = (
        {
            **reply,
            "uuid": f"{reply['uuid']}-{part}",
            "message": {**reply["message"], "content": [{"type": "text", "text": t}]},
        }
        for part, t in (("a", text[:20]), ("b", text[20:]))
    )
    user = next(line for line in lines if line["type"] == "user")
    between = {
        **user,
        "uuid": f"{reply['uuid']}-between",
        "parentUuid": first["uuid"],
        "message": {"role": "user", "content": "go on"},
    }
    second["parentUuid"] = between["uuid"]
    for line in lines[index + 1 :]:
        if line.get("parentUuid") == reply["uuid"]:
            line["parentUuid"] = second["uuid"]
    return [*lines[:index], first, between, second, *lines[index + 1 :]]


AGENT = "a7e501"


def _agent_session_lines() -> list[dict[str, Any]]:
    """`agent_session.jsonl`, with a hex agent ID so its Task agent loads."""
    session = _lines("agent_session.jsonl")
    session[2]["message"]["content"][0]["content"][1]["text"] = f"agentId: {AGENT}"
    session[2]["toolUseResult"]["agentId"] = AGENT
    return session


async def _reply_ids(
    directory: Path, files: dict[str, list[dict[str, Any]]]
) -> dict[str, str | None]:
    """Import a directory's sessions as one transcript; map call uuids to reply IDs."""
    directory.mkdir()
    for name, lines in files.items():
        (directory / f"{name}.jsonl").write_text(
            "".join(json.dumps(line) + "\n" for line in lines)
        )
    [transcript] = [t async for t in claude_code(path=directory)]
    assert_message_ids_consistent(transcript)
    return {
        e.uuid: e.output.message.id
        for e in transcript.events
        if isinstance(e, ModelEvent) and e.output.choices and e.uuid
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("split_in_agent", [False, True])
async def test_split_response_id_gives_way_to_a_real_id_across_agents(
    tmp_path: Path, split_in_agent: bool
) -> None:
    session = _agent_session_lines()
    agent = _lines("agent-atest01.jsonl")
    # One side splits its final reply; the other's real reply ID will equal
    # the second fragment's edit ID.
    if split_in_agent:
        agent, real = _split_reply(agent, 3), session[3]
        split = "sidechain-004-b"
    else:
        session, real = _split_reply(session, 3), agent[1]
        split = "agent-004-b"
    files = {"session": session, f"agent-{AGENT}": agent}
    edit = (await _reply_ids(tmp_path / "first", files))[split]
    assert edit is not None
    real["message"]["id"] = edit

    replies = await _reply_ids(tmp_path / "second", files)

    assert replies[real["uuid"]] == edit
    assert replies[split] == f"{edit}.1"


@pytest.mark.asyncio
@pytest.mark.parametrize("split_in_first", [True, False])
async def test_split_response_id_gives_way_to_a_real_id_across_merged_sessions(
    tmp_path: Path, split_in_first: bool
) -> None:
    plan = _lines("slug_session_1.jsonl")
    execute = _lines("slug_session_2.jsonl")
    if split_in_first:
        plan, real, split = _split_reply(plan, 1), execute[1], "s1-002-b"
    else:
        execute, real, split = _split_reply(execute, 1), plan[1], "s2-002-b"
    files = {"plan": plan, "execute": execute}
    edit = (await _reply_ids(tmp_path / "first", files))[split]
    assert edit is not None
    real["message"]["id"] = edit

    replies = await _reply_ids(tmp_path / "second", files)

    assert replies[real["uuid"]] == edit
    assert replies[split] == f"{edit}.1"


@pytest.mark.asyncio
async def test_unpaired_model_events_are_an_error() -> None:
    lines = parse_events(_lines("simple_conversation.jsonl"))
    events: list[Event] = [e async for e in process_parsed_events(lines)]
    first_call = next(i for i, e in enumerate(events) if isinstance(e, ModelEvent))
    del events[first_call]

    with pytest.raises(RuntimeError, match="1 model events from 2 assistant lines"):
        apply_source_ids(lines, events)
