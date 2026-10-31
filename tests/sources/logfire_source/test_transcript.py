"""Logfire traces: message IDs, model call IDs and the transcript's conversation."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources._logfire import _trace_to_transcript

from tests.sources.logfire_source.mocks import (
    create_agent_span,
    create_openai_llm_span,
    create_tool_span,
)
from tests.sources.message_id_checks import assert_message_ids_consistent, ids

START = datetime(2026, 1, 1)

SYSTEM = {"role": "system", "content": "You are a helpful assistant."}
HELLO = {"role": "user", "content": "Hello!"}
HI = {"role": "assistant", "content": "Hi! How can I help?"}
JOKE = {"role": "user", "content": "Tell me a joke."}


def _at(span: dict[str, Any], second: int) -> dict[str, Any]:
    span["start_timestamp"] = START + timedelta(seconds=second)
    return span


def _llm(
    span_id: str, parent: str, second: int, messages: list[dict[str, Any]], reply: str
) -> dict[str, Any]:
    return _at(
        create_openai_llm_span(
            span_id=span_id,
            parent_span_id=parent,
            input_messages=messages,
            output_content=reply,
        ),
        second,
    )


def _root_agent_trace() -> list[dict[str, Any]]:
    return [
        _at(create_agent_span(span_id="root"), 0),
        _llm("llm-1", "root", 1, [SYSTEM, HELLO], HI["content"]),
        _llm("llm-2", "root", 2, [SYSTEM, HELLO, HI, JOKE], "Why did..."),
    ]


async def _transcript(spans: list[dict[str, Any]]) -> Transcript:
    client = MagicMock()
    client.query_json_rows = AsyncMock(return_value={"rows": spans})
    transcript = await _trace_to_transcript(client, "trace-001", None)
    assert transcript is not None
    return transcript


@pytest.mark.asyncio
async def test_ids_come_from_each_messages_first_span() -> None:
    transcript = await _transcript(_root_agent_trace())

    llm_1, llm_2 = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert (llm_1.uuid, llm_2.uuid) == ("llm-1", "llm-2")
    assert ids(llm_1.input) == ["llm-1-0", "llm-1-1"]
    assert llm_1.output.message.id == "llm-1-2"
    # This event format carries only the user and system messages as input.
    assert ids(llm_2.input) == ["llm-1-0", "llm-1-1", "llm-2-2"]
    assert transcript.messages_from == ["llm-2"]
    assert_message_ids_consistent(transcript)


# A sub-agent's own conversation, longer than the root agent's.
LONG = [
    {"role": "system", "content": "You are a researcher."},
    *[JOKE, HI] * 3,
    JOKE,
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sub_agent_spans",
    [
        pytest.param(
            [
                _at(create_tool_span(span_id="tool", parent_span_id="llm-1"), 2),
                _at(create_agent_span(span_id="sub", parent_span_id="tool"), 2),
                _llm("sub-llm", "sub", 2, LONG, "sub-agent reply"),
            ],
            id="sub_agent_inside_tool",
        ),
        pytest.param(
            [
                _at(create_agent_span(span_id="sub", parent_span_id="root"), 2),
                _llm("sub-llm", "sub", 2, LONG, "sub-agent reply"),
            ],
            id="nested_sub_agent",
        ),
    ],
)
async def test_conversation_comes_from_root_agent(
    sub_agent_spans: list[dict[str, Any]],
) -> None:
    transcript = await _transcript([*_root_agent_trace(), *sub_agent_spans])

    # The sub-agent's call has the longest input, but isn't the root agent's.
    assert transcript.messages_from == ["llm-2"]
    assert transcript.messages[-1].text == "Why did..."
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_nested_model_call_spans_still_compete_on_input_length() -> None:
    # A framework's chat span wrapping the SDK's chat span for the same call.
    spans = [
        _at(create_agent_span(span_id="root"), 0),
        _llm("framework", "root", 1, [SYSTEM, HELLO], "Hi!"),
        _llm("sdk", "framework", 1, [SYSTEM, HELLO, HI, JOKE], "Why did..."),
    ]

    transcript = await _transcript(spans)

    assert transcript.messages_from == ["sdk"]
