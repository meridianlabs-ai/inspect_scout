"""Event type detection for Claude Code sessions.

Detects event types, /clear commands, local-command wrappers, model names,
and filters conversation events from internal events.
"""

import re

from .models import (
    AssistantEvent,
    BaseEvent,
    ContentToolUse,
    SystemEvent,
    TaskAgentInfo,
    ToolUseResult,
    UserEvent,
)

# Command tag constants for Claude Code's XML-wrapped slash commands.
_COMMAND_TAG_PATTERN = re.compile(r"<command-name>/([^<]+)</command-name>")
_BUILTIN_COMMANDS = frozenset({"clear", "exit", "compact"})


def get_event_type(event: BaseEvent) -> str:
    """Get the type of a Claude Code event.

    Args:
        event: Claude Code event

    Returns:
        Event type string (user, assistant, progress, system, etc.)
    """
    return event.type


def _get_command_name(event: BaseEvent) -> str | None:
    """Extract the command name from a user event with a command tag.

    Args:
        event: Claude Code event

    Returns:
        The command name (e.g. "clear", "feature-dev:feature-dev"), or None
    """
    if not isinstance(event, UserEvent):
        return None
    content = event.message.content
    if not isinstance(content, str):
        return None
    match = _COMMAND_TAG_PATTERN.search(content)
    return match.group(1) if match else None


def is_user_event(event: BaseEvent) -> bool:
    """Check if event is a user message event."""
    return isinstance(event, UserEvent)


def is_assistant_event(event: BaseEvent) -> bool:
    """Check if event is an assistant response event."""
    return isinstance(event, AssistantEvent)


def is_system_event(event: BaseEvent) -> bool:
    """Check if event is a system event."""
    return isinstance(event, SystemEvent)


def is_clear_command(event: BaseEvent) -> bool:
    """Check if event is a /clear command.

    Args:
        event: Claude Code event

    Returns:
        True if this is a /clear command
    """
    return _get_command_name(event) == "clear"


def is_exit_command(event: BaseEvent) -> bool:
    """Check if event is a /exit command.

    Args:
        event: Claude Code event

    Returns:
        True if this is a /exit command
    """
    return _get_command_name(event) == "exit"


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

    Args:
        event: Claude Code event

    Returns:
        The skill name if this is a skill command, None otherwise
    """
    command = _get_command_name(event)
    if command is None or command in _BUILTIN_COMMANDS:
        return None
    return command


def is_local_command_caveat(event: BaseEvent) -> bool:
    """Check if event is a local-command-caveat wrapper message.

    Claude Code wraps slash commands in a three-message sequence. The first
    message is a caveat instructing the model to ignore the command messages.
    These are pure UI chrome and should be filtered from transcripts.

    Args:
        event: Claude Code event

    Returns:
        True if this is a local-command-caveat message
    """
    if not isinstance(event, UserEvent):
        return False
    content = event.message.content
    if not isinstance(content, str):
        return False
    return content.startswith("<local-command-caveat>")


def is_local_command_stdout(event: BaseEvent) -> bool:
    """Check if event is a local-command-stdout wrapper message.

    Claude Code wraps slash commands in a three-message sequence. The third
    message contains the command's stdout output (often empty). These are
    pure UI chrome and should be filtered from transcripts.

    Args:
        event: Claude Code event

    Returns:
        True if this is a local-command-stdout message
    """
    if not isinstance(event, UserEvent):
        return False
    content = event.message.content
    if not isinstance(content, str):
        return False
    return content.startswith("<local-command-stdout>")


def should_skip_event(event: BaseEvent) -> bool:
    """Check if an event should be skipped during processing.

    Only checks events that pass the allowlist in parse_events()
    (user, assistant, system). Events to skip:
    - turn_duration system events
    - All slash command events (command-name, caveat, stdout)

    Args:
        event: Claude Code event

    Returns:
        True if the event should be skipped
    """
    # Skip turn duration events
    if is_turn_duration_event(event):
        return True

    # Skip all slash command events (/clear, /exit, /fast, /plan, skills, etc.)
    if _get_command_name(event) is not None:
        return True

    # Skip local-command-caveat wrapper messages
    if is_local_command_caveat(event):
        return True

    # Skip local-command-stdout wrapper messages
    if is_local_command_stdout(event):
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

    if isinstance(event.toolUseResult, ToolUseResult) and event.toolUseResult.agentId:
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


def get_task_agent_info(content_block: ContentToolUse) -> TaskAgentInfo | None:
    """Extract agent info from a Task tool call.

    Args:
        content_block: A Task tool_use content block

    Returns:
        TaskAgentInfo, or None if not a Task tool call
    """
    if not is_task_tool_call(content_block):
        return None

    input_data = content_block.input

    return TaskAgentInfo(
        subagent_type=str(input_data.get("subagent_type", "unknown")),
        description=str(input_data.get("description", "")),
        prompt=str(input_data.get("prompt", "")),
        tool_use_id=content_block.id,
    )
