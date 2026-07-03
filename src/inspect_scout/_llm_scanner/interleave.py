"""Chronological interleaving of non-message events into the message list."""

from collections import defaultdict
from typing import AsyncIterator, Literal

from inspect_ai.event import CompactionEvent, Event, ModelEvent
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY
from .._scanner.util import _event_id, _message_id
from .._transcript.event_text import event_as_str
from .._transcript.handle import TranscriptHandle
from .._transcript.messages import span_messages
from .._transcript.types import EventType, Transcript

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


def has_interleavable_events(
    transcript: Transcript, events: EventsSpec = "all"
) -> bool:
    return any(_interleavable_text(e, events) is not None for e in transcript.events)


def interleave_events(
    transcript: Transcript,
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> list[ChatMessage]:
    """Splice loaded non-message events into ``transcript.messages``.

    Each event is anchored after the most recent preceding assistant message
    (the output of the most recent ``ModelEvent`` whose message is present in
    ``transcript.messages``). Events with no preceding turn are prepended.

    When the transcript carries no top-level messages (events-only loads),
    the message thread is reconstructed from model events via
    ``span_messages`` (honoring ``compaction``) and events are spliced into
    the reconstructed thread.

    Args:
        transcript: Transcript providing messages and events.
        events: Which event types to interleave (``"all"`` or a list).
        compaction: Compaction handling for events-only thread reconstruction.
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages
    if not messages:
        messages = span_messages(transcript.events, compaction=compaction)

    walk = _AnchorWalk([_message_id(m) for m in messages], events)
    for event in transcript.events:
        walk.add(event)

    result: list[ChatMessage] = [
        _event_message(event_id, text) for event_id, text in walk.leading
    ]
    for index, message in enumerate(messages):
        result.append(message)
        for event_id, text in walk.anchored.get(index, []):
            result.append(_event_message(event_id, text))
    return result


async def stream_interleave_events(
    handle: TranscriptHandle,
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> AsyncIterator[ChatMessage]:
    """Streaming counterpart to ``interleave_events`` over a handle.

    Yields the same message sequence ``interleave_events`` would produce for
    the materialized transcript, without holding messages and event payloads
    in memory at once.

    Messages-present transcripts take three passes over the handle
    (multi-shot contract): collect message ids, run the anchor walk
    (retaining just id + rendered text per selected event), then re-stream
    messages splicing anchored entries. Retained memory is one id per
    message plus the rendered text of selected events.

    Events-only transcripts (empty ``messages()``) reconstruct the thread
    from model events in a single events pass: only the most recent
    ``ModelEvent`` per compaction region is retained (that event's input
    already carries the region's conversation — the thread itself), plus a
    small op log of output-message ids and rendered entries so anchors
    resolve against the reconstructed thread in event order.
    """
    message_ids = [_message_id(m) async for m in handle.messages()]
    types = None if events == "all" else ["model", "compaction", *events]

    if message_ids:
        walk = _AnchorWalk(message_ids, events)
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

    # Events-only: reconstruct the thread from model events. `skeleton`
    # keeps compaction events plus the most recent ModelEvent per region
    # (span_messages only reads the region-last event); `ops` records the
    # anchor walk's inputs in event order for replay once the thread exists.
    # Each op is (kind, a, b): ("m", output_message_id, "") for a model
    # event, ("e", event_id, rendered_text) for an interleavable event.
    skeleton: list[Event] = []
    ops: list[tuple[str, str, str]] = []
    async for event in handle.events(types=types):
        if isinstance(event, ModelEvent):
            mid = _model_output_id(event)
            if mid is not None:
                ops.append(("m", mid, ""))
            if skeleton and isinstance(skeleton[-1], ModelEvent):
                skeleton[-1] = event
            else:
                skeleton.append(event)
        elif isinstance(event, CompactionEvent):
            skeleton.append(event)
        else:
            rendered = _interleavable_text(event, events)
            if rendered is not None:
                ops.append(("e", _event_id(event), rendered))

    thread = span_messages(skeleton, compaction=compaction)
    walk = _AnchorWalk([_message_id(m) for m in thread], events)
    for kind, a, b in ops:
        if kind == "m":
            walk.add_model_output(a)
        else:
            walk.add_rendered(a, b)

    for event_id, text in walk.leading:
        yield _event_message(event_id, text)
    for index, message in enumerate(thread):
        yield message
        for event_id, text in walk.anchored.get(index, []):
            yield _event_message(event_id, text)
