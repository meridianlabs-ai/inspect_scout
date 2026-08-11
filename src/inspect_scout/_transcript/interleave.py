"""Chronological interleaving of non-message events into the message list."""

from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    AsyncIterator,
    Final,
    Iterable,
    Iterator,
    Literal,
    NamedTuple,
)

from inspect_ai.event import (
    CompactionEvent,
    Event,
    EventTreeSpan,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
    event_sequence,
    event_tree,
    timeline_filter,
)
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY, message_as_str
from .._scanner.util import _event_id, _message_id
from .event_text import event_as_str
from .messages import span_messages
from .timeline import (
    OwnedBranch,
    OwnedItem,
    OwnedSpan,
    _span_has_direct_model_event,
    span_is_scannable,
)
from .types import EventType, Transcript

if TYPE_CHECKING:
    from .handle import TranscriptHandle


class InterleavedEvent(NamedTuple):
    """An interleavable event's id paired with its rendered ``[E#]`` text."""

    event_id: str
    text: str


SpanExternalEvents = dict[str, list[InterleavedEvent]]
"""Mapping of scannable span id (or ``""``) to its span-external entries.

See ``collect_span_external()``'s docstring for the key/ordering contract.
"""

INTERLEAVE_DEPENDENCIES: Final[frozenset[EventType]] = frozenset(
    {"model", "tool", "compaction", "span_begin", "span_end", "branch"}
)
"""Event types that must be LOADED for interleaving to be correct.

These carry the structure the walk runs on -- model events anchor entries,
compaction events drive pruning, span begins resolve scorer spans, tool events
nest sub-agent models, and ``timeline_build`` needs a ``BranchEvent`` to form a
branch span at all (without one it unrolls the branch into its parent, so the
scanner reads the branch as the main thread). A caller that filters any of them
out gets silent degradation rather than an error, so any content filter built
for interleaving must be a superset of this.

``span_end`` is retained without a demonstrated consumer: ``scorer_span_ids``
reads begins only, and no probe has produced output that differs without ends.
It stays because over-loading costs a few filtered events while under-loading
is the silent-degradation bug this constant exists to prevent -- every member
here was added after that failure, twice.
"""

_NON_INTERLEAVED: Final[frozenset[EventType]] = frozenset(
    {"model", "tool", "compaction", "span_begin", "span_end", "anchor", "checkpoint"}
)
"""Event types never RENDERED as ``[E#]`` entries.

Either already present in the message thread (model, tool) or pure structure,
plus replay/infrastructure markers carrying nothing a judge could cite.

Deliberately independent of ``INTERLEAVE_DEPENDENCIES`` rather than derived
from it: the two answer different questions and neither contains the other.
``branch`` is required for structure yet renders a useful ``BRANCH`` entry;
``anchor``/``checkpoint`` render nothing yet need not be loaded.
"""

EventsSpec = Literal["all"] | list[EventType]
"""Which event types to interleave: ``"all"`` or an explicit list.

Deliberately narrower than ``EventFilter``, which admits bare ``str``: an
unrecognised name here renders nothing and reports nothing, so ``events=
["scoer"]`` would silently produce a judge prompt with no ``[E#]`` entries.
The ``| str`` this used to carry was justified as covering "event types not yet
in the literal, e.g. score" -- the EventType widening put all of them in.
"""

Compaction = Literal["all", "last"] | int
"""How to handle compaction boundaries when the message thread is
reconstructed from model events (events-only transcripts)."""


class EventsOnlyInterleaveUnsupported(Exception):
    """A flat interleave driver was given a transcript with no messages.

    Reconstructing the thread from events alone cannot be made to agree with
    the materialized driver inside a bounded-memory streaming pass: `trim`
    compaction needs the whole trimmed prefix, which the region-last skeleton
    deliberately does not retain, so an entire compaction region goes missing.

    `llm_scanner` never hit this -- it routes every handle without messages to
    `stream_timeline_messages`, which handles span structure properly. Callers
    reaching it directly should do the same.
    """


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


