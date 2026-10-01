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
    AnchorEvent,
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
from .._util._async import aclosing_iter
from .event_text import event_as_str
from .messages import span_messages
from .timeline import OwnedBranch, OwnedItem, OwnedSpan
from .types import EventType, Transcript
from .util import nested_tool_events

if TYPE_CHECKING:
    from .handle import TranscriptHandle


class InterleavedEvent(NamedTuple):
    event_id: EventId
    text: str


INTERLEAVE_DEPENDENCIES: Final[frozenset[EventType]] = frozenset(
    {"model", "tool", "compaction", "span_begin", "span_end", "branch", "anchor"}
)
"""Event types that must be loaded for interleaving to be correct.

Filtering any of them out degrades silently rather than raising, so a content
filter built for interleaving must be a superset of this. Model events anchor
entries, compaction events drive pruning, span begins resolve scorer spans, tool
events nest sub-agent models, anchor events mark where a branch forked, and
``timeline_build`` needs a ``BranchEvent`` to form a branch span at all (without
one the branch unrolls into its parent and reads as the main thread).
``span_end`` has no known consumer; it stays because over-loading is cheap
and under-loading fails silently.
"""

_NON_INTERLEAVED: Final[frozenset[EventType]] = frozenset(
    {"model", "tool", "compaction", "span_begin", "span_end", "anchor", "checkpoint"}
)
"""Event types never rendered as ``[E#]`` entries.

Already in the message thread (model, tool), pure structure, or markers with
nothing a judge could cite. Not derived from ``INTERLEAVE_DEPENDENCIES``:
``branch`` must be loaded yet renders, and ``checkpoint`` renders nothing yet
need not be loaded.
"""

EventsSpec = Literal["all"] | list[EventType]
"""Which event types to interleave: ``"all"`` or an explicit list.

Narrower than ``EventFilter`` (no bare ``str``) because a misspelled name would
otherwise silently render no ``[E#]`` entries.
"""

Compaction = Literal["all", "last"] | int
"""How to handle compaction boundaries when the message thread is
reconstructed from model events (events-only transcripts)."""


class EventsOnlyInterleaveUnsupported(Exception):
    """A flat interleave driver was given a transcript with no messages.

    Raised rather than reconstructing one thread from events, which would
    collapse parallel agents into it. Use the timeline machinery for
    events-only transcripts; ``llm_scanner`` routes them there automatically.
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
    """Render an off-thread ModelEvent's output as a ``MODEL (BRANCH):`` entry."""
    out = event.output
    if out is None or not out.choices or out.choices[0].message is None:
        return None
    # Render the output message itself (not `output.completion`): fork
    # outputs often carry an empty completion with their real content in
    # reasoning content parts.
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
    """Ids in the untruncated ``compaction="all"`` thread absent from the current one.

    These compaction-pruned turns must stay hidden rather than resurface as
    ``MODEL (BRANCH)`` entries. ``compaction="all"`` returns nothing, so a caller
    whose current thread does not come from ``span_messages`` (e.g. a
    transcript's top-level messages) must pass a non-``"all"`` value.
    """
    if compaction == "all":
        return frozenset()
    all_messages = span_messages(source, compaction="all")
    return frozenset(_message_id(m) for m in all_messages) - frozenset(
        current_message_ids
    )


