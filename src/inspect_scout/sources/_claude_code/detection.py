"""Event type detection for Claude Code sessions.

Detects event types, /clear commands, model names, and filters
conversation events from internal events.
"""

import re
from typing import Any


def get_event_type(event: dict[str, Any]) -> str:
    """Get the type of a Claude Code event.

    Args:
        event: Claude Code event dictionary

    Returns:
        Event type string (user, assistant, progress, system, file-history-snapshot, etc.)
    """
    return str(event.get("type", "unknown"))


def is_user_event(event: dict[str, Any]) -> bool:
    """Check if event is a user message event."""
    return get_event_type(event) == "user"


def is_assistant_event(event: dict[str, Any]) -> bool:
    """Check if event is an assistant response event."""
    return get_event_type(event) == "assistant"


def is_progress_event(event: dict[str, Any]) -> bool:
    """Check if event is a progress/streaming event."""
    return get_event_type(event) == "progress"


def is_system_event(event: dict[str, Any]) -> bool:
    """Check if event is a system event."""
    return get_event_type(event) == "system"


def is_file_history_event(event: dict[str, Any]) -> bool:
    """Check if event is a file history snapshot."""
    return get_event_type(event) == "file-history-snapshot"


def is_clear_command(event: dict[str, Any]) -> bool:
    """Check if event is a /clear command.

    /clear commands appear in user events with content like:
    '<command-name>/clear</command-name>...'

    Args:
        event: Claude Code event dictionary

    Returns:
        True if this is a /clear command
    """
    if not is_user_event(event):
        return False

    message = event.get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        return "<command-name>/clear</command-name>" in content
    return False


def is_exit_command(event: dict[str, Any]) -> bool:
    """Check if event is a /exit command.

    Args:
        event: Claude Code event dictionary

    Returns:
        True if this is a /exit command
    """
    if not is_user_event(event):
        return False

    message = event.get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        return "<command-name>/exit</command-name>" in content
    return False


def is_compact_boundary(event: dict[str, Any]) -> bool:
    """Check if event is a compaction boundary system event.

    Args:
        event: Claude Code event dictionary

    Returns:
        True if this is a compaction boundary marker
    """
    if not is_system_event(event):
        return False
    return event.get("subtype") == "compact_boundary"


def is_compact_summary(event: dict[str, Any]) -> bool:
    """Check if event is a compaction summary user message.

    These are user messages that contain the conversation summary
    after compaction. They have isCompactSummary: true.

    Args:
        event: Claude Code event dictionary

    Returns:
        True if this is a compaction summary message
    """
    if not is_user_event(event):
        return False
    return bool(event.get("isCompactSummary", False))


def is_turn_duration_event(event: dict[str, Any]) -> bool:
    """Check if event is a turn duration system event (internal timing)."""
    if not is_system_event(event):
        return False
    return event.get("subtype") == "turn_duration"


def is_sidechain_event(event: dict[str, Any]) -> bool:
    """Check if event is from a sidechain (agent subprocess)."""
    return bool(event.get("isSidechain", False))


def is_skill_command(event: dict[str, Any]) -> str | None:
    """Check if event is a skill command and return the skill name.

    Skill commands appear in user messages with content like:
    '<command-name>/feature-dev:feature-dev</command-name>...'

    Args:
        event: Claude Code event dictionary

    Returns:
        The skill name if this is a skill command, None otherwise
    """
    if not is_user_event(event):
        return None

    message = event.get("message", {})
    content = message.get("content", "")

    if not isinstance(content, str):
        return None

    # Match skill commands like /feature-dev:feature-dev, /commit, etc.
    match = re.search(r"<command-name>/([^<]+)</command-name>", content)
    if match:
        command = match.group(1)
        # Skip built-in commands
        if command in ("clear", "exit", "compact"):
            return None
        return command

    return None


