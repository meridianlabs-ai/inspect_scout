"""Event conversion for OpenCode sessions.

Converts OpenCode messages and parts to Inspect AI event types:
- Assistant steps → ModelEvent
- Tool parts → ToolEvent (wrapped in SpanBeginEvent/SpanEndEvent)
- Task tool calls → agent spans with recursive child session events
- Patch parts → InfoEvent
- Compaction parts → CompactionEvent
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import Any

from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import ModelOutput
from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model_output import ChatCompletionChoice, ModelUsage, StopReason
from inspect_ai.tool._tool_call import ToolCall, ToolCallError

from .client import (
    _EPOCH,
    MessageRow,
    PartRow,
    _ms_to_datetime,
    extract_child_session_id,
    read_messages,
    read_parts,
    read_session,
)

logger = getLogger(__name__)


# ---------------------------------------------------------------------------
# Step splitting
# ---------------------------------------------------------------------------


def _split_into_steps(
    parts: list[PartRow],
) -> list[list[PartRow]]:
    """Split a message's parts into steps delimited by step-start/step-finish.

    Each step is a list of parts between a step-start and step-finish (inclusive).
    Parts outside step boundaries (e.g. trailing patch parts) are grouped
    into the last step if one exists, otherwise into their own group.

    Returns:
        List of step groups. Each group is a list of PartRow.
    """
    steps: list[list[PartRow]] = []
    current: list[PartRow] = []

    for part in parts:
        ptype = part.data.get("type")
        if ptype == "step-start":
            # Start a new step group
            if current:
                steps.append(current)
            current = [part]
        elif ptype == "step-finish":
            current.append(part)
            steps.append(current)
            current = []
        else:
            current.append(part)

    # Trailing parts (e.g. patch after last step-finish)
    if current:
        if steps:
            # Attach to last step
            steps[-1].extend(current)
        else:
            steps.append(current)

    return steps


# ---------------------------------------------------------------------------
# Event builders
# ---------------------------------------------------------------------------


def _build_model_event(
    text_parts: list[PartRow],
    tool_parts: list[PartRow],
    step_finish: PartRow | None,
    model_name: str,
    input_messages: list[Any],
    timestamp: datetime,
) -> ModelEvent:
    """Build a ModelEvent from a single step's parts."""
    # Content from text parts
    text_content = "\n\n".join(
        p.data.get("text", "") for p in text_parts if p.data.get("text")
    )

    # Tool calls from tool parts
    tool_calls: list[ToolCall] = []
    for tp in tool_parts:
        state = tp.data.get("state", {})
        tool_calls.append(
            ToolCall(
                id=tp.data.get("callID", tp.id),
                type="function",
                function=tp.data.get("tool", "unknown"),
                arguments=state.get("input", {}),
            )
        )

    # Build output message
    output_content: str | list[Any] = text_content if text_content else ""
    output_message = ChatMessageAssistant(
        content=output_content,
        tool_calls=tool_calls if tool_calls else None,
    )

    # Usage from step-finish
    usage = None
    if step_finish:
        tokens = step_finish.data.get("tokens", {})
        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)
        reasoning_tokens = tokens.get("reasoning", 0)
        cache = tokens.get("cache", {})
        cache_read = cache.get("read", 0)
        cache_write = cache.get("write", 0)
        total = tokens.get("total", input_tokens + output_tokens)
        usage = ModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens + reasoning_tokens,
            total_tokens=total,
            input_tokens_cache_read=cache_read if cache_read else None,
            input_tokens_cache_write=cache_write if cache_write else None,
        )

    stop_reason: StopReason = "tool_calls" if tool_calls else "stop"

    return ModelEvent(
        model=model_name,
        input=list(input_messages),
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    message=output_message,
                    stop_reason=stop_reason,
                )
            ],
            usage=usage,
        ),
        timestamp=timestamp,
    )


def _build_tool_event(
    part: PartRow,
    timestamp: datetime,
) -> ToolEvent:
    """Build a ToolEvent from a tool part."""
    state = part.data.get("state", {})
    call_id = part.data.get("callID", part.id)
    tool_name = part.data.get("tool", "unknown")
    tool_input = state.get("input", {})
    status = state.get("status", "completed")

    result = state.get("output", "")
    error = None
    if status == "error":
        error_msg = state.get("error", "Unknown error")
        error = ToolCallError(type="unknown", message=error_msg)
        result = error_msg

    time_info = state.get("time", {})
    start = _ms_to_datetime(time_info.get("start"))
    end = _ms_to_datetime(time_info.get("end")) if time_info.get("end") else None

    return ToolEvent(
        id=call_id,
        type="function",
        function=tool_name,
        arguments=tool_input,
        result=result,
        timestamp=start if start != _EPOCH else timestamp,
        completed=end,
        error=error,
    )


