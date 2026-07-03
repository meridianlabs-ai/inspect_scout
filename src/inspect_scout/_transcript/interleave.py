"""Primitives for chronological interleaving of non-message events into the message list."""

from collections import defaultdict
from typing import Literal

from inspect_ai.event import Event, ModelEvent, Timeline, TimelineEvent, TimelineSpan
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY
from .._scanner.util import _event_id, _message_id
from .event_text import event_as_str
from .messages import span_messages
from .types import EventType

# Events that already appear in the message thread (model, tool) or are pure
# structure are never rendered as [E#] entries.
_NON_INTERLEAVED: frozenset[EventType] = frozenset(
    {"model", "tool", "compaction", "span_begin", "span_end"}
)

EventsSpec = Literal["all"] | list[EventType | str]
"""Which event types to interleave: ``"all"`` or an explicit list.

``str`` is accepted alongside ``EventType`` (matching ``EventFilter``) for
event types not yet in the literal, e.g. ``"score"``.
"""

Compaction = Literal["all", "last"] | int
"""How to handle compaction boundaries when the message thread is
reconstructed from model events (events-only transcripts)."""


def _interleavable_text(event: Event, events: EventsSpec = "all") -> str | None:
    if event.event in _NON_INTERLEAVED:
        return None
    if events != "all" and event.event not in events:
        return None
    return event_as_str(event)


def _event_message(event_id: str, text: str) -> ChatMessage:
    return ChatMessageUser(
        id=event_id,
        content=text,
        metadata={EVENT_MARKER_KEY: True},
    )


def _model_output_id(event: ModelEvent) -> str | None:
    out = event.output
    if out and out.choices and out.choices[0].message is not None:
        return _message_id(out.choices[0].message)
    return None


class _AnchorWalk:
    """Incremental anchor walk shared by the materialized and streaming drivers.

    Consumes events one at a time and retains only what splicing needs: the
    event's id, its rendered text, and the message *position* it anchors to.
    Event payloads are never held.

    Anchoring assumes a ModelEvent's output message id matches the same
    message in the message list (the invariant Inspect logs satisfy).
    Anchors are message positions: messages without explicit ids fall back
    to a text hash, so duplicate ids are real (e.g. two identical "yes"
    turns) and each ModelEvent must consume the next occurrence rather than
    re-anchoring to the first.
    """

    def __init__(self, message_ids: list[str], events: EventsSpec) -> None:
        self._events = events
        occurrences: dict[str, list[int]] = defaultdict(list)
        for index, message_id in enumerate(message_ids):
            occurrences[message_id].append(index)
        self._occurrences = occurrences
        self._next_occurrence: dict[str, int] = defaultdict(int)
        self._last_anchor: int | None = None
        self.leading: list[tuple[str, str]] = []
        self.anchored: dict[int, list[tuple[str, str]]] = defaultdict(list)

    def add_model_output(self, message_id: str) -> None:
        position = self._next_occurrence[message_id]
        if position < len(self._occurrences.get(message_id, [])):
            self._last_anchor = self._occurrences[message_id][position]
            self._next_occurrence[message_id] = position + 1

    def add_rendered(self, event_id: str, text: str) -> None:
        entry = (event_id, text)
        if self._last_anchor is None:
            self.leading.append(entry)
        else:
            self.anchored[self._last_anchor].append(entry)

    def add(self, event: Event) -> None:
        if isinstance(event, ModelEvent):
            mid = _model_output_id(event)
            if mid is not None:
                self.add_model_output(mid)
            return
        text = _interleavable_text(event, self._events)
        if text is not None:
            self.add_rendered(_event_id(event), text)


def span_interleaved_messages(
    span: TimelineSpan, *, events: EventsSpec, compaction: Compaction
) -> list[ChatMessage]:
    """Splice a span's interleavable events into its message thread.

    Per-span counterpart to ``interleave_events``: draws ``ModelEvent``s
    and interleavable events from the span's direct ``TimelineEvent``
    content (descendant spans are not considered), reconstructs the
    span's message thread via ``span_messages`` (honoring ``compaction``),
    then anchors and splices events into that thread with ``_AnchorWalk``.

    Anchoring walks the span's full, unfiltered content in order, so an
    event whose anchoring ``ModelEvent`` output was dropped by compaction
    is not found in the (possibly truncated) thread and falls back to
    being anchored to the previous surviving turn, or leads the span if
    none survived.

    Args:
        span: The scannable span to process.
        events: Which event types to interleave (``"all"`` or a list).
        compaction: Compaction handling for the span's message thread.

    Returns:
        The span's messages with marked event entries spliced in.
    """
    messages = span_messages(span, compaction=compaction)

    walk = _AnchorWalk([_message_id(m) for m in messages], events)
    for item in span.content:
        if isinstance(item, TimelineEvent):
            walk.add(item.event)

    result: list[ChatMessage] = [
        _event_message(event_id, text) for event_id, text in walk.leading
    ]
    for index, message in enumerate(messages):
        result.append(message)
        for event_id, text in walk.anchored.get(index, []):
            result.append(_event_message(event_id, text))
    return result


def _span_has_direct_model_event(span: TimelineSpan) -> bool:
    return any(
        isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent)
        for item in span.content
    )


