"""Transcript nodes: hierarchical structure for visualization and scanning.

Transforms flat event streams into a semantic tree with agent-centric interpretation.

Uses inspect_ai's event_tree() to parse span structure.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Callable, Literal

if TYPE_CHECKING:
    from inspect_ai.model import Model

    from inspect_scout._scanner.extract import MessagesAsStr

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
from pydantic import (
    BaseModel,
    Discriminator,
    Field,
    Tag,
    ValidationInfo,
    field_serializer,
    model_validator,
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


class TimelineEvent(BaseModel):
    """Wraps a single Event."""

    type: Literal["event"] = "event"
    event: Event

    @field_serializer("event")
    def _serialize_event(self, event: Event, _info: Any) -> str:
        """Serialize event as its UUID for storage."""
        return event.uuid or ""

    @model_validator(mode="before")
    @classmethod
    def _resolve_event(cls, data: Any, info: ValidationInfo) -> Any:
        """Resolve event UUID string to Event object via validation context."""
        if isinstance(data, dict):
            event_val = data.get("event")
            if isinstance(event_val, str):
                # Resolve UUID → Event via context
                ctx = info.context or {} if info else {}
                events_by_uuid = ctx.get("events_by_uuid", {})
                resolved = events_by_uuid.get(event_val)
                if resolved is not None:
                    data = {**data, "event": resolved}
            return data
        return data

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


def _timeline_content_discriminator(v: Any) -> str:
    """Discriminator function for TimelineSpan.content and TimelineBranch.content."""
    if isinstance(v, dict):
        return str(v.get("type", "event"))
    return str(getattr(v, "type", "event"))


# Discriminated union type for content items
TimelineContentItem = Annotated[
    Annotated[TimelineEvent, Tag("event")] | Annotated["TimelineSpan", Tag("span")],
    Discriminator(_timeline_content_discriminator),
]


class TimelineSpan(BaseModel):
    """A span of execution — agent, scorer, tool, or root."""

    type: Literal["span"] = "span"
    id: str
    name: str
    span_type: str | None
    content: list[TimelineContentItem] = Field(default_factory=list)
    branches: list["TimelineBranch"] = Field(default_factory=list)
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


class TimelineBranch(BaseModel):
    """A discarded alternative path from a branch point."""

    type: Literal["branch"] = "branch"
    forked_at: str
    content: list[TimelineContentItem] = Field(default_factory=list)

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


class OutlineNode(BaseModel):
    """A node in an agent's outline, referencing an event by UUID."""

    event: str
    children: list["OutlineNode"] = Field(default_factory=list)


class Outline(BaseModel):
    """Hierarchical outline of events for an agent."""

    nodes: list[OutlineNode] = Field(default_factory=list)


