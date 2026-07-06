"""Primitives for chronological interleaving of non-message events into the message list."""

from collections import defaultdict
from typing import Iterable, Literal, NamedTuple

from inspect_ai.event import (
    Event,
    EventTreeSpan,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    event_sequence,
    event_tree,
    timeline_filter,
)
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY, message_as_str
from .._scanner.util import _event_id, _message_id
from .event_text import event_as_str
from .messages import span_messages
from .types import EventType


class InterleavedEvent(NamedTuple):
    """An interleavable event's id paired with its rendered ``[E#]`` text."""

    event_id: str
    text: str


SpanExternalEvents = dict[str, list[InterleavedEvent]]
"""Mapping of scannable span id (or ``""``) to its span-external entries.

See ``collect_span_external()``'s docstring for the key/ordering contract.
"""

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


def _off_thread_model_text(event: ModelEvent) -> str | None:
    """Render an off-thread ModelEvent's output as a ``MODEL (BRANCH):`` entry.

    Renders the output message itself (not ``output.completion``) because
    fork outputs often carry an empty completion with their real content in
    reasoning content parts. Returns None if there is no output message or
    the render is empty.
    """
    out = event.output
    if out is None or not out.choices or out.choices[0].message is None:
        return None
    message = out.choices[0].message
    branch_message = message.model_copy(
        update={
            "metadata": {**(message.metadata or {}), "role_label": "model (branch)"}
        }
    )
    text = message_as_str(branch_message)
    return text if text else None


def _compaction_excluded_ids(
    source: Timeline | TimelineSpan | list[Event],
    current_message_ids: Iterable[str],
    compaction: Compaction,
) -> frozenset[str]:
    """Ids in the untruncated ``compaction="all"`` thread absent from the current thread.

    Feeds ``_AnchorWalk``'s ``excluded_ids``: these turns were deliberately
    pruned by compaction and must stay hidden rather than resurfacing as
    ``MODEL (BRANCH)`` entries. ``compaction="all"`` skips the computation
    (the current thread already is the untruncated one); callers whose
    current thread comes from elsewhere (e.g. a transcript's own top-level
    messages) must pass a non-``"all"`` value to force it.
    """
    if compaction == "all":
        return frozenset()
    all_messages = span_messages(source, compaction="all")
    return frozenset(_message_id(m) for m in all_messages) - frozenset(
        current_message_ids
    )


def scorers_collection_source(source: Timeline, include_scorers: bool) -> Timeline:
    """Compute the timeline ``collect_span_external()`` should walk.

    With ``include_scorers=False`` (default) the ``scorers`` span is pruned
    from the walked tree, so its events must be collected from the unpruned
    ``source`` -- returned unchanged. With ``include_scorers=True``, a
    ``scorers`` span with a direct ``ModelEvent`` is walked normally and
    splices its own events, so it is filtered out here to avoid
    double-rendering; one without a direct ``ModelEvent`` is never walked
    and must remain.
    """
    if not include_scorers:
        return source
    return timeline_filter(
        source,
        lambda s: not (s.span_type == "scorers" and _span_has_direct_model_event(s)),
    )


def _scorers_model_event_ids(events: list[Event]) -> frozenset[str]:
    """Ids of ModelEvents nested under a top-level ``scorers`` span, if any.

    On the flat/events-only path a grader ``ModelEvent`` is just another
    item in the event list; without this exclusion it would render as a
    branch entry, breaking the invariant that scorer model calls never
    surface in scanned content. (Timeline paths handle this structurally.)
    Mirrors ``_exclude_scorers`` (``messages.py``) in assuming a single
    top-level ``scorers`` span. Empty if the list carries no span structure
    or no ``scorers`` span is found.
    """
    if not any(isinstance(e, (SpanBeginEvent, SpanEndEvent)) for e in events):
        return frozenset()
    tree = event_tree(events)
    scorers_span = next(
        (
            item
            for item in tree
            if isinstance(item, EventTreeSpan) and item.name == "scorers"
        ),
        None,
    )
    if scorers_span is None:
        return frozenset()
    return frozenset(
        _event_id(e) for e in event_sequence(scorers_span) if isinstance(e, ModelEvent)
    )


