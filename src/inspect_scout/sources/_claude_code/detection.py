"""Event type detection for Claude Code sessions.

Detects event types, /clear commands, model names, and filters
conversation events from internal events.
"""

import re

from .models import (
    AssistantEvent,
    BaseEvent,
    ContentToolUse,
    FileHistoryEvent,
    ProgressEvent,
    QueueOperationEvent,
    SystemEvent,
    UserEvent,
)


def get_event_type(event: BaseEvent) -> str:
    """Get the type of a Claude Code event.

    Args:
        event: Claude Code event

    Returns:
        Event type string (user, assistant, progress, system, etc.)
    """
    return event.type


def is_user_event(event: BaseEvent) -> bool:
    """Check if event is a user message event."""
    return isinstance(event, UserEvent)


def is_assistant_event(event: BaseEvent) -> bool:
    """Check if event is an assistant response event."""
    return isinstance(event, AssistantEvent)


def is_progress_event(event: BaseEvent) -> bool:
    """Check if event is a progress/streaming event."""
    return isinstance(event, ProgressEvent)


def is_system_event(event: BaseEvent) -> bool:
    """Check if event is a system event."""
    return isinstance(event, SystemEvent)


def is_file_history_event(event: BaseEvent) -> bool:
    """Check if event is a file history snapshot."""
    return isinstance(event, FileHistoryEvent)


def is_clear_command(event: BaseEvent) -> bool:
    """Check if event is a /clear command.

    /clear commands appear in user events with content like:
    '<command-name>/clear</command-name>...'

    Args:
        event: Claude Code event

    Returns:
        True if this is a /clear command
    """
    if not isinstance(event, UserEvent):
        return False

    content = event.message.content

    if isinstance(content, str):
        return "<command-name>/clear</command-name>" in content
    return False


def is_exit_command(event: BaseEvent) -> bool:
    """Check if event is a /exit command.

    Args:
        event: Claude Code event

    Returns:
        True if this is a /exit command
    """
    if not isinstance(event, UserEvent):
        return False

    content = event.message.content

    if isinstance(content, str):
        return "<command-name>/exit</command-name>" in content
    return False


def is_compact_boundary(event: BaseEvent) -> bool:
    """Check if event is a compaction boundary system event.

    Args:
        event: Claude Code event

    Returns:
        True if this is a compaction boundary marker
    """
    if not isinstance(event, SystemEvent):
        return False
    return event.subtype == "compact_boundary"


def is_compact_summary(event: BaseEvent) -> bool:
    """Check if event is a compaction summary user message.

    These are user messages that contain the conversation summary
    after compaction. They have isCompactSummary: true.

    Args:
        event: Claude Code event

    Returns:
        True if this is a compaction summary message
    """
    if not isinstance(event, UserEvent):
        return False
    return event.isCompactSummary


def is_turn_duration_event(event: BaseEvent) -> bool:
    """Check if event is a turn duration system event (internal timing)."""
    if not isinstance(event, SystemEvent):
        return False
    return event.subtype == "turn_duration"


def is_sidechain_event(event: BaseEvent) -> bool:
    """Check if event is from a sidechain (agent subprocess)."""
    return event.isSidechain


def is_skill_command(event: BaseEvent) -> str | None:
    """Check if event is a skill command and return the skill name.

    Skill commands appear in user messages with content like:
    '<command-name>/feature-dev:feature-dev</command-name>...'

    Args:
        event: Claude Code event

    Returns:
        The skill name if this is a skill command, None otherwise
    """
    if not isinstance(event, UserEvent):
        return None

    content = event.message.content

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


def should_skip_event(event: BaseEvent) -> bool:
    """Check if an event should be skipped during processing.

    Events to skip:
    - progress events (streaming indicators)
    - queue-operation events
    - file-history-snapshot events
    - turn_duration system events
    - /clear and /exit commands

    Args:
        event: Claude Code event

    Returns:
        True if the event should be skipped
    """
    # Skip progress events
    if isinstance(event, ProgressEvent):
        return True

    # Skip queue operations
    if isinstance(event, QueueOperationEvent):
        return True

    # Skip file history snapshots
    if isinstance(event, FileHistoryEvent):
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


def get_model_name(event: BaseEvent) -> str | None:
    """Extract the model name from an assistant event.

    Args:
        event: Claude Code event

    Returns:
        Model name string, or None if not found
    """
    if not isinstance(event, AssistantEvent):
        return None

    return event.message.model


def get_session_id(event: BaseEvent) -> str | None:
    """Extract the session ID from an event.

    Args:
        event: Claude Code event

    Returns:
        Session ID string, or None if not found
    """
    return event.sessionId


def get_uuid(event: BaseEvent) -> str | None:
    """Extract the UUID from an event.

    Args:
        event: Claude Code event

    Returns:
        UUID string, or None if not found
    """
    return event.uuid


def get_parent_uuid(event: BaseEvent) -> str | None:
    """Extract the parent UUID from an event.

    Args:
        event: Claude Code event

    Returns:
        Parent UUID string, or None if root event
    """
    return event.parentUuid


def get_timestamp(event: BaseEvent) -> str | None:
    """Extract the timestamp from an event.

    Args:
        event: Claude Code event

    Returns:
        ISO timestamp string, or None if not found
    """
    return event.timestamp


def get_agent_id(event: BaseEvent) -> str | None:
    """Extract the agent ID from a user event with tool result.

    Args:
        event: Claude Code event

    Returns:
        Agent ID string, or None if not found
    """
    if not isinstance(event, UserEvent):
        return None

    if event.toolUseResult and event.toolUseResult.agentId:
        return event.toolUseResult.agentId

    return None


def is_task_tool_call(content_block: ContentToolUse) -> bool:
    """Check if a content block is a Task tool call (subagent spawn).

    Args:
        content_block: A ContentToolUse from an assistant message

    Returns:
        True if this is a Task tool call
    """
    return content_block.name == "Task"


def get_task_agent_info(content_block: ContentToolUse) -> dict[str, str] | None:
    """Extract agent info from a Task tool call.

    Args:
        content_block: A Task tool_use content block

    Returns:
        Dict with subagent_type, description, prompt, or None if invalid
    """
    if not is_task_tool_call(content_block):
        return None

    input_data = content_block.input

    return {
        "subagent_type": str(input_data.get("subagent_type", "unknown")),
        "description": str(input_data.get("description", "")),
        "prompt": str(input_data.get("prompt", "")),
        "tool_use_id": content_block.id,
    }
