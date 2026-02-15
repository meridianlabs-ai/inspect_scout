"""Transcript nodes: hierarchical structure for visualization and scanning.

Transforms flat event streams into a semantic tree with agent-centric interpretation.

Uses inspect_ai's event_tree() to parse span structure.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from inspect_ai.event import (
    Event,
    EventTreeSpan,
    ModelEvent,
    SpanBeginEvent,
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
TreeItem = EventTreeSpan | Event


# =============================================================================
# Node Types
# =============================================================================


def _min_start_time(
    nodes: Sequence["TimelineEvent | TimelineSpan | TimelineBranch"],
) -> datetime:
    """Return the earliest start time among nodes.

    Requires at least one node (all nodes have non-null start_time).

    Args:
        nodes: Non-empty sequence of nodes to check.

    Returns:
        The minimum start_time.
    """
    return min(node.start_time for node in nodes)


def _max_end_time(
    nodes: Sequence["TimelineEvent | TimelineSpan | TimelineBranch"],
) -> datetime:
    """Return the latest end time among nodes.

    Requires at least one node (all nodes have non-null end_time).

    Args:
        nodes: Non-empty sequence of nodes to check.

    Returns:
        The maximum end_time.
    """
    return max(node.end_time for node in nodes)


def _sum_tokens(
    nodes: Sequence["TimelineEvent | TimelineSpan | TimelineBranch"],
) -> int:
    """Sum total tokens across all nodes.

    Args:
        nodes: Sequence of nodes to sum.

    Returns:
        Total token count from all nodes.
    """
    return sum(node.total_tokens for node in nodes)


@dataclass
class TimelineEvent:
    """Wraps a single Event."""

    event: Event

    @property
    def start_time(self) -> datetime:
        """Event timestamp (required field on all events)."""
        ts = getattr(self.event, "timestamp", None)
        if not isinstance(ts, datetime):
            raise ValueError("Event missing required timestamp field")
        return ts

    @property
    def end_time(self) -> datetime:
        """Event completion time if available, else timestamp."""
        completed = getattr(self.event, "completed", None)
        if isinstance(completed, datetime):
            return completed
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
class TimelineSpan:
    """A span of execution — agent, scorer, tool, or root."""

    id: str
    name: str
    span_type: str | None
    content: list["TimelineEvent | TimelineSpan"] = field(default_factory=list)
    branches: list["TimelineBranch"] = field(default_factory=list)
    task_description: str | None = None
    utility: bool = False
    outline: "Outline | None" = None

    @property
    def start_time(self) -> datetime:
        """Earliest start time among content."""
        return _min_start_time(self.content)

    @property
    def end_time(self) -> datetime:
        """Latest end time among content."""
        return _max_end_time(self.content)

    @property
    def total_tokens(self) -> int:
        """Sum of tokens from all content."""
        return _sum_tokens(self.content)


@dataclass
class TimelineBranch:
    """A discarded alternative path from a branch point."""

    forked_at: str
    content: list[TimelineEvent | TimelineSpan] = field(default_factory=list)

    @property
    def start_time(self) -> datetime:
        """Earliest start time among content."""
        return _min_start_time(self.content)

    @property
    def end_time(self) -> datetime:
        """Latest end time among content."""
        return _max_end_time(self.content)

    @property
    def total_tokens(self) -> int:
        """Sum of tokens from all content."""
        return _sum_tokens(self.content)


@dataclass
class OutlineNode:
    """A node in an agent's outline, referencing an event by UUID."""

    event: str
    children: list["OutlineNode"] = field(default_factory=list)


@dataclass
class Outline:
    """Hierarchical outline of events for an agent."""

    nodes: list[OutlineNode] = field(default_factory=list)


@dataclass
class Timeline:
    """A named timeline view over a transcript.

    Multiple timelines allow different interpretations of the same event
    stream — e.g. a default agent-centric view alongside an alternative
    grouping or filtered view.
    """

    name: str
    description: str
    root: TimelineSpan