def _build_tool_span(
    part: PartRow,
    timestamp: datetime,
) -> list[Event]:
    """Build a tool span: SpanBeginEvent → ToolEvent → SpanEndEvent."""
    call_id = part.data.get("callID", part.id)
    tool_name = part.data.get("tool", "unknown")
    state = part.data.get("state", {})
    time_info = state.get("time", {})

    start = _ms_to_datetime(time_info.get("start"))
    end = _ms_to_datetime(time_info.get("end"))
    if start == _EPOCH:
        start = timestamp
    if end == _EPOCH:
        end = start

    span_id = f"tool-{call_id}"

    return [
        SpanBeginEvent(
            id=span_id,
            name=tool_name,
            type="tool",
            timestamp=start,
            working_start=0.0,
        ),
        _build_tool_event(part, timestamp),
        SpanEndEvent(id=span_id, timestamp=end),
    ]


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


async def _process_assistant_message(
    msg: MessageRow,
    msg_parts: list[PartRow],
    model_name: str,
    accumulated_input: list[Any],
    db_path: Path | None,
    max_depth: int,
    conn: sqlite3.Connection | None,
) -> list[Event]:
    """Process one assistant message into events.

    Mutates *accumulated_input* in place (appends assistant messages,
    clears on compaction).

    Args:
        msg: The assistant message row
        msg_parts: Parts belonging to this message
        model_name: Model identifier from the message
        accumulated_input: Running list of input messages (mutated in place)
        db_path: Path to opencode.db (for child sessions)
        max_depth: Maximum recursion depth for subagent loading
        conn: Optional existing DB connection to reuse

    Returns:
        List of events produced from this message
    """
    timestamp = _ms_to_datetime(msg.time_created)
    events: list[Event] = []

    steps = _split_into_steps(msg_parts)

    for step_parts in steps:
        text_parts: list[PartRow] = []
        tool_parts: list[PartRow] = []
        step_finish: PartRow | None = None
        patch_parts: list[PartRow] = []

        for p in step_parts:
            ptype = p.data.get("type")
            if ptype == "text":
                text_parts.append(p)
            elif ptype == "tool":
                tool_parts.append(p)
            elif ptype == "step-finish":
                step_finish = p
            elif ptype == "patch":
                patch_parts.append(p)
            elif ptype == "compaction":
                events.append(
                    CompactionEvent(
                        source="opencode",
                        tokens_before=None,
                        timestamp=_ms_to_datetime(p.time_created),
                    )
                )
                accumulated_input.clear()
            # step-start and reasoning are skipped

        # Only emit ModelEvent if there's actual content
        if not text_parts and not tool_parts:
            # Handle patch-only steps
            for pp in patch_parts:
                events.append(
                    InfoEvent(
                        source="opencode",
                        data={
                            "type": "patch",
                            "hash": pp.data.get("hash"),
                            "files": pp.data.get("files", []),
                        },
                        timestamp=_ms_to_datetime(pp.time_created),
                    )
                )
            continue

        # Determine step timestamp from first content part
        step_ts = timestamp
        first_content = (
            text_parts[0] if text_parts else (tool_parts[0] if tool_parts else None)
        )
        if first_content:
            step_ts = _ms_to_datetime(first_content.time_created)

        # Emit ModelEvent
        model_event = _build_model_event(
            text_parts,
            tool_parts,
            step_finish,
            model_name,
            accumulated_input,
            step_ts,
        )
        events.append(model_event)

        # Add assistant message to accumulated input
        if model_event.output and model_event.output.message:
            accumulated_input.append(model_event.output.message)

        # Emit tool spans
        for tp in tool_parts:
            tool_name = tp.data.get("tool", "")
            state = tp.data.get("state", {})

            if tool_name == "task" and state.get("status") == "completed":
                agent_events = await _build_agent_span(
                    tp, db_path, max_depth, step_ts, conn=conn
                )
                events.extend(agent_events)
            else:
                events.extend(_build_tool_span(tp, step_ts))

        # Emit patch info events
        for pp in patch_parts:
            events.append(
                InfoEvent(
                    source="opencode",
                    data={
                        "type": "patch",
                        "hash": pp.data.get("hash"),
                        "files": pp.data.get("files", []),
                    },
                    timestamp=_ms_to_datetime(pp.time_created),
                )
            )

    return events


