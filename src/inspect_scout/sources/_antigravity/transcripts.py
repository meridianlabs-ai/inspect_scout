"""Antigravity CLI transcript import functionality.

This module imports conversations recorded by Google's Antigravity CLI
(``agy``) into Inspect Scout transcripts. Conversations are read from the
plaintext JSONL step streams under ``brain/<id>/.system_generated/logs/``
(see client.py for the on-disk layout and why the summaries index is not
used).

Sub-agent conversations are stored as first-class conversations of their
own; the parent's ``invoke_subagent`` tool result carries the child
conversation id, which is used to inline the child's events as an agent
span and exclude it from top-level iteration.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from os import PathLike
from typing import TYPE_CHECKING, Any, AsyncIterator

from inspect_ai.event import (
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    timeline_build,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    stable_message_ids,
)

from .._util import apply_working_start, parse_timestamp, utcnow
from .client import (
    ANTIGRAVITY_SOURCE_TYPE,
    ConversationRecord,
    GenerationInfo,
    discover_conversations,
    read_generation_metadata,
    read_jsonl_steps,
)
from .events import (
    Step,
    ToolCallPairer,
    checkpoint_index,
    model_from_settings,
    parse_settings_change,
    parse_steps,
    step_to_messages,
    step_tool_calls,
    to_compaction_event,
    to_model_event,
)

if TYPE_CHECKING:
    from inspect_scout import Transcript

logger = getLogger(__name__)

_MAX_SUBAGENT_DEPTH = 5

_SPAWN_RESULT_MARKER = "Created the following subagents:"
_CONVERSATION_ID_RE = re.compile(r'"conversationId"\s*:\s*"([0-9a-fA-F-]{36})"')


async def antigravity(
    path: str | PathLike[str] | None = None,
    conversation_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from Antigravity CLI conversations.

    Args:
        path: Antigravity data directory. Defaults to
            ``~/.gemini/antigravity-cli``. May also be a ``brain`` directory
            or a single conversation directory (``brain/<id>``).
        conversation_id: Specific conversation ID to import.
        from_time: Only fetch conversations whose transcript modification
            time (``st_mtime`` — not the conversation's run time, and reset
            by ``cp``/``git checkout``/rsync) is on or after this time
        to_time: Only fetch conversations whose transcript modification time
            is before this time
        limit: Maximum number of transcripts to yield.

    Yields:
        Transcript objects ready for insertion into transcript database.
        Sub-agent conversations are inlined into their parent as agent spans
        and not yielded at the top level.
    """
    records = discover_conversations(path=path, from_time=from_time, to_time=to_time)
    if not records:
        logger.info("No Antigravity conversations found")
        return

    records_by_id = {record.conversation_id: record for record in records}

    # Pre-scan to identify sub-agent children from their parents'
    # invoke_subagent results, so children are inlined into their parent's
    # span rather than yielded standalone. Every parent must be scanned
    # before yielding, but only the child ids are kept — re-parsing in the
    # yield loop keeps peak memory at one conversation (plus its children)
    # at a time. When a specific conversation is requested the exclusion set
    # is unused (its children parse on demand during span inlining).
    child_ids: set[str] = set()
    if conversation_id is None:
        for record in records:
            child_ids.update(_extract_child_conversation_ids(_read_steps(record)))

    count = 0
    matched = 0
    for record in records:
        if limit is not None and count >= limit:
            return
        cid = record.conversation_id
        if conversation_id is not None:
            if cid != conversation_id:
                continue
        elif cid in child_ids:
            # KNOWN LIMITATION: this suppression is scoped to a single
            # import. A time-windowed import that sees a child without its
            # parent yields the child standalone, storing its events twice
            # across imports (see docs/db_importing.qmd).
            continue
        matched += 1
        transcript = _create_transcript(record, records_by_id)
        if transcript is not None:
            count += 1
            yield transcript

    if conversation_id is not None and matched == 0:
        logger.warning("conversation_id=%r matched no conversations", conversation_id)


def _read_steps(record: ConversationRecord) -> list[Step]:
    """Read and validate a conversation's steps (empty if unreadable)."""
    try:
        raw_steps = read_jsonl_steps(record.transcript_path)
    except OSError as e:
        logger.warning("Skipping unreadable file %s: %s", record.transcript_path, e)
        return []
    return parse_steps(raw_steps)


