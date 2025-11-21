from dataclasses import dataclass, field
from os import PathLike
from typing import Any, Literal, Sequence, TypeAlias

from inspect_ai.event._event import Event
from inspect_ai.log._file import (
    EvalLogInfo,
)
from inspect_ai.model._chat_message import ChatMessage
from pydantic import BaseModel, Field

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

LogPaths: TypeAlias = (
    PathLike[str] | str | EvalLogInfo | Sequence[PathLike[str] | str | EvalLogInfo]
)


@dataclass
class TranscriptContent:
    messages: MessageFilter = field(default=None)
    events: EventFilter = field(default=None)


class TranscriptInfo(BaseModel):
    """Transcript identifier, location, and metadata."""

    transcript_id: str
    """Globally unique id for transcript (e.g. sample uuid)."""

    source_type: str | None = Field(default=None)
    """Type of source for transcript (e.g. "eval_log")."""

    source_id: str | None = Field(default=None)
    """Globally unique ID for transcript source (e.g. eval_id)."""

    source_uri: str | None = Field(default=None)
    """Optional. URI for source data (e.g. log file path)."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Transcript source specific metadata (e.g. model, task name, errors, epoch, dataset sample id, limits, etc.)."""


class Transcript(TranscriptInfo):
    """Transcript info and transcript content (messages and events)."""

    messages: list[ChatMessage] = Field(default_factory=list)
    """Main message thread."""

    events: list[Event] = Field(default_factory=list)
    """Events from transcript."""


# Reserved column names that cannot be used as metadata keys
# These are actual Parquet columns, so metadata keys cannot use these names
RESERVED_COLUMNS = {
    "transcript_id",
    "source_type",
    "source_id",
    "source_uri",
    "messages",
    "events",
    "filename",  # Internal column for DuckDB file-targeting optimization
}
