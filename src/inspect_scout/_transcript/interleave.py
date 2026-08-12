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
    ModelEvent,
    SpanBeginEvent,
    Timeline,
    TimelineSpan,
    ToolEvent,
)
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY, message_as_str
from .._scanner.util import EventId, MessageId, SpanId, _event_id, _message_id
from .event_text import event_as_str
from .messages import span_messages
from .timeline import OwnedBranch, OwnedItem, OwnedSpan
from .types import EventType, Transcript

if TYPE_CHECKING:
    from .handle import TranscriptHandle


class InterleavedEvent(NamedTuple):
    """An interleavable event's id paired with its rendered ``[E#]`` text."""

    event_id: EventId
    text: str


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


def _model_output_id(event: ModelEvent) -> MessageId | None:
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
    current_message_ids: Iterable[MessageId],
    compaction: Compaction,
) -> frozenset[MessageId]:
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


def scorer_span_ids(begins: Iterable[SpanBeginEvent]) -> frozenset[SpanId]:
    """Ids of spans under a top-level ``scorers`` span, by ``event_tree``'s rule.

    Streaming counterpart to the flat-oracle helper that needs the whole
    event tree in memory (``tests/llm_scanner/test_interleave_events.py``).
    This needs only the span begins.

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
        SpanId(span_id)
        for span_id, spans in spans_by_id.items()
        # A falsy span id is a root to event_tree's bucket() and can never be a
        # scorers member; keeping "" would mark every span-less event a grader.
        if span_id and any(rooted_at_scorers(b, frozenset()) for b in spans)
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
        message_ids: list[MessageId],
        events: EventsSpec,
        excluded_ids: frozenset[MessageId] = frozenset(),
        grader_spans: frozenset[SpanId] = frozenset(),
        compaction_spans: frozenset[SpanId | None] = frozenset(),
        output_positions: frozenset[int] | None = None,
    ) -> None:
        self._events = events
        occurrences: dict[MessageId, list[int]] = defaultdict(list)
        for index, message_id in enumerate(message_ids):
            occurrences[message_id].append(index)
        self._occurrences = occurrences
        self._next_occurrence: dict[MessageId, int] = defaultdict(int)
        self._last_anchor: int | None = None
        self._excluded_ids = excluded_ids
        self._grader_spans = grader_spans
        self._compaction_spans = compaction_spans
        # Thread positions holding a model OUTPUT (assistant) message, when
        # the caller can supply them. Read only when recording consumed
        # positions for branch resolution (see _consumed_positions); the
        # flat drivers stream ids without roles and never splice branches.
        self._output_positions = output_positions
        self._consumed_positions: dict[MessageId, int] = {}
        self.leading: list[InterleavedEvent] = []
        self.anchored: dict[int, list[InterleavedEvent]] = defaultdict(list)

    def add_model_output(self, message_id: MessageId) -> bool:
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
            # First-wins: the viewer resolves a branch to the FIRST output
            # event carrying the id, so later consumptions of a duplicated
            # id never displace it.
            self._consumed_positions.setdefault(
                message_id, self._turn_position(message_id, self._last_anchor)
            )
            return True
        return False

    def _turn_position(self, message_id: MessageId, consumed: int) -> int:
        """Thread position of the turn a consumption renders as.

        Normally the consumed occurrence itself. When an INPUT message
        shares the id (a cross-role duplicate), the occurrence walk -- which
        knows ids, not roles -- consumes that earlier occurrence, but a
        branch keyed on the id names the model event's OUTPUT turn (design
        §4's id tier narrowing; contentItems.ts:145 matches the output
        event), so snap forward to the id's first output occurrence.
        Anchoring is deliberately left on the consumed occurrence: this
        correction is scoped to branch positioning.
        """
        if self._output_positions is None or consumed in self._output_positions:
            return consumed
        for index in self._occurrences[message_id]:
            if index in self._output_positions:
                return index
        return consumed

    def add_rendered(self, event_id: EventId, text: str) -> None:
        entry = InterleavedEvent(event_id, text)
        if self._last_anchor is None:
            self.leading.append(entry)
        else:
            self.anchored[self._last_anchor].append(entry)

    def _consume_own_model_event(self, event: ModelEvent) -> None:
        """Consume or off-thread-render an own ``ModelEvent``.

        Shared by ``add`` and ``add_owned`` (design's own-``ModelEvent``
        handling): tries to advance the anchor to the event's output
        occurrence; if that fails, renders it as a ``MODEL (BRANCH)``
        entry unless the turn was compaction-pruned for its own span (in
        which case it stays hidden). Not used for foreign items -- those
        skip occurrence-consumption and the compaction check entirely
        (hazard 2) -- and callers remain responsible for any grader-span
        exclusion, which is not part of this shared behavior.
        """
        mid = _model_output_id(event)
        consumed = mid is not None and self.add_model_output(mid)
        if consumed:
            return
        # Only suppress against a span that actually compacted; exclusions
        # derived across all spans hid another agent's genuine fork output.
        if (
            mid is not None
            and mid in self._excluded_ids
            and event.span_id in self._compaction_spans
        ):
            return  # compaction-pruned: stays hidden, no branch entry
        text = _off_thread_model_text(event)
        if text is not None:
            self.add_rendered(_event_id(event), text)

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
            self._consume_own_model_event(event)
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
                self._consume_own_model_event(event)
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

    def spliced_position_after(self, index: int) -> int:
        """Index in ``spliced()``'s output just past thread message ``index``.

        Translates a thread position into an insertion point in the
        rendered sequence, mirroring ``spliced()``'s interleaving exactly:
        the leading entries, then each message followed by the entries
        anchored to it. The returned point is after the message AND its
        anchored ``[E#]`` entries.
        """
        return len(self.leading) + sum(
            1 + len(self.anchored.get(position, [])) for position in range(index + 1)
        )


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


def _branch_thread_index(
    key: MessageId,
    owned: OwnedSpan,
    walk: _AnchorWalk,
    message_ids: list[MessageId],
) -> int | None:
    """Thread position a branch keyed ``key`` splices after, or None.

    Event-level resolution over the owner's OWN items in document order,
    first match wins (design §4). A matching ``ModelEvent`` positions at
    the occurrence the anchor walk actually consumed for it -- one whose
    output never landed on the thread is off-thread and cannot position a
    branch at all. A matching ``ToolEvent`` has no occurrence bookkeeping,
    so it positions at the first thread message carrying the id -- a
    cross-role duplicate of a tool message id resolves to whichever thread
    message comes first.
    """
    # Escalate to uuid/event-identity-keyed positioning rather than
    # patching the role heuristics further (same route as _AnchorWalk's
    # duplicate-id anchoring note).
    for item in owned.items:
        if not item.own:
            continue
        event = item.event
        if isinstance(event, ModelEvent):
            if _model_output_id(event) == key:
                return walk._consumed_positions.get(key)
        elif isinstance(event, ToolEvent) and event.message_id == key:
            return next(
                (index for index, mid in enumerate(message_ids) if mid == key), None
            )
    return None


def _splice_branches(
    spliced: list[ChatMessage],
    owned: OwnedSpan,
    events: EventsSpec,
    *,
    walk: _AnchorWalk,
    message_ids: list[MessageId],
) -> list[ChatMessage]:
    """Insert branch blocks at their branched_from positions (design §4).

    Branches sharing a ``branched_from`` are grouped and spliced
    consecutively at the single resolved index; unmatched branches --
    including ``""`` -- append at the end, matching the viewer's inline
    positioning. Resolution is event-level against the owner's OWN items:
    output message ids and ``ToolEvent.message_id`` only, never input ids
    (the streaming stub strips those, and a tier one path cannot reach
    would break streamed == materialized).

    Known limitation, duplicate message ids within one thread only
    (reachable for converter/synthetic logs; Inspect auto-mints unique
    ids): an assistant-history message or tool-result sharing an id with
    the resolution target can pull the splice off the viewer's position,
    and anchoring may disagree with branch placement.
    """
    # Mirrors the viewer's insertBranchCards/findEventByMessageId (ts-mono
    # inspect-components contentItems.ts). Knowing divergences: splice.py
    # reads "" as "no shared prefix"; the swimlane geometry (markers.ts
    # resolveForkTimestamp) draws a "" branch from the parent's start.
    # Inline card order is what a debugging human compares against, and
    # this matches it.
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

    def insertion_index(key: str) -> int | None:
        # "" matches no own item and falls out here: unmatched, appended.
        # Resolution goes through the anchor walk's consumed occurrences,
        # translated by spliced_position_after -- never a message-id scan
        # over the rendered sequence: a scan can match a foreign event's
        # uuid (written into its marker's ChatMessage.id) or an input
        # message sharing an output's id, before the turn the key names.
        index = _branch_thread_index(MessageId(key), owned, walk, message_ids)
        return None if index is None else walk.spliced_position_after(index)

    resolved = [(key, insertion_index(key)) for key in order]
    matched: list[tuple[str, int]] = [
        (key, idx) for key, idx in resolved if idx is not None
    ]
    # Index insertion, never add_model_output -- consuming an occurrence
    # would re-open hazard 2 through the branch door. Back-to-front so
    # earlier insertions don't shift later indexes.
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

    Walks the ownership traversal's per-span view (design §2): the thread
    comes from the span's DIRECT content only
    (``span_messages`` — hazard 1: foreign items never reach it), items
    are consumed by ``_AnchorWalk.add_owned`` in document order, and
    branch blocks are inserted at their resolved positions afterwards.
    ``compaction_spans`` derives from OWN items only (hazard 3).
    """
    span = owned.span
    messages = span_messages(span, compaction=compaction)
    message_ids = [_message_id(m) for m in messages]
    excluded_ids = _compaction_excluded_ids(span, message_ids, compaction)
    own_event_spans = frozenset(
        None if item.event.span_id is None else SpanId(item.event.span_id)
        for item in owned.items
        if item.own
    )
    walk = _AnchorWalk(
        message_ids,
        events,
        excluded_ids=excluded_ids,
        compaction_spans=own_event_spans,
        output_positions=frozenset(
            index for index, m in enumerate(messages) if m.role == "assistant"
        ),
    )
    for item in owned.items:
        walk.add_owned(item)
    spliced = list(walk.spliced(messages))
    return _splice_branches(spliced, owned, events, walk=walk, message_ids=message_ids)


def interleave_events(
    transcript: Transcript,
    events: EventsSpec = "all",
) -> list[ChatMessage]:
    """Splice loaded non-message events into ``transcript.messages``.

    Each event is anchored after the most recent preceding assistant turn;
    events with no preceding turn are prepended. A ``ModelEvent`` whose
    output never joined the thread renders as a ``[E#] MODEL (BRANCH):``
    entry unless the turn was compaction-pruned, in which case it stays
    hidden (see ``_AnchorWalk``). Grader model calls under a ``scorers``
    span are excluded from the walk entirely.

    Args:
        transcript: Transcript providing messages and events.
        events: Which event types to interleave (``"all"`` or a list).

    Raises:
        EventsOnlyInterleaveUnsupported: The transcript has events but no
            top-level messages; use the timeline machinery instead --
            ``llm_scanner`` routes such transcripts there automatically.
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages
    excluded_ids: frozenset[MessageId] = frozenset()
    if messages:
        # `messages` is the transcript's own live thread, already shaped by
        # the original run's compaction. The "last" sentinel forces
        # `_compaction_excluded_ids` past its `"all"` fast path.
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
            None if e.span_id is None else SpanId(e.span_id)
            for e in transcript.events
            if isinstance(e, CompactionEvent)
        ),
    )
    for event in transcript.events:
        walk.add(event)

    return list(walk.spliced(messages))


async def stream_interleave_events(
    handle: "TranscriptHandle",
    events: EventsSpec = "all",
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

    Raises:
        EventsOnlyInterleaveUnsupported: The handle has no messages; use
            ``stream_timeline_messages`` instead -- ``llm_scanner`` routes
            such handles there automatically.
    """
    message_ids = [_message_id(m) async for m in handle.messages()]
    # Span boundaries are needed to spot grader model calls; the rest of the
    # dependency set is inert here but keeps the two filters in step.
    types = None if events == "all" else [*sorted(INTERLEAVE_DEPENDENCIES), *events]

    if message_ids:
        # Region-last skeleton solely to derive compaction-pruned
        # `excluded_ids`. Without a CompactionEvent this pass costs only
        # the filtered scan.
        excluded_ids: frozenset[MessageId] = frozenset()
        compaction_skeleton: list[Event] = []
        begins: list[SpanBeginEvent] = []
        compaction_spans: set[SpanId | None] = set()
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
                compaction_spans.add(
                    None if event.span_id is None else SpanId(event.span_id)
                )
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
