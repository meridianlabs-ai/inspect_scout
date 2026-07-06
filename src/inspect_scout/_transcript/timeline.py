"""Timeline: re-exports from inspect_ai.event and scout-specific utilities.

Types and builder functions live in ``inspect_ai.event``.  This module
re-exports them for backwards compatibility and provides scout-specific
functionality: ``TimelineMessages``, ``timeline_messages``,
``filter_timeline_events``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from logging import getLogger
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from inspect_scout._scanner.extract import MessagesAsStr
    from inspect_scout._transcript.interleave import EventsSpec, SpanExternalEvents

from inspect_ai.event import (
    Timeline,
    TimelineEvent,
    TimelineSpan,
    timeline_branch,
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

logger = getLogger(__name__)

# Re-export everything that moved to inspect_ai.event
__all__ = [
    # Types
    "Outline",
    "OutlineNode",
    "Timeline",
    "TimelineContentItem",
    "TimelineEvent",
    "TimelineSpan",
    # Functions
    "timeline_build",
    "timeline_dump",
    "timeline_filter",
    "timeline_load",
    "timeline_branch",
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
    filtered_branches_list: list[TimelineSpan] = []
    for b in span.branches:
        fb = _filter_span(b, allowed)
        if fb.content or fb.branches:
            filtered_branches_list.append(
                TimelineSpan(
                    id=fb.id,
                    name=fb.name,
                    span_type=fb.span_type,
                    content=fb.content,
                    branches=fb.branches,
                    branched_from=b.branched_from,
                    description=fb.description,
                    utility=fb.utility,
                    outline=fb.outline,
                )
            )
    return TimelineSpan(
        id=span.id,
        name=span.name,
        span_type=span.span_type,
        content=filtered_content,
        branches=filtered_branches_list,
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
    prompt_reserve: int | float = 0.2,
    events: EventsSpec | None = None,
    span_external: SpanExternalEvents | None = None,
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
            See ``prompt_reserve`` below for how the budget available
            for messages is derived from the window.
        compaction: How to handle compaction boundaries when extracting
            messages from span events.
        depth: Maximum nesting level of *scannable* spans to process. A
            scannable span is a non-utility span containing at least
            one direct ``ModelEvent``; pure container spans (such as
            the synthetic root produced by ``timeline_build``) and
            utility spans are transparent and do not consume a depth
            level. ``1`` processes only the outermost scannable span on
            each branch (typically top-level agents/solvers); ``N``
            allows up to N nested scannable layers. ``None`` (default)
            recurses without limit. ``0`` yields nothing.
        prompt_reserve: Context-window allowance for prompt scaffolding
            wrapped around the rendered messages (e.g. a scanner
            template). A ``float`` reserves that fraction of the window;
            an ``int`` reserves that many tokens (plus a small safety
            margin). Default ``0.2`` leaves 80% of the window for
            messages. Forwarded to ``segment_messages()``.
        events: Which non-message event types to interleave into each
            span's message thread as marked entries (``"all"``, a list
            of event types, or ``None`` (default) to disable
            interleaving). When set, each span's thread is built via
            ``span_interleaved_messages()`` before segmentation.
        span_external: Optional mapping of span id to ``(event_id,
            rendered_text)`` entries to append after that span's own
            messages, before segmentation (so they count toward the
            token budget). The reserved key ``""`` prepends its entries
            to the first scannable span. Ignored when ``events`` is
            ``None``.

    Yields:
        TimelineMessages for each segment. Empty spans are skipped.
    """
    from inspect_scout._transcript.messages import segment_messages

    root = timeline.root if isinstance(timeline, Timeline) else timeline

    if events is None:
        counter = 0
        for span in _walk_spans(root, depth=depth):
            async for seg in segment_messages(
                span,
                messages_as_str=messages_as_str,
                model=model,
                context_window=context_window,
                compaction=compaction,
                prompt_reserve=prompt_reserve,
            ):
                yield TimelineMessages(
                    messages=seg.messages,
                    messages_str=seg.messages_str,
                    segment=counter,
                    span=span,
                )
                counter += 1
        return

    from inspect_scout._transcript.interleave import (
        _event_message,
        span_interleaved_messages,
    )

    span_external = span_external or {}
    counter = 0
    is_first_span = True
    for span in _walk_spans(root, depth=depth):
        source = span_interleaved_messages(span, events=events, compaction=compaction)
        if is_first_span:
            leading = span_external.get("", [])
            if leading:
                source = [_event_message(eid, text) for eid, text in leading] + source
            is_first_span = False
        trailing = span_external.get(span.id, [])
        if trailing:
            source = source + [_event_message(eid, text) for eid, text in trailing]

        async for seg in segment_messages(
            source,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            # splice already resolved compaction; source is a message list
            prompt_reserve=prompt_reserve,
        ):
            yield TimelineMessages(
                messages=seg.messages,
                messages_str=seg.messages_str,
                segment=counter,
                span=span,
            )
            counter += 1

    if is_first_span and span_external:
        dropped = sum(len(entries) for entries in span_external.values())
        logger.debug(
            "timeline_messages: no scannable span was walked; dropping "
            "%d span-external event(s)",
            dropped,
        )


def _walk_spans(
    span: TimelineSpan,
    *,
    depth: int | None = None,
    _scannable_depth: int = 0,
) -> Iterator[TimelineSpan]:
    """Walk the span tree depth-first, yielding scannable spans.

    A span is "scannable" when it is not a utility span and contains at
    least one direct ``ModelEvent``. Non-scannable spans (utility spans
    and pure container spans, including the synthetic root from
    ``timeline_build``) are transparent: traversed so their scannable
    descendants are reached, but they do not consume a level of
    ``depth``.

    ``depth`` therefore counts levels of *scannable* spans:

    - ``1`` = outermost scannable span on each branch
    - ``N`` = up to N nested scannable layers
    - ``None`` = unlimited
    - ``<= 0`` = nothing

    Args:
        span: The root span to walk.
        depth: Maximum nesting level of scannable spans (see above).
        _scannable_depth: Internal counter tracking how many scannable
            ancestors are above the current node (0 means none yet).

    Yields:
        Scannable TimelineSpan nodes in depth-first order.
    """
    from inspect_scout._transcript.interleave import span_is_scannable

    if depth is not None and depth <= 0:
        return

    is_scannable = span_is_scannable(span)

    if is_scannable:
        next_depth = _scannable_depth + 1
        if depth is not None and next_depth > depth:
            return
        yield span
    else:
        next_depth = _scannable_depth

    for item in span.content:
        if isinstance(item, TimelineSpan):
            yield from _walk_spans(item, depth=depth, _scannable_depth=next_depth)
