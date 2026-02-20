"""Event conversion for Claude Code sessions.

Converts Claude Code events to Scout event types:
- Assistant events -> ModelEvent
- Tool use -> ToolEvent
- Task tool calls -> SpanBeginEvent + SpanEndEvent (agent spans)
- System events -> InfoEvent
"""

import re
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any, Literal, TypeVar

from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import ContentText, ModelOutput
from inspect_ai.model._chat_message import ChatMessageAssistant
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model_output import ChatCompletionChoice, ModelUsage
from inspect_ai.tool._tool_call import ToolCallError

from .detection import (
    get_task_agent_info,
    get_timestamp,
    is_compact_boundary,
    is_skill_command,
    is_task_tool_call,
)
from .extraction import (
    extract_assistant_content,
    extract_compaction_info,
    extract_tool_result_messages,
    extract_usage,
    extract_user_message,
)
from .models import (
    AssistantEvent,
    BaseEvent,
    ContentToolUse,
    SystemEvent,
    TaskAgentInfo,
    ToolUseResult,
    UserEvent,
    parse_events,
)
from .tree import build_event_tree, flatten_tree_chronological, get_conversation_events
from .util import parse_timestamp as _parse_timestamp

logger = getLogger(__name__)

T = TypeVar("T")


# Sentinel timestamp for events with unparseable timestamps.
# Using epoch avoids extending timelines to the present day.
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def to_model_event(
    event: AssistantEvent,
    input_messages: list[Any],
    timestamp: datetime | None = None,
) -> ModelEvent:
    """Convert a Claude Code assistant event to ModelEvent.

    Args:
        event: Claude Code assistant event
        input_messages: The input messages for this model call
        timestamp: Pre-parsed timestamp. Falls back to parsing from event.

    Returns:
        ModelEvent object
    """
    message_content = event.message.content
    model_name = event.message.model or "unknown"

    # Extract content and tool calls
    content, tool_calls = extract_assistant_content(message_content)

    # Build output message
    if len(content) == 1 and isinstance(content[0], ContentText):
        output_content: str | list[Any] = content[0].text
    else:
        output_content = content if content else ""

    output_message = ChatMessageAssistant(
        content=output_content,
        tool_calls=tool_calls if tool_calls else None,
    )

    # Extract usage
    usage_data = extract_usage(event)
    usage = None
    if usage_data:
        usage = ModelUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            total_tokens=(
                usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
            ),
            input_tokens_cache_read=usage_data.get("cache_read_input_tokens"),
            input_tokens_cache_write=usage_data.get("cache_creation_input_tokens"),
        )

    # Determine stop reason
    stop_reason: Literal["stop", "tool_calls"] = "tool_calls" if tool_calls else "stop"

    output = ModelOutput(
        model=model_name,
        choices=[
            ChatCompletionChoice(
                message=output_message,
                stop_reason=stop_reason,
            )
        ],
        usage=usage,
    )

    return ModelEvent(
        model=model_name,
        input=list(input_messages),
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=output,
        timestamp=timestamp or _parse_timestamp(get_timestamp(event)) or _EPOCH,
    )


def to_tool_event(
    tool_use_block: ContentToolUse,
    tool_result: dict[str, Any] | None,
    timestamp: datetime,
    completed: datetime | None = None,
) -> ToolEvent:
    """Create a ToolEvent from a tool_use block and its result.

    Args:
        tool_use_block: The ContentToolUse from assistant message
        tool_result: The tool_result content block from user message, or None
        timestamp: When the tool call started
        completed: When the tool call completed, or None

    Returns:
        ToolEvent object
    """
    tool_id = tool_use_block.id
    function_name = tool_use_block.name
    arguments = tool_use_block.input

    # Extract result if available
    result = ""
    error = None

    if tool_result:
        result_content = tool_result.get("content", "")
        is_error = tool_result.get("is_error", False)

        # Handle content that might be a list
        if isinstance(result_content, list):
            text_parts = []
            for item in result_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            result = "\n".join(text_parts)
        elif isinstance(result_content, str):
            result = result_content
        else:
            result = str(result_content)

        if is_error:
            error = ToolCallError(type="unknown", message=result)

    return ToolEvent(
        id=tool_id,
        type="function",
        function=function_name,
        arguments=arguments if isinstance(arguments, dict) else {},
        result=result,
        timestamp=timestamp,
        completed=completed,
        error=error,
    )


