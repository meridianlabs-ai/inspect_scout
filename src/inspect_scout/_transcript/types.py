from dataclasses import dataclass, field
from os import PathLike
from typing import Any, Literal, Sequence, TypeAlias

from inspect_ai.event._event import Event
from inspect_ai.log._file import (
    EvalLogInfo,
)
from inspect_ai.model._chat_message import ChatMessage
from pydantic import BaseModel, ConfigDict, Field, JsonValue

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

    date: str | None = Field(default=None)
    """Date/time when the transcript was created."""

    task_set: str | None = Field(default=None)
    """Set from which transcript task was drawn (e.g. benchmark name)."""

    task_id: str | None = Field(default=None)
    """Identifier for task (e.g. dataset sample id)."""

    task_repeat: int | None = Field(default=None)
    """Repeat for a given task id within a task set (e.g. epoch)."""

    agent: str | None = Field(default=None)
    """Agent used to to execute task.."""

    agent_args: dict[str, Any] | None = Field(default=None)
    """Arguments passed to create agent."""

    model: str | None = Field(default=None)
    """Main model used by agent."""

    model_options: dict[str, Any] | None = Field(default=None)
    """Generation options for main model."""

    score: JsonValue | None = Field(default=None)
    """Value indicating score on task."""

    success: bool | None = Field(default=None)
    """Boolean reduction of score to succeeded/failed."""

    total_time: float | None = Field(default=None)
    """Time required to execute task (seconds)."""

    total_tokens: int | None = Field(default=None)
    """Tokens spent in execution of task."""

    error: str | None = Field(default=None)
    """"Error message that terminated the task."""

    limit: str | None = Field(default=None)
    """Limit that caused the task to exit (e.g. "tokens", "messages, etc.)."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Transcript source specific metadata."""

    model_config = ConfigDict(protected_namespaces=())


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
    "date",
    "task_set",
    "task_id",
    "task_repeat",
    "agent",
    "agent_args",
    "model",
    "model_options",
    "score",
    "success",
    "total_time",
    "total_tokens",
    "error",
    "limit",
    "messages",
    "events",
    "filename",  # Internal column for DuckDB file-targeting optimization
}
