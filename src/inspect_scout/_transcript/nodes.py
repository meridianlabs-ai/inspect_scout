"""Transcript nodes: hierarchical structure for visualization and scanning.

Transforms flat event streams into a semantic tree with agent-centric interpretation
and phase separation (init/agent/scoring).

Uses inspect_ai's event_tree() to parse span structure.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from inspect_ai.event import (
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanNode,
    ToolEvent,
    event_sequence,
    event_tree,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
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
    branches: list["Branch"] = field(default_factory=list)
    task_description: str | None = None
    utility: bool = False

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
class Branch(TranscriptNode):
    """A discarded alternative path from a branch point."""

    forked_at: str
    content: list[EventNode | AgentNode] = field(default_factory=list)

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

    # Detect explicit branches globally
    has_explicit_branches = any(
        isinstance(e, SpanBeginEvent) and e.type == "branch" for e in events
    )

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
            _build_agent_from_solvers_span(solvers_span, has_explicit_branches)
            if solvers_span
            else None
        )
        scoring_section = (
            _build_section_from_span("scoring", scorers_span) if scorers_span else None
        )

        if agent_node is not None:
            _classify_utility_agents(agent_node)
            _classify_branches(agent_node, has_explicit_branches)

        return TranscriptNodes(
            init=init_section,
            agent=agent_node,
            scoring=scoring_section,
        )
    else:
        # No phase spans - treat entire tree as agent
        agent_node = _build_agent_from_tree(tree, has_explicit_branches)
        _classify_utility_agents(agent_node)
        _classify_branches(agent_node, has_explicit_branches)
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


def _build_agent_from_solvers_span(
    solvers_span: SpanNode, has_explicit_branches: bool
) -> AgentNode | None:
    """Build agent hierarchy from the solvers span.

    Looks for explicit agent spans (type='agent') within the solvers span.
    If found, builds the agent tree from those spans. If not found, uses
    the solvers span itself as the agent container.

    Args:
        solvers_span: The top-level solvers SpanNode.
        has_explicit_branches: Whether explicit branch spans exist globally.

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
            return _build_agent_from_span(
                agent_spans[0], has_explicit_branches, other_items
            )
        else:
            # Multiple agent spans - create root containing all
            children: list[EventNode | AgentNode] = [
                _build_agent_from_span(span, has_explicit_branches, [])
                for span in agent_spans
            ]
            # Add any orphan events
            for item in other_items:
                children.insert(0, _tree_item_to_node(item, has_explicit_branches))
            return AgentNode(
                id="root",
                name="root",
                source=AgentSourceSpan(span_id="root"),
                content=children,
            )
    else:
        # No explicit agent spans - use solvers span itself as the agent container
        content, branches = _process_children(
            solvers_span.children, has_explicit_branches
        )

        return AgentNode(
            id=solvers_span.id,
            name=solvers_span.name,
            source=AgentSourceSpan(span_id=solvers_span.id),
            content=content,
            branches=branches,
        )


def _build_agent_from_span(
    span: SpanNode,
    has_explicit_branches: bool,
    extra_items: list[TreeItem] | None = None,
) -> AgentNode:
    """Build an AgentNode from a SpanNode with type='agent'.

    Args:
        span: The agent SpanNode to convert.
        has_explicit_branches: Whether explicit branch spans exist globally.
        extra_items: Additional tree items (orphan events) to include
            at the start of the agent's content.

    Returns:
        An AgentNode with the span's children as content.
    """
    content: list[EventNode | AgentNode] = []

    # Add any extra items first (orphan events)
    if extra_items:
        for item in extra_items:
            content.append(_tree_item_to_node(item, has_explicit_branches))

    # Process span children with branch awareness
    child_content, branches = _process_children(span.children, has_explicit_branches)
    content.extend(child_content)

    return AgentNode(
        id=span.id,
        name=span.name,
        source=AgentSourceSpan(span_id=span.id),
        content=content,
        branches=branches,
    )


