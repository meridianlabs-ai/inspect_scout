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
from datetime import datetime
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
    get_event_type,
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
    UserEvent,
    parse_events,
)
from .tree import build_event_tree, flatten_tree_chronological, get_conversation_events

logger = getLogger(__name__)

T = TypeVar("T")


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse an ISO timestamp string to datetime.

    Args:
        ts_str: ISO format timestamp string (with optional 'Z' suffix)

    Returns:
        Parsed datetime, or None if parsing fails or input is empty
    """
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def to_model_event(
    event: AssistantEvent,
    input_messages: list[Any],
) -> ModelEvent:
    """Convert a Claude Code assistant event to ModelEvent.

    Args:
        event: Claude Code assistant event
        input_messages: The input messages for this model call

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
        timestamp=_parse_timestamp(get_timestamp(event)) or datetime.now(),
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
) -> list[tuple[ContentToolUse, datetime, bool, dict[str, Any] | None]]:
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
# Streaming Event Processing
# =============================================================================


@dataclass
class PendingTool:
    """Tracks a pending tool call with optional subagent event buffering.

    Used by claude_code_events() for streaming mode where subagent events
    need to be buffered until the parent Task completes.
    """

    tool_use_block: ContentToolUse
    timestamp: datetime
    is_task: bool
    agent_info: dict[str, Any] | None
    buffered_subagent_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProcessingState:
    """State for streaming event processing in claude_code_events()."""

    main_session_id: str | None = None
    accumulated_messages: list[Any] = field(default_factory=list)
    pending_tools: dict[str, PendingTool] = field(default_factory=dict)
    session_to_tool: dict[str, str] = field(default_factory=dict)


async def _to_async_iter(items: Iterable[T]) -> AsyncIterator[T]:
    """Convert a sync iterable to an async iterator."""
    for item in items:
        yield item


