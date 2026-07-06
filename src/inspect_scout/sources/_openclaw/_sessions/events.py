"""OpenClaw native session event + message conversion.

Builds the Inspect AI event stream and the main-thread ``ChatMessage`` list
from a :class:`~.parse.ParsedSession`.

Mapping (mirrors the Claude Code and telemetry-hal importers):

- The session's own thread is the spine: user/assistant/toolResult records
  become the ``ModelEvent`` / ``ToolEvent`` / ``CompactionEvent`` stream and
  the ``messages`` thread; ``model_change`` / ``thinking_level_change`` become
  ``InfoEvent`` timeline markers.
- Each spawned sub-agent becomes a nested agent span (``SpanBeginEvent`` /
  ``SpanEndEvent``, ``type="agent"``) anchored at the spawning tool call, its
  file located via the ``sessions.json`` registry and parsed recursively.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator, cast

from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    ToolEvent,
)
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    ModelOutput,
    ModelUsage,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool import ToolCallError
from inspect_ai.tool import ToolResult as ToolResultContent

from ..extraction import (
    content_blocks,
    content_to_text,
    rich_or_text,
    to_tool_call,
    toolcalls_of,
    usage_to_inspect,
)
from .client import RegistryEntry
from .parse import (
    AssistantTurn,
    CompactionRecord,
    ConfigChange,
    ParsedSession,
    ToolResultMsg,
    UserTurn,
)

logger = getLogger(__name__)

_EPOCH = datetime.fromtimestamp(0, tz=timezone.utc)

# toolResult.details keys surfaced into ToolEvent.metadata. Selected small
# scalars only: the full details can duplicate the entire result body (e.g.
# ``exec``'s ``aggregated`` output).
_DETAIL_METADATA_KEYS = ("status", "exitCode", "durationMs", "tookMs")


@dataclass
class BuildContext:
    """Cross-file context for building one transcript's content.

    ``registry``/``sessions_dir`` locate spawned sub-agent session files;
    with either absent, spawn calls degrade to plain tool events.
    """

    sessions_dir: Path | None
    registry: dict[str, RegistryEntry] | None
    max_depth: int = 5


def build_content(
    parsed: ParsedSession, ctx: BuildContext
) -> tuple[list[Event], list[ChatMessage]]:
    """Build the event stream and main-thread messages for one session.

    A single running conversation is threaded through both outputs: each
    ``ModelEvent.input`` carries the conversation up to that turn, and the
    final running list is the message thread. Sub-agent spans are emitted
    inline at their spawning tool call; their messages stay out of the thread.
    """
    events: list[Event] = []
    messages: list[ChatMessage] = []
    order = count()
    _build_thread(parsed, ctx, ctx.max_depth, events, messages, None, order)
    return events, messages


def _build_thread(
    parsed: ParsedSession,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    messages: list[ChatMessage],
    span_id: str | None,
    order: Iterator[int],
) -> datetime:
    """Emit one session's records into ``events``/``messages``.

    Returns the last timestamp seen (used as the enclosing span's end time).
    """
    last_ts = parsed.header.timestamp or _EPOCH
    for record in parsed.records:
        last_ts = max(last_ts, record.timestamp)
        if isinstance(record, UserTurn):
            messages.append(ChatMessageUser(content=rich_or_text(record.content)))
        elif isinstance(record, ConfigChange):
            events.append(
                InfoEvent(
                    source="openclaw",
                    data={"type": record.change, **record.data},
                    timestamp=record.timestamp,
                    working_start=float(next(order)),
                    span_id=span_id,
                )
            )
        elif isinstance(record, CompactionRecord):
            metadata = {
                key: value
                for key, value in (
                    ("summary", record.summary),
                    ("first_kept_entry_id", record.first_kept_entry_id),
                    ("details", record.details),
                    ("from_hook", record.from_hook),
                )
                if value is not None
            }
            events.append(
                CompactionEvent(
                    source="openclaw",
                    tokens_before=record.tokens_before,
                    tokens_after=None,
                    timestamp=record.timestamp,
                    working_start=float(next(order)),
                    span_id=span_id,
                    metadata=metadata or None,
                )
            )
        elif isinstance(record, AssistantTurn):
            turn_end = _emit_assistant_turn(
                record, parsed, ctx, depth, events, messages, span_id, order
            )
            last_ts = max(last_ts, turn_end)
    return last_ts


def _emit_assistant_turn(
    turn: AssistantTurn,
    parsed: ParsedSession,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    messages: list[ChatMessage],
    span_id: str | None,
    order: Iterator[int],
) -> datetime:
    """Emit a model event, then a tool event (or agent span) per tool call."""
    toolcalls = toolcalls_of(turn.content)
    tool_calls = [to_tool_call(tc) for tc in toolcalls]
    assistant_msg = ChatMessageAssistant(
        content=content_blocks(turn.content),
        tool_calls=tool_calls or None,
        model=turn.model,
    )
    output = ModelOutput(
        model=turn.model,
        choices=[
            ChatCompletionChoice(
                message=assistant_msg,
                stop_reason="tool_calls" if tool_calls else "stop",
            )
        ],
        usage=ModelUsage(**usage_to_inspect(turn.usage)),
    )
    events.append(
        ModelEvent(
            model=turn.model,
            input=list(messages),  # conversation up to (not including) this turn
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=output,
            timestamp=turn.timestamp,
            completed=turn.timestamp,
            working_start=float(next(order)),
            span_id=span_id,
        )
    )
    messages.append(assistant_msg)
    last_ts = turn.timestamp

    for tc, tool_call in zip(toolcalls, tool_calls, strict=True):
        result = parsed.result_by_callid.get(tool_call.id)
        result_content, completed, error, failed = _tool_result_fields(
            result, turn.timestamp
        )
        child = _resolve_spawned_child(result, ctx, depth)
        if child is not None:
            child_session, child_entry = child
            span_end = _emit_subagent_span(
                child_session,
                child_entry,
                tc,
                result,
                ctx,
                depth,
                events,
                span_id,
                order,
                turn.timestamp,
            )
            last_ts = max(last_ts, span_end)
        else:
            events.append(
                ToolEvent(
                    id=tool_call.id,
                    function=tool_call.function,
                    arguments=tool_call.arguments,
                    result=cast(ToolResultContent, result_content),
                    error=error,
                    failed=failed,
                    timestamp=turn.timestamp,
                    completed=completed,
                    working_start=float(next(order)),
                    span_id=span_id,
                    metadata=_result_metadata(result),
                )
            )
        # The tool result belongs in the message thread either way.
        messages.append(
            ChatMessageTool(
                content=result_content,
                tool_call_id=tool_call.id,
                function=tool_call.function,
                error=error,
            )
        )
        last_ts = max(last_ts, completed)
    return last_ts


def _resolve_spawned_child(
    result: ToolResultMsg | None, ctx: BuildContext, depth: int
) -> tuple[ParsedSession, RegistryEntry] | None:
    """Resolve a spawn tool result to its child session, if any.

    Implemented in the sub-agent span task; the thread-only build always
    returns ``None``.
    """
    return None


def _emit_subagent_span(
    child: ParsedSession,
    entry: RegistryEntry,
    spawn_tool: dict[str, Any],
    spawn_result: ToolResultMsg | None,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    parent_span_id: str | None,
    order: Iterator[int],
    spawn_ts: datetime,
) -> datetime:
    """Implemented in the sub-agent span task."""
    raise NotImplementedError


def _tool_result_fields(
    result: ToolResultMsg | None, started: datetime
) -> tuple[Any, datetime, ToolCallError | None, bool | None]:
    """Resolve a tool result into ``ToolEvent`` fields.

    Returns ``(content, completed, error, failed)``. The completion time is
    the result's own timestamp (a real call→result span); a call with no
    recorded result (e.g. an aborted run) gets an empty result completing at
    the turn's own time with ``failed`` unknown.
    """
    if result is None:
        return "", started, None, None
    result_content = rich_or_text(result.content)
    if result.is_error:
        return (
            result_content,
            result.timestamp,
            ToolCallError("unknown", content_to_text(result.content)),
            True,
        )
    failed = False if result.is_error is False else None
    return result_content, result.timestamp, None, failed


def _result_metadata(result: ToolResultMsg | None) -> dict[str, Any] | None:
    """Small scalar ``details`` fields worth carrying on the tool event."""
    if result is None or result.details is None:
        return None
    metadata = {
        key: result.details[key]
        for key in _DETAIL_METADATA_KEYS
        if result.details.get(key) is not None
    }
    return metadata or None