def _tree_item_to_node(
    item: TreeItem, has_explicit_branches: bool
) -> EventNode | AgentNode:
    """Convert a tree item (SpanNode or Event) to an EventNode or AgentNode.

    Dispatches to the appropriate builder based on item type:
    - SpanNode with type='agent' -> _build_agent_from_span
    - Other SpanNode -> _build_agent_from_span_generic
    - Event -> _event_to_node

    Args:
        item: A tree item from event_tree() (SpanNode or Event).
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        An EventNode or AgentNode representing the item.
    """
    if isinstance(item, SpanNode):
        if item.type == "agent":
            return _build_agent_from_span(item, has_explicit_branches)
        else:
            # Non-agent span - flatten to events wrapped in a synthetic agent
            # or just return the events directly
            return _build_agent_from_span_generic(item, has_explicit_branches)
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


def _build_agent_from_span_generic(
    span: SpanNode, has_explicit_branches: bool
) -> AgentNode:
    """Build an AgentNode from a non-agent SpanNode.

    If the span is a tool span (type="tool") containing model events,
    we treat it as a tool-spawned agent.
    """
    content, branches = _process_children(span.children, has_explicit_branches)

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
        branches=branches,
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


def _build_agent_from_tree(
    tree: list[TreeItem], has_explicit_branches: bool
) -> AgentNode:
    """Build agent from a list of tree items when no explicit phase spans exist.

    Creates a synthetic "main" agent containing all tree items as content.

    Args:
        tree: List of tree items from event_tree().
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        An AgentNode with id="main" containing all items.
    """
    content, branches = _process_children(tree, has_explicit_branches)

    return AgentNode(
        id="main",
        name="main",
        source=AgentSourceSpan(span_id="main"),
        content=content,
        branches=branches,
    )


# =============================================================================
# Branch Processing
# =============================================================================


def _process_children(
    children: list[TreeItem], has_explicit_branches: bool
) -> tuple[list[EventNode | AgentNode], list[Branch]]:
    """Process a span's children with branch awareness.

    When explicit branches are active, collects adjacent type="branch" SpanNode
    runs and builds Branch objects from them. Otherwise, standard processing.

    Args:
        children: List of tree items to process.
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        Tuple of (content nodes, branch list).
    """
    if not has_explicit_branches:
        # Standard processing - no branch detection at build time
        content: list[EventNode | AgentNode] = []
        for item in children:
            content.append(_tree_item_to_node(item, has_explicit_branches))
        return content, []

    # Explicit branch mode: collect branch spans and build Branch objects
    content = []
    branches: list[Branch] = []
    branch_run: list[SpanNode] = []

    def _flush_branch_run(
        branch_run: list[SpanNode],
        parent_content: list[EventNode | AgentNode],
    ) -> list[Branch]:
        """Convert accumulated branch spans into Branch objects."""
        result: list[Branch] = []
        for span in branch_run:
            branch_content: list[EventNode | AgentNode] = []
            for child in span.children:
                branch_content.append(_tree_item_to_node(child, has_explicit_branches))
            branch_input = _get_branch_input(branch_content)
            forked_at = (
                _find_forked_at(parent_content, branch_input)
                if branch_input is not None
                else ""
            )
            result.append(Branch(forked_at=forked_at, content=branch_content))
        return result

    for item in children:
        if isinstance(item, SpanNode) and item.type == "branch":
            branch_run.append(item)
        else:
            if branch_run:
                branches.extend(_flush_branch_run(branch_run, content))
                branch_run = []
            content.append(_tree_item_to_node(item, has_explicit_branches))

    if branch_run:
        branches.extend(_flush_branch_run(branch_run, content))

    return content, branches


