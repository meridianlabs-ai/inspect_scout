"""Message and metadata extraction for Claude Code sessions.

Extracts ChatMessage objects, token usage, metadata, and other
information from Claude Code events.
"""

from datetime import datetime
from logging import getLogger
from typing import Any

from inspect_ai.model import (
    Content,
    ContentReasoning,
    ContentText,
)
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.tool import ToolCall

from .detection import (
    get_event_type,
    get_timestamp,
    is_assistant_event,
    is_compact_summary,
    is_system_event,
    is_user_event,
)

logger = getLogger(__name__)


def extract_user_message(event: dict[str, Any]) -> ChatMessageUser | None:
    """Extract a ChatMessageUser from a user event.

    Args:
        event: Claude Code user event

    Returns:
        ChatMessageUser, or None if extraction fails
    """
    if not is_user_event(event):
        return None

    message = event.get("message", {})
    content = message.get("content", "")

    # Handle string content
    if isinstance(content, str):
        # Skip command messages
        if content.startswith("<command-name>"):
            return None
        return ChatMessageUser(content=content)

    # Handle list content (tool results, etc.)
    if isinstance(content, list):
        # Check if this is a tool result message
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                # Tool results become ChatMessageTool, not ChatMessageUser
                return None

        # Extract text content
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif "text" in block:
                    text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)

        if text_parts:
            return ChatMessageUser(content="\n".join(text_parts))

    return None


def extract_tool_result_messages(event: dict[str, Any]) -> list[ChatMessageTool]:
    """Extract ChatMessageTool objects from a user event with tool results.

    Args:
        event: Claude Code user event that may contain tool results

    Returns:
        List of ChatMessageTool objects
    """
    if not is_user_event(event):
        return []

    message = event.get("message", {})
    content = message.get("content", [])

    if not isinstance(content, list):
        return []

    tool_messages = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            tool_use_id = block.get("tool_use_id", "")
            result_content = block.get("content", "")
            # Note: is_error could be used to set error state in future

            # Handle content that might be a list or string
            if isinstance(result_content, list):
                # Extract text from content blocks
                text_parts = []
                for item in result_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                result_content = "\n".join(text_parts)
            elif not isinstance(result_content, str):
                result_content = str(result_content)

            tool_messages.append(
                ChatMessageTool(
                    content=result_content,
                    tool_call_id=tool_use_id,
                )
            )

    return tool_messages


def extract_assistant_content(
    message_content: list[dict[str, Any]],
) -> tuple[list[Content], list[ToolCall]]:
    """Extract content and tool calls from assistant message content blocks.

    Args:
        message_content: List of content blocks from assistant message

    Returns:
        Tuple of (content list, tool calls list)
    """
    content: list[Content] = []
    tool_calls: list[ToolCall] = []

    for block in message_content:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type", "")

        if block_type == "text":
            text = block.get("text", "")
            if text:
                content.append(ContentText(text=text))

        elif block_type == "thinking":
            thinking = block.get("thinking", "")
            signature = block.get("signature")
            if thinking:
                content.append(
                    ContentReasoning(
                        reasoning=thinking,
                        signature=signature,
                    )
                )

        elif block_type == "tool_use":
            tool_id = block.get("id", "")
            tool_name = block.get("name", "")
            tool_input = block.get("input", {})

            tool_calls.append(
                ToolCall(
                    id=tool_id,
                    function=tool_name,
                    arguments=tool_input if isinstance(tool_input, dict) else {},
                    type="function",
                )
            )

    return content, tool_calls


def extract_assistant_message(event: dict[str, Any]) -> ChatMessageAssistant | None:
    """Extract a ChatMessageAssistant from an assistant event.

    Args:
        event: Claude Code assistant event

    Returns:
        ChatMessageAssistant, or None if extraction fails
    """
    if not is_assistant_event(event):
        return None

    message = event.get("message", {})
    message_content = message.get("content", [])

    if not isinstance(message_content, list):
        return None

    content, tool_calls = extract_assistant_content(message_content)

    # If we only have text content, simplify to string
    if len(content) == 1 and isinstance(content[0], ContentText):
        return ChatMessageAssistant(
            content=content[0].text,
            tool_calls=tool_calls if tool_calls else None,
        )

    # Multiple content blocks or non-text content
    if content or tool_calls:
        return ChatMessageAssistant(
            content=content if content else "",
            tool_calls=tool_calls if tool_calls else None,
        )

    return None


