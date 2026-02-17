"""Conversation tree reconstruction for Claude Code sessions.

Claude Code stores events in a flat JSONL format with parentUuid/uuid links.
This module reconstructs the hierarchical tree structure for proper
event ordering.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .models import BaseEvent


@dataclass
class EventNode:
    """A node in the conversation tree."""

    event: BaseEvent
    children: list["EventNode"] = field(default_factory=list)

    @property
    def uuid(self) -> str:
        """Get the event's UUID."""
        return self.event.uuid

    @property
    def parent_uuid(self) -> str | None:
        """Get the parent UUID, or None for root events."""
        return self.event.parentUuid

    @property
    def timestamp(self) -> datetime | None:
        """Get the event timestamp as datetime."""
        ts = self.event.timestamp
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                # Handle ISO format with timezone
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return self.event.type


def build_event_tree(events: list[BaseEvent]) -> list[EventNode]:
    """Build a tree structure from flat list of events.

    Args:
        events: Flat list of Claude Code events with parentUuid/uuid links

    Returns:
        List of root EventNode objects (events with null/missing parentUuid)
    """
    # Create nodes for all events with UUIDs
    nodes: dict[str, EventNode] = {}
    for event in events:
        uuid = event.uuid
        if uuid:
            nodes[uuid] = EventNode(event=event)

    # Build parent-child relationships
    roots: list[EventNode] = []
    for node in nodes.values():
        parent_uuid = node.parent_uuid
        if parent_uuid and parent_uuid in nodes:
            nodes[parent_uuid].children.append(node)
        else:
            roots.append(node)

    # Sort children by timestamp at each level
    def sort_children(node: EventNode) -> None:
        node.children.sort(key=lambda n: n.timestamp or datetime.min)
        for child in node.children:
            sort_children(child)

    for root in roots:
        sort_children(root)

    # Sort roots by timestamp
    roots.sort(key=lambda n: n.timestamp or datetime.min)

    return roots


def flatten_tree_chronological(roots: list[EventNode]) -> list[BaseEvent]:
    """Flatten tree to chronologically ordered list of events.

    Performs a depth-first traversal, emitting events in the order
    they would have executed.

    Args:
        roots: List of root EventNode objects

    Returns:
        Chronologically ordered list of events
    """
    result: list[BaseEvent] = []

    def visit(node: EventNode) -> None:
        result.append(node.event)
        for child in node.children:
            visit(child)

    for root in roots:
        visit(root)

    return result


def find_clear_indices(events: list[BaseEvent]) -> list[int]:
    """Find indices where /clear commands occur.

    Args:
        events: Chronologically ordered list of events

    Returns:
        List of indices where /clear commands appear
    """
    from .detection import is_clear_command

    return [i for i, event in enumerate(events) if is_clear_command(event)]


def split_on_clear(
    events: list[BaseEvent],
) -> list[list[BaseEvent]]:
    """Split events into segments at /clear boundaries.

    Each /clear command starts a new conversation segment.
    The /clear event itself is not included in any segment.

    Args:
        events: Chronologically ordered list of events

    Returns:
        List of event lists, one per conversation segment
    """
    clear_indices = find_clear_indices(events)

    if not clear_indices:
        # No splits - return all events as single segment
        return [events]

    segments: list[list[BaseEvent]] = []
    start_idx = 0

    for clear_idx in clear_indices:
        # Add segment before this /clear
        if start_idx < clear_idx:
            segments.append(events[start_idx:clear_idx])

        # Next segment starts after the /clear
        start_idx = clear_idx + 1

    # Add final segment after last /clear
    if start_idx < len(events):
        segments.append(events[start_idx:])

    # Filter out empty segments
    return [seg for seg in segments if seg]


def get_conversation_events(events: list[BaseEvent]) -> list[BaseEvent]:
    """Filter events to only conversation-relevant ones.

    Removes progress events, file history, and other internal events,
    keeping only user messages, assistant responses, and system events
    that affect the conversation (like compaction).

    Args:
        events: List of events to filter

    Returns:
        Filtered list containing only conversation events
    """
    from .detection import should_skip_event

    return [e for e in events if not should_skip_event(e)]


def find_root_event(events: list[BaseEvent]) -> BaseEvent | None:
    """Find the root event in a list of events.

    The root event is typically the first user message with parentUuid=None.

    Args:
        events: List of events

    Returns:
        The root event, or None if not found
    """
    for event in events:
        if event.parentUuid is None:
            return event
    return events[0] if events else None


def group_by_parent(
    events: list[BaseEvent],
) -> dict[str | None, list[BaseEvent]]:
    """Group events by their parent UUID.

    Args:
        events: List of events

    Returns:
        Dict mapping parent UUID to list of child events
    """
    groups: dict[str | None, list[BaseEvent]] = {}

    for event in events:
        parent = event.parentUuid
        if parent not in groups:
            groups[parent] = []
        groups[parent].append(event)

    return groups
