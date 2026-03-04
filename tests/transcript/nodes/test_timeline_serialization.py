"""Tests for Timeline Pydantic serialization/deserialization."""

from datetime import datetime
from typing import Any

from inspect_ai.event import ModelEvent
from inspect_ai.model import ModelOutput
from inspect_ai.model._generate_config import GenerateConfig
from inspect_scout._transcript.timeline import (
    Outline,
    OutlineNode,
    Timeline,
    TimelineBranch,
    TimelineEvent,
    TimelineSpan,
)


def _make_model_event(
    model: str = "gpt-4",
    uuid: str = "uuid-1",
) -> ModelEvent:
    """Create a minimal ModelEvent for testing."""
    return ModelEvent(
        event="model",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        model=model,
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(model=model, choices=[]),
        uuid=uuid,
    )


def _make_timeline(events: list[ModelEvent] | None = None) -> Timeline:
    """Create a simple Timeline with events for testing."""
    if events is None:
        events = [_make_model_event()]
    content: list[Any] = [TimelineEvent(event=e) for e in events]
    return Timeline(
        name="Default",
        description="Test timeline",
        root=TimelineSpan(
            id="root",
            name="root",
            span_type="root",
            content=content,
        ),
    )


class TestTimelineEventSerialization:
    """Tests for TimelineEvent serialization roundtrip."""

    def test_serialize_event_as_uuid(self) -> None:
        """model_dump should serialize event as UUID string."""
        event = _make_model_event(uuid="test-uuid-123")
        te = TimelineEvent(event=event)

        data = te.model_dump()

        assert data["type"] == "event"
        assert data["event"] == "test-uuid-123"

    def test_deserialize_with_context(self) -> None:
        """model_validate with events_by_uuid context should resolve UUID."""
        event = _make_model_event(uuid="test-uuid-123")
        context = {"events_by_uuid": {"test-uuid-123": event}}

        te = TimelineEvent.model_validate(
            {"type": "event", "event": "test-uuid-123"},
            context=context,
        )

        assert te.event is event

    def test_deserialize_without_context_keeps_event_object(self) -> None:
        """Direct construction with Event object should work (no context needed)."""
        event = _make_model_event()
        te = TimelineEvent(event=event)

        assert te.event is event

    def test_roundtrip(self) -> None:
        """Serialize then deserialize should preserve the event."""
        event = _make_model_event(uuid="roundtrip-uuid")
        te = TimelineEvent(event=event)

        data = te.model_dump()
        assert data["event"] == "roundtrip-uuid"

        restored = TimelineEvent.model_validate(
            data,
            context={"events_by_uuid": {"roundtrip-uuid": event}},
        )
        assert restored.event is event

    def test_computed_properties_not_serialized(self) -> None:
        """start_time, end_time, total_tokens should not be in model_dump."""
        event = _make_model_event()
        te = TimelineEvent(event=event)

        data = te.model_dump()

        assert "start_time" not in data
        assert "end_time" not in data
        assert "total_tokens" not in data


