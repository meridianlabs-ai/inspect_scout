"""Type definitions for scanner and loader modules."""

from typing import Sequence, Union

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from typing_extensions import Literal

from .._transcript.types import Transcript

ScannerInput = Union[
    Transcript,
    ChatMessage,
    Sequence[ChatMessage],
    Event,
    Sequence[Event],
]
"""Union of all valid scanner input types."""

ScannerInputNames = Literal["transcript", "event", "events", "message", "messages"]
