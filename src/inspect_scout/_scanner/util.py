from typing import Any, Sequence, cast

from inspect_ai.analysis._dataframe.extract import auto_id
from inspect_ai.analysis._dataframe.extract import (
    messages_as_str as messages_as_str_impl,
)
from inspect_ai.event import Event
from inspect_ai.event._base import BaseEvent
from inspect_ai.model import ChatMessage, ChatMessageBase

from inspect_scout._scanner.types import ScannerInput, ScannerInputNames
from inspect_scout._transcript.types import Transcript


def messages_as_str(messages: list[ChatMessage]) -> str:
    """Concatenate list of chat messages into a string.

    Args:
       messages: List of chat messages

    Returns:
       str: Messages as a string.
    """
    return messages_as_str_impl(messages)


def get_input_type_and_ids(
    loader_result: ScannerInput,
) -> tuple[ScannerInputNames, str | list[str]] | None:
    """Determine the type of loader result/scanner input and extract associated IDs.

    Args:
        loader_result: Scanner input which can be a Transcript, ChatMessage, Event,
          or a sequence of messages/events.

    Returns:
        A tuple of (input type name, ID or list of IDs) for the given input, or
          None if the input is an empty sequence. For single items, returns a single
          ID string. For sequences, returns a list of ID strings.
    """
    if isinstance(loader_result, Transcript):
        return ("transcript", loader_result.id)
    elif isinstance(loader_result, ChatMessageBase):
        return ("message", _message_id(loader_result))
    elif isinstance(loader_result, BaseEvent):
        return ("event", _event_id(loader_result))
    elif len(loader_result) == 0:
        return None
    elif isinstance(loader_result[0], ChatMessageBase):
        _validate_homogeneous_sequence(loader_result, ChatMessageBase)
        return (
            "messages",
            [_message_id(msg) for msg in cast(Sequence[ChatMessage], loader_result)],
        )
    elif isinstance(loader_result[0], BaseEvent):
        _validate_homogeneous_sequence(loader_result, BaseEvent)
        return (
            "events",
            [_event_id(evt) for evt in cast(Sequence[Event], loader_result)],
        )


def _validate_homogeneous_sequence(
    sequence: Sequence[Any], expected_type: type
) -> None:
    if not all(isinstance(item, expected_type) for item in sequence):
        raise ValueError(
            f"All items in sequence must be {expected_type.__name__} instances"
        )


def _event_id(event: Event) -> str:
    # TODO: This is not reversible
    return event.uuid or auto_id("event", str(event.timestamp))


def _message_id(message: ChatMessage) -> str:
    # TODO: This isn't good enough. It's neither unique nor
    # reversible
    return message.id or auto_id("message", message.text)