def to_info_event(
    source: str,
    data: Any,
    timestamp: datetime,
    metadata: dict[str, Any] | None = None,
) -> InfoEvent:
    """Create an InfoEvent.

    Args:
        source: Event source identifier
        data: Event data
        timestamp: When the event occurred
        metadata: Optional additional metadata

    Returns:
        InfoEvent object
    """
    return InfoEvent(
        source=source,
        data=data,
        timestamp=timestamp,
        metadata=metadata,
    )


def to_span_begin_event(
    span_id: str,
    name: str,
    span_type: str | None,
    timestamp: datetime,
    parent_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SpanBeginEvent:
    """Create a SpanBeginEvent.

    Args:
        span_id: Unique span identifier
        name: Span name
        span_type: Optional span type (e.g., "agent")
        timestamp: When the span started
        parent_id: Parent span ID if nested
        metadata: Optional additional metadata

    Returns:
        SpanBeginEvent object
    """
    return SpanBeginEvent(
        id=span_id,
        name=name,
        type=span_type,
        parent_id=parent_id,
        timestamp=timestamp,
        working_start=0.0,
        metadata=metadata,
    )


def to_span_end_event(
    span_id: str,
    timestamp: datetime,
    metadata: dict[str, Any] | None = None,
) -> SpanEndEvent:
    """Create a SpanEndEvent.

    Args:
        span_id: Span identifier (must match SpanBeginEvent.id)
        timestamp: When the span ended
        metadata: Optional additional metadata

    Returns:
        SpanEndEvent object
    """
    return SpanEndEvent(
        id=span_id,
        timestamp=timestamp,
        metadata=metadata,
    )


# =============================================================================
# Common Event Processing Helpers
# =============================================================================


def _extract_tool_use_blocks(
    message_content: list[Any],
    timestamp: datetime,
) -> list[tuple[ContentToolUse, datetime, bool, TaskAgentInfo | None]]:
    """Extract and parse tool_use blocks from an assistant message.

    Args:
        message_content: The content list from an assistant message
        timestamp: Timestamp of the assistant event

    Returns:
        List of tuples: (tool_use_block, timestamp, is_task, agent_info)
    """
    from .models import parse_content_block

    result = []
    for block in message_content:
        if not isinstance(block, dict):
            continue

        if block.get("type") == "tool_use":
            parsed_block = parse_content_block(block)
            if not isinstance(parsed_block, ContentToolUse):
                continue

            is_task = is_task_tool_call(parsed_block)
            agent_info = get_task_agent_info(parsed_block) if is_task else None
            result.append((parsed_block, timestamp, is_task, agent_info))

    return result


def _accumulate_user_messages(
    event: UserEvent,
    accumulated_messages: list[Any],
) -> None:
    """Extract and accumulate messages from a user event.

    Args:
        event: The user event to process
        accumulated_messages: List to append messages to (modified in place)
    """
    user_msg = extract_user_message(event)
    if user_msg:
        accumulated_messages.append(user_msg)

    tool_msgs = extract_tool_result_messages(event)
    accumulated_messages.extend(tool_msgs)


# =============================================================================
# Event Processing Core
# =============================================================================


@dataclass
class _PendingTool:
    """Tracks a pending tool call awaiting its result.

    In streaming mode, also buffers subagent events that arrive between
    the tool_use block and the tool_result.
    """

    tool_use_block: ContentToolUse
    timestamp: datetime
    is_task: bool
    agent_info: TaskAgentInfo | None
    buffered_subagent_events: list[dict[str, Any]] = field(default_factory=list)


class _EventProcessor:
    """Shared event-processing logic for both batch and streaming modes.

    Tracks accumulated input messages and pending tool calls. Both
    ``process_parsed_events()`` and ``claude_code_events()`` delegate
    their core assistant/user/system event handling here.
    """

    def __init__(
        self,
        project_dir: Path | None,
        max_depth: int,
        session_file: Path | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.max_depth = max_depth
        self.session_file = session_file

        self.accumulated_messages: list[Any] = []
        self.pending_tools: dict[str, _PendingTool] = {}
        self.last_timestamp: datetime = _EPOCH

    async def process_assistant(
        self,
        event: AssistantEvent,
        timestamp: datetime,
    ) -> list[Event]:
        """Process an assistant event and return Scout events.

        Yields a ModelEvent and tracks any tool_use blocks for later matching.
        """
        model_event = to_model_event(
            event, self.accumulated_messages, timestamp=timestamp
        )
        result: list[Event] = [model_event]

        # Add assistant message to accumulated
        if model_event.output and model_event.output.message:
            self.accumulated_messages.append(model_event.output.message)

        # Extract and track tool_use blocks
        for tool_info in _extract_tool_use_blocks(event.message.content, timestamp):
            tool_use_block, ts, is_task, agent_info = tool_info
            self.pending_tools[tool_use_block.id] = _PendingTool(
                tool_use_block=tool_use_block,
                timestamp=ts,
                is_task=is_task,
                agent_info=agent_info,
            )

        return result

    async def process_user(
        self,
        event: UserEvent,
        timestamp: datetime,
        *,
        subagent_events_for_tool: (
            dict[str, dict[str, list[dict[str, Any]]]] | None
        ) = None,
    ) -> list[Event]:
        """Process a user event and return Scout events.

        Matches tool results to pending tool calls and yields completed
        tool spans. ``subagent_events_for_tool`` is an optional mapping
        from tool_use_id to grouped subagent events (used in streaming mode).
        """
        result: list[Event] = []
        content = event.message.content

        # Check for skill commands
        skill_name = is_skill_command(event)
        if skill_name:
            result.append(
                to_info_event(
                    source="skill_command",
                    data={"skill": skill_name},
                    timestamp=timestamp,
                )
            )

        # Extract agentId from toolUseResult if available
        event_agent_id: str | None = None
        if isinstance(event.toolUseResult, ToolUseResult):
            event_agent_id = event.toolUseResult.agentId

        # Process tool results
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_use_id = str(block.get("tool_use_id", ""))

                    if tool_use_id in self.pending_tools:
                        pending = self.pending_tools.pop(tool_use_id)

                        # Get subagent events (streaming mode buffers these)
                        subagent_dict: dict[str, list[dict[str, Any]]] | None = None
                        if subagent_events_for_tool:
                            subagent_dict = subagent_events_for_tool.get(tool_use_id)
                        elif pending.buffered_subagent_events:
                            subagent_dict = {}
                            for evt in pending.buffered_subagent_events:
                                sid = evt.get("sessionId", "")
                                subagent_dict.setdefault(sid, []).append(evt)

                        span_events = await _create_tool_span_events(
                            tool_use_block=pending.tool_use_block,
                            tool_result=block,
                            tool_timestamp=pending.timestamp,
                            result_timestamp=timestamp,
                            is_task=pending.is_task,
                            agent_info=pending.agent_info,
                            project_dir=self.project_dir,
                            subagent_events=subagent_dict,
                            max_depth=self.max_depth,
                            session_file=self.session_file,
                            agent_id=event_agent_id,
                        )
                        result.extend(span_events)

        # Accumulate user and tool result messages
        _accumulate_user_messages(event, self.accumulated_messages)

        return result

    async def process_system(
        self,
        event: SystemEvent,
        timestamp: datetime,
    ) -> list[Event]:
        """Process a system event and return Scout events."""
        result: list[Event] = []
        if is_compact_boundary(event):
            compaction_info = extract_compaction_info(event)
            if compaction_info:
                result.append(
                    CompactionEvent(
                        source="claude_code",
                        tokens_before=compaction_info.pop("preTokens", None),
                        metadata=compaction_info,
                        timestamp=timestamp,
                    )
                )
        return result

    async def flush_pending(self) -> list[Event]:
        """Yield events for any tool calls that never received a result."""
        result: list[Event] = []
        for pending in self.pending_tools.values():
            span_events = await _create_tool_span_events(
                tool_use_block=pending.tool_use_block,
                tool_result=None,
                tool_timestamp=pending.timestamp,
                result_timestamp=pending.timestamp,
                is_task=pending.is_task,
                agent_info=pending.agent_info,
                project_dir=None,  # Don't load agents for incomplete tools
                subagent_events=None,
                max_depth=0,
            )
            result.extend(span_events)
        return result

    def update_timestamp(self, event: BaseEvent) -> datetime:
        """Parse and track the latest timestamp."""
        timestamp = _parse_timestamp(get_timestamp(event)) or self.last_timestamp
        self.last_timestamp = timestamp
        return timestamp


# =============================================================================
# Public Entry Points
# =============================================================================


async def _to_async_iter(items: Iterable[T]) -> AsyncIterator[T]:
    """Convert a sync iterable to an async iterator."""
    for item in items:
        yield item


async def claude_code_events(
    raw_events: Iterable[dict[str, Any]] | AsyncIterable[dict[str, Any]],
    project_dir: Path | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
) -> AsyncIterator[Event]:
    """Convert raw Claude Code JSONL events to Inspect AI events.

    Processes events incrementally — yields Inspect AI events as soon as
    possible rather than buffering all input first. This enables real-time
    streaming from stdout in headless mode.

    Handles subagent event inlining: uses the ``isSidechain`` flag on each
    raw event to distinguish main-session events from subagent events.
    Subagent sessions are matched to parent Task tool calls via a FIFO queue:
    new Task tool_use blocks are enqueued in order, and each new subagent
    sessionId pops the next unmatched Task tool. If subagent events arrive
    before their Task tool_use block is processed, they are buffered and
    drained once the corresponding Task tool is registered.

    Args:
        raw_events: Iterable or AsyncIterable of raw event dictionaries.
        project_dir: Path to project directory for loading nested agent files.
        max_depth: Maximum depth for loading nested subagent events (0 = no loading)
        session_file: Path to the session JSONL file (for locating subagent files)

    Yields:
        Inspect AI Event objects (ModelEvent, ToolEvent, SpanBeginEvent, etc.)
    """
    from .models import parse_event

    # Convert sync iterable to async if needed
    if isinstance(raw_events, AsyncIterable):
        event_stream = raw_events
    else:
        event_stream = _to_async_iter(raw_events)

    proc = _EventProcessor(project_dir, max_depth, session_file)

    # Streaming-specific state for session routing
    session_to_tool: dict[str, str] = {}
    unmatched_task_tools: list[str] = []  # FIFO queue
    unmatched_subagent_events: dict[str, list[dict[str, Any]]] = {}

    async for raw_event in event_stream:
        # Route subagent events by isSidechain flag
        if raw_event.get("isSidechain", False):
            session_id = raw_event.get("sessionId", "")

            if session_id not in session_to_tool:
                if unmatched_task_tools:
                    session_to_tool[session_id] = unmatched_task_tools.pop(0)
                else:
                    # Task tool_use hasn't been seen yet — buffer for later
                    unmatched_subagent_events.setdefault(session_id, []).append(
                        raw_event
                    )
                    continue

            pending_tool_id = session_to_tool[session_id]
            if pending_tool_id in proc.pending_tools:
                proc.pending_tools[pending_tool_id].buffered_subagent_events.append(
                    raw_event
                )
            continue

        # Skip non-conversation events
        event_type = raw_event.get("type")
        if event_type not in ("user", "assistant"):
            continue

        # Parse to Pydantic model
        try:
            pydantic_event = parse_event(raw_event)
        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            continue
        if pydantic_event is None:
            continue

        timestamp = proc.update_timestamp(pydantic_event)

        if isinstance(pydantic_event, AssistantEvent):
            pending_before = set(proc.pending_tools.keys())
            for evt in await proc.process_assistant(pydantic_event, timestamp):
                yield evt

            # Enqueue newly registered Task tools (FIFO order)
            new_task_ids = [
                tid
                for tid in proc.pending_tools
                if tid not in pending_before and proc.pending_tools[tid].is_task
            ]
            unmatched_task_tools.extend(new_task_ids)

            # Drain early-arrival buffer for subagent sessions
            for sid in list(unmatched_subagent_events):
                if not unmatched_task_tools:
                    break
                tool_id = unmatched_task_tools.pop(0)
                session_to_tool[sid] = tool_id
                proc.pending_tools[tool_id].buffered_subagent_events.extend(
                    unmatched_subagent_events.pop(sid)
                )

        elif isinstance(pydantic_event, UserEvent):
            for evt in await proc.process_user(pydantic_event, timestamp):
                yield evt

    # Flush pending tool calls
    for evt in await proc.flush_pending():
        yield evt


async def process_parsed_events(
    events: Sequence[BaseEvent],
    project_dir: Path | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
) -> AsyncIterator[Event]:
    """Convert parsed Claude Code events to Scout events.

    This is the core conversion function for already-parsed Pydantic models.
    Use this when you have pre-validated events (e.g., from transcript processing).

    For raw dict streams (e.g., from stdout), use claude_code_events() instead.

    Args:
        events: Chronologically ordered Claude Code events (Pydantic models)
        project_dir: Path to project directory (for loading agent files)
        max_depth: Maximum depth for loading nested subagent events (0 = no loading)
        session_file: Path to the session JSONL file (for locating subagent files)

    Yields:
        Scout Event objects (ModelEvent, ToolEvent, SpanBeginEvent, etc.)
    """
    proc = _EventProcessor(project_dir, max_depth, session_file)

    for event in events:
        timestamp = proc.update_timestamp(event)

        if isinstance(event, AssistantEvent):
            for evt in await proc.process_assistant(event, timestamp):
                yield evt

        elif isinstance(event, UserEvent):
            for evt in await proc.process_user(event, timestamp):
                yield evt

        elif isinstance(event, SystemEvent):
            for evt in await proc.process_system(event, timestamp):
                yield evt

    # Flush pending tool calls
    for evt in await proc.flush_pending():
        yield evt


async def _create_tool_span_events(
    tool_use_block: ContentToolUse,
    tool_result: dict[str, Any] | None,
    tool_timestamp: datetime,
    result_timestamp: datetime,
    is_task: bool,
    agent_info: TaskAgentInfo | None,
    project_dir: Path | None,
    subagent_events: dict[str, list[dict[str, Any]]] | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
    agent_id: str | None = None,
) -> list[Event]:
    """Create the complete span structure for a tool call.

    Follows Inspect's pattern where ToolEvent is inside the span:

    Regular tools:
      SpanBeginEvent(type="tool", name="Bash")
        ToolEvent(function="Bash", ...)
      SpanEndEvent

    Task tools (agent spawns):
      SpanBeginEvent(type="tool", name="Task")
        ToolEvent(function="Task", ...)
        SpanBeginEvent(type="agent", name="Explore")
          InfoEvent (task description)
          [nested agent events...]
        SpanEndEvent  # agent span
      SpanEndEvent  # tool span

    Args:
        tool_use_block: The tool_use content block
        tool_result: The tool_result content block (may be None)
        tool_timestamp: When the tool was called
        result_timestamp: When the result was received
        is_task: Whether this is a Task tool call (agent spawn)
        agent_info: Agent info if is_task is True
        project_dir: Project directory for loading agent files
        subagent_events: Pre-grouped subagent events by sessionId (streaming mode)
        max_depth: Maximum depth for loading nested subagent events (0 = no loading)
        session_file: Path to the session JSONL file (for locating subagent files)
        agent_id: Pre-extracted agent ID (e.g., from toolUseResult.agentId)

    Returns:
        List of events in correct order
    """
    events: list[Event] = []
    tool_id = tool_use_block.id

    # For Task tools with agent info, emit just the agent span (no tool wrapper)
    if is_task and agent_info:
        agent_span_id = f"agent-{tool_id}"
        agent_name = agent_info.subagent_type

        # SpanBeginEvent for agent (directly under parent, no tool wrapper)
        events.append(
            to_span_begin_event(
                span_id=agent_span_id,
                name=agent_name or "agent",
                span_type="agent",
                timestamp=tool_timestamp,
                metadata={
                    "description": agent_info.description,
                },
            )
        )

        # ToolEvent inside the agent span (for metadata/audit)
        tool_event = to_tool_event(
            tool_use_block,
            tool_result,
            tool_timestamp,
            completed=result_timestamp,
        )
        tool_event.span_id = agent_span_id
        events.append(tool_event)

        # InfoEvent with task description
        if agent_info.description:
            info_event = to_info_event(
                source="agent_task",
                data=agent_info.description,
                timestamp=tool_timestamp,
            )
            info_event.span_id = agent_span_id
            events.append(info_event)

        # Load and process nested agent events
        if tool_result:
            agent_events = await _load_agent_events(
                project_dir,
                tool_result,
                subagent_events,
                max_depth=max_depth,
                session_file=session_file,
                agent_id=agent_id,
            )
            # Re-parent top-level items so event_tree() nests them
            # under the agent span
            for evt in agent_events:
                if isinstance(evt, SpanBeginEvent):
                    if evt.parent_id is None:
                        evt.parent_id = agent_span_id
                elif not isinstance(evt, SpanEndEvent):
                    if evt.span_id is None:
                        evt.span_id = agent_span_id
            events.extend(agent_events)

        # SpanEndEvent for agent
        events.append(to_span_end_event(agent_span_id, result_timestamp))
    else:
        # Regular tool: wrap in tool span
        tool_span_id = f"tool-{tool_id}"

        events.append(
            to_span_begin_event(
                span_id=tool_span_id,
                name=tool_use_block.name,
                span_type="tool",
                timestamp=tool_timestamp,
            )
        )

        tool_event = to_tool_event(
            tool_use_block,
            tool_result,
            tool_timestamp,
            completed=result_timestamp,
        )
        events.append(tool_event)

        events.append(to_span_end_event(tool_span_id, result_timestamp))

    return events


def _extract_agent_id_from_result(tool_result: dict[str, Any]) -> str | None:
    """Extract agent ID from a Task tool result using JSON parsing.

    Args:
        tool_result: The tool_result block containing agent response

    Returns:
        The agent ID if found, None otherwise
    """
    import json

    content = tool_result.get("content", [])

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text", ""))
                # Try to parse as JSON first (more robust)
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "agentId" in parsed:
                        return str(parsed["agentId"])
                except json.JSONDecodeError:
                    logger.debug("Failed to parse tool result as JSON, trying regex")
                # Fallback: regex for partial JSON or embedded JSON
                match = re.search(r'"agentId"\s*:\s*"([^"]+)"', text)
                if match:
                    return match.group(1)
                # Plain-text format from Claude Code output:
                #   "agentId: aa9e523 (for resuming...)"
                match = re.search(r"agentId:\s*([a-f0-9]+)", text)
                if match:
                    return match.group(1)

    logger.debug("Could not extract agentId from tool result")
    return None


async def _load_agent_events(
    project_dir: Path | None,
    tool_result: dict[str, Any],
    subagent_events: dict[str, list[dict[str, Any]]] | None = None,
    max_depth: int = 5,
    session_file: Path | None = None,
    agent_id: str | None = None,
) -> list[Event]:
    """Load and process events from an agent session file or stream.

    Args:
        project_dir: Path to project directory (for file-based loading)
        tool_result: The tool_result block that completed the agent
        subagent_events: Pre-grouped subagent events by sessionId (streaming mode).
            Note: In streaming mode, events are keyed by sessionId (not agentId).
        max_depth: Maximum remaining depth for loading nested subagents (0 = no loading)
        session_file: Path to the parent session JSONL file (for locating subagent files)
        agent_id: Pre-extracted agent ID (e.g., from toolUseResult.agentId)

    Returns:
        List of Scout events from the agent session
    """
    from .client import find_agent_file, read_jsonl_events

    # Try to extract agent ID from the tool result content, fall back to provided
    agent_id = _extract_agent_id_from_result(tool_result) or agent_id

    raw_events: list[dict[str, Any]] | None = None
    agent_file: Path | None = None

    # Try stream-provided events first
    # Note: subagent_events is keyed by sessionId, not agentId
    # In streaming mode, we collect all buffered events for this tool since
    # they all belong to this agent (one subagent session per Task tool)
    if subagent_events:
        # Flatten all events from all sessions - they all belong to this agent
        all_events = []
        for session_events in subagent_events.values():
            all_events.extend(session_events)
        if all_events:
            raw_events = all_events

    # Fall back to file loading if we have an agent_id and project_dir
    if not raw_events and agent_id and project_dir:
        agent_file = find_agent_file(project_dir, agent_id, session_file=session_file)
        if not agent_file:
            logger.debug(f"Agent file not found for ID: {agent_id}")
            return []
        raw_events = read_jsonl_events(agent_file)

    if not raw_events:
        return []

    # Parse to Pydantic models
    agent_events = parse_events(raw_events)

    # Build tree and flatten
    tree = build_event_tree(agent_events)
    flat_events = flatten_tree_chronological(tree)

    # Filter to conversation events
    conversation_events = get_conversation_events(flat_events)

    # Convert to Scout events, with bounded recursion for nested subagents
    next_depth = max_depth - 1
    next_project_dir = project_dir if next_depth > 0 else None
    # The loaded agent file becomes the session_file for further nesting
    next_session_file = agent_file if next_depth > 0 else None
    result: list[Event] = []
    async for event in process_parsed_events(
        conversation_events,
        project_dir=next_project_dir,
        max_depth=next_depth,
        session_file=next_session_file,
    ):
        result.append(event)
    return result
