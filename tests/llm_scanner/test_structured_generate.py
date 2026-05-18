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


def _assistant_tool_call(
    call_id: str, function: str, arguments: dict[str, Any]
) -> ModelOutput:
    """ModelOutput whose message carries a single tool call."""
    msg = ChatMessageAssistant(
        content="",
        tool_calls=[ToolCall(id=call_id, function=function, arguments=arguments)],
    )
    return ModelOutput.from_message(msg)


class RecordingGenerate:
    """Stand-in for ``generate_retry_refusals`` that snapshots ``input`` at
    call time (the real list is mutated in place, so a plain mock would only
    show the final state)."""

    def __init__(self, outputs: list[ModelOutput]) -> None:
        self._outputs = iter(outputs)
        self.inputs: list[list[ChatMessage]] = []

    async def __call__(self, *args: Any, **kwargs: Any) -> ModelOutput:
        self.inputs.append(list(kwargs["input"]))
        return next(self._outputs)


def _assert_tool_calls_paired(messages: list[ChatMessage]) -> None:
    """Every assistant tool_call must be immediately followed by ChatMessageTool(s)
    that cover all of its tool_call_ids — the invariant the Anthropic API enforces.
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
                tcid = follow.tool_call_id
                got.update(tcid if isinstance(tcid, list) else [tcid or ""])
                j += 1
            missing = want - got
            assert not missing, (
                f"orphan tool_use id(s) {missing} at messages[{i}] "
                f"(roles: {[m.role for m in messages]})"
            )
            i = j
        else:
            i += 1


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


@pytest.mark.anyio
async def test_structured_generate_retry_pairs_invalid_answer_call() -> None:
    """First attempt: answer() called with bad args (validation error).
    Second attempt: answer() called with good args.
    The second generate must receive a conversation where the first
    tool_use is paired with a tool_result.
    """
    gen = RecordingGenerate(
        [
            _assistant_tool_call("c1", "answer", {"explanation": "x"}),
            _assistant_tool_call("c2", "answer", {"explanation": "x", "score": 5}),
        ]
    )
    with patch(
        "inspect_scout._llm_scanner.structured.generate_retry_refusals", new=gen
    ):
        value, messages, _ = await structured_generate(
            input="rate this", schema=SCHEMA, model="mockllm/model"
        )

    assert len(gen.inputs) == 2
    _assert_tool_calls_paired(gen.inputs[1])
    _assert_tool_calls_paired(messages)
    assert value == {"explanation": "x", "score": 5}


@pytest.mark.anyio
async def test_structured_generate_retry_pairs_non_answer_call() -> None:
    """First attempt: model ignores tool_choice and calls some other tool.
    The retry loop must still pair that tool_use with a tool_result before
    re-generating, otherwise the next API call is rejected.
    """
    gen = RecordingGenerate(
        [
            _assistant_tool_call("c1", "lookup", {"q": "hello"}),
            _assistant_tool_call("c2", "answer", {"explanation": "x", "score": 5}),
        ]
    )
    with patch(
        "inspect_scout._llm_scanner.structured.generate_retry_refusals", new=gen
    ):
        value, messages, _ = await structured_generate(
            input="rate this", schema=SCHEMA, model="mockllm/model"
        )

    assert len(gen.inputs) == 2
    _assert_tool_calls_paired(gen.inputs[1])
    _assert_tool_calls_paired(messages)
    assert value == {"explanation": "x", "score": 5}
