"""Tests for structured_generate retry loop — message pairing across attempts.

The retry loop appends the model's assistant message (which may carry
``tool_use`` blocks) to the running conversation before deciding whether
to break or retry. Every ``tool_use`` it appends MUST be followed by a
matching ``tool_result`` before the next generate, otherwise the next
API call is rejected with::

    BadRequestError: messages.N: 'tool_use' ids were found without
    'tool_result' blocks immediately after

These tests drive ``structured_generate`` through its retry paths with a
mocked generate and assert that the ``input`` passed to each subsequent
generate is well-formed (every assistant tool_call has a following
ChatMessageTool with the same ``tool_call_id``).
"""

from typing import Any
from unittest.mock import patch

import pytest
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ModelOutput,
)
from inspect_ai.tool import ToolCall
from inspect_ai.util import JSONSchema
from inspect_scout._llm_scanner.structured import structured_generate


def _assistant_with_calls(*calls: ToolCall) -> ModelOutput:
    """ModelOutput whose assistant message carries ``calls`` (possibly none)."""
    msg = ChatMessageAssistant(content="", tool_calls=list(calls) or None)
    return ModelOutput.from_message(msg)


def _tc(call_id: str, function: str, arguments: dict[str, Any]) -> ToolCall:
    return ToolCall(id=call_id, function=function, arguments=arguments)


class RecordingGenerate:
    """Stand-in for ``generate_retry_refusals`` that snapshots ``input`` per call.

    The real list is mutated in place, so a plain mock would only show the
    final state.
    """

    def __init__(self, outputs: list[ModelOutput]) -> None:
        self._outputs = iter(outputs)
        self.inputs: list[list[ChatMessage]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> ModelOutput:
        self.inputs.append(list(kwargs["input"]))
        return next(self._outputs)


def _assert_tool_calls_paired(messages: list[ChatMessage]) -> None:
    """Assert every assistant tool_call is followed by a matching ChatMessageTool.

    This is the invariant the Anthropic API enforces on the next request.
    """
    i = 0
    while i < len(messages):
        msg = messages[i]
        if isinstance(msg, ChatMessageAssistant) and msg.tool_calls:
            want = {tc.id for tc in msg.tool_calls}
            got: set[str] = set()
            j = i + 1
            while j < len(messages):
                follow = messages[j]
                if not isinstance(follow, ChatMessageTool):
                    break
                got.add(follow.tool_call_id or "")
                j += 1
            missing = want - got
            assert not missing, (
                f"orphan tool_use id(s) {missing} at messages[{i}] "
                f"(roles: {[m.role for m in messages]})"
            )
            i = j
        else:
            i += 1


def _tool_result(messages: list[ChatMessage], call_id: str) -> ChatMessageTool:
    for m in messages:
        if isinstance(m, ChatMessageTool) and m.tool_call_id == call_id:
            return m
    raise AssertionError(f"no tool result for {call_id}")


SCHEMA = JSONSchema.model_validate(
    {
        "type": "object",
        "properties": {
            "explanation": {"type": "string", "description": "why"},
            "score": {"type": "integer", "description": "the score"},
        },
        "required": ["explanation", "score"],
    }
)

VALID = {"explanation": "x", "score": 5}


async def _run(
    outputs: list[ModelOutput],
) -> tuple[dict[str, Any] | None, list[ChatMessage], RecordingGenerate]:
    gen = RecordingGenerate(outputs)
    with patch(
        "inspect_scout._llm_scanner.structured.generate_retry_refusals", new=gen
    ):
        value, messages, _ = await structured_generate(
            input="rate this", schema=SCHEMA, model="mockllm/model"
        )
    # every conversation handed to generate, plus the final one, must be paired
    for inp in gen.inputs:
        _assert_tool_calls_paired(inp)
    _assert_tool_calls_paired(messages)
    return value, messages, gen


@pytest.mark.anyio
async def test_valid_answer_first_try() -> None:
    value, messages, gen = await _run(
        [_assistant_with_calls(_tc("c1", "answer", VALID))]
    )
    assert len(gen.inputs) == 1
    assert value == VALID
    assert _tool_result(messages, "c1").error is None


@pytest.mark.anyio
async def test_invalid_answer_args_then_retry() -> None:
    """answer() called with bad args → parsing error fed back, retry succeeds."""
    value, messages, gen = await _run(
        [
            _assistant_with_calls(_tc("c1", "answer", {"explanation": "x"})),
            _assistant_with_calls(_tc("c2", "answer", VALID)),
        ]
    )
    assert len(gen.inputs) == 2
    err = _tool_result(gen.inputs[1], "c1").error
    assert err is not None and err.type == "parsing"
    assert "score" in err.message
    assert value == VALID


@pytest.mark.anyio
async def test_context_tool_call_then_retry() -> None:
    """Model ignores tool_choice and calls a context tool → rejected, retry."""
    value, messages, gen = await _run(
        [
            _assistant_with_calls(_tc("c1", "lookup", {"q": "hello"})),
            _assistant_with_calls(_tc("c2", "answer", VALID)),
        ]
    )
    assert len(gen.inputs) == 2
    err = _tool_result(gen.inputs[1], "c1").error
    assert err is not None and err.type == "unknown"
    assert value == VALID


@pytest.mark.anyio
async def test_hallucinated_tool_then_retry() -> None:
    """Model invents a tool name not in the tool list → same rejection path."""
    value, _, gen = await _run(
        [
            _assistant_with_calls(_tc("c1", "made_up_tool", {})),
            _assistant_with_calls(_tc("c2", "answer", VALID)),
        ]
    )
    assert len(gen.inputs) == 2
    err = _tool_result(gen.inputs[1], "c1").error
    assert err is not None and err.type == "unknown"
    assert "answer()" in err.message
    assert value == VALID


@pytest.mark.anyio
async def test_answer_alongside_other_call_is_accepted() -> None:
    """answer() + something else in one turn → accept the answer, stub the other."""
    value, messages, gen = await _run(
        [
            _assistant_with_calls(
                _tc("c1", "lookup", {"q": "hello"}),
                _tc("c2", "answer", VALID),
            )
        ]
    )
    assert len(gen.inputs) == 1
    assert value == VALID
    assert _tool_result(messages, "c1").error is not None
    assert _tool_result(messages, "c2").error is None


@pytest.mark.anyio
async def test_no_tool_call_then_retry() -> None:
    """Model returns plain text → nudge with a user message, retry."""
    value, _, gen = await _run(
        [
            _assistant_with_calls(),
            _assistant_with_calls(_tc("c1", "answer", VALID)),
        ]
    )
    assert len(gen.inputs) == 2
    assert gen.inputs[1][-1].role == "user"
    assert value == VALID