# =============================================================================
# Builder
# =============================================================================


def build_timeline(events: list[Event]) -> Timeline:
    """Build a Timeline from a flat event list.

    Uses inspect_ai's event_tree() to parse span structure, then:
    1. Look for top-level spans: "init", "solvers", "scorers"
    2. If present, use them to partition events into sections
    3. If not present, treat the entire event stream as the agent

    Agent detection within the solvers section (or entire stream):
    - Explicit agent spans (type='agent') -> span_type="agent"
    - Tool spans/calls with model events -> span_type=None (tool-spawned)
    """
    if not events:
        return Timeline(
            name="Default",
            description="",
            root=TimelineSpan(id="root", name="root", span_type=None),
        )

    # Detect explicit branches globally
    has_explicit_branches = any(
        isinstance(e, SpanBeginEvent) and e.type == "branch" for e in events
    )

    # Use event_tree to get hierarchical structure
    tree = event_tree(events)

    # Find top-level spans by name
    top_spans: dict[str, EventTreeSpan] = {}
    for item in tree:
        if isinstance(item, EventTreeSpan) and item.name in (
            "init",
            "solvers",
            "scorers",
        ):
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

        # Build init events (flattened into root content)
        init_events: list[TimelineEvent] = []
        if init_span:
            flat_events = event_sequence(init_span.children)
            init_events = [TimelineEvent(event=e) for e in flat_events]

        # Build agent node from solvers
        agent_node = (
            _build_agent_from_solvers_span(solvers_span, has_explicit_branches)
            if solvers_span
            else None
        )

        # Build scoring span
        scoring_span: TimelineSpan | None = None
        if scorers_span:
            flat_events = event_sequence(scorers_span.children)
            scoring_content: list[TimelineEvent | TimelineSpan] = [
                TimelineEvent(event=e) for e in flat_events
            ]
            if scoring_content:
                scoring_span = TimelineSpan(
                    id=scorers_span.id,
                    name="Scoring",
                    span_type="scorer",
                    content=scoring_content,
                )

        if agent_node is not None:
            _classify_utility_agents(agent_node)
            _classify_branches(agent_node, has_explicit_branches)

            # Fold init events into the beginning of agent content
            if init_events:
                init_content: list[TimelineEvent | TimelineSpan] = list(init_events)
                agent_node.content = init_content + agent_node.content

            # Append scoring as a child span
            if scoring_span:
                agent_node.content.append(scoring_span)

            root = agent_node
        else:
            # No solvers span — build root from init + scoring
            root_content: list[TimelineEvent | TimelineSpan] = list(init_events)
            if scoring_span:
                root_content.append(scoring_span)
            root = TimelineSpan(
                id="root",
                name="root",
                span_type=None,
                content=root_content,
            )
    else:
        # No phase spans - treat entire tree as agent
        root = _build_agent_from_tree(tree, has_explicit_branches)
        _classify_utility_agents(root)
        _classify_branches(root, has_explicit_branches)

    return Timeline(name="Default", description="", root=root)


def _build_agent_from_solvers_span(
    solvers_span: EventTreeSpan, has_explicit_branches: bool
) -> TimelineSpan | None:
    """Build agent hierarchy from the solvers span.

    Looks for explicit agent spans (type='agent') within the solvers span.
    If found, builds the agent tree from those spans. If not found, uses
    the solvers span itself as the agent container.

    Args:
        solvers_span: The top-level solvers EventTreeSpan.
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        A TimelineSpan representing the agent hierarchy, or None if empty.
    """
    if not solvers_span.children:
        return None

    # Look for agent spans within solvers
    agent_spans: list[EventTreeSpan] = []
    other_items: list[TreeItem] = []

    for child in solvers_span.children:
        if isinstance(child, EventTreeSpan) and child.type == "agent":
            agent_spans.append(child)
        else:
            other_items.append(child)

    if agent_spans:
        # Build from explicit agent spans
        if len(agent_spans) == 1:
            return _build_span_from_agent_span(
                agent_spans[0], has_explicit_branches, other_items
            )
        else:
            # Multiple agent spans - create root containing all
            children: list[TimelineEvent | TimelineSpan] = [
                _build_span_from_agent_span(span, has_explicit_branches, [])
                for span in agent_spans
            ]
            # Add any orphan events
            for item in other_items:
                children.insert(0, _tree_item_to_node(item, has_explicit_branches))
            return TimelineSpan(
                id="root",
                name="root",
                span_type="agent",
                content=children,
            )
    else:
        # No explicit agent spans - use solvers span itself as the agent container
        content, branches = _process_children(
            solvers_span.children, has_explicit_branches
        )

        return TimelineSpan(
            id=solvers_span.id,
            name=solvers_span.name,
            span_type="agent",
            content=content,
            branches=branches,
        )