class TestTimelineSpanSerialization:
    """Tests for TimelineSpan serialization with discriminated union."""

    def test_serialize_span(self) -> None:
        """model_dump should serialize span with type discriminator."""
        event = _make_model_event(uuid="span-event")
        span = TimelineSpan(
            id="span1",
            name="test-span",
            span_type="agent",
            content=[TimelineEvent(event=event)],
        )

        data = span.model_dump()

        assert data["type"] == "span"
        assert data["id"] == "span1"
        assert data["name"] == "test-span"
        assert len(data["content"]) == 1
        assert data["content"][0]["type"] == "event"
        assert data["content"][0]["event"] == "span-event"

    def test_nested_span_serialization(self) -> None:
        """Nested spans should serialize correctly."""
        event = _make_model_event(uuid="nested-event")
        inner_span = TimelineSpan(
            id="inner",
            name="inner-span",
            span_type="tool",
            content=[TimelineEvent(event=event)],
        )
        outer_span = TimelineSpan(
            id="outer",
            name="outer-span",
            span_type="agent",
            content=[inner_span],
        )

        data = outer_span.model_dump()

        assert data["content"][0]["type"] == "span"
        assert data["content"][0]["content"][0]["type"] == "event"

    def test_discriminated_union_deserialization(self) -> None:
        """JSON with type discriminators should deserialize to correct types."""
        event = _make_model_event(uuid="disc-event")
        context = {"events_by_uuid": {"disc-event": event}}

        data = {
            "type": "span",
            "id": "s1",
            "name": "test",
            "span_type": "agent",
            "content": [
                {"type": "event", "event": "disc-event"},
                {
                    "type": "span",
                    "id": "s2",
                    "name": "nested",
                    "span_type": "tool",
                    "content": [{"type": "event", "event": "disc-event"}],
                    "branches": [],
                },
            ],
            "branches": [],
        }

        span = TimelineSpan.model_validate(data, context=context)

        assert isinstance(span.content[0], TimelineEvent)
        assert isinstance(span.content[1], TimelineSpan)
        assert span.content[0].event is event


class TestTimelineBranchSerialization:
    """Tests for TimelineBranch serialization."""

    def test_serialize_branch(self) -> None:
        """model_dump should serialize branch with type discriminator."""
        event = _make_model_event(uuid="branch-event")
        branch = TimelineBranch(
            forked_at="fork-point",
            content=[TimelineEvent(event=event)],
        )

        data = branch.model_dump()

        assert data["type"] == "branch"
        assert data["forked_at"] == "fork-point"
        assert len(data["content"]) == 1


class TestTimelineSerialization:
    """Tests for full Timeline serialization roundtrip."""

    def test_full_roundtrip(self) -> None:
        """Full Timeline serialize/deserialize roundtrip."""
        event1 = _make_model_event(uuid="e1", model="gpt-4")
        event2 = _make_model_event(uuid="e2", model="claude")

        timeline = Timeline(
            name="Default",
            description="Test timeline",
            root=TimelineSpan(
                id="root",
                name="root",
                span_type="root",
                content=[
                    TimelineEvent(event=event1),
                    TimelineSpan(
                        id="agent1",
                        name="Agent",
                        span_type="agent",
                        content=[TimelineEvent(event=event2)],
                    ),
                ],
            ),
        )

        data = timeline.model_dump()

        # Verify serialized structure
        assert data["name"] == "Default"
        assert data["root"]["content"][0]["event"] == "e1"
        assert data["root"]["content"][1]["content"][0]["event"] == "e2"

        # Deserialize with context
        context = {"events_by_uuid": {"e1": event1, "e2": event2}}
        restored = Timeline.model_validate(data, context=context)

        assert restored.name == "Default"
        assert restored.root.content[0].event is event1  # type: ignore[union-attr]
        assert restored.root.content[1].content[0].event is event2  # type: ignore[union-attr]


class TestMutability:
    """Tests that models remain mutable (no frozen=True)."""

    def test_span_content_append(self) -> None:
        """Content list should be mutable."""
        event = _make_model_event()
        span = TimelineSpan(id="s1", name="test", span_type="agent")

        span.content.append(TimelineEvent(event=event))

        assert len(span.content) == 1

    def test_span_utility_flag(self) -> None:
        """Utility flag should be mutable."""
        event = _make_model_event()
        span = TimelineSpan(
            id="s1",
            name="test",
            span_type="agent",
            content=[TimelineEvent(event=event)],
        )

        span.utility = True

        assert span.utility is True

    def test_span_outline_assignment(self) -> None:
        """Outline should be assignable."""
        event = _make_model_event()
        span = TimelineSpan(
            id="s1",
            name="test",
            span_type="agent",
            content=[TimelineEvent(event=event)],
        )

        span.outline = Outline(nodes=[OutlineNode(event="e1", children=[])])

        assert span.outline is not None
        assert len(span.outline.nodes) == 1
