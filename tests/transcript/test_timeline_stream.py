"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from inspect_ai.event import ModelEvent, ToolEvent, timeline_build
from inspect_scout._transcript.timeline import TimelineSpan

from tests.transcript.fixtures_agentic import agentic_events

try:
    from inspect_ai.event._timeline import (
        _get_system_prompt_for_event,
        _has_tool_calls,
    )
except ImportError:  # pragma: no cover - fallback if private API moves

    def _get_system_prompt_for_event(event: ModelEvent) -> str | None:
        from inspect_ai.model import ChatMessageSystem

        for msg in event.input:
            if isinstance(msg, ChatMessageSystem):
                if isinstance(msg.content, str):
                    return msg.content
                parts = [c.text for c in msg.content if hasattr(c, "text")]
                return "\n".join(parts) if parts else None
        return None

    def _has_tool_calls(event: ModelEvent) -> bool:
        if event.output.choices:
            msg = event.output.choices[0].message
            if msg.tool_calls:
                return True
        return False


def _collect_utility(span: TimelineSpan) -> list[TimelineSpan]:
    """Recursively collect every utility-classified span in the tree."""
    utility: list[TimelineSpan] = []
    if span.utility:
        utility.append(span)
    for item in span.content:
        if isinstance(item, TimelineSpan):
            utility.extend(_collect_utility(item))
    return utility


def test_agentic_fixture_classification() -> None:
    """The fixture must exercise the classification paths the spec names."""
    from inspect_scout._transcript.timeline import _walk_spans

    tree = timeline_build(agentic_events())
    spans = list(_walk_spans(tree.root, depth=None))
    names = [s.name for s in spans]
    # main agent, sub2 (non-utility nested agent), and the tool-spawned agent
    # are scannable; "sub" (utility) and the wrapped helper are NOT.
    assert "main" in names
    assert "sub2" in names
    assert "browser" in names
    assert "sub" not in names
    utility_spans = _collect_utility(tree.root)
    assert len(utility_spans) >= 2  # "sub" + wrapped foreign-prompt helper


def test_stub_model_event_preserves_classification_signals() -> None:
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    events = agentic_events(big_payload="y" * 100_000)
    interner = _PromptInterner()
    for ev in events:
        stub = stub_event(ev, interner)
        assert stub.uuid == ev.uuid and stub.span_id == ev.span_id
        if isinstance(ev, ModelEvent):
            assert isinstance(stub, ModelEvent)
            assert _get_system_prompt_for_event(stub) == _get_system_prompt_for_event(
                ev
            )
            assert _has_tool_calls(stub) == _has_tool_calls(ev)
            assert "y" * 1000 not in stub.model_dump_json()
        if isinstance(ev, ToolEvent):
            assert isinstance(stub, ToolEvent)
            assert stub.agent == ev.agent and stub.function == ev.function
            assert "y" * 1000 not in stub.model_dump_json()


def test_prompt_interning_shares_instances() -> None:
    from inspect_scout._transcript.timeline_stream import _PromptInterner

    interner = _PromptInterner()
    a = interner.intern("p" * 10_000)
    b = interner.intern("p" * 10_000)
    assert a is b
