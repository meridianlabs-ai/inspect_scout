"""Chronological interleaving of non-message events into the message list."""

from collections import defaultdict
from typing import AsyncIterator, Literal

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY
from .._scanner.util import _event_id, _message_id
from .._transcript.event_text import event_as_str
from .._transcript.handle import TranscriptHandle
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

    def add(self, event: Event) -> None:
        if isinstance(event, ModelEvent):
            out = event.output
            if out and out.choices and out.choices[0].message is not None:
                mid = _message_id(out.choices[0].message)
                position = self._next_occurrence[mid]
                if position < len(self._occurrences.get(mid, [])):
                    self._last_anchor = self._occurrences[mid][position]
                    self._next_occurrence[mid] = position + 1
            return
        text = _interleavable_text(event, self._events)
        if text is None:
            return
        entry = (_event_id(event), text)
        if self._last_anchor is None:
            self.leading.append(entry)
        else:
            self.anchored[self._last_anchor].append(entry)


def has_interleavable_events(
    transcript: Transcript, events: EventsSpec = "all"
) -> bool:
    return any(_interleavable_text(e, events) is not None for e in transcript.events)


def interleave_events(
    transcript: Transcript, events: EventsSpec = "all"
) -> list[ChatMessage]:
    """Splice loaded non-message events into ``transcript.messages``.

    Each event is anchored after the most recent preceding assistant message
    (the output of the most recent ``ModelEvent`` whose message is present in
    ``transcript.messages``). Events with no preceding turn are prepended.

    Args:
        transcript: Transcript providing messages and events.
        events: Which event types to interleave (``"all"`` or a list).
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages

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
    handle: TranscriptHandle, events: EventsSpec = "all"
) -> AsyncIterator[ChatMessage]:
    """Streaming counterpart to ``interleave_events`` over a handle.

    Yields the same message sequence ``interleave_events`` would produce for
    the materialized transcript, without holding messages and event payloads
    in memory at once. Three passes over the handle (multi-shot contract):

    1. ``messages()``: collect message ids only (anchor positions).
    2. ``events()``: run the anchor walk, retaining just id + rendered text
       per selected event (narrowed to ``model`` + selected types when the
       selection is a list).
    3. ``messages()``: yield each message, splicing anchored event entries.

    Retained memory is one id per message plus the rendered text of selected
    events — never the bulk model/tool payloads.
    """
    message_ids = [_message_id(m) async for m in handle.messages()]
    walk = _AnchorWalk(message_ids, events)

    types = None if events == "all" else ["model", *events]
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
