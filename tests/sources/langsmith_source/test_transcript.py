"""LangSmith traces: message IDs, model call IDs and the transcript's conversation."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources._langsmith import _trace_to_transcript

from tests.sources.langsmith_source.mocks import (
    MockRun,
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
