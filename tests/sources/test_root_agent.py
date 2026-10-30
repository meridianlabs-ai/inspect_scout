"""Which of a trace's model calls belong to its root agent."""

import time
from datetime import datetime

import pytest
from inspect_ai.event import ModelEvent
from inspect_ai.model import ChatMessageUser, GenerateConfig, ModelOutput
from inspect_scout.sources._root_agent import root_agent_calls


def _call(uuid: str, input_ids: list[str]) -> ModelEvent:
    return ModelEvent(
        model="m",
        input=[ChatMessageUser(content=i, id=i) for i in input_ids],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(),
        timestamp=datetime(2026, 1, 1),
        uuid=uuid,
    )


FIRST = ["s", "u"]
SECOND = ["s", "u", "r", "u2"]


@pytest.mark.parametrize(
    "calls,parents,tools,spans,expected",
    [
        pytest.param(
            {"a": FIRST, "b": SECOND, "sub-call": ["t"]},
            {"a": "root", "b": "root", "sub-call": "sub", "sub": "root"},
            set(),
            {"root", "sub"},
            ["a", "b"],
            id="nested_sub_agent_left_out",
        ),
        pytest.param(
            {"a": FIRST, "b": SECOND, "tool-call": ["t"]},
            {"a": "root", "b": "root", "tool-call": "tool", "tool": "a"},
            {"tool"},
            {"root"},
            ["a", "b"],
            id="call_inside_tool_left_out",
        ),
        pytest.param(
            {"first": FIRST, "final": SECOND},
            {"first": "root", "final": "helper", "helper": "root"},
            set(),
            {"root", "helper"},
            ["first", "final"],
            id="turn_through_a_helper_span_continues_the_conversation",
        ),
        pytest.param(
            {"a": FIRST, "b": FIRST, "c": SECOND, "d": SECOND, "sub-call": ["t"]},
            {"a": "root", "b": "a", "c": "root", "d": "c", "sub-call": "sub"}
            | {"sub": "root"},
            set(),
            {"root", "sub"},
            ["a", "b", "c", "d"],
            id="model_call_span_wrapping_another_is_not_nesting",
        ),
        pytest.param(
            {"helper": ["q"], "a": FIRST, "b": SECOND},
            {"helper": "root", "a": "loop", "b": "loop", "loop": "root"},
            set(),
            {"root", "loop"},
            ["helper", "a", "b"],
            id="lone_call_above_an_agent_loop_is_ambiguous",
        ),
        pytest.param(
            {"helper-fw": ["q"], "helper-sdk": ["q"], "a": FIRST, "b": SECOND},
            {"helper-fw": "root", "helper-sdk": "helper-fw"}
            | {"a": "loop", "b": "loop", "loop": "root"},
            set(),
            {"root", "loop"},
            ["helper-fw", "helper-sdk", "a", "b"],
            id="one_call_recorded_twice_is_one_turn",
        ),
        pytest.param(
            {"sub-1": ["t"], "sub-2": ["t", "r"], "final": FIRST},
            {"sub-1": "sub", "sub-2": "sub", "sub": "root", "final": "root"},
            set(),
            {"root", "sub"},
            ["sub-1", "sub-2", "final"],
            id="single_root_call_with_nested_sub_agent_is_ambiguous",
        ),
        pytest.param(
            {"a": FIRST, "b": ["s2", "v"], "sub-call": ["t"]},
            {"a": "root", "b": "root", "sub-call": "sub", "sub": "root"},
            set(),
            {"root", "sub"},
            ["a", "b", "sub-call"],
            id="two_conversations_at_the_top_are_ambiguous",
        ),
        pytest.param(
            {"a": ["x"], "b": ["y"]},
            {"a": "tool", "b": "tool"},
            {"tool"},
            set(),
            ["a", "b"],
            id="every_call_inside_a_tool",
        ),
        pytest.param(
            {"a": FIRST, "b": SECOND},
            {"a": "x", "x": "y", "y": "x", "b": "x"},
            set(),
            {"x", "y"},
            ["a", "b"],
            id="parent_cycle",
        ),
    ],
)
def test_root_agent_calls(
    calls: dict[str, list[str]],
    parents: dict[str, str | None],
    tools: set[str],
    spans: set[str],
    expected: list[str],
) -> None:
    events = [_call(uuid, input_ids) for uuid, input_ids in calls.items()]

    result = root_agent_calls(events, parents, tools, spans)

    assert [call.uuid for call in result] == expected


def test_no_calls() -> None:
    assert root_agent_calls([], {}, set(), set()) == []


@pytest.mark.slow
def test_many_independent_calls_take_linear_time() -> None:
    # Distinct system prompts, then the same task: every call's input ends
    # alike. A gross-regression budget, not a benchmark: this takes about
    # 0.03s on a laptop, while comparing each call with every earlier one
    # took over 7s.
    calls = [_call(f"call-{i}", [f"system-{i}", "prompt"]) for i in range(20_000)]

    start = time.perf_counter()
    result = root_agent_calls(calls, {}, set(), set())
    elapsed = time.perf_counter() - start

    assert len(result) == len(calls)
    assert elapsed < 3


@pytest.mark.slow
def test_deeply_nested_calls_take_linear_time() -> None:
    # A call in each of 3,000 nested spans. A gross-regression budget, not a
    # benchmark: this takes about 0.005s on a laptop, while walking every
    # call's ancestors afresh took over 15s.
    nodes = [f"span-{i}" for i in range(3_000)]
    parents: dict[str, str | None] = {
        node: nodes[i - 1] if i else None for i, node in enumerate(nodes)
    }
    calls = [_call(node, []) for node in nodes]

    start = time.perf_counter()
    result = root_agent_calls(calls, parents, set(), set(nodes))
    elapsed = time.perf_counter() - start

    assert len(result) == len(calls)
    assert elapsed < 3
