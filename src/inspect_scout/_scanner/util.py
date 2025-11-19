from typing import Sequence, cast

from inspect_ai.analysis._dataframe.extract import auto_id
from inspect_ai.event import Event
from inspect_ai.event._base import BaseEvent
from inspect_ai.model import ChatMessage, ChatMessageBase

from inspect_scout._scanner.types import ScannerInput, ScannerInputNames
from inspect_scout._transcript.types import Transcript


def get_input_type_and_ids(
    loader_result: ScannerInput,
) -> tuple[ScannerInputNames, list[str]] | None:
    """Determine the type of loader result/scanner input and extract associated IDs.

    Args:
        loader_result: Scanner input which can be a Transcript, ChatMessage, Event,
          or a sequence of messages/events.

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


def _event_id(event: Event) -> str:
    return event.uuid or auto_id("event", str(event.timestamp))


def _message_id(message: ChatMessage) -> str:
    return message.id or auto_id("message", message.text)
