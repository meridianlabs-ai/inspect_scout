"""Phoenix traces: message IDs, model call IDs and the transcript's conversation."""

from typing import Any

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources._phoenix import _build_transcript

from tests.sources.message_id_checks import assert_message_ids_consistent, ids
from tests.sources.phoenix_source.mocks import (
    create_chain_span,
    create_openai_llm_span,
    create_tool_span,
)

SYSTEM = {"role": "system", "content": "You are a helpful assistant."}
HELLO = {"role": "user", "content": "Hello!"}
HI = {"role": "assistant", "content": "Hi! How can I help?"}
JOKE = {"role": "user", "content": "Tell me a joke."}
# A sub-agent's own conversation, longer than the root agent's.
LONG = [
    {"role": "system", "content": "You are a researcher."},
    *[JOKE, HI] * 3,
    JOKE,
]


def _time(second: int) -> str:
    return f"2025-01-01T00:00:{second:02d}Z"


def _llm(
    span_id: str, parent: str, second: int, messages: list[dict[str, Any]], reply: str
) -> dict[str, Any]:
    return create_openai_llm_span(
        span_id=span_id,
        parent_id=parent,
        input_messages=messages,
        output_content=reply,
        start_time=_time(second),
        end_time=_time(second),
    )


def _root_agent_trace() -> list[dict[str, Any]]:
    return [
        create_chain_span(span_id="root", start_time=_time(0), end_time=_time(9)),
        _llm("llm-1", "root", 1, [SYSTEM, HELLO], HI["content"]),
        _llm("llm-2", "root", 2, [SYSTEM, HELLO, HI, JOKE], "Why did..."),
    ]


async def _transcript(spans: list[dict[str, Any]]) -> Transcript:
    transcript = await _build_transcript(spans, "project", "trace-001", None)
    assert transcript is not None
    return transcript


@pytest.mark.asyncio
async def test_ids_come_from_each_messages_first_span() -> None:
    transcript = await _transcript(_root_agent_trace())

    llm_1, llm_2 = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert (llm_1.uuid, llm_2.uuid) == ("llm-1", "llm-2")
    assert ids(llm_1.input) == ["llm-1-0", "llm-1-1"]
    assert llm_1.output.message.id == "llm-1-2"
    assert ids(llm_2.input) == ["llm-1-0", "llm-1-1", "llm-1-2", "llm-2-3"]
    assert transcript.messages_from == ["llm-2"]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sub_agent_spans",
    [
        pytest.param(
            [
                create_tool_span(span_id="tool", parent_id="root", start_time=_time(3)),
                create_chain_span(span_id="sub", parent_id="tool", start_time=_time(3)),
                _llm("sub-llm", "sub", 3, LONG, "sub-agent reply"),
            ],
            id="sub_agent_inside_tool",
        ),
        pytest.param(
            [
                create_chain_span(span_id="sub", parent_id="root", start_time=_time(3)),
                _llm("sub-llm", "sub", 3, LONG, "sub-agent reply"),
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
