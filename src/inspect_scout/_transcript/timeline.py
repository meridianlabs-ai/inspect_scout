"""Timeline: re-exports from inspect_ai.event and scout-specific utilities.

Types and builder functions live in ``inspect_ai.event``.  This module
re-exports them for backwards compatibility and provides scout-specific
functionality: ``TimelineMessages``, ``timeline_messages``,
``filter_timeline_events``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from inspect_scout._scanner.extract import MessagesAsStr

from inspect_ai.event import (
    ModelEvent,
    Timeline,
    TimelineBranch,
    TimelineEvent,
    TimelineSpan,
    timeline_build,
    timeline_dump,
    timeline_filter,
    timeline_load,
)
from inspect_ai.event._timeline import (
    Outline,
    OutlineNode,
    TimelineContentItem,
    _timeline_content_discriminator,
)
from inspect_ai.model import ChatMessage, Model

# Re-export everything that moved to inspect_ai.event
__all__ = [
    # Types
    "Outline",
    "OutlineNode",
    "Timeline",
    "TimelineBranch",
    "TimelineContentItem",
    "TimelineEvent",
    "TimelineSpan",
    # Functions
    "timeline_build",
    "timeline_dump",
    "timeline_filter",
    "timeline_load",
    # Scout-specific
    "TimelineMessages",
    "filter_timeline_events",
    "timeline_messages",
    # Private helpers (used by other scout modules)
    "_timeline_content_discriminator",
]


# =============================================================================
# Timeline Event Filtering (scout-specific)
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
        description=span.description,
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
    """A segment of messages from a specific timeline span.

    Structurally compatible with ``MessagesSegment`` (shares
    ``messages``, ``messages_str``, ``segment`` fields) with additional
    span context. Can be used anywhere a ``MessagesSegment``
    is expected via duck typing.

    Attributes:
        messages: The original ChatMessage objects in this segment.
        messages_str: Pre-rendered string from messages_as_str.
        segment: 0-based segment index, globally unique across yields.
        span: The TimelineSpan this segment was extracted from.
    """

    messages: list[ChatMessage]
    messages_str: str
    segment: int
    span: TimelineSpan


async def timeline_messages(
    timeline: Timeline | TimelineSpan,
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
) -> AsyncIterator[TimelineMessages]:
    """Yield pre-rendered message segments from timeline spans.

    Walks the span tree, passes each non-utility span with direct
    ``ModelEvent`` content to ``segment_messages()`` for message
    extraction and context window segmentation. Each yielded item
    includes the span context alongside the pre-rendered text.

    To filter which spans are processed, use ``filter_timeline()``
    before calling this function.

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
        depth: Maximum depth of the span tree to process. ``1`` processes
            only the root span, ``2`` includes immediate children, etc.
            None (default) recurses without limit.

    Yields:
        TimelineMessages for each segment. Empty spans are skipped.
    """
    from inspect_scout._transcript.messages import segment_messages

    root = timeline.root if isinstance(timeline, Timeline) else timeline

    counter = 0
    for span in _walk_spans(root, depth=depth):
        async for seg in segment_messages(
            span,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            compaction=compaction,
        ):
            yield TimelineMessages(
                messages=seg.messages,
                messages_str=seg.messages_str,
                segment=counter,
                span=span,
            )
            counter += 1


def _walk_spans(
    span: TimelineSpan,
    *,
    depth: int | None = None,
    _current_depth: int = 1,
) -> Iterator[TimelineSpan]:
    """Walk the span tree depth-first, yielding scannable spans.

    A span is yielded if it is not a utility span and has at least one
    direct ``ModelEvent`` in its content. Non-matching spans are still
    traversed so their children can be checked.

    Args:
        span: The root span to walk.
        depth: Maximum depth to recurse. 1 = root only, 2 = root +
            children, None = unlimited.
        _current_depth: Internal counter tracking current depth.

    Yields:
        Scannable TimelineSpan nodes in depth-first order.
    """
    if not span.utility and any(
        isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent)
        for item in span.content
    ):
        yield span

    if depth is not None and _current_depth >= depth:
        return

    for item in span.content:
        if isinstance(item, TimelineSpan):
            yield from _walk_spans(item, depth=depth, _current_depth=_current_depth + 1)