async def claude_code_events(
    raw_events: Iterable[dict[str, Any]] | AsyncIterable[dict[str, Any]],
    project_dir: Path | None = None,
) -> AsyncIterator[Event]:
    """Convert raw Claude Code JSONL events to Inspect AI events.

    Processes events incrementally - yields Inspect AI events as soon as
    possible rather than buffering all input first. This enables real-time
    streaming from stdout in headless mode.

    Handles:
    - Parsing raw dicts to Pydantic models (validation)
    - Filtering to conversation events (user/assistant)
    - Converting to Inspect AI event types incrementally
    - Subagent event inlining (buffers by sessionId, yields when Task completes)

    Does NOT handle:
    - File discovery
    - /clear command splitting (yields continuous event stream)
    - Transcript creation
    - Complex tree building (assumes events arrive in chronological order)

    Ordering Assumption:
        Subagent events must arrive AFTER the parent Task tool_use block has
        been processed. Events with non-main sessionIds that arrive before any
        Task tool_use block will be silently dropped. This assumption holds for
        Claude Code's normal operation where the assistant message containing
        the Task tool_use is logged before the subagent begins execution.

    Args:
        raw_events: Iterable or AsyncIterable of raw event dictionaries.
            Accepts both sync sequences (list, generator) and async streams.
            May include subagent events with different sessionIds.
        project_dir: Path to project directory for loading nested agent files.
            If None, relies on subagent events being in the raw_events stream.

    Yields:
        Inspect AI Event objects (ModelEvent, ToolEvent, SpanBeginEvent, etc.)
        as they become available.
    """
    from .models import parse_event

    # Convert sync iterable to async if needed
    if isinstance(raw_events, AsyncIterable):
        event_stream = raw_events
    else:
        event_stream = _to_async_iter(raw_events)

    state = ProcessingState()

    async for raw_event in event_stream:
        session_id = raw_event.get("sessionId", "")

        # First event determines main session
        if state.main_session_id is None:
            state.main_session_id = session_id

        # Is this a subagent event? Buffer it for later
        if session_id != state.main_session_id:
            # Associate with pending Task tool if not already
            if session_id not in state.session_to_tool:
                # Find pending Task without assigned subagent
                for tool_id, tool in state.pending_tools.items():
                    if tool.is_task:
                        state.session_to_tool[session_id] = tool_id
                        break

            pending_tool_id = state.session_to_tool.get(session_id)
            if pending_tool_id and pending_tool_id in state.pending_tools:
                state.pending_tools[pending_tool_id].buffered_subagent_events.append(
                    raw_event
                )
            else:
                # Subagent event arrived before Task tool_use - see Ordering Assumption
                logger.debug(
                    f"Dropping subagent event for session {session_id}: "
                    "no pending Task tool found"
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

        timestamp = _parse_timestamp(get_timestamp(pydantic_event)) or datetime.now()

        if isinstance(pydantic_event, AssistantEvent):
            # Yield ModelEvent immediately
            model_event = to_model_event(pydantic_event, state.accumulated_messages)
            yield model_event

            # Add assistant message to accumulated
            if model_event.output and model_event.output.message:
                state.accumulated_messages.append(model_event.output.message)

            # Extract and track tool_use blocks (with subagent buffering support)
            for tool_info in _extract_tool_use_blocks(
                pydantic_event.message.content, timestamp
            ):
                tool_use_block, ts, is_task, agent_info = tool_info
                state.pending_tools[tool_use_block.id] = PendingTool(
                    tool_use_block=tool_use_block,
                    timestamp=ts,
                    is_task=is_task,
                    agent_info=agent_info,
                )

        elif isinstance(pydantic_event, UserEvent):
            content = pydantic_event.message.content

            # Check for skill commands
            skill_name = is_skill_command(pydantic_event)
            if skill_name:
                yield to_info_event(
                    source="skill_command",
                    data={"skill": skill_name},
                    timestamp=timestamp,
                )

            # Process tool results - yield complete spans
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_use_id = str(block.get("tool_use_id", ""))

                        if tool_use_id in state.pending_tools:
                            pending = state.pending_tools.pop(tool_use_id)

                            # Build subagent_events dict from buffered events
                            subagent_events_dict: (
                                dict[str, list[dict[str, Any]]] | None
                            ) = None
                            if pending.buffered_subagent_events:
                                subagent_events_dict = {}
                                for evt in pending.buffered_subagent_events:
                                    sid = evt.get("sessionId", "")
                                    subagent_events_dict.setdefault(sid, []).append(evt)

                            # Yield complete tool span
                            span_events = await _create_tool_span_events(
                                tool_use_block=pending.tool_use_block,
                                tool_result=block,
                                tool_timestamp=pending.timestamp,
                                result_timestamp=timestamp,
                                is_task=pending.is_task,
                                agent_info=pending.agent_info,
                                project_dir=project_dir,
                                subagent_events=subagent_events_dict,
                            )
                            for span_evt in span_events:
                                yield span_evt

            # Accumulate user and tool result messages
            _accumulate_user_messages(pydantic_event, state.accumulated_messages)

    # Handle any remaining pending tool calls without results
    for pending in state.pending_tools.values():
        remaining_events = await _create_tool_span_events(
            tool_use_block=pending.tool_use_block,
            tool_result=None,
            tool_timestamp=pending.timestamp,
            result_timestamp=datetime.now(),
            is_task=pending.is_task,
            agent_info=pending.agent_info,
            project_dir=None,  # Don't load agents for incomplete tools
            subagent_events=None,
        )
        for remaining_evt in remaining_events:
            yield remaining_evt


async def process_parsed_events(
    events: Sequence[BaseEvent],
    project_dir: Path | None = None,
) -> AsyncIterator[Event]:
    """Convert parsed Claude Code events to Scout events.

    This is the core conversion function for already-parsed Pydantic models.
    Use this when you have pre-validated events (e.g., from transcript processing).

    For raw dict streams (e.g., from stdout), use claude_code_events() instead.

    Args:
        events: Chronologically ordered Claude Code events (Pydantic models)
        project_dir: Path to project directory (for loading agent files)

    Yields:
        Scout Event objects (ModelEvent, ToolEvent, SpanBeginEvent, etc.)
    """
    # Track pending tool calls to match with results
    # Format: tool_id -> (tool_use_block, timestamp, is_task, agent_info)
    pending_tool_calls: dict[
        str, tuple[ContentToolUse, datetime, bool, dict[str, Any] | None]
    ] = {}

    # Track messages for ModelEvent input
    accumulated_messages: list[Any] = []

    for event in events:
        event_type = get_event_type(event)
        timestamp = _parse_timestamp(get_timestamp(event)) or datetime.now()

        if isinstance(event, AssistantEvent):
            # Yield ModelEvent
            model_event = to_model_event(event, accumulated_messages)
            yield model_event

            # Add assistant message to accumulated
            if model_event.output and model_event.output.message:
                accumulated_messages.append(model_event.output.message)

            # Extract and track tool_use blocks
            for tool_info in _extract_tool_use_blocks(event.message.content, timestamp):
                tool_use_block = tool_info[0]
                pending_tool_calls[tool_use_block.id] = tool_info

        elif isinstance(event, UserEvent):
            content = event.message.content

            # Check for skill commands
            skill_name = is_skill_command(event)
            if skill_name:
                yield to_info_event(
                    source="skill_command",
                    data={"skill": skill_name},
                    timestamp=timestamp,
                )

            # Process tool results
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_use_id = str(block.get("tool_use_id", ""))

                        if tool_use_id in pending_tool_calls:
                            tool_use_block, tool_timestamp, is_task, agent_info = (
                                pending_tool_calls.pop(tool_use_id)
                            )

                            tool_events = await _create_tool_span_events(
                                tool_use_block=tool_use_block,
                                tool_result=block,
                                tool_timestamp=tool_timestamp,
                                result_timestamp=timestamp,
                                is_task=is_task,
                                agent_info=agent_info,
                                project_dir=project_dir,
                            )
                            for tool_evt in tool_events:
                                yield tool_evt

            # Accumulate user and tool result messages
            _accumulate_user_messages(event, accumulated_messages)

        elif event_type == "system":
            # Handle compaction boundaries
            if is_compact_boundary(event):
                compaction_info = extract_compaction_info(event)
                if compaction_info:
                    yield CompactionEvent(
                        source="claude_code",
                        tokens_before=compaction_info.pop("preTokens", None),
                        metadata=compaction_info,
                        timestamp=timestamp,
                    )

    # Handle any remaining tool calls without results
    for (
        tool_use_block,
        tool_timestamp,
        is_task,
        agent_info,
    ) in pending_tool_calls.values():
        tool_events = await _create_tool_span_events(
            tool_use_block=tool_use_block,
            tool_result=None,
            tool_timestamp=tool_timestamp,
            result_timestamp=datetime.now(),
            is_task=is_task,
            agent_info=agent_info,
            project_dir=None,
        )
        for tool_evt in tool_events:
            yield tool_evt


async def _create_tool_span_events(
    tool_use_block: ContentToolUse,
    tool_result: dict[str, Any] | None,
    tool_timestamp: datetime,
    result_timestamp: datetime,
    is_task: bool,
    agent_info: dict[str, Any] | None,
    project_dir: Path | None,
    subagent_events: dict[str, list[dict[str, Any]]] | None = None,
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

    Returns:
        List of events in correct order
    """
    events: list[Event] = []
    tool_id = tool_use_block.id
    tool_span_id = f"tool-{tool_id}"

    # 1. SpanBeginEvent for tool
    events.append(
        to_span_begin_event(
            span_id=tool_span_id,
            name=tool_use_block.name,
            span_type="tool",
            timestamp=tool_timestamp,
        )
    )

    # 2. ToolEvent (inside the span)
    tool_event = to_tool_event(
        tool_use_block,
        tool_result,
        tool_timestamp,
        completed=result_timestamp,
    )
    events.append(tool_event)

    # 3. For Task tools, create nested agent span
    if is_task and agent_info:
        agent_span_id = f"agent-{tool_id}"
        agent_name = agent_info.get("subagent_type", "agent")

        # SpanBeginEvent for agent
        events.append(
            to_span_begin_event(
                span_id=agent_span_id,
                name=agent_name or "agent",
                span_type="agent",
                timestamp=tool_timestamp,
                parent_id=tool_span_id,
                metadata={
                    "description": agent_info.get("description", ""),
                },
            )
        )

        # InfoEvent with task description
        if agent_info.get("description"):
            events.append(
                to_info_event(
                    source="agent_task",
                    data=agent_info.get("description"),
                    timestamp=tool_timestamp,
                )
            )

        # Load and process nested agent events
        if tool_result:
            agent_events = await _load_agent_events(
                project_dir, tool_result, subagent_events
            )
            events.extend(agent_events)

        # SpanEndEvent for agent
        events.append(to_span_end_event(agent_span_id, result_timestamp))

    # 4. SpanEndEvent for tool
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

    logger.debug("Could not extract agentId from tool result")
    return None


async def _load_agent_events(
    project_dir: Path | None,
    tool_result: dict[str, Any],
    subagent_events: dict[str, list[dict[str, Any]]] | None = None,
) -> list[Event]:
    """Load and process events from an agent session file or stream.

    Args:
        project_dir: Path to project directory (for file-based loading)
        tool_result: The tool_result block that completed the agent
        subagent_events: Pre-grouped subagent events by sessionId (streaming mode).
            Note: In streaming mode, events are keyed by sessionId (not agentId).

    Returns:
        List of Scout events from the agent session
    """
    from .client import find_agent_file, read_jsonl_events

    # Try to extract agent ID from the tool result content
    agent_id = _extract_agent_id_from_result(tool_result)

    raw_events: list[dict[str, Any]] | None = None

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
        agent_file = find_agent_file(project_dir, agent_id)
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

    # Convert to Scout events (recursive, but without loading nested agents to avoid loops)
    result: list[Event] = []
    async for event in process_parsed_events(conversation_events, project_dir=None):
        result.append(event)
    return result