def scorer_span_ids(begins: Iterable[SpanBeginEvent]) -> frozenset[str]:
    """Ids of spans under a top-level ``scorers`` span, by ``event_tree``'s rule.

    Streaming counterpart to ``_scorers_model_event_ids``, which needs the
    whole event tree in memory. This needs only the span begins.

    ``event_tree`` indexes every span before resolving parents, and its
    ``bucket()`` treats a span as a root when its parent id is falsy *or* names
    a span it never saw. Resolving from the complete set of begins is what
    makes this match the tree rather than approximate it: arrival order, span
    ends, and boundary balance are all irrelevant to the tree, so they must be
    irrelevant here too. Two previous incremental formulations -- counting
    boundaries, then requiring ``parent_id is None`` -- each leaked grader
    output on shapes the tree handles: sliced checkpoint-restore transcripts,
    events preceding their own span begin, and the ``parent_id=""`` that this
    repo's weave/langsmith/logfire converters emit for roots.

    A cyclic parent chain (possible with reused span ids) terminates here
    rather than recursing, unlike ``event_tree``.
    """
    spans_by_id: dict[str, list[SpanBeginEvent]] = defaultdict(list)
    for begin in begins:
        spans_by_id[begin.id].append(begin)
    # Last begin wins for the name, as event_tree's node index does.
    name_by_id = {begin.id: begin.name for begin in begins}

    def rooted_at_scorers(begin: SpanBeginEvent, seen: frozenset[str]) -> bool:
        if begin.id in seen:
            return False
        parents = spans_by_id.get(begin.parent_id) if begin.parent_id else None
        if not parents:
            return name_by_id[begin.id] == "scorers"
        # A reused id is reachable from every begin that declared it, which is
        # how event_tree sees it -- resolving only the last one loses a parent.
        return any(rooted_at_scorers(p, seen | {begin.id}) for p in parents)

    return frozenset(
        span_id
        for span_id, spans in spans_by_id.items()
        # A falsy span id is a root to event_tree's bucket() and can never be a
        # scorers member; keeping "" would mark every span-less event a grader.
        if span_id and any(rooted_at_scorers(b, frozenset()) for b in spans)
    )