def extract_messages_from_events(
    events: list[dict[str, Any]],
) -> list[ChatMessage]:
    """Extract a conversation's messages from events.

    Args:
        events: List of conversation events (user, assistant)

    Returns:
        List of ChatMessage objects in conversation order
    """
    messages: list[ChatMessage] = []

    for event in events:
        event_type = get_event_type(event)

        if event_type == "user":
            # Check for tool results first
            tool_msgs = extract_tool_result_messages(event)
            if tool_msgs:
                messages.extend(tool_msgs)
            else:
                # Regular user message
                user_msg = extract_user_message(event)
                if user_msg:
                    messages.append(user_msg)

        elif event_type == "assistant":
            assistant_msg = extract_assistant_message(event)
            if assistant_msg:
                messages.append(assistant_msg)

        # System events with compact summary become user messages
        elif is_compact_summary(event):
            summary_msg = extract_user_message(event)
            if summary_msg:
                messages.append(summary_msg)

    return messages


def extract_usage(event: dict[str, Any]) -> dict[str, int]:
    """Extract token usage from an assistant event.

    Args:
        event: Claude Code assistant event

    Returns:
        Dict with input_tokens, output_tokens, cache_creation_input_tokens,
        cache_read_input_tokens
    """
    if not is_assistant_event(event):
        return {}

    message = event.get("message", {})
    usage = message.get("usage", {})

    result: dict[str, int] = {}

    if "input_tokens" in usage:
        result["input_tokens"] = int(usage["input_tokens"])
    if "output_tokens" in usage:
        result["output_tokens"] = int(usage["output_tokens"])
    if "cache_creation_input_tokens" in usage:
        result["cache_creation_input_tokens"] = int(
            usage["cache_creation_input_tokens"]
        )
    if "cache_read_input_tokens" in usage:
        result["cache_read_input_tokens"] = int(usage["cache_read_input_tokens"])

    return result


def sum_tokens(events: list[dict[str, Any]]) -> int:
    """Sum total tokens across all events.

    Args:
        events: List of events to sum

    Returns:
        Total token count (input + output)
    """
    total = 0
    for event in events:
        usage = extract_usage(event)
        total += usage.get("input_tokens", 0)
        total += usage.get("output_tokens", 0)
    return total


def sum_latency(events: list[dict[str, Any]]) -> float:
    """Calculate total time from first to last event.

    Args:
        events: List of events

    Returns:
        Duration in seconds, or 0.0 if cannot be calculated
    """
    if not events:
        return 0.0

    timestamps = []
    for event in events:
        ts_str = get_timestamp(event)
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamps.append(ts)
            except ValueError:
                continue

    if len(timestamps) < 2:
        return 0.0

    timestamps.sort()
    duration = (timestamps[-1] - timestamps[0]).total_seconds()
    return max(0.0, duration)


def extract_model_name(events: list[dict[str, Any]]) -> str | None:
    """Extract the model name from events.

    Args:
        events: List of events

    Returns:
        Model name, or None if not found
    """
    for event in events:
        if is_assistant_event(event):
            message = event.get("message", {})
            model = message.get("model")
            if model:
                return str(model)
    return None


def extract_session_metadata(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract session metadata from events.

    Args:
        events: List of events

    Returns:
        Dict with cwd, gitBranch, version, slug, etc.
    """
    metadata: dict[str, Any] = {}

    # Get from first event with these fields
    for event in events:
        if "cwd" in event and "cwd" not in metadata:
            metadata["cwd"] = event["cwd"]
        if "gitBranch" in event and "gitBranch" not in metadata:
            metadata["gitBranch"] = event["gitBranch"]
        if "version" in event and "version" not in metadata:
            metadata["version"] = event["version"]
        if "slug" in event and "slug" not in metadata:
            metadata["slug"] = event["slug"]

        # Stop once we have all common fields
        if all(k in metadata for k in ["cwd", "gitBranch", "version", "slug"]):
            break

    return metadata


def extract_compaction_info(event: dict[str, Any]) -> dict[str, Any] | None:
    """Extract compaction information from a system event.

    Args:
        event: System event with subtype=compact_boundary

    Returns:
        Dict with trigger, preTokens, or None if not a compaction event
    """
    if not is_system_event(event) or event.get("subtype") != "compact_boundary":
        return None

    compact_metadata = event.get("compactMetadata", {})
    return {
        "trigger": compact_metadata.get("trigger", "auto"),
        "preTokens": compact_metadata.get("preTokens"),
        "content": event.get("content", "Conversation compacted"),
    }


def get_first_timestamp(events: list[dict[str, Any]]) -> str | None:
    """Get the earliest timestamp from events.

    Args:
        events: List of events

    Returns:
        ISO timestamp string, or None if no timestamps found
    """
    timestamps = []
    for event in events:
        ts = get_timestamp(event)
        if ts:
            timestamps.append(ts)

    if not timestamps:
        return None

    # Sort and return earliest
    timestamps.sort()
    return timestamps[0]