class _AnchorWalk:
    """Incremental anchor walk shared by the materialized and streaming drivers.

    Consumes events one at a time and retains only the event id, rendered
    text, and the message *position* it anchors to -- never event payloads.
    Duplicate message ids are real (id-less messages fall back to a text
    hash), so each ModelEvent consumes the next occurrence of its output id
    rather than re-anchoring to the first.

    A ModelEvent whose output id is not found in the thread splits on
    ``excluded_ids``: if absent from it, the event is a genuine fork/branch
    and renders unconditionally (regardless of the ``events`` selection) as
    a ``MODEL (BRANCH)`` entry at the current anchor; if present, the turn
    was compaction-pruned and stays hidden.

    Known limitation (id-less messages only, unreachable for Inspect logs
    since Inspect auto-mints message ids): the text-hash fallback is
    order-based, so a fork whose output text equals a later on-thread
    turn's text steals that turn's occurrence (pinned by
    ``test_idless_duplicate_text_fork_steals_anchor_known_limitation``).
    If a non-Inspect importer ever produces id-less messages, escalate to
    uuid-keyed anchoring rather than patching the heuristic.
    """

    def __init__(
        self,
        message_ids: list[str],
        events: EventsSpec,
        excluded_ids: frozenset[str] = frozenset(),
    ) -> None:
        self._events = events
        occurrences: dict[str, list[int]] = defaultdict(list)
        for index, message_id in enumerate(message_ids):
            occurrences[message_id].append(index)
        self._occurrences = occurrences
        self._next_occurrence: dict[str, int] = defaultdict(int)
        self._last_anchor: int | None = None
        self._excluded_ids = excluded_ids
        self.leading: list[InterleavedEvent] = []
        self.anchored: dict[int, list[InterleavedEvent]] = defaultdict(list)

    def add_model_output(self, message_id: str) -> bool:
        """Consume the next occurrence of `message_id` as the current anchor.

        Returns:
            True if an occurrence was found and consumed (the anchor
            advanced to it). False if no (further) occurrence exists --
            the output is off-thread and the anchor is left unchanged.
        """
        position = self._next_occurrence[message_id]
        if position < len(self._occurrences.get(message_id, [])):
            self._last_anchor = self._occurrences[message_id][position]
            self._next_occurrence[message_id] = position + 1
            return True
        return False

    def add_rendered(self, event_id: str, text: str) -> None:
        entry = InterleavedEvent(event_id, text)
        if self._last_anchor is None:
            self.leading.append(entry)
        else:
            self.anchored[self._last_anchor].append(entry)

    def add(self, event: Event) -> None:
        if isinstance(event, ModelEvent):
            mid = _model_output_id(event)
            consumed = mid is not None and self.add_model_output(mid)
            if not consumed:
                if mid is not None and mid in self._excluded_ids:
                    return  # compaction-pruned: stays hidden, no branch entry
                text = _off_thread_model_text(event)
                if text is not None:
                    self.add_rendered(_event_id(event), text)
            return
        text = _interleavable_text(event, self._events)
        if text is not None:
            self.add_rendered(_event_id(event), text)


def span_interleaved_messages(
    span: TimelineSpan, *, events: EventsSpec, compaction: Compaction
) -> list[ChatMessage]:
    """Splice a span's interleavable events into its message thread.

    Draws events from the span's direct ``TimelineEvent`` content only
    (descendant spans are not considered), reconstructs the span's thread
    via ``span_messages`` (honoring ``compaction``), then anchors and
    splices with ``_AnchorWalk``. An event whose anchoring turn was dropped
    by compaction anchors to the previous surviving turn, or leads the span.

    Args:
        span: The scannable span to process.
        events: Which event types to interleave (``"all"`` or a list).
        compaction: Compaction handling for the span's message thread.

    Returns:
        The span's messages with marked event entries spliced in.
    """
    messages = span_messages(span, compaction=compaction)
    excluded_ids = _compaction_excluded_ids(
        span, (_message_id(m) for m in messages), compaction
    )

    walk = _AnchorWalk(
        [_message_id(m) for m in messages], events, excluded_ids=excluded_ids
    )
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