def should_skip_event(event: dict[str, Any]) -> bool:
    """Check if an event should be skipped during processing.

    Events to skip:
    - progress events (streaming indicators)
    - queue-operation events
    - file-history-snapshot events
    - turn_duration system events
    - /clear and /exit commands

    Args:
        event: Claude Code event dictionary

    Returns:
        True if the event should be skipped
    """
    event_type = get_event_type(event)

    # Skip progress events
    if event_type == "progress":
        return True

    # Skip queue operations
    if event_type == "queue-operation":
        return True

    # Skip file history snapshots
    if event_type == "file-history-snapshot":
        return True

    # Skip turn duration events
    if is_turn_duration_event(event):
        return True

    # Skip /clear commands (they're split boundaries, not content)
    if is_clear_command(event):
        return True

    # Skip /exit commands
    if is_exit_command(event):
        return True

    return False


def get_model_name(event: dict[str, Any]) -> str | None:
    """Extract the model name from an assistant event.

    Args:
        event: Claude Code event dictionary

    Returns:
        Model name string, or None if not found
    """
    if not is_assistant_event(event):
        return None

    message = event.get("message", {})
    model = message.get("model")
    return str(model) if model else None


def get_session_id(event: dict[str, Any]) -> str | None:
    """Extract the session ID from an event.

    Args:
        event: Claude Code event dictionary

    Returns:
        Session ID string, or None if not found
    """
    session_id = event.get("sessionId")
    return str(session_id) if session_id else None


def get_uuid(event: dict[str, Any]) -> str | None:
    """Extract the UUID from an event.

    Args:
        event: Claude Code event dictionary

    Returns:
        UUID string, or None if not found
    """
    uuid = event.get("uuid")
    return str(uuid) if uuid else None


def get_parent_uuid(event: dict[str, Any]) -> str | None:
    """Extract the parent UUID from an event.

    Args:
        event: Claude Code event dictionary

    Returns:
        Parent UUID string, or None if root event
    """
    parent = event.get("parentUuid")
    return str(parent) if parent else None


def get_timestamp(event: dict[str, Any]) -> str | None:
    """Extract the timestamp from an event.

    Args:
        event: Claude Code event dictionary

    Returns:
        ISO timestamp string, or None if not found
    """
    ts = event.get("timestamp")
    return str(ts) if ts else None


def get_agent_id(event: dict[str, Any]) -> str | None:
    """Extract the agent ID from an event or progress data.

    Args:
        event: Claude Code event dictionary

    Returns:
        Agent ID string, or None if not found
    """
    # Direct agent ID
    if "agentId" in event:
        return str(event["agentId"])

    # Nested in progress data
    data = event.get("data", {})
    if isinstance(data, dict) and "agentId" in data:
        return str(data["agentId"])

    return None


def is_task_tool_call(content_block: dict[str, Any]) -> bool:
    """Check if a content block is a Task tool call (subagent spawn).

    Args:
        content_block: A content block from an assistant message

    Returns:
        True if this is a Task tool call
    """
    if content_block.get("type") != "tool_use":
        return False
    return content_block.get("name") == "Task"


def get_task_agent_info(content_block: dict[str, Any]) -> dict[str, Any] | None:
    """Extract agent info from a Task tool call.

    Args:
        content_block: A Task tool_use content block

    Returns:
        Dict with subagent_type, description, prompt, or None if invalid
    """
    if not is_task_tool_call(content_block):
        return None

    input_data = content_block.get("input", {})
    if not isinstance(input_data, dict):
        return None

    return {
        "subagent_type": input_data.get("subagent_type", "unknown"),
        "description": input_data.get("description", ""),
        "prompt": input_data.get("prompt", ""),
        "tool_use_id": content_block.get("id", ""),
    }


def extract_tool_result_agent_id(content_block: dict[str, Any]) -> str | None:
    """Extract agent ID from a Task tool result.

    Tool results for Task calls contain:
    {
        "toolUseResult": {
            "agentId": "a774434",
            "totalDurationMs": ...,
            "totalTokens": ...,
            ...
        }
    }

    Args:
        content_block: A tool_result content block

    Returns:
        Agent ID string, or None if not a Task result
    """
    if content_block.get("type") != "tool_result":
        return None

    # Check if content is a list with tool use result
    content = content_block.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and "text" in item:
                # The text might contain the agentId info
                pass

    # Check direct toolUseResult
    # Note: In Claude Code, the result structure varies
    return None
