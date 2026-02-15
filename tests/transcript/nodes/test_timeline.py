"""Tests for transcript nodes module.

Uses JSON fixtures for data-driven testing. Each fixture contains
a minimal event representation and expected node structure.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from inspect_ai.event import (
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
    ModelUsage,
)
from inspect_scout._transcript.timeline import (
    Timeline,
    TimelineBranch,
    TimelineEvent,
    TimelineSpan,
    build_timeline,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "events"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture file containing events and expectations.

    Each fixture has:
    - description: Human-readable test case description
    - events: List of events in minimal JSON format
    - expected: Expected structure

    The same fixtures can be used by both Python and TypeScript test suites.
    """
    path = FIXTURES_DIR / f"{name}.json"
    with open(path) as f:
        return cast(dict[str, Any], json.load(f))


def get_fixture_names() -> list[str]:
    """Get all fixture names from the fixtures directory."""
    return [p.stem for p in FIXTURES_DIR.glob("*.json")]


def parse_timestamp(ts_str: str | None) -> datetime:
    """Parse ISO timestamp string to datetime."""
    if ts_str is None:
        return datetime.now(timezone.utc)
    # Handle various ISO formats
    ts_str = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(ts_str)


def _parse_input_messages(input_data: list[dict[str, Any]]) -> list[ChatMessage]:
    """Parse input messages from fixture JSON into ChatMessage objects."""
    messages: list[ChatMessage] = []
    for msg in input_data:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            messages.append(ChatMessageSystem(content=content))
        elif role == "user":
            messages.append(ChatMessageUser(content=content))
        elif role == "assistant":
            messages.append(ChatMessageAssistant(content=content))
        elif role == "tool":
            messages.append(
                ChatMessageTool(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                )
            )
    return messages


def events_from_json(data: dict[str, Any]) -> list[Event]:
    """Deserialize minimal JSON to full inspect_ai Events.

    Fills in required fields with sensible defaults.
    """
    events: list[Event] = []

    for event_data in data.get("events", []):
        event_type = event_data.get("event")
        event = _create_event(event_type, event_data)
        if event is not None:
            events.append(event)

    return events


def _create_event(event_type: str, data: dict[str, Any]) -> Event | None:
    """Create a specific event type from JSON data."""
    timestamp = parse_timestamp(data.get("timestamp"))
    completed = (
        parse_timestamp(data.get("completed")) if data.get("completed") else None
    )
    uuid = data.get("uuid")
    span_id = data.get("span_id")
    working_start = data.get("working_start", 0.0)

    if event_type == "model":
        output_data = data.get("output", {})
        usage_data = output_data.get("usage", {})
        usage = ModelUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
        )
        output = ModelOutput(
            model=data.get("model", "test-model"),
            usage=usage,
        )
        input_messages: list[ChatMessage] = _parse_input_messages(data.get("input", []))
        return ModelEvent(
            uuid=uuid,
            span_id=span_id,
            timestamp=timestamp,
            working_start=working_start,
            pending=False,
            metadata=None,
            event="model",
            model=data.get("model", "test-model"),
            role=None,
            input=input_messages,
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=output,
            retries=None,
            error=None,
            cache=None,
            call=None,
            completed=completed,
            working_time=None,
        )

    elif event_type == "tool":
        # Handle nested events for tool-spawned agents
        nested_events: list[Event] = []
        if "events" in data:
            for nested_data in data["events"]:
                nested_event = _create_event(nested_data.get("event"), nested_data)
                if nested_event is not None:
                    nested_events.append(nested_event)

        return ToolEvent(
            uuid=uuid,
            span_id=span_id,
            timestamp=timestamp,
            working_start=working_start,
            pending=False,
            metadata=None,
            event="tool",
            type="function",
            id=data.get("id", "tool-id"),
            function=data.get("function", "unknown"),
            arguments={},
            view=None,
            result="",
            truncated=None,
            error=None,
            events=nested_events,
            completed=completed,
            working_time=None,
            agent=data.get("agent"),
            failed=None,
            message_id=None,
        )

    elif event_type == "info":
        return InfoEvent(
            uuid=uuid,
            span_id=span_id,
            timestamp=timestamp,
            working_start=working_start,
            pending=False,
            metadata=None,
            event="info",
            source=data.get("source", ""),
            data=data.get("data"),
        )

    elif event_type == "span_begin":
        return SpanBeginEvent(
            uuid=uuid,
            span_id=data.get("id"),  # span_id is the span's own id for begin events
            timestamp=timestamp,
            working_start=working_start,
            pending=False,
            metadata=None,
            event="span_begin",
            id=data.get("id", ""),
            parent_id=data.get("parent_id"),
            type=data.get("type"),
            name=data.get("name", ""),
        )

    elif event_type == "span_end":
        return SpanEndEvent(
            uuid=uuid,
            span_id=data.get("span_id"),
            timestamp=timestamp,
            working_start=working_start,
            pending=False,
            metadata=None,
            event="span_end",
            id=data.get("id", data.get("span_id", "")),
        )

    return None