def _collect_span_external(
    span: TimelineSpan,
    events: EventsSpec,
    *,
    last_scannable: str | None,
    in_scorers: bool,
    external: dict[str, list[tuple[str, str]]],
    depth: int | None = None,
    _scannable_depth: int = 0,
) -> str | None:
    """Depth-first helper for ``collect_span_external``; see its docstring."""
    span_in_scorers = in_scorers or span.span_type == "scorers"
    structurally_scannable = (
        not span_in_scorers and not span.utility and _span_has_direct_model_event(span)
    )
    # Mirrors `_walk_spans`' scannable-depth bookkeeping (`timeline.py`): a
    # structurally scannable span still consumes a depth level even when it
    # exceeds `depth` and is therefore never actually walked (and its own
    # splice never runs). `next_scannable_depth` only grows, so once a span
    # exceeds `depth` every descendant does too -- their events fall through
    # to external collection, attributed to the last span that IS walked.
    if structurally_scannable:
        next_scannable_depth = _scannable_depth + 1
        is_scannable = depth is None or next_scannable_depth <= depth
    else:
        next_scannable_depth = _scannable_depth
        is_scannable = False

    if is_scannable:
        last_scannable = span.id

    for item in span.content:
        if isinstance(item, TimelineEvent):
            if is_scannable:
                continue  # owned by this span's own splice (span_interleaved_messages)
            text = _interleavable_text(item.event, events)
            if text is not None:
                key = last_scannable if last_scannable is not None else ""
                external[key].append((_event_id(item.event), text))
        else:
            last_scannable = _collect_span_external(
                item,
                events,
                last_scannable=last_scannable,
                in_scorers=span_in_scorers,
                external=external,
                depth=depth,
                _scannable_depth=next_scannable_depth,
            )
    return last_scannable


def collect_span_external(
    timeline: Timeline | TimelineSpan, events: EventsSpec, *, depth: int | None = None
) -> dict[str, list[tuple[str, str]]]:
    """Collect span-external interleavable events from the unpruned timeline.

    Companion to ``span_interleaved_messages()``: that function splices
    events that live in a scannable span's own direct content; this
    function walks the *whole* tree (spans and their ``TimelineEvent``
    content, depth-first, in document order) to find every
    interleavable event that is NOT owned by such a splice -- because
    it sits in a utility span, a pure container span, root level, or a
    ``scorers`` span -- and attributes each one to the most recently
    reached scannable span (or the reserved key ``""`` if none has
    been reached yet). The result is meant to be passed as
    ``timeline_messages(..., span_external=...)``.

    A span is scannable for this purpose when it is not a utility
    span, has at least one direct ``ModelEvent``, and is not a
    ``scorers`` span. ``scorers`` spans (and, recursively, all of
    their descendants regardless of the descendants' own type) are
    always treated as non-scannable here, even though a ``scorers``
    span containing a grader ``ModelEvent`` would otherwise satisfy
    the plain scannable predicate used by ``_walk_spans``. This is
    deliberate: ``transcript_messages`` calls this collector on the
    *unpruned* timeline before pruning the ``scorers`` span away (the
    default, ``include_scorers=False``), so a ``scorers`` span's
    events (e.g. the final ``ScoreEvent``) must be collected here or
    they would be silently lost -- they would otherwise look "owned"
    by a per-span splice that will never run, because the span is
    pruned before ``timeline_messages`` ever walks it.

    When ``include_scorers=True`` the ``scorers`` span is *not*
    pruned, but it is only walked as an ordinary scannable span by
    ``timeline_messages`` (whose ``_walk_spans`` predicate is not
    ``scorers``-aware) when it has a direct ``ModelEvent`` -- in that
    case its events are spliced in directly by
    ``span_interleaved_messages`` instead, and must not also be
    collected here or they would be double-rendered. A ``scorers``
    span with no direct ``ModelEvent`` (e.g. a non-model-graded
    scorer such as ``match`` or ``includes``) is never walked by
    ``_walk_spans`` regardless of ``include_scorers``, so it must
    remain in the tree passed here or its events (e.g. the final
    ``ScoreEvent``) would be silently lost. Callers therefore must
    invoke this collector on a copy of the timeline with only those
    ``scorers`` spans that have a direct ``ModelEvent`` filtered out
    (e.g. via ``timeline_filter`` combined with
    ``_span_has_direct_model_event``) rather than filtering out every
    ``scorers`` span -- keeping this function's behavior a pure,
    unconditional function of the tree it is given.

    Args:
        timeline: The (unpruned, or selectively pre-filtered by the
            caller) timeline or span subtree to walk.
        events: Which event types to interleave (``"all"`` or a list),
            passed through to ``_interleavable_text``.
        depth: Maximum nesting level of scannable spans, matching the
            ``depth`` passed to ``timeline_messages()`` /
            ``_walk_spans()``. A structurally scannable span beyond this
            limit is never actually walked (its own splice never runs),
            so its events -- and its descendants' events -- are treated
            as external here too, attributed to the last span that IS
            within the depth limit. ``None`` (default) matches
            ``_walk_spans``' unlimited depth and preserves prior
            behavior exactly.

    Returns:
        Mapping of scannable span id (or ``""`` for events preceding
        the first scannable span) to a list of ``(event_id,
        rendered_text)`` entries, in document order.
    """
    root = timeline.root if isinstance(timeline, Timeline) else timeline
    external: dict[str, list[tuple[str, str]]] = defaultdict(list)
    _collect_span_external(
        root,
        events,
        last_scannable=None,
        in_scorers=False,
        external=external,
        depth=depth,
    )
    return dict(external)