class Timeline(BaseModel):
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
            if not has_explicit_branches:
                _detect_auto_branches(agent_node)
            _classify_auto_spans(agent_node)
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
        if not has_explicit_branches:
            _detect_auto_branches(root)
        _classify_auto_spans(root)
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

    CompactionEvents act as hard boundaries: fingerprint grouping is done
    independently within each region separated by compaction events, so
    re-rolls are never matched across a compaction boundary.

    Mutates agent in-place.

    Args:
        agent: The span node to process.
    """
    # Split content into regions at compaction boundaries
    regions: list[tuple[int, int]] = []
    region_start = 0
    for i, item in enumerate(agent.content):
        if isinstance(item, TimelineEvent) and item.event.event == "compaction":
            regions.append((region_start, i))
            region_start = i + 1
    regions.append((region_start, len(agent.content)))

    # Collect branch ranges across all regions
    branch_ranges: list[tuple[int, int, list[ChatMessage]]] = []

    for r_start, r_end in regions:
        # Find ModelEvent indices and their fingerprints within this region
        model_indices: list[tuple[int, str]] = []
        for i in range(r_start, r_end):
            item = agent.content[i]
            if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
                input_msgs = list(item.event.input)
                if not input_msgs:
                    continue
                fp = _input_fingerprint(input_msgs)
                model_indices.append((i, fp))

        # Group by fingerprint within this region
        fingerprint_groups: dict[str, list[int]] = {}
        for idx, fp in model_indices:
            fingerprint_groups.setdefault(fp, []).append(idx)

        # Only process groups with duplicates
        for _fp, indices in fingerprint_groups.items():
            if len(indices) <= 1:
                continue

            first_idx = indices[0]
            first_item = agent.content[first_idx]
            assert isinstance(first_item, TimelineEvent) and isinstance(
                first_item.event, ModelEvent
            )
            shared_input = list(first_item.event.input)

            for i, branch_start in enumerate(indices[:-1]):
                next_reroll = indices[i + 1]
                branch_ranges.append((branch_start, next_reroll, shared_input))

    if not branch_ranges:
        return

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
# Auto-Span Detection (Conversation Threading)
# =============================================================================


def _get_last_assistant_message(
    input_msgs: list[ChatMessage],
) -> ChatMessageAssistant | None:
    """Extract the last assistant message from a ModelEvent's input.

    Args:
        input_msgs: The input message list.

    Returns:
        The last assistant message, or None if not found.
    """
    for msg in reversed(input_msgs):
        if isinstance(msg, ChatMessageAssistant):
            return msg
    return None


def _get_output_fingerprint(event: ModelEvent) -> str | None:
    """Fingerprint a ModelEvent's output message.

    Python output: event.output.choices[0].message (a ChatMessage).

    Args:
        event: The ModelEvent to fingerprint.

    Returns:
        The fingerprint string, or None if no output message.
    """
    output = getattr(event, "output", None)
    if output is None:
        return None
    choices = getattr(output, "choices", None)
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    if message is None:
        return None
    return _message_fingerprint(message)


def _system_prompt_fingerprint(input_msgs: list[ChatMessage]) -> str:
    """Fingerprint just the system prompt from a ModelEvent's input messages.

    Args:
        input_msgs: The input message list.

    Returns:
        Fingerprint of the system message, or empty string if none.
    """
    for msg in input_msgs:
        if isinstance(msg, ChatMessageSystem):
            return _message_fingerprint(msg)
    return ""


def _detect_auto_spans_for_span(span: TimelineSpan) -> None:
    """Detect conversation threads in a single flat span and create child spans.

    Uses conversation threading: tracks which ModelEvent inputs continue a prior
    ModelEvent's output via fingerprinting. Mutates span in-place.

    Args:
        span: The span node to process.
    """
    # Guard: only flat content (no child TimelineSpans)
    for item in span.content:
        if isinstance(item, TimelineSpan):
            return

    # Guard: need at least 2 ModelEvents with output fingerprints
    # (without output messages, threading detection cannot work)
    model_with_output_count = sum(
        1
        for item in span.content
        if isinstance(item, TimelineEvent)
        and isinstance(item.event, ModelEvent)
        and _get_output_fingerprint(item.event) is not None
    )
    if model_with_output_count < 2:
        return

    # Thread detection
    threads: list[
        dict[str, Any]
    ] = []  # Each: {"items": [...], "system_prompt_fp": str}
    output_fp_to_thread: dict[str, int] = {}  # output fingerprint → thread index
    preamble: list[TimelineEvent | TimelineSpan] = []

    for item in span.content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            input_msgs = list(item.event.input)
            if input_msgs:
                last_assistant = _get_last_assistant_message(input_msgs)
                if last_assistant is not None:
                    fp = _message_fingerprint(last_assistant)
                    thread_idx = output_fp_to_thread.get(fp)
                    if thread_idx is not None:
                        # Match — append to existing thread
                        threads[thread_idx]["items"].append(item)
                        # Update output tracking
                        del output_fp_to_thread[fp]
                        new_output_fp = _get_output_fingerprint(item.event)
                        if new_output_fp:
                            output_fp_to_thread[new_output_fp] = thread_idx
                        continue

            # New thread
            sys_fp = _system_prompt_fingerprint(input_msgs)
            threads.append({"items": [item], "system_prompt_fp": sys_fp})
            output_fp = _get_output_fingerprint(item.event)
            if output_fp:
                output_fp_to_thread[output_fp] = len(threads) - 1
        elif isinstance(item, TimelineEvent) and item.event.event == "compaction":
            # Hard boundary: reset fingerprint tracking
            output_fp_to_thread.clear()
            if threads:
                threads[-1]["items"].append(item)
            else:
                preamble.append(item)
        else:
            # Non-model event
            if threads:
                threads[-1]["items"].append(item)
            else:
                preamble.append(item)

    # Only create structure if multiple threads found
    if len(threads) <= 1:
        return

    # Name threads by prompt group (ordered by first occurrence)
    prompt_group_order: list[str] = []
    prompt_group_threads: dict[str, list[int]] = {}
    for i, thread in enumerate(threads):
        fp = thread["system_prompt_fp"]
        if fp in prompt_group_threads:
            prompt_group_threads[fp].append(i)
        else:
            prompt_group_order.append(fp)
            prompt_group_threads[fp] = [i]

    name_map: dict[int, str] = {}
    group_num = 1
    for fp in prompt_group_order:
        thread_indices = prompt_group_threads[fp]
        base_name = "Agent" if len(prompt_group_order) == 1 else f"Agent {group_num}"
        for idx in thread_indices:
            name_map[idx] = base_name
        group_num += 1

    # Build child spans
    new_content: list[TimelineEvent | TimelineSpan] = list(preamble)
    for i, thread in enumerate(threads):
        child_span = TimelineSpan(
            id=f"auto-span-{i}",
            name=name_map[i],
            span_type=None,
            content=thread["items"],
        )
        new_content.append(child_span)

    span.content = new_content


def _classify_auto_spans(span: TimelineSpan) -> None:
    """Recursively detect auto-spans via conversation threading.

    Skips spans that already have child spans, recurses into children
    (including newly created ones).

    Args:
        span: The span node to process.
    """
    # Try detection on this span (only works if flat)
    _detect_auto_spans_for_span(span)

    # Recurse into any child spans (including newly created ones)
    for item in span.content:
        if isinstance(item, TimelineSpan):
            _classify_auto_spans(item)


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


# =============================================================================
# Timeline Event Filtering
# =============================================================================


def filter_timeline_events(
    timeline: Timeline,
    event_types: list[str] | Literal["all"],
) -> Timeline:
    """Return a copy of the timeline with only matching event types.

    Walks the tree and removes TimelineEvent nodes whose event.event
    is not in event_types. Keeps TimelineSpan structure; prunes empty
    spans/branches after filtering.

    Args:
        timeline: The timeline to filter.
        event_types: Event type strings to keep, or "all" to keep everything.

    Returns:
        A new Timeline with only matching events.
    """
    if event_types == "all":
        return timeline
    allowed = set(event_types)
    new_root = _filter_span(timeline.root, allowed)
    return Timeline(name=timeline.name, description=timeline.description, root=new_root)


def _filter_span(span: TimelineSpan, allowed: set[str]) -> TimelineSpan:
    """Filter a span's content and branches, keeping only allowed event types."""
    filtered_content = _filter_content_list(span.content, allowed)
    filtered_branches = [
        TimelineBranch(
            forked_at=b.forked_at,
            content=_filter_content_list(b.content, allowed),
        )
        for b in span.branches
    ]
    # Remove branches that ended up empty
    filtered_branches = [b for b in filtered_branches if b.content]
    return TimelineSpan(
        id=span.id,
        name=span.name,
        span_type=span.span_type,
        content=filtered_content,
        branches=filtered_branches,
        task_description=span.task_description,
        utility=span.utility,
        outline=span.outline,
    )


