"""Transcript nodes: hierarchical structure for visualization and scanning.

Transforms flat event streams into a semantic tree with agent-centric interpretation
and phase separation (init/agent/scoring).

Uses inspect_ai's event_tree() to parse span structure.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from inspect_ai.event import (
    Event,
    ModelEvent,
    SpanNode,
    ToolEvent,
    event_sequence,
    event_tree,
)

# Type alias for tree items returned by event_tree
TreeItem = SpanNode | Event


# =============================================================================
# Agent Source Types
# =============================================================================


@dataclass(frozen=True)
class AgentSourceSpan:
    """Agent detected via explicit span with type='agent'."""

    source: Literal["span"] = "span"
    span_id: str = ""
    invoked_by: ToolEvent | None = None


@dataclass(frozen=True)
class AgentSourceTool:
    """Agent inferred from tool call spawning nested events."""

    source: Literal["tool"] = "tool"
    tool_event: ToolEvent | None = None


AgentSource = AgentSourceSpan | AgentSourceTool


# =============================================================================
# Node Types
# =============================================================================


def _min_start_time(nodes: Sequence["TranscriptNode"]) -> datetime | None:
    """Return the earliest start time among nodes.

    Args:
        nodes: Sequence of transcript nodes to check.

    Returns:
        The minimum start_time, or None if no nodes have start times.
    """
    times = [node.start_time for node in nodes if node.start_time]
    return min(times) if times else None


def _max_end_time(nodes: Sequence["TranscriptNode"]) -> datetime | None:
    """Return the latest end time among nodes.

    Args:
        nodes: Sequence of transcript nodes to check.

    Returns:
        The maximum end_time, or None if no nodes have end times.
    """
    times = [node.end_time for node in nodes if node.end_time]
    return max(times) if times else None


def _sum_tokens(nodes: Sequence["TranscriptNode"]) -> int:
    """Sum total tokens across all nodes.

    Args:
        nodes: Sequence of transcript nodes to sum.

    Returns:
        Total token count from all nodes.
    """
    return sum(node.total_tokens for node in nodes)


class TranscriptNode(ABC):
    """Abstract base for all transcript nodes."""

    @property
    @abstractmethod
    def start_time(self) -> datetime | None:
        """Start time of this node."""
        ...

    @property
    @abstractmethod
    def end_time(self) -> datetime | None:
        """End time of this node."""
        ...

    @property
    @abstractmethod
    def total_tokens(self) -> int:
        """Total tokens consumed by this node and its children."""
        ...


@dataclass
class EventNode(TranscriptNode):
    """Wraps a single Event."""

    event: Event

    @property
    def start_time(self) -> datetime | None:
        """Event timestamp."""
        ts = getattr(self.event, "timestamp", None)
        if ts is not None:
            return ts if isinstance(ts, datetime) else None
        return None

    @property
    def end_time(self) -> datetime | None:
        """Event completion time if available, else timestamp."""
        completed = getattr(self.event, "completed", None)
        if completed is not None:
            return completed if isinstance(completed, datetime) else None
        return self.start_time

    @property
    def total_tokens(self) -> int:
        """Tokens from this event (ModelEvent only)."""
        if isinstance(self.event, ModelEvent):
            output = getattr(self.event, "output", None)
            if output is not None:
                usage = getattr(output, "usage", None)
                if usage is not None:
                    input_tokens = getattr(usage, "input_tokens", 0) or 0
                    output_tokens = getattr(usage, "output_tokens", 0) or 0
                    return input_tokens + output_tokens
        return 0


@dataclass
class AgentNode(TranscriptNode):
    """Represents an agent with nested content (events and child agents)."""

    id: str
    name: str
    source: AgentSource
    content: list["EventNode | AgentNode"] = field(default_factory=list)
    task_description: str | None = None

    @property
    def start_time(self) -> datetime | None:
        """Earliest start time among content."""
        return _min_start_time(self.content)

    @property
    def end_time(self) -> datetime | None:
        """Latest end time among content."""
        return _max_end_time(self.content)

    @property
    def total_tokens(self) -> int:
        """Sum of tokens from all content."""
        return _sum_tokens(self.content)


@dataclass
class SectionNode(TranscriptNode):
    """Section node for init or scoring phases (EventNodes only)."""

    section: Literal["init", "scoring"]
    content: list[EventNode] = field(default_factory=list)

    @property
    def start_time(self) -> datetime | None:
        """Earliest start time among content."""
        return _min_start_time(self.content)

    @property
    def end_time(self) -> datetime | None:
        """Latest end time among content."""
        return _max_end_time(self.content)

    @property
    def total_tokens(self) -> int:
        """Sum of tokens from all content."""
        return _sum_tokens(self.content)


@dataclass
class TranscriptNodes:
    """Root container for transcript node hierarchy."""

    init: SectionNode | None = None
    agent: AgentNode | None = None
    scoring: SectionNode | None = None

    def _sections(self) -> list[TranscriptNode]:
        """Return list of non-None sections for aggregation."""
        return [s for s in [self.init, self.agent, self.scoring] if s is not None]

    @property
    def start_time(self) -> datetime | None:
        """Earliest start time across all sections."""
        return _min_start_time(self._sections())

    @property
    def end_time(self) -> datetime | None:
        """Latest end time across all sections."""
        return _max_end_time(self._sections())

    @property
    def total_tokens(self) -> int:
        """Total tokens across all sections."""
        return _sum_tokens(self._sections())


# =============================================================================
# Builder
# =============================================================================


def build_transcript_nodes(events: list[Event]) -> TranscriptNodes:
    """Build structured nodes from flat event list.

    Uses inspect_ai's event_tree() to parse span structure, then:
    1. Look for top-level spans: "init", "solvers", "scorers"
    2. If present, use them to partition events into sections
    3. If not present, treat the entire event stream as the agent

    Agent detection within the solvers section (or entire stream):
    - Explicit agent spans (type='agent') -> AgentSourceSpan
    - Tool spans/calls with model events -> AgentSourceTool
    """
    if not events:
        return TranscriptNodes()

    # Use event_tree to get hierarchical structure
    tree = event_tree(events)

    # Find top-level spans by name
    top_spans: dict[str, SpanNode] = {}
    for item in tree:
        if isinstance(item, SpanNode) and item.name in ("init", "solvers", "scorers"):
            top_spans[item.name] = item

    # Check for explicit phase spans (init, solvers, or scorers)
    has_phase_spans = (
        "init" in top_spans or "solvers" in top_spans or "scorers" in top_spans
    )

    if has_phase_spans:
        # Use spans to partition events
        init_span = top_spans.get("init")
        solvers_span = top_spans.get("solvers")
        scorers_span = top_spans.get("scorers")

        init_section = (
            _build_section_from_span("init", init_span) if init_span else None
        )
        agent_node = (
            _build_agent_from_solvers_span(solvers_span) if solvers_span else None
        )
        scoring_section = (
            _build_section_from_span("scoring", scorers_span) if scorers_span else None
        )

        return TranscriptNodes(
            init=init_section,
            agent=agent_node,
            scoring=scoring_section,
        )
    else:
        # No phase spans - treat entire tree as agent
        agent_node = _build_agent_from_tree(tree)
        return TranscriptNodes(agent=agent_node)


def _build_section_from_span(
    section: Literal["init", "scoring"], span: SpanNode
) -> SectionNode:
    """Build a SectionNode from a SpanNode.

    Uses event_sequence to flatten any nested spans into a list of events.

    Args:
        section: The section type ("init" or "scoring").
        span: The SpanNode containing the section's events.

    Returns:
        A SectionNode with EventNodes for all events in the span.
    """
    # event_sequence flattens the tree, extracting just the events
    events = event_sequence(span.children)
    content = [EventNode(event=e) for e in events]
    return SectionNode(section=section, content=content)


def _build_agent_from_solvers_span(solvers_span: SpanNode) -> AgentNode | None:
    """Build agent hierarchy from the solvers span.

    Looks for explicit agent spans (type='agent') within the solvers span.
    If found, builds the agent tree from those spans. If not found, uses
    the solvers span itself as the agent container.

    Args:
        solvers_span: The top-level solvers SpanNode.

    Returns:
        An AgentNode representing the agent hierarchy, or None if empty.
    """
    if not solvers_span.children:
        return None

    # Look for agent spans within solvers
    agent_spans: list[SpanNode] = []
    other_items: list[TreeItem] = []

    for child in solvers_span.children:
        if isinstance(child, SpanNode) and child.type == "agent":
            agent_spans.append(child)
        else:
            other_items.append(child)

    if agent_spans:
        # Build from explicit agent spans
        if len(agent_spans) == 1:
            return _build_agent_from_span(agent_spans[0], other_items)
        else:
            # Multiple agent spans - create root containing all
            children: list[EventNode | AgentNode] = [
                _build_agent_from_span(span, []) for span in agent_spans
            ]
            # Add any orphan events
            for item in other_items:
                children.insert(0, _tree_item_to_node(item))
            return AgentNode(
                id="root",
                name="root",
                source=AgentSourceSpan(span_id="root"),
                content=children,
            )
    else:
        # No explicit agent spans - use solvers span itself as the agent container
        # Process children, which may include tool spans with model events
        content: list[EventNode | AgentNode] = []
        for item in solvers_span.children:
            content.append(_tree_item_to_node(item))

        return AgentNode(
            id=solvers_span.id,
            name=solvers_span.name,
            source=AgentSourceSpan(span_id=solvers_span.id),
            content=content,
        )


def _build_agent_from_span(
    span: SpanNode, extra_items: list[TreeItem] | None = None
) -> AgentNode:
    """Build an AgentNode from a SpanNode with type='agent'.

    Args:
        span: The agent SpanNode to convert.
        extra_items: Additional tree items (orphan events) to include
            at the start of the agent's content.

    Returns:
        An AgentNode with the span's children as content.
    """
    content: list[EventNode | AgentNode] = []

    # Add any extra items first (orphan events)
    if extra_items:
        for item in extra_items:
            content.append(_tree_item_to_node(item))

    # Process span children
    for child in span.children:
        content.append(_tree_item_to_node(child))

    return AgentNode(
        id=span.id,
        name=span.name,
        source=AgentSourceSpan(span_id=span.id),
        content=content,
    )


def _tree_item_to_node(item: TreeItem) -> EventNode | AgentNode:
    """Convert a tree item (SpanNode or Event) to an EventNode or AgentNode.

    Dispatches to the appropriate builder based on item type:
    - SpanNode with type='agent' -> _build_agent_from_span
    - Other SpanNode -> _build_agent_from_span_generic
    - Event -> _event_to_node

    Args:
        item: A tree item from event_tree() (SpanNode or Event).

    Returns:
        An EventNode or AgentNode representing the item.
    """
    if isinstance(item, SpanNode):
        if item.type == "agent":
            return _build_agent_from_span(item)
        else:
            # Non-agent span - flatten to events wrapped in a synthetic agent
            # or just return the events directly
            return _build_agent_from_span_generic(item)
    else:
        return _event_to_node(item)


def _event_to_node(event: Event) -> EventNode | AgentNode:
    """Convert an Event to an EventNode or AgentNode.

    Handles ToolEvents that spawn nested agents, recursively processing
    nested events to detect further agent spawning.
    """
    if isinstance(event, ToolEvent):
        agent_name = getattr(event, "agent", None)
        nested_events = getattr(event, "events", None)
        if agent_name and nested_events:
            # Recursively process nested events to handle nested tool agents
            nested_content: list[EventNode | AgentNode] = [
                _event_to_node(e) for e in nested_events
            ]
            return AgentNode(
                id=f"tool-agent-{event.id}",
                name=agent_name,
                source=AgentSourceTool(tool_event=event),
                content=nested_content,
            )
    return EventNode(event=event)


def _build_agent_from_span_generic(span: SpanNode) -> AgentNode:
    """Build an AgentNode from a non-agent SpanNode.

    If the span is a tool span (type="tool") containing model events,
    we treat it as a tool-spawned agent.
    """
    content: list[EventNode | AgentNode] = []
    for child in span.children:
        content.append(_tree_item_to_node(child))

    # Determine the source based on span type and content
    source: AgentSource
    if span.type == "tool" and _contains_model_events(span):
        # Tool span with model generations = tool-spawned agent
        source = AgentSourceTool(tool_event=None)
    else:
        source = AgentSourceSpan(span_id=span.id)

    return AgentNode(
        id=span.id,
        name=span.name,
        source=source,
        content=content,
    )


def _contains_model_events(span: SpanNode) -> bool:
    """Check if a span contains any ModelEvent (recursively).

    Args:
        span: The SpanNode to search.

    Returns:
        True if any descendant is a ModelEvent, False otherwise.
    """
    for child in span.children:
        if isinstance(child, SpanNode):
            if _contains_model_events(child):
                return True
        elif isinstance(child, ModelEvent):
            return True
    return False


def _build_agent_from_tree(tree: list[TreeItem]) -> AgentNode:
    """Build agent from a list of tree items when no explicit phase spans exist.

    Creates a synthetic "main" agent containing all tree items as content.

    Args:
        tree: List of tree items from event_tree().

    Returns:
        An AgentNode with id="main" containing all items.
    """
    content: list[EventNode | AgentNode] = []

    for item in tree:
        content.append(_tree_item_to_node(item))

    return AgentNode(
        id="main",
        name="main",
        source=AgentSourceSpan(span_id="main"),
        content=content,
    )