def _scorers_model_event_ids(events: list[Event]) -> frozenset[str]:
    """Ids of ModelEvents nested under any top-level ``scorers`` span.

    On the flat/events-only path a grader ``ModelEvent`` is just another
    item in the event list; without this exclusion it would render as a
    branch entry, breaking the invariant that scorer model calls never
    surface in scanned content. (Timeline paths handle this structurally.)

    Every top-level ``scorers`` span counts, matching ``scorer_span_ids``;
    taking only the first would leak later graders on re-scored and spliced
    checkpoint-restore transcripts. Empty if the list carries no span
    structure or no ``scorers`` span is found.
    """
    if not any(isinstance(e, (SpanBeginEvent, SpanEndEvent)) for e in events):
        return frozenset()
    tree = event_tree(events)
    scorers_spans = [
        item
        for item in tree
        if isinstance(item, EventTreeSpan) and item.name == "scorers"
    ]
    return frozenset(
        _event_id(e)
        for span in scorers_spans
        for e in event_sequence(span)
        if isinstance(e, ModelEvent)
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

    Known limitation, id-less messages only (unreachable for Inspect logs,
    which auto-mint message ids): the order-based text-hash fallback lets a
    fork steal the occurrence of a later on-thread turn with equal text
    (pinned by ``test_idless_duplicate_text_fork_steals_anchor_known_limitation``).
    Escalate to uuid-keyed anchoring rather than patching the heuristic.
    """

    def __init__(
        self,
        message_ids: list[str],
        events: EventsSpec,
        excluded_ids: frozenset[str] = frozenset(),
        grader_spans: frozenset[str] = frozenset(),
        compaction_spans: frozenset[str | None] = frozenset(),
    ) -> None:
        self._events = events
        occurrences: dict[str, list[int]] = defaultdict(list)
        for index, message_id in enumerate(message_ids):
            occurrences[message_id].append(index)
        self._occurrences = occurrences
        self._next_occurrence: dict[str, int] = defaultdict(int)
        self._last_anchor: int | None = None
        self._excluded_ids = excluded_ids
        self._grader_spans = grader_spans
        self._compaction_spans = compaction_spans
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
        if isinstance(event, ToolEvent):
            # A tool-spawned sub-agent's model events never appear at the top
            # level of the event list, so without this its output is absent
            # from the prompt entirely. Only ids and rendered text are
            # retained, so this costs nothing on the streaming path.
            for nested in event.events:
                self.add(nested)
            return
        if isinstance(event, ModelEvent):
            # Grader calls are excluded by span, not by event id: a uuid-less
            # grader and a real ScoreEvent can synthesize the same id and the
            # score would disappear with it.
            if event.span_id in self._grader_spans:
                return
            mid = _model_output_id(event)
            consumed = mid is not None and self.add_model_output(mid)
            if not consumed:
                # Only suppress against a span that actually compacted;
                # exclusions derived across all spans hid another agent's
                # genuine fork output.
                if (
                    mid is not None
                    and mid in self._excluded_ids
                    and event.span_id in self._compaction_spans
                ):
                    return  # compaction-pruned: stays hidden, no branch entry
                text = _off_thread_model_text(event)
                if text is not None:
                    self.add_rendered(_event_id(event), text)
            return
        text = _interleavable_text(event, self._events)
        if text is not None:
            self.add_rendered(_event_id(event), text)

    def add_owned(self, item: OwnedItem) -> None:
        """Timeline-path entry point (design §2).

        No ``ToolEvent.events`` recursion — the ownership traversal already
        flattened nested events into their own items (decision 6). Foreign
        items never call ``add_model_output``, so they cannot consume an
        owner turn's occurrence (hazard 2, both doors). Foreign
        ``ModelEvent``s render unconditionally as ``MODEL (BRANCH)``;
        foreign non-model events obey the ``events`` filter, as own ones do.
        No grader handling here: with ``include_scorers=False`` the
        traversal never emits grader events (suppression by non-existence,
        hazard 4).
        """
        event = item.event
        if isinstance(event, ToolEvent):
            return  # nested events arrive as their own flattened items
        if isinstance(event, ModelEvent):
            if item.own:
                mid = _model_output_id(event)
                consumed = mid is not None and self.add_model_output(mid)
                if not consumed:
                    if (
                        mid is not None
                        and mid in self._excluded_ids
                        and event.span_id in self._compaction_spans
                    ):
                        return  # compaction-pruned: stays hidden
                    text = _off_thread_model_text(event)
                    if text is not None:
                        self.add_rendered(_event_id(event), text)
            else:
                text = _off_thread_model_text(event)
                if text is not None:
                    self.add_rendered(_event_id(event), text)
            return
        text = _interleavable_text(event, self._events)
        if text is not None:
            self.add_rendered(_event_id(event), text)

    def spliced(self, messages: Iterable[ChatMessage]) -> Iterator[ChatMessage]:
        """Yield ``messages`` with the walk's entries spliced in.

        Leading entries first, then each message followed by the entries
        anchored to its position.
        """
        for event_id, text in self.leading:
            yield _event_message(event_id, text)
        for index, message in enumerate(messages):
            yield message
            for event_id, text in self.anchored.get(index, []):
                yield _event_message(event_id, text)


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

    # excluded_ids is derived from this span alone, so every id in it belongs
    # to a turn this span compacted -- the whole span is the compaction scope.
    # `None` is a real span_id here (the repo's compaction fixtures build
    # span-less events), so it must be a bucket rather than filtered out.
    span_event_spans = frozenset(
        item.event.span_id for item in span.content if isinstance(item, TimelineEvent)
    )
    walk = _AnchorWalk(
        [_message_id(m) for m in messages],
        events,
        excluded_ids=excluded_ids,
        compaction_spans=span_event_spans,
    )
    for item in span.content:
        if isinstance(item, TimelineEvent):
            walk.add(item.event)

    return list(walk.spliced(messages))


def _render_branch_block(branch: OwnedBranch, events: EventsSpec) -> list[ChatMessage]:
    """Render a branch's items as a flat block of [E#] marker messages.

    Foreign rules apply: ModelEvents render unconditionally as MODEL
    (BRANCH); everything else obeys the ``events`` filter. Branch items
    never anchor (design §4).
    """
    block: list[ChatMessage] = []
    for item in branch.items:
        event = item.event
        if isinstance(event, ToolEvent):
            continue  # nested events are their own flattened items
        if isinstance(event, ModelEvent):
            text = _off_thread_model_text(event)
        else:
            text = _interleavable_text(event, events)
        if text is not None:
            block.append(_event_message(_event_id(event), text))
    return block


def _splice_branches(
    spliced: list[ChatMessage], owned: OwnedSpan, events: EventsSpec
) -> list[ChatMessage]:
    """Insert branch blocks at their branched_from positions (design §4).

    Mirrors the viewer's insertBranchCards/findEventByMessageId
    (ts-mono inspect-components contentItems.ts): branches sharing a
    branched_from are grouped and spliced consecutively at the single
    resolved index; unmatched branches — including ``""``, exactly as the
    viewer's inline positioning treats it — append at the end. Resolution
    is event-level against the owner's OWN items, output message ids and
    ToolEvent.message_id only: the streaming stub strips input message
    ids, so the viewer's input-id tier would break streamed==materialized.
    KNOWN DIVERGENCES (deliberate): splice.py reads ``""`` as "no shared
    prefix"; the swimlane geometry (markers.ts resolveForkTimestamp) draws
    a ``""`` branch from the parent's start. Inline card order is what a
    debugging human compares against, and this matches it.

    Injection is INDEX INSERTION, never add_model_output — consuming an
    occurrence would re-open hazard 2 through the branch door.
    """
    if not owned.branches:
        return spliced

    groups: dict[str, list[ChatMessage]] = {}
    order: list[str] = []
    for branch in owned.branches:
        block = _render_branch_block(branch, events)
        if not block:
            continue
        if branch.branched_from not in groups:
            groups[branch.branched_from] = []
            order.append(branch.branched_from)
        groups[branch.branched_from].extend(block)
    if not groups:
        return spliced

    resolvable: set[str] = set()
    for item in owned.items:
        if not item.own:
            continue
        if isinstance(item.event, ModelEvent):
            mid = _model_output_id(item.event)
            if mid is not None:
                resolvable.add(mid)
        elif isinstance(item.event, ToolEvent) and item.event.message_id:
            resolvable.add(item.event.message_id)

    def insertion_index(key: str) -> int | None:
        if key not in resolvable:
            return None  # includes "": unmatched, appends at the end
        for i, message in enumerate(spliced):
            if _message_id(message) == key:
                # After the message and its anchored [E#] entries.
                j = i + 1
                while j < len(spliced) and (
                    (spliced[j].metadata or {}).get(EVENT_MARKER_KEY)
                ):
                    j += 1
                return j
        return None

    resolved = [(key, insertion_index(key)) for key in order]
    matched: list[tuple[str, int]] = [
        (key, idx) for key, idx in resolved if idx is not None
    ]
    # Back-to-front so earlier insertions don't shift later indexes.
    for key, idx in sorted(matched, key=lambda pair: pair[1], reverse=True):
        spliced[idx:idx] = groups[key]
    for unmatched_key, unmatched_idx in resolved:
        if unmatched_idx is None:
            spliced.extend(groups[unmatched_key])
    return spliced


def span_owned_messages(
    owned: OwnedSpan, *, events: EventsSpec, compaction: Compaction
) -> list[ChatMessage]:
    """Splice an owned span's items and branches into its message thread.

    Successor to ``span_interleaved_messages`` under the ownership model
    (design §2): the thread comes from the span's DIRECT content only
    (``span_messages`` — hazard 1: foreign items never reach it), items
    are consumed by ``_AnchorWalk.add_owned`` in document order, and
    branch blocks are inserted at their resolved positions afterwards.
    ``compaction_spans`` derives from OWN items only (hazard 3).
    """
    span = owned.span
    messages = span_messages(span, compaction=compaction)
    excluded_ids = _compaction_excluded_ids(
        span, (_message_id(m) for m in messages), compaction
    )
    own_event_spans = frozenset(item.event.span_id for item in owned.items if item.own)
    walk = _AnchorWalk(
        [_message_id(m) for m in messages],
        events,
        excluded_ids=excluded_ids,
        compaction_spans=own_event_spans,
    )
    for item in owned.items:
        walk.add_owned(item)
    spliced = list(walk.spliced(messages))
    return _splice_branches(spliced, owned, events)


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
                continue
            event = item.event
            if isinstance(event, ModelEvent):
                if span_in_scorers:
                    continue
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
    span's own direct events: this walks the tree's ``content`` depth-first to
    find every event NOT owned by such a splice (utility spans, pure
    containers, root level, ``scorers`` spans, spans beyond ``depth``) and
    attributes each to the most recently reached scannable span (key ``""``
    before the first one). The result is passed as
    ``timeline_messages(..., span_external=...)``.

    KNOWN GAP: ``TimelineSpan.branches`` is not walked, so events inside a
    branch span are collected by neither driver -- ``_walk_spans`` does not
    yield branch spans either. Loading ``BranchEvent`` (see
    ``INTERLEAVE_DEPENDENCIES``) is what routes a branch into ``.branches``
    rather than unrolling it into its parent's content, which is why those
    events used to surface at all: misattributed to the parent thread. Not
    rendering them is the safer of the two, but it is still a gap, and
    ``timeline_stream._substitute_full_events`` *does* recurse into
    ``.branches`` -- so the two walks disagree about the tree.

    ``ModelEvent``s collected this way always render as ``MODEL (BRANCH)``
    entries, except grader model calls under a ``scorers`` span, which never
    render. Pass the tree through ``scorers_collection_source`` first -- it
    documents the ``include_scorers`` handling.

    Args:
        timeline: The (unpruned, or caller-pre-filtered) timeline or span
            subtree to walk.
        events: Which event types to interleave (``"all"`` or a list).
        depth: Maximum nesting level of scannable spans, matching
            ``timeline_messages()``. A scannable span beyond this limit is
            never walked, so its own events are collected as external too.

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


def interleave_events(
    transcript: Transcript,
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> list[ChatMessage]:
    """Splice loaded non-message events into ``transcript.messages``.

    Each event is anchored after the most recent preceding assistant turn;
    events with no preceding turn are prepended. A ``ModelEvent`` whose
    output never joined the thread renders as a ``[E#] MODEL (BRANCH):``
    entry unless the turn was compaction-pruned, in which case it stays
    hidden (see ``_AnchorWalk``). Grader model calls under a ``scorers``
    span are excluded from the walk entirely.

    When the transcript has no top-level messages (events-only loads), the
    thread is reconstructed from model events via ``span_messages``
    (honoring ``compaction``).

    Warning:
        The events-only reconstruction assumes a single linear
        conversation; with multiple parallel agents it drops every agent
        but the last from the thread (their outputs surface only as branch
        entries). Multi-agent transcripts must use the timeline machinery
        instead; ``llm_scanner`` routes them there automatically.

    Args:
        transcript: Transcript providing messages and events.
        events: Which event types to interleave (``"all"`` or a list).
        compaction: Compaction handling for events-only thread reconstruction.
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages
    excluded_ids: frozenset[str] = frozenset()
    if messages:
        # `messages` is the transcript's own live thread, already shaped by
        # the original run's compaction (the `compaction` argument only
        # governs events-only reconstruction below). The "last" sentinel
        # forces `_compaction_excluded_ids` past its `"all"` fast path.
        if any(isinstance(e, CompactionEvent) for e in transcript.events):
            excluded_ids = _compaction_excluded_ids(
                transcript.events,
                (_message_id(m) for m in messages),
                compaction="last",
            )
    else:
        raise EventsOnlyInterleaveUnsupported(
            "interleave_events needs transcript.messages; use timeline_messages "
            "for an events-only transcript"
        )

    walk = _AnchorWalk(
        [_message_id(m) for m in messages],
        events,
        excluded_ids=excluded_ids,
        grader_spans=scorer_span_ids(
            [e for e in transcript.events if isinstance(e, SpanBeginEvent)]
        ),
        compaction_spans=frozenset(
            e.span_id for e in transcript.events if isinstance(e, CompactionEvent)
        ),
    )
    for event in transcript.events:
        walk.add(event)

    return list(walk.spliced(messages))


async def stream_interleave_events(
    handle: "TranscriptHandle",
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> AsyncIterator[ChatMessage]:
    """Streaming counterpart to ``interleave_events`` over a handle.

    Yields the same message sequence ``interleave_events`` would produce,
    without holding messages and event payloads in memory at once.

    Messages-present transcripts take four passes over the handle: collect
    message ids; one pass that both derives compaction-pruned ``excluded_ids``
    from a region-last-``ModelEvent`` skeleton (cheap no-op when there is no
    ``CompactionEvent``) and collects span begins for grader-span resolution;
    the anchor walk (retaining just id + rendered text per selected event);
    then re-stream messages splicing anchored entries.

    Events-only transcripts take two events passes -- one for span begins,
    one to reconstruct the thread -- the latter
    retaining only the region-last ``ModelEvent`` (whose input carries the
    region's conversation) plus an op log of output-message ids and
    pre-rendered branch text, replayed against the reconstructed thread.
    That reconstruction carries ``interleave_events``' linear-conversation
    limitation. ``llm_scanner`` never reaches it: it routes *every* handle
    without messages to ``stream_timeline_messages``, so this branch serves
    direct library callers only.
    """
    message_ids = [_message_id(m) async for m in handle.messages()]
    # Span boundaries are needed to spot grader model calls; the rest of the
    # dependency set is inert here but keeps the two filters in step.
    types = None if events == "all" else [*sorted(INTERLEAVE_DEPENDENCIES), *events]

    if message_ids:
        # Region-last skeleton solely to derive compaction-pruned
        # `excluded_ids`. Without a CompactionEvent this pass costs only
        # the filtered scan.
        excluded_ids: frozenset[str] = frozenset()
        compaction_skeleton: list[Event] = []
        begins: list[SpanBeginEvent] = []
        compaction_spans: set[str | None] = set()
        saw_compaction = False
        # Span begins ride along rather than costing their own pass: a handle's
        # type filter applies after deserialization, so a "span_begin only"
        # pass still replays and validates every event in the transcript.
        async for event in handle.events(types=["model", "compaction", "span_begin"]):
            if isinstance(event, SpanBeginEvent):
                begins.append(event)
                continue  # must not reach compaction_skeleton -> span_messages
            if isinstance(event, CompactionEvent):
                saw_compaction = True
                compaction_spans.add(event.span_id)
            _skeleton_add(compaction_skeleton, event)
        if saw_compaction:
            excluded_ids = _compaction_excluded_ids(
                compaction_skeleton, message_ids, compaction="last"
            )

        walk = _AnchorWalk(
            message_ids,
            events,
            excluded_ids=excluded_ids,
            grader_spans=scorer_span_ids(begins),
            compaction_spans=frozenset(compaction_spans),
        )
        async for event in handle.events(types=types):
            walk.add(event)

        for event_id, text in walk.leading:
            yield _event_message(event_id, text)
        index = 0
        async for message in handle.messages():
            yield message
            for event_id, text in walk.anchored.get(index, []):
                yield _event_message(event_id, text)
            index += 1
        return

    raise EventsOnlyInterleaveUnsupported(
        "stream_interleave_events needs a handle with messages; use "
        "stream_timeline_messages for an events-only transcript"
    )


def _skeleton_add(skeleton: list[Event], event: Event) -> None:
    """Append ``event``, replacing a trailing ModelEvent (region-last wins).

    Only sound for deriving compaction-pruned ids against an existing message
    thread. It is NOT sound for reconstructing a thread: under ``trim``
    compaction ``span_messages`` also reads the trimmed prefix, which this
    discards -- that is why the events-only branch was removed rather than
    fixed (see ``EventsOnlyInterleaveUnsupported``).
    """
    if (
        isinstance(event, ModelEvent)
        and skeleton
        and isinstance(skeleton[-1], ModelEvent)
    ):
        skeleton[-1] = event
    else:
        skeleton.append(event)