def span_is_scannable(span: TimelineSpan) -> bool:
    """Return True if ``span`` is scannable: not a utility span, with a direct ModelEvent.

    Shared by ``_walk_spans`` (``timeline.py``) and
    ``_collect_span_external`` so both agree on which spans own their
    events.
    """
    return not span.utility and _span_has_direct_model_event(span)


def _collect_span_external(
    span: TimelineSpan,
    events: EventsSpec,
    *,
    last_scannable: str | None,
    in_scorers: bool,
    external: defaultdict[str, list[InterleavedEvent]],
    depth: int | None = None,
    _scannable_depth: int = 0,
) -> str | None:
    """Depth-first helper for ``collect_span_external``; see its docstring."""
    span_in_scorers = in_scorers or span.span_type == "scorers"
    structurally_scannable = not span_in_scorers and span_is_scannable(span)
    # Mirrors `_walk_spans`' depth bookkeeping (`timeline.py`): a scannable
    # span beyond `depth` still consumes a depth level but is never walked,
    # so its events (and its descendants') fall through to external
    # collection, attributed to the last span that IS walked.
    if structurally_scannable:
        next_scannable_depth = _scannable_depth + 1
        is_scannable = depth is None or next_scannable_depth <= depth
    else:
        next_scannable_depth = _scannable_depth
        is_scannable = False

    if is_scannable:
        last_scannable = span.id

    # A ModelEvent reached here has no thread to be "on", so it always
    # renders as a `MODEL (BRANCH)` entry attached to `last_scannable`
    # (ignoring `events` -- model content is always-on). This covers both
    # genuinely non-scannable locations (utility spans, containers, root)
    # and scannable spans excluded purely by `depth`. Grader ModelEvents
    # (`span_in_scorers`) are the exception and never render. A scannable
    # span's own events are skipped -- owned by its own splice.
    for item in span.content:
        if isinstance(item, TimelineEvent):
            if is_scannable:
                continue  # owned by this span's own splice (span_interleaved_messages)
            event = item.event
            if isinstance(event, ModelEvent):
                if span_in_scorers:
                    continue  # grader ModelEvents never render, even as branches
                text = _off_thread_model_text(event)
            else:
                text = _interleavable_text(event, events)
            if text is not None:
                key = last_scannable if last_scannable is not None else ""
                external[key].append(InterleavedEvent(_event_id(event), text))
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
) -> SpanExternalEvents:
    """Collect span-external interleavable events from the unpruned timeline.

    Companion to ``span_interleaved_messages()``, which splices a scannable
    span's own direct events: this walks the whole tree depth-first to find
    every event NOT owned by such a splice (utility spans, pure containers,
    root level, ``scorers`` spans, spans beyond ``depth``) and attributes
    each to the most recently reached scannable span (key ``""`` before the
    first one). The result is passed as
    ``timeline_messages(..., span_external=...)``.

    ``ModelEvent``s collected this way always render as ``MODEL (BRANCH)``
    entries, except grader model calls under a ``scorers`` span (or its
    descendants), which never render. ``scorers`` spans are collected here
    (rather than spliced) because ``transcript_messages`` prunes them from
    the walked tree by default -- without this, their events (e.g. the
    final ``ScoreEvent``) would be lost. Callers that walk a ``scorers``
    span normally (``include_scorers=True`` with a direct ``ModelEvent``)
    must pre-filter it from the tree passed here to avoid double-rendering
    -- see ``scorers_collection_source``.

    Args:
        timeline: The (unpruned, or caller-pre-filtered) timeline or span
            subtree to walk.
        events: Which event types to interleave (``"all"`` or a list).
        depth: Maximum nesting level of scannable spans, matching
            ``timeline_messages()``. A scannable span beyond this limit is
            never walked, so its events (including its own on-thread
            ``ModelEvent``s, which then have no thread to be on) are
            collected as external, attributed to the last walked span.

    Returns:
        Mapping of scannable span id (or ``""``) to ``(event_id,
        rendered_text)`` entries, in document order.
    """
    root = timeline.root if isinstance(timeline, Timeline) else timeline
    external: defaultdict[str, list[InterleavedEvent]] = defaultdict(list)
    _collect_span_external(
        root,
        events,
        last_scannable=None,
        in_scorers=False,
        external=external,
        depth=depth,
    )
    return dict(external)
