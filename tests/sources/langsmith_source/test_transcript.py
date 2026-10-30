"""LangSmith traces: message IDs, model call IDs and the transcript's conversation."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import TranscriptContent
from inspect_scout.sources._langsmith import _trace_to_transcript

from tests.sources.langsmith_source.mocks import (
    MockRun,
    create_anthropic_llm_run,
    create_chain_run,
    create_openai_llm_run,
    create_tool_run,
)
from tests.sources.message_id_checks import assert_message_ids_consistent, ids

START = datetime(2026, 1, 1)


def _at(run: MockRun, second: int) -> MockRun:
    run.start_time = START + timedelta(seconds=second)
    run.end_time = run.start_time + timedelta(milliseconds=500)
    return run


def _llm(
    run_id: str, parent: str, second: int, messages: list[dict[str, Any]], reply: str
) -> MockRun:
    run = create_openai_llm_run(run_id=run_id, parent_run_id=parent, messages=messages)
    run.outputs = {
        "id": f"chatcmpl-{run_id}",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
    }
    return _at(run, second)


SYSTEM = {"role": "system", "content": "You are a helpful assistant."}
HELLO = {"role": "user", "content": "Hello!"}
HI = {"role": "assistant", "content": "Hi! How can I help?"}
JOKE = {"role": "user", "content": "Tell me a joke."}


def _root_agent_trace() -> list[MockRun]:
    return [
        _at(create_chain_run(run_id="root"), 0),
        _llm("llm-1", "root", 1, [SYSTEM, HELLO], HI["content"]),
        _llm("llm-2", "root", 2, [SYSTEM, HELLO, HI, JOKE], "Why did..."),
    ]


async def _transcript(runs: list[MockRun]) -> Transcript:
    client = MagicMock()
    client.list_runs.return_value = runs
    client.api_url = "https://smith.example"
    transcript = await _trace_to_transcript(client, runs[0], "project")
    assert transcript is not None
    return transcript


@pytest.mark.asyncio
async def test_ids_come_from_each_messages_first_run() -> None:
    transcript = await _transcript(_root_agent_trace())

    llm_1, llm_2 = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert (llm_1.uuid, llm_2.uuid) == ("llm-1", "llm-2")
    assert ids(llm_1.input) == ["llm-1-0", "llm-1-1"]
    assert llm_1.output.message.id == "llm-1-2"
    assert ids(llm_2.input) == ["llm-1-0", "llm-1-1", "llm-1-2", "llm-2-3"]
    assert transcript.messages_from == ["llm-2"]
    assert_message_ids_consistent(transcript)


def _langchain(type: str, content: str, id: str | None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"type": type, "content": content}
    if id is not None:
        kwargs["id"] = id
    return {
        "lc": 1,
        "type": "constructor",
        "id": ["langchain", "schema", "messages", f"{type.title()}Message"],
        "kwargs": kwargs,
    }


def _langchain_llm(
    run_id: str, second: int, messages: list[dict[str, Any]], reply_id: str
) -> MockRun:
    run = _llm(run_id, "root", second, [], "")
    run.inputs = {"messages": [messages]}
    run.outputs = {
        "generations": [
            [
                {
                    "text": f"reply from {run_id}",
                    "type": "ChatGeneration",
                    "message": _langchain("ai", f"reply from {run_id}", reply_id),
                }
            ]
        ],
        "type": "LLMResult",
    }
    return run


@pytest.mark.asyncio
async def test_langchain_message_ids_are_kept() -> None:
    hello = _langchain("human", "Hello!", "human-1")
    runs = [
        _at(create_chain_run(run_id="root"), 0),
        _langchain_llm("llm-1", 1, [hello], "run-llm-1-0"),
        _langchain_llm(
            "llm-2",
            2,
            [
                hello,
                _langchain("ai", "reply from llm-1", "run-llm-1-0"),
                # No LangChain ID: gets its run's ID and position.
                _langchain("human", "And?", None),
            ],
            "run-llm-2-0",
        ),
    ]

    transcript = await _transcript(runs)

    llm_1, llm_2 = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert ids(llm_1.input) == ["human-1"]
    assert llm_1.output.message.id == "run-llm-1-0"
    assert ids(llm_2.input) == ["human-1", "run-llm-1-0", "llm-2-2"]
    assert ids(transcript.messages) == [
        "human-1",
        "run-llm-1-0",
        "llm-2-2",
        "run-llm-2-0",
    ]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_langchain_id_seen_later_names_earlier_copies() -> None:
    runs = [
        _at(create_chain_run(run_id="root"), 0),
        _llm("a", "root", 1, [HELLO], "reply1"),
        _langchain_llm(
            "b",
            2,
            [
                _langchain("human", "Hello!", None),
                _langchain("ai", "reply1", "reply-a-id"),
                _langchain("human", "And?", None),
            ],
            "reply-b-id",
        ),
        _llm(
            "c",
            "root",
            3,
            [HELLO, {"role": "assistant", "content": "reply1"}, JOKE],
            "Why did...",
        ),
    ]

    transcript = await _transcript(runs)

    a, b, c = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert a.output.message.id == "reply-a-id"
    assert ids(b.input) == ["a-0", "reply-a-id", "b-2"]
    assert ids(c.input) == ["a-0", "reply-a-id", "c-2"]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_langchain_id_equal_to_a_positional_id_names_only_its_message() -> None:
    runs = [
        _at(create_chain_run(run_id="root"), 0),
        _llm("a", "root", 1, [HELLO], "reply1"),
        _langchain_llm(
            "b", 2, [_langchain("human", "different content", "a-0")], "reply-b-id"
        ),
    ]

    transcript = await _transcript(runs)

    a, b = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert ids(b.input) == ["a-0"]
    assert ids(a.input) == ["a-0.1"]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_langchain_id_on_edited_content_takes_its_own_id() -> None:
    edited = _langchain("human", "Hello, edited", "human-1")
    runs = [
        _at(create_chain_run(run_id="root"), 0),
        _langchain_llm("a", 1, [_langchain("human", "Hello!", "human-1")], "r-a"),
        _langchain_llm("b", 2, [edited], "r-b"),
        _langchain_llm(
            "c", 3, [edited, _langchain("ai", "reply from b", "r-b")], "r-c"
        ),
    ]

    transcript = await _transcript(runs)
    again = await _transcript(runs)

    a, b, c = [e for e in transcript.events if isinstance(e, ModelEvent)]
    edit = b.input[0].id
    assert ids(a.input) == ["human-1"]
    assert edit is not None and edit.startswith("human-1.")
    assert ids(c.input) == [edit, "r-b"]
    assert [m.metadata for m in [*a.input, *b.input]] == [None, None]
    assert _input_ids(again) == _input_ids(transcript)
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_langchain_edit_id_depends_only_on_its_source_id_and_content() -> None:
    def trace(*contents: str) -> list[MockRun]:
        return [
            _at(create_chain_run(run_id="root"), 0),
            *(
                _langchain_llm(
                    f"call-{i}", i + 1, [_langchain("human", text, "human-1")], "r"
                )
                for i, text in enumerate(contents)
            ),
        ]

    one_edit = _input_ids(await _transcript(trace("original", "edit")))
    two_edits = _input_ids(await _transcript(trace("original", "other", "edit")))

    assert one_edit[1] == two_edits[2]
    assert two_edits[1] != two_edits[2]


def _input_ids(transcript: Transcript) -> list[list[str | None]]:
    return [ids(e.input) for e in transcript.events if isinstance(e, ModelEvent)]


@pytest.mark.asyncio
async def test_langchain_id_seen_later_names_only_the_reply_it_came_from(
    tmp_path: Path,
) -> None:
    hello = _langchain("human", "hello", "user")
    runs = [
        _at(create_chain_run(run_id="root"), 0),
        _langchain_llm("a", 1, [hello], "reply-A"),
        # Separately generates the same text as a's reply, with no source ID.
        _llm("b", "root", 2, [{"role": "user", "content": "hello"}], "reply from a"),
        _langchain_llm(
            "c",
            3,
            [
                hello,
                _langchain("ai", "reply from a", "reply-A"),
                _langchain("human", "next", "next"),
            ],
            "reply-C",
        ),
    ]

    transcript = await _transcript(runs)
    stored = await _store_and_read(transcript, tmp_path)

    for imported in (transcript, stored):
        a, b, c = [e for e in imported.events if isinstance(e, ModelEvent)]
        assert (a.output.message.id, b.output.message.id) == ("reply-A", "b-1")
        assert ids(c.input) == ["user", "reply-A", "next"]


@pytest.mark.asyncio
async def test_langchain_id_equal_to_an_edits_id_keeps_its_own_id() -> None:
    runs = [
        _at(create_chain_run(run_id="root"), 0),
        _langchain_llm("a", 1, [_langchain("human", "original", "source")], "out-a"),
        _langchain_llm("b", 2, [_langchain("human", "edited", "source")], "out-b"),
    ]
    [edit] = _input_ids(await _transcript(runs))[1]
    assert edit is not None
    runs.append(
        _langchain_llm("c", 3, [_langchain("human", "independent", edit)], "out-c")
    )

    transcript = await _transcript(runs)

    a, b, c = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert [(m.id, m.metadata) for m in [*a.input, *b.input, *c.input]] == [
        ("source", None),
        (f"{edit}.1", None),
        (edit, None),
    ]
    assert_message_ids_consistent(transcript)


async def _store_and_read(transcript: Transcript, location: Path) -> Transcript:
    db = ParquetTranscriptsDB(str(location))
    await db.connect()
    try:
        await db.insert([transcript])
        [info] = [info async for info in db.select()]
        return await db.read(info, TranscriptContent(messages="all", events="all"))
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_stored_import_keeps_ids_of_equal_messages(tmp_path: Path) -> None:
    transcript = await _transcript(
        [
            _at(create_chain_run(run_id="root"), 0),
            _langchain_llm("a", 1, [_langchain("human", "same", "human-a")], "r-a"),
            _langchain_llm("b", 2, [_langchain("human", "same", "human-b")], "r-b"),
        ]
    )

    stored = await _store_and_read(transcript, tmp_path)

    a, b = [e for e in stored.events if isinstance(e, ModelEvent)]
    assert (ids(a.input), ids(b.input)) == (["human-a"], ["human-b"])
    assert_message_ids_consistent(stored)


@pytest.mark.asyncio
async def test_anthropic_reply_keeps_its_message_id() -> None:
    run = create_anthropic_llm_run(run_id="llm-1", parent_run_id="root")
    assert run.outputs is not None
    run.outputs.update(
        id="msg_123", type="message", role="assistant", model="claude-3-5-haiku-latest"
    )

    transcript = await _transcript([_at(create_chain_run(run_id="root"), 0), run])

    event = next(e for e in transcript.events if isinstance(e, ModelEvent))
    assert event.output.message.id == "msg_123"
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "later_runs",
    [
        pytest.param(
            [
                _at(create_chain_run(run_id="sub", parent_run_id="root"), 3),
                _llm("sub-llm", "sub", 4, [HELLO, JOKE], "sub-agent reply"),
            ],
            id="nested_sub_agent",
        ),
        pytest.param(
            [
                _at(create_tool_run(run_id="tool", parent_run_id="root"), 3),
                _llm("tool-llm", "tool", 4, [HELLO, JOKE], "helper reply"),
            ],
            id="helper_inside_tool",
        ),
    ],
)
async def test_conversation_comes_from_root_agent(later_runs: list[MockRun]) -> None:
    transcript = await _transcript([*_root_agent_trace(), *later_runs])

    assert transcript.messages_from == ["llm-2"]
    assert transcript.messages[-1].text == "Why did..."
    assert_message_ids_consistent(transcript)
