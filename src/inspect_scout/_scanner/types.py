"""Type definitions for scanner and loader modules."""

from typing import Sequence, TypeVar, Union

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage

from .._transcript.types import Transcript

ScannerInput = Union[
    Transcript,
    ChatMessage,
    Sequence[ChatMessage],
    Event,
    Sequence[Event],
]
"""Union of all valid scanner input types."""


# Additional TypeVars for specific overloads (maintaining existing behavior)
# These are used in the overload signatures for type narrowing
TMessage = TypeVar("TMessage", ChatMessage, list[ChatMessage])
TEvent = TypeVar("TEvent", Event, list[Event])