async def process_session(
    messages: list[MessageRow],
    parts: list[PartRow],
    db_path: Path | None = None,
    max_depth: int = 3,
    conn: sqlite3.Connection | None = None,
) -> list[Event]:
    """Convert an OpenCode session's messages and parts to Inspect AI events.

    Args:
        messages: Messages for this session, ordered by time_created
        parts: Parts for this session, ordered by time_created
        db_path: Path to opencode.db (for loading child sessions)
        max_depth: Maximum depth for recursive subagent loading
        conn: Optional existing DB connection to reuse

    Returns:
        List of Inspect AI events in chronological order
    """
    # Group parts by message_id
    parts_by_msg: dict[str, list[PartRow]] = defaultdict(list)
    for part in parts:
        parts_by_msg[part.message_id].append(part)

    events: list[Event] = []
    accumulated_input: list[Any] = []

    for msg in messages:
        role = msg.data.get("role")

        if role == "user":
            msg_parts = parts_by_msg.get(msg.id, [])
            text_pieces = [
                p.data.get("text", "")
                for p in msg_parts
                if p.data.get("type") == "text" and p.data.get("text")
            ]
            if text_pieces:
                accumulated_input.append(
                    ChatMessageUser(content="\n\n".join(text_pieces))
                )

        elif role == "assistant":
            msg_parts = parts_by_msg.get(msg.id, [])
            model_name = msg.data.get("modelID", "unknown")
            assistant_events = await _process_assistant_message(
                msg,
                msg_parts,
                model_name,
                accumulated_input,
                db_path,
                max_depth,
                conn,
            )
            events.extend(assistant_events)

    return events


async def _build_agent_span(
    task_part: PartRow,
    db_path: Path | None,
    max_depth: int,
    fallback_ts: datetime,
    conn: sqlite3.Connection | None = None,
) -> list[Event]:
    """Build an agent span for a task tool call.

    Loads the child session recursively and wraps its events in a span.
    """
    state = task_part.data.get("state", {})
    call_id = task_part.data.get("callID", task_part.id)
    tool_input = state.get("input", {})
    time_info = state.get("time", {})

    start = _ms_to_datetime(time_info.get("start"))
    end = _ms_to_datetime(time_info.get("end"))
    if start == _EPOCH:
        start = fallback_ts
    if end == _EPOCH:
        end = start

    agent_name = tool_input.get("subagent_type") or tool_input.get("agent", "agent")
    description = tool_input.get("description", "")
    span_id = f"agent-{call_id}"

    events: list[Event] = []

    # Agent span begin
    events.append(
        SpanBeginEvent(
            id=span_id,
            name=agent_name,
            type="agent",
            timestamp=start,
            working_start=0.0,
            metadata={"description": description} if description else None,
        )
    )

    # ToolEvent for the task call itself
    events.append(_build_tool_event(task_part, start))

    # Load child session events
    if db_path and max_depth > 0:
        child_events = await _load_child_session_events(
            task_part, db_path, max_depth, conn=conn
        )
        # Re-parent top-level spans under the agent span
        for evt in child_events:
            if isinstance(evt, SpanBeginEvent) and evt.parent_id is None:
                evt.parent_id = span_id
            elif not isinstance(evt, SpanEndEvent) and evt.span_id is None:
                evt.span_id = span_id
        events.extend(child_events)

    # Agent span end
    events.append(SpanEndEvent(id=span_id, timestamp=end))

    return events


async def _load_child_session_events(
    task_part: PartRow,
    db_path: Path,
    max_depth: int,
    conn: sqlite3.Connection | None = None,
) -> list[Event]:
    """Load events from a child session linked by a task tool part."""
    state = task_part.data.get("state", {})
    output = state.get("output", "")

    # Try to extract child session ID from output
    child_id = extract_child_session_id(output) if isinstance(output, str) else None

    if not child_id:
        logger.debug(
            f"Could not extract child session ID from task part {task_part.id}"
        )
        return []

    # Verify the child session exists
    child_session = read_session(db_path, child_id, conn=conn)
    if not child_session:
        logger.debug(f"Child session not found: {child_id}")
        return []

    # Load child session data
    child_messages = read_messages(db_path, child_id, conn=conn)
    child_parts = read_parts(db_path, child_id, conn=conn)

    if not child_messages:
        return []

    # Recursively process
    return await process_session(
        child_messages,
        child_parts,
        db_path=db_path,
        max_depth=max_depth - 1,
        conn=conn,
    )
