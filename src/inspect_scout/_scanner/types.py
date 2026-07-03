"""Type definitions for scanner and loader modules."""

from typing import Sequence, Union

from inspect_ai.event import Timeline
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from typing_extensions import Literal

from .._transcript.types import Transcript, TranscriptInfo

ScannerInput = Union[
    Transcript,
    TranscriptInfo,
    ChatMessage,
    Sequence[ChatMessage],
    Event,
    Sequence[Event],
    Timeline,
    Sequence[Timeline],
]
"""Union of all valid scanner input types."""

ScannerInputNames = Literal[
    "transcript",
    # "transcript_info" = info-only input record (used by streaming handle
    # scans); stable schema value.
    "transcript_info",
    "event",
    "events",
    "message",
    "messages",
    "timeline",
    "timelines",
]
