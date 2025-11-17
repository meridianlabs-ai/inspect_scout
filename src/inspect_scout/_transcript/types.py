from dataclasses import dataclass, field
from typing import Literal, Sequence, TypeAlias

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from pydantic import BaseModel, Field, JsonValue

MessageType = Literal["system", "user", "assistant", "tool"]
"""Message types."""

EventType = Literal[
    "model",
    "tool",
    "approval",
    "sandbox",
    "info",
    "logger",
    "error",
    "span_begin",
    "span_end",
]
"""Event types."""

MessageFilter: TypeAlias = Literal["all"] | Sequence[MessageType] | None
EventFilter: TypeAlias = Literal["all"] | Sequence[EventType | str] | None


@dataclass
class TranscriptContent:
    messages: MessageFilter = field(default=None)
    events: EventFilter = field(default=None)


class TranscriptInfo(BaseModel):
    """Transcript identifier, location, and metadata."""

    id: str
    """Globally unique id for transcript (e.g. sample uuid)."""

    source_id: str
    """Globally unique ID for transcript source (e.g. eval_id)."""

    source_uri: str
    """URI for source data (e.g. log file path)"""

    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    """Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.)."""


class Transcript(TranscriptInfo):
    """Transcript info and transcript content (messages and events)."""

    messages: list[ChatMessage] = Field(default_factory=list)
    """Main message thread."""

    events: list[Event] = Field(default_factory=list)
    """Events from transcript."""
