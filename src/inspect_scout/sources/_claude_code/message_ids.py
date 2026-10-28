"""Claude Code's own IDs for imported messages and model events."""

import json
from bisect import bisect_left
from collections.abc import Sequence
from typing import NamedTuple

import mmh3
from inspect_ai.event import Event, ModelEvent, SpanBeginEvent, SpanEndEvent
from inspect_ai.model import ChatMessage, ChatMessageTool, ChatMessageUser
from inspect_swe._claude_code._events.extraction import extract_user_message
from inspect_swe._claude_code._events.models import (
    AssistantEvent,
    BaseEvent,
    UserEvent,
)

from .._message_ids import edit_id


def apply_source_ids(
    conversation: Sequence[BaseEvent], events: Sequence[Event]
) -> None:
    """Give one conversation's model events and messages their Claude Code IDs.

    - A model event's `uuid` is the `uuid` of its assistant line (the last
      line of the response, which is the one later lines' `parentUuid` names).
    - An assistant message keeps the Anthropic `message.id` it was built with,
      or takes its line's `uuid` if it has none. Fragments of one response
      split apart by other lines become separate replies with the same
      `message.id`; each later one takes `edit_id(message.id, content)`,
      plus a `.1`, `.2`, ... suffix if another line's ID equals it.
    - The messages a user line adds (its text, then its tool results) take the
      line's `uuid`, with `-1`, `-2`, ... added after the first. One that
      matches no line takes its call's `uuid` plus its position.

    Events from nested agents are left alone; they get their IDs when their
    own conversation is loaded.

    Args:
        conversation: The conversation's parsed Claude Code lines, as they
            were converted (assistant fragments already merged).
        events: The events converted from them.

    Raises:
        RuntimeError: If the conversion didn't make one model event per
            assistant line, so events can't be paired with their lines.
    """
    calls = [
        (index, line)
        for index, line in enumerate(conversation)
        if isinstance(line, AssistantEvent)
    ]
    model_events = _own_model_events(events)
    if len(calls) != len(model_events):
        # inspect_swe's converter makes exactly one model event per (merged)
        # assistant line; pairing by position depends on it.
        raise RuntimeError(
            f"Claude Code session {_session_id(conversation)}: conversion made "
            f"{len(model_events)} model events from {len(calls)} assistant "
            "lines, so model events can't be matched to their lines."
        )
    pairs = list(zip(model_events, calls, strict=True))

    sources = _line_messages(conversation)
    starts = [source.line for source in sources]
    seen: set[int] = set()
    replies = _ReplyIds(
        {_reply_source_id(line) for _, line in calls} | {s.id for s in sources}
    )
    for event, (line_index, line) in pairs:
        event.uuid = line.uuid
        if event.output.choices:
            replies.apply(event.output.message, _reply_source_id(line))
        _apply_input_ids(event, sources, bisect_left(starts, line_index) - 1, seen)
        seen.update(id(message) for message in event.input)
        if event.output.choices:
            seen.add(id(event.output.message))


def _session_id(conversation: Sequence[BaseEvent]) -> str | None:
    return conversation[0].sessionId if conversation else None


def _reply_source_id(line: AssistantEvent) -> str:
    return line.message.id or line.uuid


class _ReplyIds:
    """Reply IDs, kept distinct for different replies sharing a source ID."""

    def __init__(self, line_ids: set[str]) -> None:
        """Create the reply IDs for one conversation.

        Args:
            line_ids: Every ID the conversation's lines give their messages,
                which an edited reply's ID must not take.
        """
        self._line_ids = line_ids
        self._first: dict[str, str] = {}

    def apply(self, reply: ChatMessage, source_id: str) -> None:
        content = _content_key(reply)
        first = self._first.setdefault(source_id, content)
        if content == first:
            reply.id = source_id
            return
        candidate = edit_id(source_id, content)
        reply_id, suffix = candidate, 1
        while reply_id in self._line_ids:
            reply_id, suffix = f"{candidate}.{suffix}", suffix + 1
        reply.id = reply_id


class _LineMessage(NamedTuple):
    """A message a user line adds to the conversation."""

    line: int
    key: str
    id: str


def _line_messages(conversation: Sequence[BaseEvent]) -> list[_LineMessage]:
    """The messages user lines add, in the order the converter adds them."""
    messages: list[_LineMessage] = []
    for index, line in enumerate(conversation):
        if not isinstance(line, UserEvent):
            continue
        keys: list[str] = []
        user = extract_user_message(line)
        if user is not None:
            keys.append(_user_key(user))
        content = line.message.content
        if isinstance(content, list):
            keys.extend(
                _tool_key(str(block.get("tool_use_id", "")))
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_result"
            )
        messages.extend(
            _LineMessage(index, key, f"{line.uuid}-{k}" if k else line.uuid)
            for k, key in enumerate(keys)
        )
    return messages


def _apply_input_ids(
    event: ModelEvent, sources: list[_LineMessage], last: int, seen: set[int]
) -> None:
    """Match the messages new in a call's input to the lines before the call.

    The input grows by appending (or restarts after a compaction), so its new
    messages are a suffix, and each matches the nearest earlier line message
    with the same key. Matching from the end keeps repeated keys (the same
    text sent twice, a reused tool call ID) in order, and skips lines whose
    messages were dropped before any call.
    """
    position = len(event.input)
    for message in reversed(event.input):
        if id(message) in seen:
            break
        position -= 1
        key = _message_key(message)
        if key is None:
            continue
        match = next((s for s in range(last, -1, -1) if sources[s].key == key), None)
        if match is not None:
            message.id = sources[match].id
            last = match - 1
        else:
            message.id = f"{event.uuid}-{position}"


def _message_key(message: ChatMessage) -> str | None:
    if isinstance(message, ChatMessageTool):
        return _tool_key(str(message.tool_call_id))
    if isinstance(message, ChatMessageUser):
        return _user_key(message)
    return None


def _tool_key(tool_call_id: str) -> str:
    return f"tool:{tool_call_id}"


def _user_key(message: ChatMessageUser) -> str:
    return "user:" + _content_key(message)


def _content_key(message: ChatMessage) -> str:
    data = message.model_dump(
        mode="json", exclude={"id", "metadata"}, exclude_none=True
    )
    return mmh3.hash_bytes(json.dumps(data, sort_keys=True).encode()).hex()


def _own_model_events(events: Sequence[Event]) -> list[ModelEvent]:
    """Model events outside the spans of nested tools and agents."""
    own: list[ModelEvent] = []
    depth = 0
    for event in events:
        if isinstance(event, SpanBeginEvent):
            depth += 1
        elif isinstance(event, SpanEndEvent):
            depth -= 1
        elif depth == 0 and isinstance(event, ModelEvent):
            own.append(event)
    return own