def _build_span_from_agent_span(
    span: EventTreeSpan,
    has_explicit_branches: bool,
    extra_items: list[TreeItem] | None = None,
) -> TimelineSpan:
    """Build a TimelineSpan from a EventTreeSpan with type='agent'.

    Args:
        span: The agent EventTreeSpan to convert.
        has_explicit_branches: Whether explicit branch spans exist globally.
        extra_items: Additional tree items (orphan events) to include
            at the start of the span's content.

    Returns:
        A TimelineSpan with the span's children as content.
    """
    content: list[TimelineEvent | TimelineSpan] = []

    # Add any extra items first (orphan events)
    if extra_items:
        for item in extra_items:
            content.append(_tree_item_to_node(item, has_explicit_branches))

    # Process span children with branch awareness
    child_content, branches = _process_children(span.children, has_explicit_branches)
    content.extend(child_content)

    return TimelineSpan(
        id=span.id,
        name=span.name,
        span_type="agent",
        content=content,
        branches=branches,
    )


def _tree_item_to_node(
    item: TreeItem, has_explicit_branches: bool
) -> TimelineEvent | TimelineSpan:
    """Convert a tree item (EventTreeSpan or Event) to a TimelineEvent or TimelineSpan.

    Dispatches to the appropriate builder based on item type:
    - EventTreeSpan with type='agent' -> _build_span_from_agent_span
    - Other EventTreeSpan -> _build_span_from_generic_span
    - Event -> _event_to_node

    Args:
        item: A tree item from event_tree() (EventTreeSpan or Event).
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        A TimelineEvent or TimelineSpan representing the item.
    """
    if isinstance(item, EventTreeSpan):
        if item.type == "agent":
            return _build_span_from_agent_span(item, has_explicit_branches)
        else:
            return _build_span_from_generic_span(item, has_explicit_branches)
    else:
        return _event_to_node(item)


def _event_to_node(event: Event) -> TimelineEvent | TimelineSpan:
    """Convert an Event to a TimelineEvent or TimelineSpan.

    Handles ToolEvents that spawn nested agents, recursively processing
    nested events to detect further agent spawning.
    """
    if isinstance(event, ToolEvent):
        agent_name = getattr(event, "agent", None)
        nested_events = getattr(event, "events", None)
        if agent_name and nested_events:
            # Recursively process nested events to handle nested tool agents
            nested_content: list[TimelineEvent | TimelineSpan] = [
                _event_to_node(e) for e in nested_events
            ]
            return TimelineSpan(
                id=f"tool-agent-{event.id}",
                name=agent_name,
                span_type=None,
                content=nested_content,
            )
    return TimelineEvent(event=event)


def _build_span_from_generic_span(
    span: EventTreeSpan, has_explicit_branches: bool
) -> TimelineSpan:
    """Build a TimelineSpan from a non-agent EventTreeSpan.

    If the span is a tool span (type="tool") containing model events,
    we treat it as a tool-spawned agent (span_type=None).
    """
    content, branches = _process_children(span.children, has_explicit_branches)

    # Determine the span_type based on span type and content
    span_type: str | None
    if span.type == "tool" and _contains_model_events(span):
        span_type = None
    else:
        span_type = span.type

    return TimelineSpan(
        id=span.id,
        name=span.name,
        span_type=span_type,
        content=content,
        branches=branches,
    )