def _find_forked_at(
    agent_content: list[EventNode | AgentNode],
    branch_input: list[ChatMessage],
) -> str:
    """Determine the fork point by matching the last shared input message.

    Examines the last message in branch_input and matches it back to an event
    in the parent's content.

    Args:
        agent_content: The parent agent's content list.
        branch_input: The shared input messages of the branching ModelEvent.

    Returns:
        UUID of the event at the fork point, or "" if at the beginning.
    """
    if not branch_input:
        return ""

    last_msg = branch_input[-1]

    if isinstance(last_msg, ChatMessageTool):
        # Match tool_call_id to a ToolEvent.id
        tool_call_id = getattr(last_msg, "tool_call_id", None)
        if tool_call_id:
            for item in agent_content:
                if (
                    isinstance(item, EventNode)
                    and isinstance(item.event, ToolEvent)
                    and item.event.id == tool_call_id
                ):
                    return item.event.uuid or ""
        return ""

    if isinstance(last_msg, ChatMessageAssistant):
        # Match message id to ModelEvent.output.message.id
        msg_id = getattr(last_msg, "id", None)
        if msg_id:
            for item in agent_content:
                if isinstance(item, EventNode) and isinstance(item.event, ModelEvent):
                    output = getattr(item.event, "output", None)
                    if output is not None:
                        out_msg = getattr(output, "message", None)
                        if out_msg is not None:
                            out_id = getattr(out_msg, "id", None)
                            if out_id == msg_id:
                                return item.event.uuid or ""
        # Fallback: compare content
        msg_content = getattr(last_msg, "content", None)
        if msg_content:
            for item in agent_content:
                if isinstance(item, EventNode) and isinstance(item.event, ModelEvent):
                    output = getattr(item.event, "output", None)
                    if output is not None:
                        out_msg = getattr(output, "message", None)
                        if out_msg is not None:
                            out_content = getattr(out_msg, "content", None)
                            if out_content == msg_content:
                                return item.event.uuid or ""
        return ""

    # ChatMessageUser / ChatMessageSystem - fork at beginning
    return ""


def _get_branch_input(
    content: list[EventNode | AgentNode],
) -> list[ChatMessage] | None:
    """Extract the input from the first ModelEvent in branch content.

    Args:
        content: The branch's content nodes.

    Returns:
        The input message list, or None if no ModelEvent found.
    """
    for item in content:
        if isinstance(item, EventNode) and isinstance(item.event, ModelEvent):
            return list(item.event.input)
    return None


# =============================================================================
# Branch Auto-Detection
# =============================================================================


def _message_fingerprint(msg: ChatMessage) -> str:
    """Compute a fingerprint for a single ChatMessage.

    Serializes role + content, ignoring auto-generated fields like id, source,
    metadata.

    Args:
        msg: The chat message to fingerprint.

    Returns:
        SHA-256 hex digest of the message content.
    """
    role = getattr(msg, "role", "")
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        serialized = content
    else:
        # Content is list of Content objects
        serialized = json.dumps(
            [c.model_dump(exclude_none=True) for c in content],
            sort_keys=True,
        )
    raw = f"{role}:{serialized}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _input_fingerprint(messages: list[ChatMessage]) -> str:
    """Compute a fingerprint for a sequence of input messages.

    Args:
        messages: The input message list.

    Returns:
        SHA-256 hex digest of the concatenated message fingerprints.
    """
    parts = [_message_fingerprint(m) for m in messages]
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()


def _detect_auto_branches(agent: AgentNode) -> None:
    """Detect re-rolled ModelEvents with identical inputs and create branches.

    For each group of ModelEvents with the same input fingerprint, the last
    one stays in content and earlier ones (plus their trailing events up to
    the next re-roll) become branches.

    Mutates agent in-place.

    Args:
        agent: The agent node to process.
    """
    # Find ModelEvent indices and their fingerprints (skip empty inputs)
    model_indices: list[tuple[int, str]] = []
    for i, item in enumerate(agent.content):
        if isinstance(item, EventNode) and isinstance(item.event, ModelEvent):
            input_msgs = list(item.event.input)
            if not input_msgs:
                continue
            fp = _input_fingerprint(input_msgs)
            model_indices.append((i, fp))

    # Group by fingerprint
    fingerprint_groups: dict[str, list[int]] = {}
    for idx, fp in model_indices:
        fingerprint_groups.setdefault(fp, []).append(idx)

    # Only process groups with duplicates
    duplicate_groups = {
        fp: indices for fp, indices in fingerprint_groups.items() if len(indices) > 1
    }

    if not duplicate_groups:
        return

    # For each duplicate group, determine which indices become branches
    branch_ranges: list[tuple[int, int, list[ChatMessage]]] = []

    for _fp, indices in duplicate_groups.items():
        # Last re-roll stays in content, earlier ones become branches
        # Get the shared input from any of them
        first_idx = indices[0]
        first_item = agent.content[first_idx]
        assert isinstance(first_item, EventNode) and isinstance(
            first_item.event, ModelEvent
        )
        shared_input = list(first_item.event.input)

        for i, branch_start in enumerate(indices[:-1]):
            # Branch extends from this ModelEvent to just before the next re-roll
            next_reroll = indices[i + 1]
            branch_ranges.append((branch_start, next_reroll, shared_input))

    # Sort by start index descending so we can remove from the end first
    branch_ranges.sort(key=lambda x: x[0], reverse=True)

    for start, end, shared_input in branch_ranges:
        branch_content = list(agent.content[start:end])
        forked_at = _find_forked_at(agent.content, shared_input)
        agent.branches.append(Branch(forked_at=forked_at, content=branch_content))
        del agent.content[start:end]

    # Reverse branches so they're in original order
    agent.branches.reverse()