def scorer_span_ids(begins: Iterable[SpanBeginEvent]) -> frozenset[SpanId]:
    """Ids of spans under a top-level ``scorers`` span, by ``event_tree``'s rule.

    A cyclic parent chain (possible with reused span ids) terminates here
    rather than recursing, unlike ``event_tree``.
    """
    spans_by_id: dict[str, list[SpanBeginEvent]] = defaultdict(list)
    for begin in begins:
        spans_by_id[begin.id].append(begin)
    # Last begin wins for the name, as event_tree's node index does.
    name_by_id = {begin.id: begin.name for begin in begins}

    # Like event_tree, resolve parents only after indexing every span, and
    # treat a span as a root when its parent id is falsy or unknown: arrival
    # order, span ends and boundary balance must not matter.
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
    """Incremental anchor walk over a message thread.

    Retains only each entry's event id, text and anchor position, never event
    payloads. Duplicate message ids are real (id-less messages fall back to a
    text hash), so each ModelEvent consumes the next occurrence of its output id
    rather than re-anchoring to the first. A ModelEvent whose output is not on
    the thread renders as a ``MODEL (BRANCH)`` entry regardless of the
    ``events`` selection, unless ``excluded_ids`` marks it compaction-pruned.

    Known limitation, id-less messages only (Inspect auto-mints message ids):
    the text-hash fallback lets a fork steal the occurrence of a later
    on-thread turn with equal text. Escalate to uuid-keyed anchoring rather
    than patching the heuristic.
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
        # Assistant-message positions, used only to position branches (see
        # _turn_position). None for the flat drivers, which have no roles and
        # never splice branches.
        self._output_positions = output_positions
        self._consumed_positions: dict[MessageId, int] = {}
        self._anchor_positions: dict[str, int] = {}
        self.leading: list[InterleavedEvent] = []
        self.anchored: dict[int, list[InterleavedEvent]] = defaultdict(list)

    def add_model_output(self, message_id: MessageId) -> bool:
        """Advance the anchor to the next occurrence of ``message_id``.

        Returns False, leaving the anchor unchanged, if none remains.
        """
        position = self._next_occurrence[message_id]
        if position < len(self._occurrences.get(message_id, [])):
            self._last_anchor = self._occurrences[message_id][position]
            self._next_occurrence[message_id] = position + 1
            # First wins: the viewer resolves a branch to the first output
            # event carrying the id.
            self._consumed_positions.setdefault(
                message_id, self._turn_position(message_id, self._last_anchor)
            )
            return True
        return False

    def _turn_position(self, message_id: MessageId, consumed: int) -> int:
        """Thread position a branch keyed on ``message_id`` resolves to.

        Normally the consumed occurrence. When an input message shares the id,
        the occurrence walk (ids, not roles) consumes that earlier occurrence,
        but the viewer matches the model event's output turn, so snap forward to
        the id's first assistant occurrence. Anchoring stays on the consumed
        occurrence.
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
        """Anchor to the event's output, else render it as ``MODEL (BRANCH)``.

        A compaction-pruned turn stays hidden. Callers handle grader exclusion.
        Never call this for foreign items: consuming an occurrence would let
        them steal the owner's anchor.
        """
        mid = _model_output_id(event)
        consumed = mid is not None and self.add_model_output(mid)
        if consumed:
            return
        # Only suppress for a span that actually compacted: exclusions are
        # derived across all spans and would hide another agent's genuine fork.
        if (
            mid is not None
            and mid in self._excluded_ids
            and event.span_id in self._compaction_spans
        ):
            return
        text = _off_thread_model_text(event)
        if text is not None:
            self.add_rendered(_event_id(event), text)

    def add(self, event: Event) -> None:
        if isinstance(event, ToolEvent):
            # A tool-spawned sub-agent's model events are nested here, never
            # at the top level of the event list.
            for nested in nested_tool_events(event):
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
        self._note_anchor(event)
        text = _interleavable_text(event, self._events)
        if text is not None:
            self.add_rendered(_event_id(event), text)

    def _note_anchor(self, event: Event) -> None:
        """Record where a branch anchor sits in the thread.

        ``timeline_branch`` emits an ``AnchorEvent`` in the parent span and a
        ``BranchEvent`` carrying the same id, so ``branched_from`` names an
        anchor rather than a message. An anchor seen before any turn has been
        consumed is left unresolved, so its branch appends at the end.
        """
        if isinstance(event, AnchorEvent) and self._last_anchor is not None:
            self._anchor_positions.setdefault(event.anchor_id, self._last_anchor)

    def anchor_position(self, anchor_id: str) -> int | None:
        return self._anchor_positions.get(anchor_id)

    def add_owned(self, item: OwnedItem) -> None:
        """Timeline-path counterpart of ``add``, for ``walk_owned_spans`` items.

        Foreign ``ModelEvent``s always render as ``MODEL (BRANCH)``. Grader
        model calls are already dropped by the traversal unless
        ``include_scorers``.
        """
        event = item.event
        if isinstance(event, ToolEvent):
            return  # nested events arrive as their own flattened items
        if item.own:
            self._note_anchor(event)
        if isinstance(event, ModelEvent):
            if item.own:
                self._consume_own_model_event(event)
            else:
                # Never consume an occurrence for a foreign event: it would
                # steal the owner turn's anchor.
                text = _off_thread_model_text(event)
                if text is not None:
                    self.add_rendered(_event_id(event), text)
            return
        text = _interleavable_text(event, self._events)
        if text is not None:
            self.add_rendered(_event_id(event), text)

    def spliced(self, messages: Iterable[ChatMessage]) -> Iterator[ChatMessage]:
        """Yield ``messages`` with the walk's entries spliced in."""
        for event_id, text in self.leading:
            yield _event_message(event_id, text)
        for index, message in enumerate(messages):
            yield message
            for event_id, text in self.anchored.get(index, []):
                yield _event_message(event_id, text)

    def spliced_position_after(self, index: int) -> int:
        """Index in ``spliced()``'s output past message ``index`` and its entries."""
        return len(self.leading) + sum(
            1 + len(self.anchored.get(position, [])) for position in range(index + 1)
        )


