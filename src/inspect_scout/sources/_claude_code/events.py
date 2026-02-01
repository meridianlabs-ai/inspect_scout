"""Event conversion for Claude Code sessions.

Converts Claude Code events to Scout event types:
- Assistant events -> ModelEvent
- Tool use -> ToolEvent
- Task tool calls -> SpanBeginEvent + SpanEndEvent (agent spans)
- System events -> InfoEvent
"""

import re
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any, Literal, TypeVar

from inspect_ai.event import (
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


def _parse_timestamp(ts_str: str | None) -> datetime:
    """Parse an ISO timestamp string to datetime."""
    if not ts_str:
        return datetime.min
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


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
        timestamp=_parse_timestamp(get_timestamp(event)),
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
# Streaming Event Processing
# =============================================================================


@dataclass
class PendingTool:
    """Tracks a pending tool call being buffered."""

    tool_id: str
    tool_use_block: ContentToolUse
    timestamp: datetime
    is_task: bool
    agent_info: dict[str, Any] | None
    buffered_subagent_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProcessingState:
    """State for incremental event processing."""

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
    from .models import parse_content_block, parse_event

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

        timestamp = _parse_timestamp(get_timestamp(pydantic_event))

        if isinstance(pydantic_event, AssistantEvent):
            # Yield ModelEvent immediately
            model_event = to_model_event(pydantic_event, state.accumulated_messages)
            yield model_event

            # Add assistant message to accumulated
            if model_event.output and model_event.output.message:
                state.accumulated_messages.append(model_event.output.message)

            # Track tool_use blocks (start buffering)
            message_content = pydantic_event.message.content
            for block in message_content:
                if not isinstance(block, dict):
                    continue

                if block.get("type") == "tool_use":
                    parsed_block = parse_content_block(block)
                    if not isinstance(parsed_block, ContentToolUse):
                        continue

                    is_task = is_task_tool_call(parsed_block)
                    agent_info = get_task_agent_info(parsed_block) if is_task else None

                    state.pending_tools[parsed_block.id] = PendingTool(
                        tool_id=parsed_block.id,
                        tool_use_block=parsed_block,
                        timestamp=timestamp,
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
                            span_events = _create_tool_span_events(
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

            # Extract user message for accumulation
            user_msg = extract_user_message(pydantic_event)
            if user_msg:
                state.accumulated_messages.append(user_msg)

            # Extract tool result messages for accumulation
            tool_msgs = extract_tool_result_messages(pydantic_event)
            state.accumulated_messages.extend(tool_msgs)

    # Handle any remaining pending tool calls without results
    for pending in state.pending_tools.values():
        remaining_events = _create_tool_span_events(
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


def events_to_scout_events(
    events: list[BaseEvent],
    project_dir: Path | None = None,
) -> list[Event]:
    """Convert Claude Code events to Scout events.

    This is the main conversion function. It processes events in order,
    creating ModelEvent, ToolEvent, InfoEvent, and span events as needed.

    Event ordering follows Inspect's pattern where ToolEvent is recorded
    inside the tool span:
      SpanBeginEvent(type="tool", name="Bash")
        ToolEvent(function="Bash", ...)
      SpanEndEvent

    For Task tools (agent spawns):
      SpanBeginEvent(type="tool", name="Task")
        ToolEvent(function="Task", ...)
        SpanBeginEvent(type="agent", name="Explore")
          InfoEvent (task description)
          [nested agent events...]
        SpanEndEvent  # agent span
      SpanEndEvent  # tool span

    Args:
        events: Chronologically ordered Claude Code events (Pydantic models)
        project_dir: Path to project directory (for loading agent files)

    Returns:
        List of Scout Event objects
    """
    scout_events: list[Event] = []

    # Track pending tool calls to match with results
    # Maps tool_use_id -> (ContentToolUse, timestamp, is_task_tool, agent_info)
    pending_tool_calls: dict[
        str, tuple[ContentToolUse, datetime, bool, dict[str, Any] | None]
    ] = {}

    # Track messages for ModelEvent input
    accumulated_messages: list[Any] = []

    for event in events:
        event_type = get_event_type(event)
        timestamp = _parse_timestamp(get_timestamp(event))

        if isinstance(event, AssistantEvent):
            # Create ModelEvent
            model_event = to_model_event(event, accumulated_messages)
            scout_events.append(model_event)

            # Add assistant message to accumulated
            if model_event.output and model_event.output.message:
                accumulated_messages.append(model_event.output.message)

            # Process tool_use blocks - just track them, don't create spans yet
            message_content = event.message.content
            for block in message_content:
                if not isinstance(block, dict):
                    continue

                if block.get("type") == "tool_use":
                    # Parse to ContentToolUse
                    from .models import parse_content_block

                    parsed_block = parse_content_block(block)
                    if not isinstance(parsed_block, ContentToolUse):
                        continue

                    tool_id = parsed_block.id

                    # Check if this is a Task tool call (agent spawn)
                    is_task = is_task_tool_call(parsed_block)
                    agent_info = get_task_agent_info(parsed_block) if is_task else None

                    # Track for result matching - spans created at result time
                    pending_tool_calls[tool_id] = (
                        parsed_block,
                        timestamp,
                        is_task,
                        agent_info,
                    )

        elif isinstance(event, UserEvent):
            content = event.message.content

            # Check for skill commands
            skill_name = is_skill_command(event)
            if skill_name:
                scout_events.append(
                    to_info_event(
                        source="skill_command",
                        data={"skill": skill_name},
                        timestamp=timestamp,
                    )
                )

            # Process tool results
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_use_id = str(block.get("tool_use_id", ""))

                        # Match with pending tool call
                        if tool_use_id in pending_tool_calls:
                            tool_use_block, tool_timestamp, is_task, agent_info = (
                                pending_tool_calls.pop(tool_use_id)
                            )

                            # Create span structure with ToolEvent inside
                            # All events emitted at tool_result time when we have
                            # the complete picture
                            tool_events = _create_tool_span_events(
                                tool_use_block=tool_use_block,
                                tool_result=block,
                                tool_timestamp=tool_timestamp,
                                result_timestamp=timestamp,
                                is_task=is_task,
                                agent_info=agent_info,
                                project_dir=project_dir,
                            )
                            scout_events.extend(tool_events)

            # Extract user message for accumulation
            user_msg = extract_user_message(event)
            if user_msg:
                accumulated_messages.append(user_msg)

            # Extract tool result messages for accumulation
            tool_msgs = extract_tool_result_messages(event)
            accumulated_messages.extend(tool_msgs)

        elif event_type == "system":
            # Handle compaction boundaries
            if is_compact_boundary(event):
                compaction_info = extract_compaction_info(event)
                if compaction_info:
                    scout_events.append(
                        to_info_event(
                            source="compaction",
                            data=compaction_info,
                            timestamp=timestamp,
                        )
                    )

    # Handle any remaining tool calls without results
    for _tool_id, (
        tool_use_block,
        tool_timestamp,
        is_task,
        agent_info,
    ) in pending_tool_calls.items():
        # Create span structure even without result
        tool_events = _create_tool_span_events(
            tool_use_block=tool_use_block,
            tool_result=None,
            tool_timestamp=tool_timestamp,
            result_timestamp=datetime.now(),
            is_task=is_task,
            agent_info=agent_info,
            project_dir=None,  # Don't load agents for incomplete tools
        )
        scout_events.extend(tool_events)

    # Sort by timestamp
    scout_events.sort(key=lambda e: e.timestamp or datetime.min)

    return scout_events


def _create_tool_span_events(
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
            agent_events = _load_agent_events(project_dir, tool_result, subagent_events)
            events.extend(agent_events)

        # SpanEndEvent for agent
        events.append(to_span_end_event(agent_span_id, result_timestamp))

    # 4. SpanEndEvent for tool
    events.append(to_span_end_event(tool_span_id, result_timestamp))

    return events


def _load_agent_events(
    project_dir: Path | None,
    tool_result: dict[str, Any],
    subagent_events: dict[str, list[dict[str, Any]]] | None = None,
) -> list[Event]:
    """Load and process events from an agent session file or stream.

    Args:
        project_dir: Path to project directory (for file-based loading)
        tool_result: The tool_result block that completed the agent
        subagent_events: Pre-grouped subagent events by sessionId (streaming mode)

    Returns:
        List of Scout events from the agent session
    """
    from .client import find_agent_file, read_jsonl_events

    # Try to extract agent ID from the tool result content
    content = tool_result.get("content", [])
    agent_id = None

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text", ""))
                # Look for agentId in the response
                match = re.search(r'"agentId"\s*:\s*"([^"]+)"', text)
                if match:
                    agent_id = match.group(1)
                    break

    if not agent_id:
        return []

    # Try stream-provided events first
    raw_events: list[dict[str, Any]] | None = None
    if subagent_events and agent_id in subagent_events:
        raw_events = subagent_events[agent_id]
    elif project_dir:
        # Fall back to file loading
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
    # For nested agents, we could pass project_dir=None or implement depth limiting
    return events_to_scout_events(conversation_events, project_dir=None)
