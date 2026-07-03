"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from inspect_ai.event import Event, ModelEvent, TimelineEvent, ToolEvent, timeline_build
from inspect_ai.model import ChatMessageSystem, ContentText
from inspect_scout._transcript.timeline import TimelineSpan, _walk_spans

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
    # main agent, sub2 (non-utility nested agent), the span-based tool-spawned
    # agent ("browser"), and the flat-ToolEvent tool-spawned agent
    # ("handoff_agent") are scannable; "sub" (utility) and the wrapped helper
    # are NOT.
    assert "main" in names
    assert "sub2" in names
    assert "browser" in names
    assert "handoff_agent" in names
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


def _span_model_event_uuids(span: TimelineSpan) -> list[str | None]:
    """Return the uuids of ModelEvents directly in `span.content` (not nested)."""
    uuids: list[str | None] = []
    for item in span.content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            uuids.append(item.event.uuid)
    return uuids


def test_stub_tree_matches_full_tree_structure() -> None:
    """The regression guard for Finding 1: stubbing must not change span shape.

    Building the timeline from stubbed events must yield the same
    scannable span names, the same utility classification, and the same
    per-span direct-ModelEvent uuid sequence as building it from the full
    events -- in particular for "handoff_agent", the ToolEvent-with-nested-
    `.events` tool-spawned agent, whose nested ModelEvents would vanish if
    `_stub_tool_event` emptied `.events` instead of recursively stubbing it.
    """
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    events = agentic_events(big_payload="z" * 100_000)
    interner = _PromptInterner()
    stubbed_events: list[Event] = [stub_event(e, interner) for e in events]

    full_tree = timeline_build(events)
    stub_tree = timeline_build(stubbed_events)

    full_spans = list(_walk_spans(full_tree.root, depth=None))
    stub_spans = list(_walk_spans(stub_tree.root, depth=None))

    full_names = [s.name for s in full_spans]
    stub_names = [s.name for s in stub_spans]
    assert stub_names == full_names
    assert "handoff_agent" in full_names

    full_utility = _collect_utility(full_tree.root)
    stub_utility = _collect_utility(stub_tree.root)
    assert [s.name for s in stub_utility] == [s.name for s in full_utility]

    for full_span, stub_span in zip(full_spans, stub_spans, strict=True):
        assert full_span.utility == stub_span.utility
        assert _span_model_event_uuids(stub_span) == _span_model_event_uuids(full_span)

    # The nested ModelEvents inside handoff-tool's `.events` must survive
    # stubbing with distinct uuids and bulk content stripped.
    handoff_span = next(s for s in stub_spans if s.name == "handoff_agent")
    nested_uuids = _span_model_event_uuids(handoff_span)
    assert nested_uuids == ["evt-handoff-1", "evt-handoff-2"]
    assert "z" * 1000 not in handoff_span.model_dump_json()


def test_stub_model_event_interns_list_content_system_prompt() -> None:
    """Finding 2: list-content ChatMessageSystem parts must be interned too."""
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    prompt_text = "list-content-system-prompt " + "q" * 10_000
    base = agentic_events()[2]
    assert isinstance(base, ModelEvent)
    assert base.uuid is not None
    base_uuid = base.uuid

    def _with_list_system_prompt(label_suffix: str) -> ModelEvent:
        list_content_message = ChatMessageSystem(
            content=[ContentText(text=prompt_text)]
        )
        other_input = [m for m in base.input if not isinstance(m, ChatMessageSystem)]
        return base.model_copy(
            update={
                "uuid": base_uuid + label_suffix,
                "input": [list_content_message, *other_input],
            }
        )

    event_a = _with_list_system_prompt("-a")
    event_b = _with_list_system_prompt("-b")

    interner = _PromptInterner()
    stub_a = stub_event(event_a, interner)
    stub_b = stub_event(event_b, interner)
    assert isinstance(stub_a, ModelEvent)
    assert isinstance(stub_b, ModelEvent)

    # The system-prompt signal the classifier reads is preserved.
    assert _get_system_prompt_for_event(stub_a) == _get_system_prompt_for_event(event_a)
    assert _get_system_prompt_for_event(stub_b) == _get_system_prompt_for_event(event_b)

    # Interning applies to list-content parts: two events with identical
    # list-content prompts share the interned part text instance.
    stub_sys_a = stub_a.input[0]
    stub_sys_b = stub_b.input[0]
    assert isinstance(stub_sys_a, ChatMessageSystem)
    assert isinstance(stub_sys_b, ChatMessageSystem)
    assert isinstance(stub_sys_a.content, list)
    assert isinstance(stub_sys_b.content, list)
    part_a = stub_sys_a.content[0]
    part_b = stub_sys_b.content[0]
    assert isinstance(part_a, ContentText)
    assert isinstance(part_b, ContentText)
    assert part_a.text is part_b.text
