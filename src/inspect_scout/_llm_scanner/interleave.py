"""Chronological interleaving of non-message events into the message list."""

from collections import defaultdict
from typing import Literal

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY
from .._scanner.util import _event_id, _message_id
from .._transcript.event_text import event_as_str
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


def _event_message(event: Event, text: str) -> ChatMessage:
    return ChatMessageUser(
        id=_event_id(event),
        content=text,
        metadata={EVENT_MARKER_KEY: True},
    )


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

    # Anchoring assumes a ModelEvent's output message id matches the same
    # message in transcript.messages (the invariant Inspect logs satisfy).
    # Anchors are message *positions*: messages without explicit ids fall
    # back to a text hash, so duplicate ids are real (e.g. two identical
    # "yes" turns) and each ModelEvent must consume the next occurrence
    # rather than re-anchoring to the first.
    occurrences: dict[str, list[int]] = defaultdict(list)
    for index, message in enumerate(messages):
        occurrences[_message_id(message)].append(index)
    next_occurrence: dict[str, int] = defaultdict(int)

    leading: list[tuple[Event, str]] = []
    anchored: dict[int, list[tuple[Event, str]]] = defaultdict(list)
    last_anchor: int | None = None
    for event in transcript.events:
        if isinstance(event, ModelEvent):
            out = event.output
            if out and out.choices and out.choices[0].message is not None:
                mid = _message_id(out.choices[0].message)
                position = next_occurrence[mid]
                if position < len(occurrences.get(mid, [])):
                    last_anchor = occurrences[mid][position]
                    next_occurrence[mid] = position + 1
            continue
        text = _interleavable_text(event, events)
        if text is None:
            continue
        if last_anchor is None:
            leading.append((event, text))
        else:
            anchored[last_anchor].append((event, text))

    result: list[ChatMessage] = [_event_message(e, text) for e, text in leading]
    for index, message in enumerate(messages):
        result.append(message)
        for event, text in anchored.get(index, []):
            result.append(_event_message(event, text))
    return result