def _extract_child_conversation_ids(steps: list[Step]) -> list[str]:
    """Extract child conversation ids from invoke_subagent result steps."""
    ids: list[str] = []
    for step in steps:
        if (
            step.type == "GENERIC"
            and step.content
            and (_SPAWN_RESULT_MARKER in step.content)
        ):
            ids.extend(_CONVERSATION_ID_RE.findall(step.content))
    return ids


def _extract_subagent_role_names(step: Step) -> list[str | None]:
    """Extract subagent role names from a planner step's spawn calls.

    ``invoke_subagent`` args carry ``Subagents: [{"Role", "Prompt", …}]``,
    ordered to match the ``conversationId`` order in the spawn result (the
    same FIFO design as tool-result pairing). Entries without a ``Role``
    yield None to keep that alignment.
    """
    roles: list[str | None] = []
    for tc in step.tool_calls or []:
        if tc.name == "invoke_subagent":
            subagents = tc.args.get("Subagents")
            if isinstance(subagents, list):
                for sub in subagents:
                    role = sub.get("Role") if isinstance(sub, dict) else None
                    roles.append(role if isinstance(role, str) else None)
    return roles


def _create_transcript(
    record: ConversationRecord,
    records_by_id: dict[str, ConversationRecord],
) -> "Transcript | None":
    """Create a Transcript from a discovered conversation."""
    from inspect_scout import Transcript

    steps = _read_steps(record)
    generations = read_generation_metadata(record.db_path) if record.db_path else []
    # child conversation id -> role name, filled in from spawn calls as
    # _convert_steps encounters them
    roles: dict[str, str] = {}

    messages, events, info = _convert_steps(
        steps,
        generations,
        records_by_id=records_by_id,
        roles=roles,
        depth=0,
    )
    if not messages:
        return None

    apply_working_start(events)

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for evt in events:
        if isinstance(evt, ModelEvent):
            apply_ids(evt)
    apply_ids(messages)

    metadata: dict[str, Any] = {}
    if record.title:
        metadata["title"] = record.title
    if info.compaction_count:
        metadata["compaction_count"] = info.compaction_count
    if info.child_ids:
        metadata["subagent_conversation_ids"] = info.child_ids
    if info.settings_model:
        metadata["model_selection"] = info.settings_model

    # Token totals from decoded generation metadata (best-effort; see client)
    totals = [
        g.usage.total_tokens
        for g in generations
        if g.usage is not None and g.usage.total_tokens is not None
    ]
    total_tokens = sum(totals) if totals else None

    # Model: first wire model id (matching claude_code), falling back to the
    # display name from settings chrome
    model = next((g.model for g in generations if g.model), None) or info.settings_model

    # Total time (wall clock minus idle gaps, derived from event timeline)
    total_time: float | None = None
    if events:
        timeline = timeline_build(events)
        root = timeline.root
        wall_clock = (root.end_time() - root.start_time()).total_seconds()
        total_time = wall_clock - root.idle_time()

    return Transcript(
        transcript_id=record.conversation_id,
        source_type=ANTIGRAVITY_SOURCE_TYPE,
        source_id=record.conversation_id,
        source_uri=str(record.transcript_path),
        date=info.first_timestamp,
        agent="antigravity",
        model=model,
        message_count=len(messages),
        total_time=total_time if total_time and total_time > 0 else None,
        total_tokens=total_tokens,
        messages=messages,
        events=events,
        metadata=metadata,
    )


@dataclass
class _ConversionInfo:
    settings_model: str | None = None
    compaction_count: int = 0
    child_ids: list[str] = field(default_factory=list)
    first_timestamp: str | None = None