def get_event_uuids(node: TimelineSpan) -> list[str]:
    """Extract event UUIDs from a span's content.

    Args:
        node: The span to extract UUIDs from.

    Returns:
        List of event UUIDs (not including child spans).
    """
    uuids: list[str] = []
    for item in node.content:
        if isinstance(item, TimelineEvent):
            uuid = getattr(item.event, "uuid", None)
            if uuid:
                uuids.append(uuid)
        elif isinstance(item, TimelineSpan):
            # Don't recurse into child spans for this list
            pass
    return uuids


def get_child_spans(node: TimelineSpan) -> list[TimelineSpan]:
    """Get child spans from a span's content.

    Args:
        node: The span to search.

    Returns:
        List of child TimelineSpans.
    """
    return [item for item in node.content if isinstance(item, TimelineSpan)]


def create_model_event(
    uuid: str = "test",
    timestamp: datetime | None = None,
    completed: datetime | None = None,
    usage: ModelUsage | None = None,
) -> ModelEvent:
    """Create a ModelEvent with sensible test defaults.

    Args:
        uuid: Event UUID.
        timestamp: Event timestamp (defaults to now).
        completed: Completion timestamp.
        usage: Token usage (defaults to no usage).

    Returns:
        A ModelEvent with the specified values and sensible defaults.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    output = (
        ModelOutput(model="test", usage=usage) if usage else ModelOutput(model="test")
    )

    return ModelEvent(
        uuid=uuid,
        span_id=None,
        timestamp=timestamp,
        working_start=0.0,
        pending=False,
        metadata=None,
        event="model",
        model="test",
        role=None,
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=output,
        retries=None,
        error=None,
        cache=None,
        call=None,
        completed=completed,
        working_time=None,
    )


def assert_scoring_span_matches(
    root: TimelineSpan,
    expected: dict[str, Any] | None,
) -> None:
    """Assert a scoring span in the root matches expected structure.

    Scoring is now a TimelineSpan with span_type="scorer" in the root's content.
    """
    if expected is None:
        # No scoring expected — verify no scorer span exists
        scorer_spans = [
            item
            for item in root.content
            if isinstance(item, TimelineSpan) and item.span_type == "scorer"
        ]
        assert len(scorer_spans) == 0, "Expected no scoring span"
        return

    # Find the scoring span
    scorer_spans = [
        item
        for item in root.content
        if isinstance(item, TimelineSpan) and item.span_type == "scorer"
    ]
    assert len(scorer_spans) == 1, "Expected exactly one scoring span"
    scoring = scorer_spans[0]

    if "event_uuids" in expected:
        actual_uuids = get_event_uuids(scoring)
        assert actual_uuids == expected["event_uuids"], (
            f"scoring event UUIDs mismatch: "
            f"got {actual_uuids}, expected {expected['event_uuids']}"
        )

    if "total_tokens" in expected:
        assert scoring.total_tokens == expected["total_tokens"], (
            f"scoring token count mismatch: "
            f"got {scoring.total_tokens}, expected {expected['total_tokens']}"
        )


def assert_branch_matches(
    actual: TimelineBranch,
    expected: dict[str, Any],
    branch_name: str = "branch",
) -> None:
    """Assert a branch matches expected structure."""
    assert actual.forked_at == expected["forked_at"], (
        f"{branch_name} forked_at mismatch: "
        f"got {actual.forked_at!r}, expected {expected['forked_at']!r}"
    )

    if "event_uuids" in expected:
        actual_uuids: list[str] = []
        for item in actual.content:
            if isinstance(item, TimelineEvent):
                uuid = getattr(item.event, "uuid", None)
                if uuid:
                    actual_uuids.append(uuid)
        assert actual_uuids == expected["event_uuids"], (
            f"{branch_name} event UUIDs mismatch: "
            f"got {actual_uuids}, expected {expected['event_uuids']}"
        )


def assert_span_matches(
    actual: TimelineSpan | None,
    expected: dict[str, Any] | None,
    span_name: str = "span",
) -> None:
    """Assert a span matches expected structure."""
    if expected is None:
        assert actual is None, f"Expected {span_name} to be None"
        return

    assert actual is not None, f"Expected {span_name} to exist"
    assert actual.id == expected["id"], (
        f"{span_name} id mismatch: got {actual.id}, expected {expected['id']}"
    )
    assert actual.name == expected["name"], (
        f"{span_name} name mismatch: got {actual.name}, expected {expected['name']}"
    )

    # Check source/span_type
    expected_source = expected.get("source", {})
    if expected_source.get("source") == "span":
        # Agent from explicit span
        assert actual.span_type == "agent", (
            f"{span_name} span_type mismatch: got {actual.span_type}, expected 'agent'"
        )
    elif expected_source.get("source") == "tool":
        # Tool-spawned agent
        assert actual.span_type is None, (
            f"{span_name} span_type mismatch: got {actual.span_type}, expected None"
        )

    # Check event UUIDs if specified
    if "event_uuids" in expected:
        actual_uuids = get_event_uuids(actual)
        assert actual_uuids == expected["event_uuids"], (
            f"{span_name} event UUIDs mismatch: "
            f"got {actual_uuids}, expected {expected['event_uuids']}"
        )

    # Check total tokens if specified
    if "total_tokens" in expected:
        assert actual.total_tokens == expected["total_tokens"], (
            f"{span_name} token count mismatch: "
            f"got {actual.total_tokens}, expected {expected['total_tokens']}"
        )

    # Check utility if specified
    if "utility" in expected:
        assert actual.utility == expected["utility"], (
            f"{span_name} utility mismatch: "
            f"got {actual.utility}, expected {expected['utility']}"
        )

    # Check branches if specified
    if "branches" in expected:
        expected_branches = expected["branches"]
        assert len(actual.branches) == len(expected_branches), (
            f"{span_name} branch count mismatch: "
            f"got {len(actual.branches)}, expected {len(expected_branches)}"
        )
        for i, (actual_branch, expected_branch) in enumerate(
            zip(actual.branches, expected_branches, strict=True)
        ):
            assert_branch_matches(
                actual_branch,
                expected_branch,
                f"{span_name}.branches[{i}]",
            )

    # Check child spans if specified
    if "children" in expected:
        actual_children = get_child_spans(actual)
        expected_children = expected["children"]
        assert len(actual_children) == len(expected_children), (
            f"{span_name} child count mismatch: "
            f"got {len(actual_children)}, expected {len(expected_children)}"
        )
        for i, (actual_child, expected_child) in enumerate(
            zip(actual_children, expected_children, strict=True)
        ):
            assert_span_matches(
                actual_child, expected_child, f"{span_name}.children[{i}]"
            )


def assert_timeline_matches(actual: Timeline, expected: dict[str, Any]) -> None:
    """Assert timeline matches expected structure.

    The expected structure still uses init/agent/scoring keys for backward
    compatibility with fixtures. We map these to the new Timeline structure:
    - init events are folded into root content (not checked separately)
    - agent maps to root
    - scoring maps to a child TimelineSpan with span_type="scorer"
    """
    root = actual.root

    # Check init: init events are now in the root content, verified by
    # checking they exist as the first events if expected
    expected_init = expected.get("init")
    if expected_init is not None:
        # Verify init events exist at the beginning of root content
        expected_uuids = expected_init.get("event_uuids", [])
        if expected_uuids:
            # Init events should be TimelineEvents at the start of root content
            actual_init_uuids: list[str] = []
            for item in root.content:
                if isinstance(item, TimelineEvent):
                    uuid = getattr(item.event, "uuid", None)
                    if uuid:
                        actual_init_uuids.append(uuid)
                    if len(actual_init_uuids) >= len(expected_uuids):
                        break
                else:
                    break
            # The init UUIDs should appear at the start
            assert actual_init_uuids[: len(expected_uuids)] == expected_uuids, (
                f"init event UUIDs mismatch: "
                f"got {actual_init_uuids[: len(expected_uuids)]}, "
                f"expected {expected_uuids}"
            )

    # Check agent (now root)
    expected_agent = expected.get("agent")
    if expected_agent is not None:
        assert root.id == expected_agent["id"], (
            f"root id mismatch: got {root.id}, expected {expected_agent['id']}"
        )
        assert root.name == expected_agent["name"], (
            f"root name mismatch: got {root.name}, expected {expected_agent['name']}"
        )

        # Check event UUIDs (excluding init events and scoring span)
        if "event_uuids" in expected_agent:
            actual_uuids = get_event_uuids(root)
            # Filter out init UUIDs if init was present
            if expected_init and "event_uuids" in expected_init:
                init_uuid_set = set(expected_init["event_uuids"])
                actual_uuids = [u for u in actual_uuids if u not in init_uuid_set]
            assert actual_uuids == expected_agent["event_uuids"], (
                f"agent event UUIDs mismatch: "
                f"got {actual_uuids}, expected {expected_agent['event_uuids']}"
            )

        # Check total tokens if specified
        if "total_tokens" in expected_agent:
            # Total tokens of root includes init and scoring
            expected_tokens = expected_agent["total_tokens"]
            if expected_init and "total_tokens" in expected_init:
                expected_tokens += expected_init["total_tokens"]
            expected_scoring = expected.get("scoring")
            if expected_scoring and "total_tokens" in expected_scoring:
                expected_tokens += expected_scoring["total_tokens"]
            assert root.total_tokens == expected_tokens, (
                f"root token count mismatch: "
                f"got {root.total_tokens}, expected {expected_tokens}"
            )

        # Check utility if specified
        if "utility" in expected_agent:
            assert root.utility == expected_agent["utility"]

        # Check branches if specified
        if "branches" in expected_agent:
            expected_branches = expected_agent["branches"]
            assert len(root.branches) == len(expected_branches), (
                f"root branch count mismatch: "
                f"got {len(root.branches)}, expected {len(expected_branches)}"
            )
            for i, (actual_branch, expected_branch) in enumerate(
                zip(root.branches, expected_branches, strict=True)
            ):
                assert_branch_matches(
                    actual_branch, expected_branch, f"root.branches[{i}]"
                )

        # Check child spans if specified
        if "children" in expected_agent:
            # Filter out scorer spans from children comparison
            actual_children = [
                item
                for item in root.content
                if isinstance(item, TimelineSpan) and item.span_type != "scorer"
            ]
            expected_children = expected_agent["children"]
            assert len(actual_children) == len(expected_children), (
                f"root child count mismatch: "
                f"got {len(actual_children)}, expected {len(expected_children)}"
            )
            for i, (actual_child, expected_child) in enumerate(
                zip(actual_children, expected_children, strict=True)
            ):
                assert_span_matches(actual_child, expected_child, f"root.children[{i}]")
    else:
        # No agent expected — root should have no meaningful content
        pass

    # Check scoring (now a child TimelineSpan with span_type="scorer")
    assert_scoring_span_matches(root, expected.get("scoring"))


# =============================================================================
# Parametrized Tests
# =============================================================================


@pytest.mark.parametrize("fixture_name", get_fixture_names())
def test_build_timeline(fixture_name: str) -> None:
    """Test build_timeline with JSON fixtures.

    Each fixture contains both events and expected results, allowing the same
    test data to be used by both Python and TypeScript implementations.
    """
    fixture = load_fixture(fixture_name)
    events = events_from_json(fixture)
    result = build_timeline(events)

    expected = fixture.get("expected", {})
    assert_timeline_matches(result, expected)


# =============================================================================
# Specific Tests
# =============================================================================


def test_empty_events_returns_empty_timeline() -> None:
    """Empty event list should return Timeline with empty root."""
    result = build_timeline([])
    assert result.root is not None
    assert len(result.root.content) == 0
    assert result.root.total_tokens == 0


def test_timeline_event_extracts_timing_from_event() -> None:
    """TimelineEvent should extract timing from event."""
    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    completed = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    event = create_model_event(timestamp=ts, completed=completed)
    node = TimelineEvent(event=event)

    assert node.start_time == ts
    assert node.end_time == completed


def test_timeline_event_extracts_tokens_from_model_event() -> None:
    """TimelineEvent should extract token count from ModelEvent."""
    usage = ModelUsage(input_tokens=100, output_tokens=50)
    event = create_model_event(usage=usage)
    node = TimelineEvent(event=event)

    assert node.total_tokens == 150


def test_timeline_event_returns_zero_tokens_for_non_model_event() -> None:
    """Non-ModelEvent should have zero tokens."""
    event = InfoEvent(
        uuid="test",
        span_id=None,
        timestamp=datetime.now(timezone.utc),
        working_start=0.0,
        pending=False,
        metadata=None,
        event="info",
        source="test",
        data=None,
    )

    node = TimelineEvent(event=event)
    assert node.total_tokens == 0


def test_timeline_span_aggregates_tokens_from_content() -> None:
    """TimelineSpan should sum tokens from all content."""
    usage1 = ModelUsage(input_tokens=100, output_tokens=50)
    usage2 = ModelUsage(input_tokens=200, output_tokens=100)

    event1 = create_model_event(uuid="e1", usage=usage1)
    event2 = create_model_event(uuid="e2", usage=usage2)

    span = TimelineSpan(
        id="test",
        name="test",
        span_type="agent",
        content=[TimelineEvent(event=event1), TimelineEvent(event=event2)],
    )

    assert span.total_tokens == 450  # 150 + 300
