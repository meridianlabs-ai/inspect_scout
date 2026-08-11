from typing import NewType, Sequence, cast

from inspect_ai.analysis._dataframe.extract import auto_id
from inspect_ai.event import Event, Timeline
from inspect_ai.event._base import BaseEvent
from inspect_ai.model import ChatMessage, ChatMessageBase

from inspect_scout._scanner.types import ScannerInput, ScannerInputNames
from inspect_scout._transcript.types import Transcript

EventId = NewType("EventId", str)
"""A rendered event's citation identity (``event.uuid`` or a minted id).

Prophylactic typing for the interleave plumbing: the citation-id bug this
makes unwritable (_ModelOutputOp passing a message id where an event id was
required) no longer has a site — it died in 2492b1902. Note one deliberate
laundering point remains: ``_event_message`` writes an ``EventId`` into
``ChatMessage.id: str | None`` and ``extract.py`` reads it back as a
``MessageId``; typing that honestly forces a cast, so it stays documented
rather than half-fixed.
"""
MessageId = NewType("MessageId", str)
SpanId = NewType("SpanId", str)


def get_input_type_and_ids(
    loader_result: ScannerInput,
) -> tuple[ScannerInputNames, list[str]] | None:
    """Determine the type of loader result/scanner input and extract associated IDs.

    Args:
        loader_result: Scanner input which can be a Transcript, ChatMessage, Event,
          Timeline, or a sequence of messages/events/timelines.

    Returns:
        A tuple of (input type name, list of IDs) for the given input, or None if
          the input is an empty sequence.
    """
    if isinstance(loader_result, Transcript):
        return ("transcript", [loader_result.transcript_id])
    elif isinstance(loader_result, ChatMessageBase):
        return ("message", [_message_id(loader_result)])
    elif isinstance(loader_result, BaseEvent):
        return ("event", [_event_id(loader_result)])
    elif isinstance(loader_result, Timeline):
        return ("timeline", [loader_result.name])
    elif len(loader_result) == 0:
        return None
    elif isinstance(loader_result[0], ChatMessageBase):
        return (
            "messages",
            [_message_id(msg) for msg in cast(Sequence[ChatMessage], loader_result)],
        )
    elif isinstance(loader_result[0], BaseEvent):
        return (
            "events",
            [_event_id(evt) for evt in cast(Sequence[Event], loader_result)],
        )
    elif isinstance(loader_result[0], Timeline):
        return (
            "timelines",
            [t.name for t in cast(Sequence[Timeline], loader_result)],
        )
    return None


def _event_id(event: Event) -> EventId:
    return EventId(event.uuid or auto_id("event", str(event.timestamp)))


def _message_id(message: ChatMessage) -> MessageId:
    return MessageId(message.id or auto_id("message", message.text))
