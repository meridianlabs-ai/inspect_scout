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
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

if TYPE_CHECKING:
    from inspect_scout._scanner.extract import MessagesAsStr
    from inspect_scout._transcript.interleave import EventsSpec, SpanExternalEvents

from inspect_ai.event import (
    BranchEvent,
    Event,
    ModelEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
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
    "OwnedBranch",
    "OwnedItem",
    "OwnedSpan",
    "TimelineMessages",
    "filter_timeline_events",
    "span_is_scannable",
    "timeline_messages",
    "walk_owned_spans",
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

    if events is not None:
        from inspect_scout._transcript.interleave import (
            _event_message,
            span_interleaved_messages,
        )

    span_external = span_external or {}
    counter = 0
    is_first_span = True
    for span in _walk_spans(root, depth=depth):
        source: TimelineSpan | list[ChatMessage]
        if events is None:
            source = span
        else:
            # Splice interleavable events (which resolves compaction) and
            # attach span-external entries: leading ones to the first
            # scannable span, trailing ones after their own span.
            source = span_interleaved_messages(
                span, events=events, compaction=compaction
            )
            if is_first_span:
                leading = span_external.get("", [])
                if leading:
                    source = [
                        _event_message(eid, text) for eid, text in leading
                    ] + source
            trailing = span_external.get(span.id, [])
            if trailing:
                source = source + [_event_message(eid, text) for eid, text in trailing]
        is_first_span = False

        async for seg in segment_messages(
            source,
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


def _span_has_direct_model_event(span: TimelineSpan) -> bool:
    return any(
        isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent)
        for item in span.content
    )


def span_is_scannable(span: TimelineSpan) -> bool:
    """True if ``span`` is scannable: not a utility span, with a direct ModelEvent.

    The single walked-ness predicate for the ownership traversal
    (``walk_owned_spans``) and ``_walk_spans``.
    """
    return not span.utility and _span_has_direct_model_event(span)


# =============================================================================
# Ownership traversal (design §1/§4)
# =============================================================================


class OwnedItem(NamedTuple):
    event: Event
    own: bool


class OwnedBranch(NamedTuple):
    branched_from: str  # "" when the fork had no anchor
    items: list[OwnedItem]  # all foreign; replay prefix already cut


class OwnedSpan(NamedTuple):
    span: TimelineSpan  # real span, or the orphan sentinel
    items: list[OwnedItem]
    branches: list[OwnedBranch]


_ORPHAN_SPAN_ID: Final = "scout-orphans-9f0c6c2f"


def _orphan_span() -> TimelineSpan:
    """Reserved synthetic span for the zero-walked-spans segment (design §3).

    A fixed, collision-resistant id — NOT the root's id, which is a real
    span's id on the solvers/agent path. Documented on
    ``TimelineMessages.span``.
    """
    return TimelineSpan(id=_ORPHAN_SPAN_ID, name="orphans")


def walk_owned_spans(
    root: TimelineSpan,
    *,
    depth: int | None = None,
    include_scorers: bool = False,
) -> Iterator[OwnedSpan]:
    """Yield each walked span with every event and branch it owns.

    The single ownership traversal (design §1): the walked-ness predicate,
    the depth counter, and the scorers rule exist exactly once, here.
    Every event gets exactly one owner via three tiers: nearest enclosing
    walked ancestor; else the latest-starting walked span preceding it in
    document order; else orphan. Items are document-ordered and tagged
    ``own`` (direct content of the walked span; may advance the splice
    anchor) or ``foreign`` (never anchors). Events nested in ``ToolEvent
    .events`` are flattened recursively as foreign (decision 6). Branch
    subtrees are never walked; they ride ``OwnedSpan.branches`` with the
    replay prefix (content before the branch's first direct
    ``BranchEvent``) cut, positioned later by ``branched_from`` (§4).

    Each ``OwnedSpan`` is yielded complete, in pre-order: the traversal
    buffers because tier 1 keeps accruing items to a walked ancestor while
    nested walked spans come and go, and tier 2 depends on later document
    positions.

    ``depth <= 0`` yields nothing (orphan homing suppressed too).
    """
    if depth is not None and depth <= 0:
        return

    owners: list[OwnedSpan] = []
    orphan_items: list[OwnedItem] = []
    orphan_branches: list[OwnedBranch] = []
    latest: OwnedSpan | None = None  # tier 2: latest-starting walked span

    def sink(
        walked_ancestor: OwnedSpan | None,
    ) -> tuple[list[OwnedItem], list[OwnedBranch]]:
        owner = walked_ancestor if walked_ancestor is not None else latest
        if owner is None:
            return orphan_items, orphan_branches  # tier 3
        return owner.items, owner.branches

    def add_flattened(
        event: Event,
        items: list[OwnedItem],
        *,
        own: bool,
        drop_models: bool = False,
    ) -> None:
        # drop_models implements the scorers rule (design §2): with
        # include_scorers=False, grader MODEL events are suppressed by
        # non-existence — but the subtree's non-model events (ScoreEvents
        # above all — decision 2 exists to NOT lose them) remain foreign
        # items and render.
        if drop_models and isinstance(event, ModelEvent):
            return
        items.append(OwnedItem(event, own))
        if isinstance(event, ToolEvent):
            # Recursive and uniform (decision 6): nested events are foreign
            # at any depth, wherever the traversal meets a ToolEvent.
            for nested in event.events:
                add_flattened(nested, items, own=False, drop_models=drop_models)

    def add_branch(
        branch: TimelineSpan, in_scorers: bool, branches: list[OwnedBranch]
    ) -> None:
        items: list[OwnedItem] = []
        nested_branches: list[tuple[TimelineSpan, bool]] = []
        has_cut = any(
            isinstance(i, TimelineEvent) and isinstance(i.event, BranchEvent)
            for i in branch.content
        )

        def collect(span: TimelineSpan, span_scorers: bool, live: bool) -> None:
            span_scorers = span_scorers or span.span_type == "scorers"
            suppressed = span_scorers and not include_scorers
            for item in span.content:
                if isinstance(item, TimelineEvent):
                    # The replay cut applies to the branch span's DIRECT
                    # content only; a branch with no BranchEvent splices
                    # everything (timeline_build guarantees one, stored
                    # timelines via timeline_load do not — design §4).
                    if span is branch and isinstance(item.event, BranchEvent):
                        live = True
                    if live:
                        add_flattened(
                            item.event, items, own=False, drop_models=suppressed
                        )
                else:
                    collect(item, span_scorers, live)
            for nested in span.branches:
                nested_branches.append((nested, span_scorers))

        collect(branch, in_scorers, live=not has_cut)
        if items:
            branches.append(OwnedBranch(branch.branched_from or "", items))
        # Branches-within-branches flatten into the same owner's list; their
        # branched_from names a message absent from the owner's thread, so
        # they resolve unmatched and append (design §4, accepted).
        for nested, nested_scorers in nested_branches:
            add_branch(nested, nested_scorers, branches)

    def visit(
        span: TimelineSpan,
        *,
        walked_ancestor: OwnedSpan | None,
        in_scorers: bool,
        scannable_depth: int,
    ) -> None:
        nonlocal latest
        in_scorers = in_scorers or span.span_type == "scorers"
        suppressed = in_scorers and not include_scorers
        scannable = not suppressed and span_is_scannable(span)
        if scannable:
            next_depth = scannable_depth + 1
            walked = depth is None or next_depth <= depth
        else:
            # A scannable-but-too-deep span still consumed a level above;
            # non-scannable spans are transparent (mirrors _walk_spans).
            next_depth = scannable_depth
            walked = False

        owned: OwnedSpan | None = None
        if walked:
            owned = OwnedSpan(span, [], [])
            owners.append(owned)
            latest = owned

        # A span's owner is the owner an event at its start position would
        # get (design §1, "Spans are owned too") — captured at entry.
        branch_sink = owned.branches if owned is not None else sink(walked_ancestor)[1]
        for branch in span.branches:
            # add_branch suppresses grader MODEL events internally via
            # in_scorers; non-model scorers content still splices (§4).
            add_branch(branch, in_scorers, branch_sink)

        for item in span.content:
            if isinstance(item, TimelineEvent):
                if owned is not None:
                    add_flattened(item.event, owned.items, own=True)
                else:
                    items, _ = sink(walked_ancestor)
                    add_flattened(item.event, items, own=False, drop_models=suppressed)
            else:
                visit(
                    item,
                    walked_ancestor=owned if owned is not None else walked_ancestor,
                    in_scorers=in_scorers,
                    scannable_depth=next_depth,
                )

    visit(root, walked_ancestor=None, in_scorers=False, scannable_depth=0)

    if owners:
        if orphan_items or orphan_branches:
            # Tier-3 orphans preceding the first walked span lead it.
            owners[0].items[:0] = orphan_items
            owners[0].branches[:0] = orphan_branches
        yield from owners
    elif orphan_items or orphan_branches:
        yield OwnedSpan(_orphan_span(), orphan_items, orphan_branches)