def _render_branch_block(branch: OwnedBranch, events: EventsSpec) -> list[ChatMessage]:
    """Render a branch's items as ``[E#]`` entries; they never anchor.

    ModelEvents always render as ``MODEL (BRANCH)``; everything else obeys
    ``events``.
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

    Matches the owner's own items in document order, first match wins. A
    ``ModelEvent`` positions at the occurrence the walk consumed for it (none
    if off-thread); a ``ToolEvent`` at the first message carrying the id.
    Input message ids are never matched: not every path that must agree with
    this one has them.
    """
    # `branched_from` names an AnchorEvent id on modern transcripts and a
    # message id on older ones.
    anchored_at = walk.anchor_position(key)
    if anchored_at is not None:
        return anchored_at

    # For duplicate-id problems, escalate to uuid-keyed positioning rather
    # than patching these role heuristics.
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
    """Insert branch blocks at their ``branched_from`` positions.

    Branches sharing a ``branched_from`` splice consecutively at one index;
    unmatched ones (including ``""``) append at the end, as the viewer places
    them inline.

    Known limitation, duplicate message ids within one thread only (converter
    or synthetic logs; Inspect auto-mints unique ids): a message sharing the
    target's id can pull the splice off the viewer's position, and anchoring
    may disagree with branch placement.
    """
    # Mirrors the viewer's inline branch cards (insertBranchCards in ts-mono's
    # contentItems.ts). Known divergences: splice.py reads "" as "no shared
    # prefix", and the swimlane (markers.ts resolveForkTimestamp) draws a ""
    # branch from the parent's start. Inline card order is what a human
    # debugging compares against.
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
        # Resolve via the walk, never by scanning `spliced` for the id: a scan
        # can hit a foreign event's marker (its uuid is the ChatMessage.id) or
        # an input message sharing an output's id.
        index = _branch_thread_index(MessageId(key), owned, walk, message_ids)
        return None if index is None else walk.spliced_position_after(index)

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
    """Splice an owned span's items and branches into its message thread."""
    span = owned.span
    # The thread comes from the span's direct content only, so a descendant's
    # model event can never replace it.
    messages = span_messages(span, compaction=compaction)
    message_ids = [_message_id(m) for m in messages]
    excluded_ids = _compaction_excluded_ids(span, message_ids, compaction)
    # Own items only, so foreign spans cannot widen the compaction scope.
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
    hidden. Grader model calls under a ``scorers`` span are excluded.

    Raises:
        EventsOnlyInterleaveUnsupported: The transcript has events but no
            top-level messages.
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages
    excluded_ids: frozenset[MessageId] = frozenset()
    if messages:
        # `messages` is already the compacted live thread; any non-"all" value
        # makes `_compaction_excluded_ids` compute the pruned ids.
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

    Yields the same sequence without holding messages and event payloads in
    memory at once: one pass collects message ids, one derives compaction
    exclusions (from each region's first and last ``ModelEvent``) and grader
    spans, one runs the anchor walk, and a final one re-streams the messages
    with the anchored entries spliced in.

    Raises:
        EventsOnlyInterleaveUnsupported: The handle has no messages; use
            ``stream_timeline_messages`` instead.
    """
    async with aclosing_iter(handle.messages()) as messages:
        message_ids = [_message_id(m) async for m in messages]
    if not message_ids:
        raise EventsOnlyInterleaveUnsupported(
            "stream_interleave_events needs a handle with messages; use "
            "stream_timeline_messages for an events-only transcript"
        )

    skeleton: list[Event] = []
    begins: list[SpanBeginEvent] = []
    compaction_spans: set[SpanId | None] = set()
    async with aclosing_iter(handle.events()) as handle_events:
        async for event in handle_events:
            if isinstance(event, SpanBeginEvent):
                begins.append(event)
            elif isinstance(event, CompactionEvent):
                compaction_spans.add(
                    None if event.span_id is None else SpanId(event.span_id)
                )
                skeleton.append(event)
            elif isinstance(event, ModelEvent):
                # `span_messages` reads only each region's first ModelEvent
                # (the trim prefix) and its last; mirror any change there.
                if len(skeleton) >= 2 and all(
                    isinstance(e, ModelEvent) for e in skeleton[-2:]
                ):
                    skeleton[-1] = event
                else:
                    skeleton.append(event)
    excluded_ids: frozenset[MessageId] = frozenset()
    if compaction_spans:
        excluded_ids = _compaction_excluded_ids(
            skeleton, message_ids, compaction="last"
        )

    walk = _AnchorWalk(
        message_ids,
        events,
        excluded_ids=excluded_ids,
        grader_spans=scorer_span_ids(begins),
        compaction_spans=frozenset(compaction_spans),
    )
    async with aclosing_iter(handle.events()) as handle_events:
        async for event in handle_events:
            walk.add(event)

    for event_id, text in walk.leading:
        yield _event_message(event_id, text)
    async with aclosing_iter(handle.messages()) as messages:
        index = 0
        async for message in messages:
            yield message
            for event_id, text in walk.anchored.get(index, []):
                yield _event_message(event_id, text)
            index += 1
