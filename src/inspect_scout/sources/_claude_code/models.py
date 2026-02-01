"""Pydantic models for Claude Code JSONL event format.

These models define the expected structure of Claude Code session events.
Using Pydantic validation ensures we fail loudly if the format changes.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Content Block Models
# =============================================================================


class ContentText(BaseModel):
    """Text content block in assistant messages."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["text"]
    text: str


class ContentThinking(BaseModel):
    """Thinking/reasoning content block in assistant messages."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["thinking"]
    thinking: str
    signature: str | None = None


class ContentToolUse(BaseModel):
    """Tool use content block in assistant messages."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ContentToolResult(BaseModel):
    """Tool result content block in user messages."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["tool_result"]
    tool_use_id: str
    content: str | list[dict[str, Any]] = ""
    is_error: bool = False


# Union of content block types
ContentBlock = ContentText | ContentThinking | ContentToolUse


# =============================================================================
# Usage Model
# =============================================================================


class Usage(BaseModel):
    """Token usage information from assistant messages."""

    model_config = ConfigDict(extra="ignore")

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


# =============================================================================
# Message Models
# =============================================================================


class UserMessage(BaseModel):
    """User message structure."""

    model_config = ConfigDict(extra="ignore")

    role: Literal["user"] = "user"
    content: str | list[dict[str, Any]] = ""


class AssistantMessage(BaseModel):
    """Assistant message structure."""

    model_config = ConfigDict(extra="ignore")

    role: Literal["assistant"] = "assistant"
    model: str | None = None
    id: str | None = None
    content: list[dict[str, Any]] = Field(default_factory=list)
    stop_reason: str | None = None
    usage: Usage | None = None


# =============================================================================
# Tool Use Result Model (for Task agent spawns)
# =============================================================================


class ToolUseResult(BaseModel):
    """Result from a Task tool call (agent subprocess)."""

    model_config = ConfigDict(extra="ignore")

    status: str = "completed"
    agentId: str | None = None
    prompt: str | None = None
    content: list[dict[str, Any]] = Field(default_factory=list)
    totalDurationMs: int | None = None
    totalTokens: int | None = None
    totalToolUseCount: int | None = None


# =============================================================================
# Compaction Metadata Model
# =============================================================================


class CompactMetadata(BaseModel):
    """Metadata for compaction boundary events."""

    model_config = ConfigDict(extra="ignore")

    trigger: str = "auto"
    preTokens: int | None = None


# =============================================================================
# Base Event Model
# =============================================================================


class BaseEvent(BaseModel):
    """Base model for all Claude Code events.

    Common fields shared by all event types.
    """

    model_config = ConfigDict(extra="ignore")

    uuid: str
    parentUuid: str | None = None
    timestamp: str
    sessionId: str
    type: str
    isSidechain: bool = False
    cwd: str | None = None
    version: str | None = None
    gitBranch: str | None = None
    slug: str | None = None


# =============================================================================
# Specific Event Models
# =============================================================================


class UserEvent(BaseEvent):
    """User message event."""

    type: Literal["user"] = "user"
    message: UserMessage
    isCompactSummary: bool = False
    toolUseResult: ToolUseResult | None = None


class AssistantEvent(BaseEvent):
    """Assistant response event."""

    type: Literal["assistant"] = "assistant"
    message: AssistantMessage


class SystemEvent(BaseEvent):
    """System event (compaction, turn duration, etc.)."""

    type: Literal["system"] = "system"
    subtype: str | None = None
    content: str | None = None
    compactMetadata: CompactMetadata | None = None


class ProgressEvent(BaseEvent):
    """Progress/streaming event (to be skipped)."""

    type: Literal["progress"] = "progress"


class FileHistoryEvent(BaseEvent):
    """File history snapshot event (to be skipped)."""

    type: Literal["file-history-snapshot"] = "file-history-snapshot"


class QueueOperationEvent(BaseEvent):
    """Queue operation event (to be skipped)."""

    type: Literal["queue-operation"] = "queue-operation"


# Union of all event types
Event = Annotated[
    UserEvent | AssistantEvent | SystemEvent | ProgressEvent | FileHistoryEvent | QueueOperationEvent,
    Field(discriminator="type"),
]


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_event(raw: dict[str, Any]) -> BaseEvent:
    """Parse a raw event dict into a typed event model.

    Args:
        raw: Raw event dictionary from JSONL

    Returns:
        Typed event model

    Raises:
        ValidationError: If the event doesn't match expected schema
    """
    event_type = raw.get("type", "unknown")

    if event_type == "user":
        return UserEvent.model_validate(raw)
    elif event_type == "assistant":
        return AssistantEvent.model_validate(raw)
    elif event_type == "system":
        return SystemEvent.model_validate(raw)
    elif event_type == "progress":
        return ProgressEvent.model_validate(raw)
    elif event_type == "file-history-snapshot":
        return FileHistoryEvent.model_validate(raw)
    elif event_type == "queue-operation":
        return QueueOperationEvent.model_validate(raw)
    else:
        # For unknown event types, use base model
        return BaseEvent.model_validate(raw)


def parse_events(raw_events: list[dict[str, Any]]) -> list[BaseEvent]:
    """Parse a list of raw events into typed event models.

    Args:
        raw_events: List of raw event dictionaries

    Returns:
        List of typed event models
    """
    return [parse_event(e) for e in raw_events]


def parse_content_block(raw: dict[str, Any]) -> ContentText | ContentThinking | ContentToolUse | dict[str, Any]:
    """Parse a content block from assistant message.

    Args:
        raw: Raw content block dictionary

    Returns:
        Typed content block, or original dict if unknown type
    """
    block_type = raw.get("type", "")

    if block_type == "text":
        return ContentText.model_validate(raw)
    elif block_type == "thinking":
        return ContentThinking.model_validate(raw)
    elif block_type == "tool_use":
        return ContentToolUse.model_validate(raw)
    else:
        # Return raw dict for unknown types
        return raw


def parse_tool_result(raw: dict[str, Any]) -> ContentToolResult | None:
    """Parse a tool result content block.

    Args:
        raw: Raw content block dictionary

    Returns:
        ContentToolResult if valid, None otherwise
    """
    if raw.get("type") != "tool_result":
        return None
    return ContentToolResult.model_validate(raw)