def _contains_model_events(span: EventTreeSpan) -> bool:
    """Check if a span contains any ModelEvent (recursively).

    Args:
        span: The EventTreeSpan to search.

    Returns:
        True if any descendant is a ModelEvent, False otherwise.
    """
    for child in span.children:
        if isinstance(child, EventTreeSpan):
            if _contains_model_events(child):
                return True
        elif isinstance(child, ModelEvent):
            return True
    return False


def _build_agent_from_tree(
    tree: list[TreeItem], has_explicit_branches: bool
) -> TimelineSpan:
    """Build agent from a list of tree items when no explicit phase spans exist.

    Creates a synthetic "main" agent containing all tree items as content.

    Args:
        tree: List of tree items from event_tree().
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        A TimelineSpan with id="main" containing all items.
    """
    content, branches = _process_children(tree, has_explicit_branches)

    return TimelineSpan(
        id="main",
        name="main",
        span_type="agent",
        content=content,
        branches=branches,
    )


# =============================================================================
# TimelineBranch Processing
# =============================================================================


def _process_children(
    children: list[TreeItem], has_explicit_branches: bool
) -> tuple[list[TimelineEvent | TimelineSpan], list[TimelineBranch]]:
    """Process a span's children with branch awareness.

    When explicit branches are active, collects adjacent type="branch" EventTreeSpan
    runs and builds TimelineBranch objects from them. Otherwise, standard processing.

    Args:
        children: List of tree items to process.
        has_explicit_branches: Whether explicit branch spans exist globally.

    Returns:
        Tuple of (content nodes, branch list).
    """
    if not has_explicit_branches:
        # Standard processing - no branch detection at build time
        content: list[TimelineEvent | TimelineSpan] = []
        for item in children:
            content.append(_tree_item_to_node(item, has_explicit_branches))
        return content, []

    # Explicit branch mode: collect branch spans and build TimelineBranch objects
    content = []
    branches: list[TimelineBranch] = []
    branch_run: list[EventTreeSpan] = []

    def _flush_branch_run(
        branch_run: list[EventTreeSpan],
        parent_content: list[TimelineEvent | TimelineSpan],
    ) -> list[TimelineBranch]:
        """Convert accumulated branch spans into TimelineBranch objects."""
        result: list[TimelineBranch] = []
        for span in branch_run:
            branch_content: list[TimelineEvent | TimelineSpan] = []
            for child in span.children:
                branch_content.append(_tree_item_to_node(child, has_explicit_branches))
            branch_input = _get_branch_input(branch_content)
            forked_at = (
                _find_forked_at(parent_content, branch_input)
                if branch_input is not None
                else ""
            )
            result.append(TimelineBranch(forked_at=forked_at, content=branch_content))
        return result

    for item in children:
        if isinstance(item, EventTreeSpan) and item.type == "branch":
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
    agent_content: list[TimelineEvent | TimelineSpan],
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
                    isinstance(item, TimelineEvent)
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
                if isinstance(item, TimelineEvent) and isinstance(
                    item.event, ModelEvent
                ):
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
                if isinstance(item, TimelineEvent) and isinstance(
                    item.event, ModelEvent
                ):
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
    content: list[TimelineEvent | TimelineSpan],
) -> list[ChatMessage] | None:
    """Extract the input from the first ModelEvent in branch content.

    Args:
        content: The branch's content nodes.

    Returns:
        The input message list, or None if no ModelEvent found.
    """
    for item in content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            return list(item.event.input)
    return None


# =============================================================================
# TimelineBranch Auto-Detection
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


