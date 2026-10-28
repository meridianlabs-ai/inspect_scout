"""Claude Code's own IDs for imported messages and model events."""

from collections import deque
from collections.abc import Sequence

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, ChatMessageTool, ChatMessageUser
from inspect_swe._claude_code._events.extraction import extract_user_message
from inspect_swe._claude_code._events.models import (
    AssistantEvent,
    BaseEvent,
    UserEvent,
)


def apply_source_ids(
    conversation: Sequence[BaseEvent], events: Sequence[Event]
) -> None:
    """Give one conversation's model events and messages their Claude Code IDs.

    - A model event's `uuid` is the `uuid` of its assistant line (the last
      line of the response, which is the one later lines' `parentUuid` names).
    - An assistant message keeps the Anthropic `message.id` it was built with.
    - A user message, or the first tool result on a line, takes the line's
      `uuid`; further tool results on the same line add `-1`, `-2`, ....

    Events from nested agents are left alone; they get their IDs when their
    own conversation is loaded.

    Args:
        conversation: The conversation's parsed Claude Code lines.
        events: The events converted from them.
    """
    call_lines = {
        line.message.id: line.uuid
        for line in conversation
        if isinstance(line, AssistantEvent) and line.message.id
    }
    model_events = [
        event
        for event in events
        if isinstance(event, ModelEvent)
        and event.output.choices
        and event.output.message.id in call_lines
    ]
    for event in model_events:
        event.uuid = call_lines[str(event.output.message.id)]

    tool_ids, user_ids = _line_ids(conversation)
    for message in _distinct_inputs(model_events):
        if isinstance(message, ChatMessageTool):
            if message.tool_call_id in tool_ids:
                message.id = tool_ids[message.tool_call_id]
        elif isinstance(message, ChatMessageUser) and isinstance(message.content, str):
            ids = user_ids.get(message.content)
            if ids:
                message.id = ids.popleft()


def _line_ids(
    conversation: Sequence[BaseEvent],
) -> tuple[dict[str, str], dict[str, deque[str]]]:
    """Message IDs by tool call ID, and by user message text, in line order."""
    tool_ids: dict[str, str] = {}
    user_ids: dict[str, deque[str]] = {}
    for line in conversation:
        if not isinstance(line, UserEvent):
            continue
        content = line.message.content
        results = (
            [
                str(block.get("tool_use_id", ""))
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_result"
            ]
            if isinstance(content, list)
            else []
        )
        for index, tool_call_id in enumerate(results):
            tool_ids[tool_call_id] = f"{line.uuid}-{index}" if index else line.uuid
        user = extract_user_message(line)
        if user is not None and isinstance(user.content, str):
            user_ids.setdefault(user.content, deque()).append(line.uuid)
    return tool_ids, user_ids


def _distinct_inputs(model_events: Sequence[ModelEvent]) -> list[ChatMessage]:
    """Input messages in order of first appearance.

    The converter shares one message object across every call it appears in.
    """
    seen: set[int] = set()
    messages: list[ChatMessage] = []
    for event in model_events:
        for message in event.input:
            if id(message) not in seen:
                seen.add(id(message))
                messages.append(message)
    return messages
