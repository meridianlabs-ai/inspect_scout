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
    """Render a ModelEvent's output as a `[E#] MODEL (BRANCH):` entry.

    Used when the event's output message id is not found in the
    reconstructed thread -- a fork/branch experiment or a retry whose
    output never joined the final conversation. Rather than silently
    dropping the output, it is rendered on a copy of the output message
    with `metadata["role_label"]` set to `"model (branch)"` (read by
    `_role_label` in `_scanner/extract.py`, which uppercases it into the
    `MODEL (BRANCH):` prefix).

    Renders via `message_as_str` on the message itself -- never
    `event.output.completion` -- because fork outputs often carry an
    empty `completion` with their real content living in reasoning-summary
    content parts, which only rendering the message's content surfaces.

    Args:
        event: The off-thread ModelEvent.

    Returns:
        The rendered text, or None if there is no output message, or the
        render is empty (e.g. nothing renderable in the message content).
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

    Shared discriminator input for ``_AnchorWalk``'s ``excluded_ids``: an id
    in this set belongs to a turn that ``compaction`` deliberately pruned
    from the caller's actual (possibly truncated) thread, and must stay
    hidden rather than resurfacing as a ``MODEL (BRANCH)`` entry (see
    ``_AnchorWalk``'s class docstring for the fork/compaction-pruned split
    this feeds).

    When ``compaction == "all"`` there is nothing to exclude by
    construction -- for callers whose ``current_message_ids`` come from
    reconstructing ``source`` with this same ``compaction`` value via
    ``span_messages``, that reconstruction already IS the untruncated one --
    so the untruncated reconstruction is skipped entirely. Callers whose
    current thread comes from elsewhere (e.g. a transcript's own top-level
    ``messages``, already shaped by whatever compaction the original run
    applied, independent of this ``compaction`` argument) must pass a
    non-``"all"`` value whenever ``source`` contains a ``CompactionEvent``
    at all, to force the computation.

    Args:
        source: The events (or span/timeline) to reconstruct the
            untruncated thread from.
        current_message_ids: Ids of the caller's current (possibly
            truncated) thread.
        compaction: ``"all"`` to skip (nothing can be excluded); any other
            value forces the untruncated reconstruction and diff.

    Returns:
        Ids present in the untruncated thread but not in
        ``current_message_ids``.
    """
    if compaction == "all":
        return frozenset()
    all_messages = span_messages(source, compaction="all")
    return frozenset(_message_id(m) for m in all_messages) - frozenset(
        current_message_ids
    )


def scorers_collection_source(source: Timeline, include_scorers: bool) -> Timeline:
    """Compute the timeline ``collect_span_external()`` should walk to gather span-external events.

    Shared by ``transcript_messages`` (``messages.py``) and
    ``stream_timeline_messages`` (``timeline_stream.py``): when
    ``include_scorers`` is ``False`` (the default), a ``scorers`` span is
    about to be pruned from the *walked* tree, so its own events (e.g. a
    grader's final ``ScoreEvent``) would be silently lost unless collected
    from the still-unpruned ``source`` -- returned unchanged. When
    ``include_scorers`` is ``True``, a ``scorers`` span WITH a direct
    ``ModelEvent`` is instead walked normally and splices its own events via
    ``span_interleaved_messages``, so it must be filtered out here or its
    events would be double-rendered; a ``scorers`` span with no direct
    ``ModelEvent`` is never walked by ``_walk_spans`` regardless of
    ``include_scorers``, so it must remain in the returned source.

    Args:
        source: The (unpruned) timeline to derive the collection source from.
        include_scorers: Mirrors the caller's ``include_scorers`` setting.

    Returns:
        The timeline ``collect_span_external()`` should walk.
    """
    if not include_scorers:
        return source
    return timeline_filter(
        source,
        lambda s: not (s.span_type == "scorers" and _span_has_direct_model_event(s)),
    )