def _detect_auto_branches(agent: TimelineSpan) -> None:
    """Detect re-rolled ModelEvents with identical inputs and create branches.

    For each group of ModelEvents with the same input fingerprint, the last
    one stays in content and earlier ones (plus their trailing events up to
    the next re-roll) become branches.

    Mutates agent in-place.

    Args:
        agent: The span node to process.
    """
    # Find ModelEvent indices and their fingerprints (skip empty inputs)
    model_indices: list[tuple[int, str]] = []
    for i, item in enumerate(agent.content):
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
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
        assert isinstance(first_item, TimelineEvent) and isinstance(
            first_item.event, ModelEvent
        )
        shared_input = list(first_item.event.input)

        for i, branch_start in enumerate(indices[:-1]):
            # TimelineBranch extends from this ModelEvent to just before the next re-roll
            next_reroll = indices[i + 1]
            branch_ranges.append((branch_start, next_reroll, shared_input))

    # Sort by start index descending so we can remove from the end first
    branch_ranges.sort(key=lambda x: x[0], reverse=True)

    for start, end, shared_input in branch_ranges:
        branch_content = list(agent.content[start:end])
        forked_at = _find_forked_at(agent.content, shared_input)
        agent.branches.append(
            TimelineBranch(forked_at=forked_at, content=branch_content)
        )
        del agent.content[start:end]

    # Reverse branches so they're in original order
    agent.branches.reverse()


def _classify_branches(agent: TimelineSpan, has_explicit_branches: bool) -> None:
    """Recursively detect branches in the agent tree.

    If not in explicit mode, calls _detect_auto_branches on each agent.
    Always recurses into child spans in both content and branches.

    Args:
        agent: The span node to process.
        has_explicit_branches: Whether explicit branch spans exist globally.
    """
    if not has_explicit_branches:
        _detect_auto_branches(agent)

    # Recurse into child spans in content
    for item in agent.content:
        if isinstance(item, TimelineSpan):
            _classify_branches(item, has_explicit_branches)

    # Recurse into spans within branches
    for branch in agent.branches:
        for item in branch.content:
            if isinstance(item, TimelineSpan):
                _classify_branches(item, has_explicit_branches)


# =============================================================================
# Utility Agent Classification
# =============================================================================


def _get_system_prompt(agent: TimelineSpan) -> str | None:
    """Extract system prompt from the first ModelEvent in agent's direct content.

    Args:
        agent: The span node to extract the system prompt from.

    Returns:
        The system prompt text, or None if no system message found.
    """
    for item in agent.content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            for msg in item.event.input:
                if isinstance(msg, ChatMessageSystem):
                    if isinstance(msg.content, str):
                        return msg.content
                    # Content is list of Content objects
                    parts = [c.text for c in msg.content if hasattr(c, "text")]
                    return "\n".join(parts) if parts else None
            return None  # ModelEvent found but no system message
    return None  # No ModelEvent found


def _is_single_turn(agent: TimelineSpan) -> bool:
    """Check if agent has a single turn or single tool-calling turn.

    A single turn is 1 ModelEvent with no ToolEvents.
    A single tool-calling turn is 2 ModelEvents with a ToolEvent between them.

    Args:
        agent: The span node to check.

    Returns:
        True if the agent matches the single-turn pattern.
    """
    # Collect direct events (not child spans) with their types
    direct_events: list[str] = []
    for item in agent.content:
        if isinstance(item, TimelineEvent):
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
    node: TimelineSpan, parent_system_prompt: str | None = None
) -> None:
    """Classify utility agents in the tree via post-processing.

    An agent is utility if it has a single turn (or single tool-calling turn)
    and a different system prompt than its parent.

    Args:
        node: The span node to classify (and recurse into).
        parent_system_prompt: The system prompt of the parent agent.
    """
    agent_system_prompt = _get_system_prompt(node)

    # Classify this node (root agent is never utility)
    if parent_system_prompt is not None and agent_system_prompt is not None:
        if agent_system_prompt != parent_system_prompt and _is_single_turn(node):
            node.utility = True

    # Recurse into child spans
    effective_prompt = agent_system_prompt or parent_system_prompt
    for item in node.content:
        if isinstance(item, TimelineSpan):
            _classify_utility_agents(item, effective_prompt)