def _classify_branches(agent: AgentNode, has_explicit_branches: bool) -> None:
    """Recursively detect branches in the agent tree.

    If not in explicit mode, calls _detect_auto_branches on each agent.
    Always recurses into child agents in both content and branches.

    Args:
        agent: The agent node to process.
        has_explicit_branches: Whether explicit branch spans exist globally.
    """
    if not has_explicit_branches:
        _detect_auto_branches(agent)

    # Recurse into child agents in content
    for item in agent.content:
        if isinstance(item, AgentNode):
            _classify_branches(item, has_explicit_branches)

    # Recurse into agents within branches
    for branch in agent.branches:
        for item in branch.content:
            if isinstance(item, AgentNode):
                _classify_branches(item, has_explicit_branches)


# =============================================================================
# Utility Agent Classification
# =============================================================================


def _get_system_prompt(agent: AgentNode) -> str | None:
    """Extract system prompt from the first ModelEvent in agent's direct content.

    Args:
        agent: The agent node to extract the system prompt from.

    Returns:
        The system prompt text, or None if no system message found.
    """
    for item in agent.content:
        if isinstance(item, EventNode) and isinstance(item.event, ModelEvent):
            for msg in item.event.input:
                if isinstance(msg, ChatMessageSystem):
                    if isinstance(msg.content, str):
                        return msg.content
                    # Content is list of Content objects
                    parts = [c.text for c in msg.content if hasattr(c, "text")]
                    return "\n".join(parts) if parts else None
            return None  # ModelEvent found but no system message
    return None  # No ModelEvent found


def _is_single_turn(agent: AgentNode) -> bool:
    """Check if agent has a single turn or single tool-calling turn.

    A single turn is 1 ModelEvent with no ToolEvents.
    A single tool-calling turn is 2 ModelEvents with a ToolEvent between them.

    Args:
        agent: The agent node to check.

    Returns:
        True if the agent matches the single-turn pattern.
    """
    # Collect direct events (not child agents) with their types
    direct_events: list[str] = []
    for item in agent.content:
        if isinstance(item, EventNode):
            if isinstance(item.event, ModelEvent):
                direct_events.append("model")
            elif isinstance(item.event, ToolEvent):
                direct_events.append("tool")

    model_count = direct_events.count("model")
    tool_count = direct_events.count("tool")

    # Single turn: exactly 1 model event
    if model_count == 1:
        return True

    # Single tool-calling turn: 2 model events with tool event(s) between
    if model_count == 2 and tool_count >= 1:
        # Verify a tool event appears between the two model events
        first_model = direct_events.index("model")
        second_model = len(direct_events) - 1 - direct_events[::-1].index("model")
        between = direct_events[first_model + 1 : second_model]
        return "tool" in between

    return False


def _classify_utility_agents(
    node: AgentNode, parent_system_prompt: str | None = None
) -> None:
    """Classify utility agents in the tree via post-processing.

    An agent is utility if it has a single turn (or single tool-calling turn)
    and a different system prompt than its parent.

    Args:
        node: The agent node to classify (and recurse into).
        parent_system_prompt: The system prompt of the parent agent.
    """
    agent_system_prompt = _get_system_prompt(node)

    # Classify this node (root agent is never utility)
    if parent_system_prompt is not None and agent_system_prompt is not None:
        if agent_system_prompt != parent_system_prompt and _is_single_turn(node):
            node.utility = True

    # Recurse into child agents
    effective_prompt = agent_system_prompt or parent_system_prompt
    for item in node.content:
        if isinstance(item, AgentNode):
            _classify_utility_agents(item, effective_prompt)
