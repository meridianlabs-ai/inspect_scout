"""Weave traces: message IDs, model call IDs and the transcript's conversation."""

from datetime import datetime, timedelta

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources._weave import _trace_to_transcript

from tests.sources.message_id_checks import assert_message_ids_consistent, ids
from tests.sources.weave_source.mocks import (
    MockWeaveCall,
    create_openai_llm_call,
    create_span_call,
    create_tool_call,
)

START = datetime(2026, 1, 1)


def _at(call: MockWeaveCall, second: int) -> MockWeaveCall:
    call.started_at = START + timedelta(seconds=second)
    call.ended_at = call.started_at + timedelta(milliseconds=500)
    return call


def _llm(
    call_id: str,
    parent_id: str,
    second: int,
    messages: list[dict[str, str]],
    reply: str,
) -> MockWeaveCall:
    call = create_openai_llm_call(call_id=call_id, trace_id="root", parent_id=parent_id)
    call.inputs = {"model": "gpt-4o-mini", "messages": messages}
    call.output = {
        "id": f"chatcmpl-{call_id}",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
    }
    return _at(call, second)


SYSTEM = {"role": "system", "content": "You are a helpful assistant."}
HELLO = {"role": "user", "content": "Hello!"}
HI = {"role": "assistant", "content": "Hi! How can I help?"}
JOKE = {"role": "user", "content": "Tell me a joke."}


def _root_agent_trace() -> list[MockWeaveCall]:
    """Root op calling the model twice, the second call resending the first."""
    return [
        _at(create_span_call(call_id="root", name="conversation"), 0),
        _llm("llm-1", "root", 1, [SYSTEM, HELLO], HI["content"]),
        _llm("llm-2", "root", 2, [SYSTEM, HELLO, HI, JOKE], "Why did..."),
    ]


async def _transcript(calls: list[MockWeaveCall]) -> Transcript:
    transcript = await _trace_to_transcript(calls, calls[0], "test/project", None)
    assert transcript is not None
    return transcript


@pytest.mark.asyncio
async def test_ids_come_from_each_messages_first_call() -> None:
    transcript = await _transcript(_root_agent_trace())

    llm_1, llm_2 = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert (llm_1.uuid, llm_2.uuid) == ("llm-1", "llm-2")
    assert ids(llm_1.input) == ["llm-1-0", "llm-1-1"]
    assert llm_1.output.message.id == "llm-1-2"
    # llm-1's output comes back as llm-2's input with the same ID.
    assert ids(llm_2.input) == ["llm-1-0", "llm-1-1", "llm-1-2", "llm-2-3"]
    assert transcript.messages_from == ["llm-2"]
    assert ids(transcript.messages) == [*ids(llm_2.input), "llm-2-4"]
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "later_calls",
    [
        pytest.param(
            [
                _at(create_span_call(call_id="sub", parent_id="root", name="sub"), 3),
                _llm("sub-llm", "sub", 4, [HELLO, JOKE], "sub-agent reply"),
            ],
            id="nested_sub_agent",
        ),
        pytest.param(
            [
                _at(create_tool_call(call_id="tool", parent_id="root"), 3),
                _llm("tool-llm", "tool", 4, [HELLO, JOKE], "helper reply"),
            ],
            id="helper_inside_tool",
        ),
    ],
)
async def test_conversation_comes_from_root_agent(
    later_calls: list[MockWeaveCall],
) -> None:
    transcript = await _transcript([*_root_agent_trace(), *later_calls])

    assert transcript.messages_from == ["llm-2"]
    assert transcript.messages[-1].text == "Why did..."
    assert_message_ids_consistent(transcript)
