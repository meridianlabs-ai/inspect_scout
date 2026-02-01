"""Event conversion for Claude Code sessions.

Converts Claude Code events to Scout event types:
- Assistant events -> ModelEvent
- Tool use -> ToolEvent
- Task tool calls -> SpanBeginEvent + SpanEndEvent (agent spans)
- System events -> InfoEvent
"""

import re
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any, Literal

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


def events_to_scout_events(
    events: list[BaseEvent],
    project_dir: Path | None = None,
) -> list[Event]:
    """Convert Claude Code events to Scout events.

    This is the main conversion function. It processes events in order,
    creating ModelEvent, ToolEvent, InfoEvent, and span events as needed.

    Args:
        events: Chronologically ordered Claude Code events (Pydantic models)
        project_dir: Path to project directory (for loading agent files)

    Returns:
        List of Scout Event objects
    """
    scout_events: list[Event] = []

    # Track pending tool calls to match with results
    pending_tool_calls: dict[str, tuple[ContentToolUse, datetime]] = {}

    # Track messages for ModelEvent input
    accumulated_messages: list[Any] = []

    # Track active spans
    active_agent_spans: dict[str, str] = {}  # tool_use_id -> span_id (for Task tools)
    active_tool_spans: dict[str, str] = {}  # tool_use_id -> span_id (for regular tools)

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

            # Process tool_use blocks
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
                    if is_task_tool_call(parsed_block):
                        agent_info = get_task_agent_info(parsed_block)
                        if agent_info:
                            # Create agent span
                            span_id = f"agent-{tool_id}"
                            agent_name = agent_info.get("subagent_type", "agent")

                            scout_events.append(
                                to_span_begin_event(
                                    span_id=span_id,
                                    name=agent_name or "agent",
                                    span_type="agent",
                                    timestamp=timestamp,
                                    metadata={
                                        "description": agent_info.get(
                                            "description", ""
                                        ),
                                    },
                                )
                            )

                            # Create info event with task description
                            if agent_info.get("description"):
                                scout_events.append(
                                    to_info_event(
                                        source="agent_task",
                                        data=agent_info.get("description"),
                                        timestamp=timestamp,
                                    )
                                )

                            active_agent_spans[tool_id] = span_id
                    else:
                        # Regular tool call - create tool span
                        span_id = f"tool-{tool_id}"
                        scout_events.append(
                            to_span_begin_event(
                                span_id=span_id,
                                name=parsed_block.name,
                                span_type="tool",
                                timestamp=timestamp,
                            )
                        )
                        active_tool_spans[tool_id] = span_id

                    # Track all tool calls for result matching
                    pending_tool_calls[tool_id] = (parsed_block, timestamp)

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
                            tool_use_block, tool_timestamp = pending_tool_calls.pop(
                                tool_use_id
                            )

                            # Create ToolEvent
                            tool_event = to_tool_event(
                                tool_use_block,
                                block,
                                tool_timestamp,
                                completed=timestamp,
                            )
                            scout_events.append(tool_event)

                            # Check if this completes a tool span
                            if tool_use_id in active_tool_spans:
                                span_id = active_tool_spans.pop(tool_use_id)
                                scout_events.append(
                                    to_span_end_event(span_id, timestamp)
                                )

                            # Check if this completes an agent span
                            elif tool_use_id in active_agent_spans:
                                span_id = active_agent_spans.pop(tool_use_id)

                                # Try to load and process agent events
                                if project_dir:
                                    agent_events = _load_agent_events(
                                        project_dir, block, timestamp
                                    )
                                    scout_events.extend(agent_events)

                                # End the agent span
                                scout_events.append(
                                    to_span_end_event(span_id, timestamp)
                                )

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

    # Close any remaining tool calls without results
    for tool_id, (tool_use_block, tool_timestamp) in pending_tool_calls.items():
        tool_event = to_tool_event(tool_use_block, None, tool_timestamp)
        scout_events.append(tool_event)

        # Close associated tool span if any
        if tool_id in active_tool_spans:
            span_id = active_tool_spans.pop(tool_id)
            scout_events.append(to_span_end_event(span_id, datetime.now()))

    # Close any remaining tool spans
    for span_id in active_tool_spans.values():
        scout_events.append(to_span_end_event(span_id, datetime.now()))

    # Close any remaining agent spans
    for span_id in active_agent_spans.values():
        scout_events.append(to_span_end_event(span_id, datetime.now()))

    # Sort by timestamp
    scout_events.sort(key=lambda e: e.timestamp or datetime.min)

    return scout_events


def _load_agent_events(
    project_dir: Path,
    tool_result: dict[str, Any],
    result_timestamp: datetime,
) -> list[Event]:
    """Load and process events from an agent session file.

    Args:
        project_dir: Path to project directory
        tool_result: The tool_result block that completed the agent
        result_timestamp: When the result was received

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

    # Find and load agent file
    agent_file = find_agent_file(project_dir, agent_id)
    if not agent_file:
        logger.debug(f"Agent file not found for ID: {agent_id}")
        return []

    raw_events = read_jsonl_events(agent_file)

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