def _filter_content_list(
    items: list[TimelineContentItem],
    allowed: set[str],
) -> list[TimelineContentItem]:
    """Filter content items, keeping events with allowed types and non-empty spans."""
    result: list[TimelineContentItem] = []
    for item in items:
        if isinstance(item, TimelineEvent):
            if item.event.event in allowed:
                result.append(item)
        else:  # TimelineSpan
            filtered = _filter_span(item, allowed)
            if filtered.content or filtered.branches:
                result.append(filtered)
    return result


# =============================================================================
# Timeline Message Extraction
# =============================================================================


@dataclass(frozen=True)
class TimelineMessages:
    """A chunk of messages from a specific timeline span.

    Extends MessagesChunk with span context. Can be used anywhere
    a MessagesChunk is expected via duck typing.

    Attributes:
        messages: The original ChatMessage objects in this chunk.
        text: Pre-rendered string from messages_as_str.
        segment: 0-based segment index, auto-increments across yields.
        span: The TimelineSpan this chunk was extracted from.
    """

    messages: list[ChatMessage]
    text: str
    segment: int
    span: TimelineSpan


async def timeline_messages(
    timeline: Timeline | TimelineSpan,
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
    compaction: Literal["all", "last"] = "all",
    include: Callable[[TimelineSpan], bool] | str | None = None,
) -> AsyncIterator[TimelineMessages]:
    """Yield pre-rendered message segments from timeline spans.

    Walks the span tree, passes each matching span to
    ``chunked_messages()`` for message extraction and context window
    chunking. Each yielded item includes the span context alongside
    the pre-rendered text.

    Args:
        timeline: The timeline (or a specific span subtree) to extract
            messages from. If a Timeline, starts from timeline.root.
        messages_as_str: Rendering function from message_numbering() that
            formats messages with globally unique IDs.
        model: The model used for scanning. Provides count_tokens() for
            measuring rendered text.
        context_window: Override for the model's context window size
            (in tokens). When None, looked up via get_model_info().
            An 80% discount factor is applied to leave room for system
            prompts and scanning overhead.
        compaction: How to handle compaction boundaries when extracting
            messages from span events.
        include: Filter for which spans to process.
            - None: all non-utility spans with direct ModelEvents (default)
            - str: only spans whose name matches (case-insensitive)
            - callable: predicate on TimelineSpan

    Yields:
        TimelineMessages for each segment. Empty spans are skipped.
    """
    from inspect_scout._transcript.messages import chunked_messages

    root = timeline.root if isinstance(timeline, Timeline) else timeline

    for span in _walk_spans(root, include):
        async for chunk in chunked_messages(
            span,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            compaction=compaction,
        ):
            yield TimelineMessages(
                messages=chunk.messages,
                text=chunk.text,
                segment=chunk.segment,
                span=span,
            )


def _walk_spans(
    span: TimelineSpan,
    include: Callable[[TimelineSpan], bool] | str | None,
) -> Iterator[TimelineSpan]:
    """Walk the span tree depth-first, yielding matching spans.

    Non-matching spans are still traversed — the filter controls which
    spans yield messages, not which subtrees are visited. Only content
    children are traversed (not branches).

    Args:
        span: The root span to walk.
        include: Filter for which spans to yield.

    Yields:
        Matching TimelineSpan nodes in depth-first order.
    """
    if _span_matches(span, include):
        yield span

    for item in span.content:
        if isinstance(item, TimelineSpan):
            yield from _walk_spans(item, include)


def _span_matches(
    span: TimelineSpan,
    include: Callable[[TimelineSpan], bool] | str | None,
) -> bool:
    """Check if a span matches the include filter.

    Args:
        span: The span to check.
        include: The filter to apply.

    Returns:
        True if the span matches.
    """
    if include is None:
        # Default: non-utility spans with at least one direct ModelEvent
        if span.utility:
            return False
        return any(
            isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent)
            for item in span.content
        )
    elif isinstance(include, str):
        return span.name.lower() == include.lower()
    else:
        return include(span)
