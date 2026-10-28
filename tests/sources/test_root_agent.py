"""Which of a trace's model calls belong to its root agent."""

from datetime import datetime

import pytest
from inspect_ai.event import ModelEvent
from inspect_ai.model import GenerateConfig, ModelOutput
from inspect_scout.sources._root_agent import root_agent_calls


def _call(uuid: str) -> ModelEvent:
    return ModelEvent(
        model="m",
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(),
        timestamp=datetime(2026, 1, 1),
        uuid=uuid,
    )


@pytest.mark.parametrize(
    "parents,tools,spans,expected",
    [
        pytest.param(
            {"a": "root", "b": "root", "sub-call": "sub", "sub": "root"},
            set(),
            {"root", "sub"},
            ["a", "b"],
            id="nested_sub_agent_left_out",
        ),
        pytest.param(
            {"a": "root", "b": "root", "tool-call": "tool", "tool": "a"},
            {"tool"},
            {"root"},
            ["a", "b"],
            id="call_inside_tool_left_out",
        ),
        pytest.param(
            {"helper": "root", "a": "loop", "b": "loop", "loop": "root"},
            set(),
            {"root", "loop"},
            ["a", "b"],
            id="lone_helper_above_agent_loop_left_out",
        ),
        pytest.param(
            {"a": "root", "b": "a", "sub-call": "sub", "sub": "root"},
            set(),
            {"root", "sub"},
            ["a", "b"],
            id="model_call_span_wrapping_another_is_not_nesting",
        ),
        pytest.param(
            {"a": "tool", "b": "tool"},
            {"tool"},
            set(),
            ["a", "b"],
            id="every_call_inside_a_tool",
        ),
        pytest.param(
            {"a": "x", "x": "y", "y": "x", "b": "x"},
            set(),
            {"x", "y"},
            ["a", "b"],
            id="parent_cycle",
        ),
    ],
)
def test_root_agent_calls(
    parents: dict[str, str | None],
    tools: set[str],
    spans: set[str],
    expected: list[str],
) -> None:
    calls = [_call(uuid) for uuid in parents if uuid not in tools and uuid not in spans]

    result = root_agent_calls(calls, parents, tools, spans)

    assert [call.uuid for call in result] == expected


def test_no_calls() -> None:
    assert root_agent_calls([], {}, set(), set()) == []
