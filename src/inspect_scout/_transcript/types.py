from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from os import PathLike
from typing import Any, Literal, Protocol, Sequence, TypeAlias

from inspect_ai.event._event import Event
from inspect_ai.log._file import (
    EvalLogInfo,
)
from inspect_ai.model._chat_message import ChatMessage
from pydantic import BaseModel, ConfigDict, Field, JsonValue

MessageType = Literal["system", "user", "assistant", "tool"]
"""Message types."""


class BytesStreamContextManager(Protocol):
    """Protocol for async context managers that yield byte streams with explicit cleanup."""

    async def __aenter__(self) -> AsyncIterator[bytes]: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None: ...

    async def aclose(self) -> None:
        """Explicitly close resources. Safe to call multiple times or after __aexit__."""
        ...


class TranscriptTooLargeError(Exception):
    """Raised when transcript content exceeds size limit."""

    def __init__(self, transcript_id: str, size: int, max_size: int):
        self.transcript_id = transcript_id
        self.size = size
        self.max_size = max_size
        super().__init__(f"Transcript {transcript_id}: {size} bytes exceeds {max_size}")


EventType = Literal[
    "model",
    "tool",
    "compaction",
    "approval",
    "sandbox",
    "info",
    "store",
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


class BytesContextManager:
    """Wraps raw bytes as AsyncContextManager[AsyncIterable[bytes]].

    This adapter satisfies TranscriptMessagesAndEvents.data's type signature.
    For raw bytes, the context manager is a no-op - nothing to clean up.
    """

    def __init__(self, data: bytes) -> None:
        self._data = data

    async def __aenter__(self) -> "BytesContextManager":
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def aclose(self) -> None:
        """Explicit cleanup. No-op for raw bytes."""
        pass

    def __aiter__(self) -> "BytesContextManager":
        return self

    async def __anext__(self) -> bytes:
        if self._data:
            data = self._data
            self._data = b""
            return data
        raise StopAsyncIteration


@dataclass
class TranscriptMessagesAndEvents:
    """Raw UTF-8 JSON bytes for transcript messages/events.

    The JSON contains at least 'messages' and 'events' fields but may
    include additional data depending on the source.
    """

    data: BytesStreamContextManager
    """Raw UTF-8 JSON bytes, possibly compressed.

    This is a "cold" iterable - the underlying stream is not opened until
    iteration begins. Caller should use as async context manager for cleanup,
    or call aclose() directly if the context manager is never entered.
    """

    compression_method: int | None
    """ZIP compression method per PKWARE APPNOTE spec, or None if uncompressed.

    See: https://pkware.cachefly.net/webdocs/APPNOTE/APPNOTE-6.3.9.TXT (section 4.4.5)
    Common values: 0 = stored (no compression), 8 = DEFLATE
    """

    uncompressed_size: int | None
    """Uncompressed size in bytes, or None if unknown."""


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

    message_count: int | None = Field(default=None)
    """Total messages in conversation."""

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