def _scorers_model_event_ids(events: list[Event]) -> frozenset[str]:
    """Ids of ModelEvents nested under a top-level ``scorers`` span, if any.

    On timeline paths, a ``scorers`` span's grader ``ModelEvent``s never
    join a scanned thread structurally: the span is either pruned entirely
    (default ``include_scorers=False``) or, when included, walked as its
    *own* scannable span (see ``collect_span_external``'s docstring) --
    either way they are never direct content of some other span, so they
    are never seen by that span's own `_AnchorWalk` at all.

    On the flat/events-only path there is no such structural boundary: a
    grader ``ModelEvent`` is just another item in the flat event list, so
    without this check it would be picked up by `_AnchorWalk.add` like any
    other off-thread model call and rendered as a branch entry -- breaking
    the original invariant that a scorer's own model calls never surface
    in scanned content. This mirrors `_exclude_scorers` (`messages.py`) in
    assuming a single top-level ``scorers`` span.

    Args:
        events: The flat event list to scan.

    Returns:
        Ids (`_event_id`) of every ModelEvent nested under the top-level
        ``scorers`` span. Empty if the event list carries no span
        structure at all (nothing to detect) or no top-level ``scorers``
        span is found.
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

    Consumes events one at a time and retains only what splicing needs: the
    event's id, its rendered text, and the message *position* it anchors to.
    Event payloads are never held.

    Anchoring assumes a ModelEvent's output message id matches the same
    message in the message list (the invariant Inspect logs satisfy).
    Anchors are message positions: messages without explicit ids fall back
    to a text hash, so duplicate ids are real (e.g. two identical "yes"
    turns) and each ModelEvent must consume the next occurrence rather than
    re-anchoring to the first.

    A ModelEvent whose output message id is NOT found in the thread splits
    into two cases, distinguished by `excluded_ids`:

    - Fork: the id is in NEITHER the thread NOR `excluded_ids` -- a
      fork/branch experiment or a retry whose output never joined the
      final conversation. Rather than being silently dropped, `add`
      renders it via `_off_thread_model_text` and anchors it at the
      current position (`add_rendered`, which does not itself advance the
      anchor) -- it is always rendered, regardless of the `events`
      selection, since it is model content that would otherwise be
      invisible entirely.
    - Compaction-pruned: the id IS in `excluded_ids` -- the turn belongs to
      a superseded region that the caller's compaction strategy
      deliberately dropped (e.g. `compaction="last"` keeping only the
      final region). `add` does nothing: no branch entry, no anchor
      advance -- the turn stays hidden, honoring the caller's explicit
      request to compact it away rather than resurrecting it as a "fork".

    Known limitation (id-less messages only): when messages lack real ids,
    the text-hash fallback makes occurrence consumption order-based rather
    than identity-aware. A fork whose output text equals a later on-thread
    turn's text steals that turn's occurrence: the fork is silently
    dropped and the real turn misrenders as a branch entry (pinned by
    ``test_idless_duplicate_text_fork_steals_anchor_known_limitation``).
    The fallback also keys on ``message.text``, which is coarser than the
    rendered output (reasoning content is invisible to it), so visually
    distinct messages can collide. Inspect auto-mints message ids at
    construction and on deserialization (a sweep of >2M real messages
    found none missing), so this is unreachable for Inspect logs; it can
    only affect synthetic transcripts or non-Inspect importers that
    construct id-less messages. If such an importer appears, escalate to
    uuid-keyed anchoring on the reconstruction paths rather than patching
    the order-based heuristic.
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

    When ``compaction`` truncates the thread (anything but ``"all"``), a
    ``ModelEvent`` whose output fell outside the kept region is only ever
    a genuine off-thread fork if it is ALSO absent from the untruncated
    ``compaction="all"`` thread -- see ``_AnchorWalk``'s ``excluded_ids``
    discriminator. Ids present in the ``"all"`` thread but not the current
    (possibly truncated) one are computed here and passed through so those
    turns stay hidden rather than resurfacing as ``MODEL (BRANCH)`` entries.

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

    Shared by ``_walk_spans`` (``timeline.py``), which yields exactly the
    spans this predicate matches, and ``_collect_span_external`` below,
    which uses it (plus a ``scorers``-span exclusion) to decide when a
    span's own splice owns its events.
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

    # A ModelEvent reached here (`is_scannable` False) has no thread of its
    # own to be "on" or "off" -- unlike `_AnchorWalk.add`, which anchors a
    # ModelEvent against a reconstructed thread and only renders it when its
    # output id is NOT found there, this collector always renders it (via
    # `_off_thread_model_text`, ignoring `events` -- model content is
    # always-on, matching `_AnchorWalk`'s off-thread case). Two distinct
    # situations land here, both rendered identically as `MODEL (BRANCH)`
    # entries attached to `last_scannable`:
    #   - Utility spans, pure containers, root level, or a `scorers` span:
    #     genuinely non-scannable locations with no thread at all.
    #   - A structurally scannable span excluded purely by `depth`: its
    #     ModelEvents (including ones that WOULD be on-thread if the span
    #     were walked) are surfaced as branch entries after the last span
    #     actually walked -- the same "below-depth content surfaces as
    #     span-external" semantics `_walk_spans` already applies to
    #     everything else in such a span.
    # `scorers` spans are the one exception: their grader ModelEvents must
    # never render, so `span_in_scorers` (computed above, propagated to
    # descendants regardless of the descendants' own type) short-circuits
    # them. Scannable spans' own direct ModelEvents are never seen here at
    # all -- the `is_scannable` branch above `continue`s past them first,
    # leaving them owned by that span's own `span_interleaved_messages`
    # splice.
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

    ``ModelEvent``s reached this way (a fork/branch inside a utility span,
    root-level model calls, or -- see ``depth`` below -- on-thread turns of
    a span that is never walked) are never silently dropped: each renders
    unconditionally as a ``MODEL (BRANCH)`` entry via
    ``_off_thread_model_text``, exactly like ``_AnchorWalk``'s off-thread
    case, except there is no thread here to be "off" from -- location alone
    (not on-thread/off-thread status) is what routes a ModelEvent through
    this collector instead of a span's own splice. The one exception is a
    ``scorers`` span's grader ``ModelEvent``s, which are always excluded
    (see below). A scannable span's own direct ``ModelEvent``s are never
    visited here at all -- they are skipped in favor of that span's own
    ``span_interleaved_messages`` splice, whether or not the span is
    actually within ``depth`` (see ``depth``'s docs for the latter case).

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
            within the depth limit. This includes the span's own
            ``ModelEvent``s, even ones that would have been ordinary
            on-thread turns had the span been walked: with no splice ever
            reconstructing that span's thread, there is nothing for them
            to be "on"; they render as ``MODEL (BRANCH)`` entries after
            the parent, matching the depth semantics already applied to
            every other event type in such a span. ``None`` (default)
            matches ``_walk_spans``' unlimited depth and preserves prior
            behavior exactly.

    Returns:
        Mapping of scannable span id (or ``""`` for events preceding
        the first scannable span) to a list of ``(event_id,
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