def _convert_steps(
    steps: list[Step],
    generations: list[GenerationInfo],
    *,
    records_by_id: dict[str, ConversationRecord],
    roles: dict[str, str],
    depth: int,
) -> tuple[list[ChatMessage], list[Event], _ConversionInfo]:
    """Convert a conversation's steps to messages and events.

    Sub-agent spawns are inlined as agent spans at the point of the spawn
    result, bounded by ``depth`` against reference cycles.
    """
    messages: list[ChatMessage] = []
    events: list[Event] = []
    info = _ConversionInfo()
    pairer = ToolCallPairer()
    pending_roles: deque[str | None] = deque()
    generation_ordinal = 0

    for step in steps:
        if info.first_timestamp is None and step.created_at:
            info.first_timestamp = step.created_at

        if step.type == "CHECKPOINT":
            # `{{ CHECKPOINT 0 }}` opens every conversation (a session-start
            # preamble); later checkpoints are real compaction boundaries.
            # Their content is the replacement context the model saw, so it
            # enters the message stream (matching claude_code), with the
            # CompactionEvent as the boundary marker.
            if (checkpoint_index(step) or 0) > 0:
                info.compaction_count += 1
                events.append(to_compaction_event(step))
                if step.content:
                    messages.append(ChatMessageSystem(content=step.content))
            continue

        if step.type == "USER_INPUT" and step.content:
            settings = parse_settings_change(step.content)
            if settings and info.settings_model is None:
                info.settings_model = model_from_settings(settings)

        tool_calls = step_tool_calls(step) if step.type == "PLANNER_RESPONSE" else []
        new_messages = step_to_messages(step, tool_calls, pairer)

        if step.type == "PLANNER_RESPONSE":
            generation = (
                generations[generation_ordinal]
                if generation_ordinal < len(generations)
                else None
            )
            generation_ordinal += 1
            assistant = next(
                (m for m in new_messages if isinstance(m, ChatMessageAssistant)),
                None,
            )
            if assistant is not None:
                events.append(
                    to_model_event(
                        step,
                        prior_messages=messages,
                        assistant_message=assistant,
                        model=(generation.model if generation else None)
                        or info.settings_model
                        or "unknown",
                        usage=generation.usage if generation else None,
                    )
                )
            pairer.push(tool_calls)
            pending_roles.extend(_extract_subagent_role_names(step))

        messages.extend(new_messages)

        # Inline spawned sub-agents as agent spans at the spawn result.
        if (
            step.type == "GENERIC"
            and step.content
            and (_SPAWN_RESULT_MARKER in step.content)
        ):
            for child_id in _CONVERSATION_ID_RE.findall(step.content):
                if child_id in info.child_ids:
                    # Resume seams can duplicate steps verbatim; inlining the
                    # same child twice would emit colliding span ids.
                    continue
                role = pending_roles.popleft() if pending_roles else None
                if role is not None:
                    roles[child_id] = role
                info.child_ids.append(child_id)
                events.extend(
                    _create_subagent_span_events(
                        child_id,
                        records_by_id=records_by_id,
                        roles=roles,
                        depth=depth,
                    )
                )

    return messages, events, info


def _conversation_time_bounds(
    steps: list[Step],
) -> tuple[datetime | None, datetime | None]:
    """Return the (earliest, latest) parsed step timestamps of a conversation."""
    timestamps: list[datetime] = []
    for step in steps:
        ts = parse_timestamp(step.created_at)
        if ts is not None:
            timestamps.append(ts)
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def _create_subagent_span_events(
    child_id: str,
    *,
    records_by_id: dict[str, ConversationRecord],
    roles: dict[str, str],
    depth: int,
) -> list[Event]:
    """Convert a child conversation to an agent span's events.

    Produces ``SpanBeginEvent(type="agent")`` / child events /
    ``SpanEndEvent``. A child with no local data (e.g. a cancelled spawn)
    produces no events.
    """
    if depth >= _MAX_SUBAGENT_DEPTH:
        logger.warning("Max sub-agent depth reached at %s", child_id)
        return []
    child = records_by_id.get(child_id)
    if child is None:
        logger.warning("Sub-agent conversation %s not found on disk", child_id)
        return []

    child_steps = _read_steps(child)
    child_generations = read_generation_metadata(child.db_path) if child.db_path else []
    _, agent_events, _ = _convert_steps(
        child_steps,
        child_generations,
        records_by_id=records_by_id,
        roles=roles,
        depth=depth + 1,
    )

    sub_begin, sub_end = _conversation_time_bounds(child_steps)
    begin_ts = sub_begin or utcnow()
    end_ts = sub_end or begin_ts

    agent_span_id = f"agent-{child_id}"
    span_begin = SpanBeginEvent(
        id=agent_span_id,
        type="agent",
        name=roles.get(child_id, "subagent"),
        timestamp=begin_ts,
    )
    span_end = SpanEndEvent(id=agent_span_id, timestamp=end_ts)
    return [span_begin, *agent_events, span_end]
