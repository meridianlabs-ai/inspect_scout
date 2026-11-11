"""Weave traces: message IDs, model call IDs and the transcript's conversation."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources._weave import _trace_to_transcript

from tests.sources.message_id_checks import assert_message_ids_consistent, ids
from tests.sources.weave_source.mocks import (
    MockWeaveCall,
    create_anthropic_llm_call,
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
    messages: list[dict[str, Any]],
    reply: str,
) -> MockWeaveCall:
    call = create_openai_llm_call(call_id=call_id, trace_id="root", parent_id=parent_id)
    call.inputs = {"model": "gpt-4o-mini", "messages": messages}
    call.output = {
        "id": f"chatcmpl-{call_id}",
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


def _span(call_id: str, parent_id: str | None, second: int) -> MockWeaveCall:
    return _at(
        create_span_call(call_id=call_id, parent_id=parent_id, name="op"), second
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "calls,expected_call,expected_reply",
    [
        pytest.param(
            [
                _span("root", None, 0),
                _llm("first", "root", 1, [SYSTEM, HELLO], HI["content"]),
                _span("helper", "root", 2),
                _llm("final", "helper", 3, [SYSTEM, HELLO, HI, JOKE], "final answer"),
            ],
            "final",
            "final answer",
            id="later_turn_through_a_helper_op",
        ),
        pytest.param(
            [
                _span("root", None, 0),
                _llm("helper-framework", "root", 1, [HELLO], "rewritten"),
                _llm("helper-sdk", "helper-framework", 2, [HELLO], "rewritten"),
                _span("chain", "root", 3),
                _llm("agent-1", "chain", 4, [SYSTEM, JOKE], HI["content"]),
                _llm("agent-2", "chain", 5, [SYSTEM, JOKE, HI, JOKE], "actual final"),
            ],
            "agent-2",
            "actual final",
            id="helper_recorded_twice_above_the_agent_loop",
        ),
        pytest.param(
            [
                _span("root", None, 0),
                _span("sub", "root", 1),
                _llm("sub-1", "sub", 2, [JOKE], HI["content"]),
                _llm("sub-2", "sub", 3, [JOKE, HI, JOKE], "sub2"),
                _llm("final", "root", 4, [SYSTEM, HELLO], "root answer"),
            ],
            "final",
            "root answer",
            id="single_root_call_after_a_nested_sub_agent",
        ),
    ],
)
async def test_root_agent_conversation_in_ambiguous_traces(
    calls: list[MockWeaveCall], expected_call: str, expected_reply: str
) -> None:
    transcript = await _transcript(calls)

    assert transcript.messages_from == [expected_call]
    assert transcript.messages[-1].text == expected_reply
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_equal_replies_to_separate_calls_are_different_messages() -> None:
    transcript = await _transcript(
        [
            _span("root", None, 0),
            _llm("a", "root", 1, [HELLO], "same reply"),
            _llm("b", "root", 2, [HELLO], "same reply"),
        ]
    )

    a, b = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert ids(a.input) == ids(b.input) == ["a-0"]
    assert (a.output.message.id, b.output.message.id) == ("a-1", "b-1")


@pytest.mark.asyncio
async def test_reply_sent_back_keeps_the_id_of_the_call_it_came_from() -> None:
    transcript = await _transcript(
        [
            _span("root", None, 0),
            _llm("a", "root", 1, [HELLO], HI["content"]),
            _llm("b", "root", 2, [HELLO], HI["content"]),
            _llm("c", "root", 3, [HELLO, HI, JOKE], "Why did..."),
        ]
    )

    c = [e for e in transcript.events if isinstance(e, ModelEvent)][-1]
    assert ids(c.input) == ["a-0", "b-1", "c-2"]


@pytest.mark.asyncio
async def test_anthropic_reply_keeps_its_message_id() -> None:
    call = create_anthropic_llm_call(call_id="llm-1", trace_id="root", parent_id="root")
    assert isinstance(call.output, dict)
    call.output["model"] = "claude-3-haiku-20240307"

    transcript = await _transcript([_span("root", None, 0), _at(call, 1)])

    event = next(e for e in transcript.events if isinstance(e, ModelEvent))
    assert event.output.message.id == "msg_123"
    assert ids(transcript.messages)[-1] == "msg_123"
    assert_message_ids_consistent(transcript)


@pytest.mark.asyncio
async def test_tool_call_turn_keeps_its_id_when_sent_back() -> None:
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city": "SF"}'},
        }
    ]
    asks = _llm("llm-1", "root", 1, [SYSTEM, HELLO], "")
    asks.output["choices"][0]["message"] = {
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls,
    }
    asks.output["choices"][0]["finish_reason"] = "tool_calls"
    answers = _llm(
        "llm-2",
        "root",
        2,
        [
            SYSTEM,
            HELLO,
            {"role": "assistant", "content": None, "tool_calls": tool_calls},
            {"role": "tool", "tool_call_id": "call_1", "content": "Foggy"},
        ],
        "It's foggy.",
    )

    transcript = await _transcript(
        [_at(create_span_call(call_id="root", name="conversation"), 0), asks, answers]
    )

    llm_2 = [e for e in transcript.events if isinstance(e, ModelEvent)][-1]
    assert ids(llm_2.input) == ["llm-1-0", "llm-1-1", "llm-1-2", "llm-2-3"]
    assert_message_ids_consistent(transcript)
