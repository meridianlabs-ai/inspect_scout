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
from inspect_scout._transcript.nodes import (
    AgentNode,
    AgentSourceSpan,
    AgentSourceTool,
    Branch,
    EventNode,
    SectionNode,
    TranscriptNodes,
    build_transcript_nodes,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "events"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture file containing events and expectations.

    Each fixture has:
    - description: Human-readable test case description
    - events: List of events in minimal JSON format
    - expected: Expected TranscriptNodes structure

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


def get_event_uuids(node: SectionNode | AgentNode) -> list[str]:
    """Extract event UUIDs from a node's content.

    Args:
        node: The node to extract UUIDs from.

    Returns:
        List of event UUIDs (not including child agents).
    """
    uuids: list[str] = []
    for item in node.content:
        if isinstance(item, EventNode):
            uuid = getattr(item.event, "uuid", None)
            if uuid:
                uuids.append(uuid)
        elif isinstance(item, AgentNode):
            # Don't recurse into child agents for this list
            pass
    return uuids


def get_child_agents(node: AgentNode) -> list[AgentNode]:
    """Get child agent nodes from an agent's content.

    Args:
        node: The agent node to search.

    Returns:
        List of child AgentNodes.
    """
    return [item for item in node.content if isinstance(item, AgentNode)]


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


def assert_section_matches(
    actual: SectionNode | None,
    expected: dict[str, Any] | None,
    section_name: str,
) -> None:
    """Assert a section node matches expected structure."""
    if expected is None:
        assert actual is None, f"Expected {section_name} to be None"
        return

    assert actual is not None, f"Expected {section_name} to exist"
    assert actual.section == expected["section"]

    if "event_uuids" in expected:
        actual_uuids = get_event_uuids(actual)
        assert actual_uuids == expected["event_uuids"], (
            f"{section_name} event UUIDs mismatch: "
            f"got {actual_uuids}, expected {expected['event_uuids']}"
        )

    if "total_tokens" in expected:
        assert actual.total_tokens == expected["total_tokens"], (
            f"{section_name} token count mismatch: "
            f"got {actual.total_tokens}, expected {expected['total_tokens']}"
        )


def assert_branch_matches(
    actual: Branch,
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
            if isinstance(item, EventNode):
                uuid = getattr(item.event, "uuid", None)
                if uuid:
                    actual_uuids.append(uuid)
        assert actual_uuids == expected["event_uuids"], (
            f"{branch_name} event UUIDs mismatch: "
            f"got {actual_uuids}, expected {expected['event_uuids']}"
        )


def assert_agent_matches(
    actual: AgentNode | None,
    expected: dict[str, Any] | None,
    agent_name: str = "agent",
) -> None:
    """Assert an agent node matches expected structure."""
    if expected is None:
        assert actual is None, f"Expected {agent_name} to be None"
        return

    assert actual is not None, f"Expected {agent_name} to exist"
    assert actual.id == expected["id"], (
        f"{agent_name} id mismatch: got {actual.id}, expected {expected['id']}"
    )
    assert actual.name == expected["name"], (
        f"{agent_name} name mismatch: got {actual.name}, expected {expected['name']}"
    )

    # Check source type
    expected_source = expected.get("source", {})
    assert actual.source.source == expected_source.get("source"), (
        f"{agent_name} source type mismatch: "
        f"got {actual.source.source}, expected {expected_source.get('source')}"
    )

    # Check source details
    if expected_source.get("source") == "span":
        assert isinstance(actual.source, AgentSourceSpan)
        if "span_id" in expected_source:
            assert actual.source.span_id == expected_source["span_id"]
    elif expected_source.get("source") == "tool":
        assert isinstance(actual.source, AgentSourceTool)

    # Check event UUIDs if specified
    if "event_uuids" in expected:
        actual_uuids = get_event_uuids(actual)
        assert actual_uuids == expected["event_uuids"], (
            f"{agent_name} event UUIDs mismatch: "
            f"got {actual_uuids}, expected {expected['event_uuids']}"
        )

    # Check total tokens if specified
    if "total_tokens" in expected:
        assert actual.total_tokens == expected["total_tokens"], (
            f"{agent_name} token count mismatch: "
            f"got {actual.total_tokens}, expected {expected['total_tokens']}"
        )

    # Check utility if specified
    if "utility" in expected:
        assert actual.utility == expected["utility"], (
            f"{agent_name} utility mismatch: "
            f"got {actual.utility}, expected {expected['utility']}"
        )

    # Check branches if specified
    if "branches" in expected:
        expected_branches = expected["branches"]
        assert len(actual.branches) == len(expected_branches), (
            f"{agent_name} branch count mismatch: "
            f"got {len(actual.branches)}, expected {len(expected_branches)}"
        )
        for i, (actual_branch, expected_branch) in enumerate(
            zip(actual.branches, expected_branches, strict=True)
        ):
            assert_branch_matches(
                actual_branch,
                expected_branch,
                f"{agent_name}.branches[{i}]",
            )

    # Check child agents if specified
    if "children" in expected:
        actual_children = get_child_agents(actual)
        expected_children = expected["children"]
        assert len(actual_children) == len(expected_children), (
            f"{agent_name} child count mismatch: "
            f"got {len(actual_children)}, expected {len(expected_children)}"
        )
        for i, (actual_child, expected_child) in enumerate(
            zip(actual_children, expected_children, strict=True)
        ):
            assert_agent_matches(
                actual_child, expected_child, f"{agent_name}.children[{i}]"
            )


def assert_nodes_match(actual: TranscriptNodes, expected: dict[str, Any]) -> None:
    """Assert transcript nodes match expected structure."""
    assert_section_matches(actual.init, expected.get("init"), "init")
    assert_agent_matches(actual.agent, expected.get("agent"), "agent")
    assert_section_matches(actual.scoring, expected.get("scoring"), "scoring")


# =============================================================================
# Parametrized Tests
# =============================================================================


@pytest.mark.parametrize("fixture_name", get_fixture_names())
def test_build_transcript_nodes(fixture_name: str) -> None:
    """Test build_transcript_nodes with JSON fixtures.

    Each fixture contains both events and expected results, allowing the same
    test data to be used by both Python and TypeScript implementations.
    """
    fixture = load_fixture(fixture_name)
    events = events_from_json(fixture)
    result = build_transcript_nodes(events)

    expected = fixture.get("expected", {})
    assert_nodes_match(result, expected)


# =============================================================================
# Specific Tests
# =============================================================================


def test_empty_events_returns_empty_nodes() -> None:
    """Empty event list should return TranscriptNodes with all None."""
    result = build_transcript_nodes([])
    assert result.init is None
    assert result.agent is None
    assert result.scoring is None
    assert result.total_tokens == 0


def test_event_node_extracts_timing_from_event() -> None:
    """EventNode should extract timing from event."""
    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    completed = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    event = create_model_event(timestamp=ts, completed=completed)
    node = EventNode(event=event)

    assert node.start_time == ts
    assert node.end_time == completed


def test_event_node_extracts_tokens_from_model_event() -> None:
    """EventNode should extract token count from ModelEvent."""
    usage = ModelUsage(input_tokens=100, output_tokens=50)
    event = create_model_event(usage=usage)
    node = EventNode(event=event)

    assert node.total_tokens == 150


def test_event_node_returns_zero_tokens_for_non_model_event() -> None:
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

    node = EventNode(event=event)
    assert node.total_tokens == 0


def test_agent_node_aggregates_tokens_from_content() -> None:
    """AgentNode should sum tokens from all content."""
    usage1 = ModelUsage(input_tokens=100, output_tokens=50)
    usage2 = ModelUsage(input_tokens=200, output_tokens=100)

    event1 = create_model_event(uuid="e1", usage=usage1)
    event2 = create_model_event(uuid="e2", usage=usage2)

    agent = AgentNode(
        id="test",
        name="test",
        source=AgentSourceSpan(span_id="test"),
        content=[EventNode(event=event1), EventNode(event=event2)],
    )

    assert agent.total_tokens == 450  # 150 + 300


def test_section_node_aggregates_tokens_from_content() -> None:
    """SectionNode should sum tokens from all content."""
    usage = ModelUsage(input_tokens=50, output_tokens=25)
    event = create_model_event(uuid="e1", usage=usage)

    section = SectionNode(
        section="init",
        content=[EventNode(event=event)],
    )

    assert section.total_tokens == 75
