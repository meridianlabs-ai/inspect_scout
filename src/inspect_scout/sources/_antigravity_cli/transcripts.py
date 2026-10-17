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
    ToolEvent,
    timeline_build,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    stable_message_ids,
)
from inspect_ai.tool import ToolCall

from .._util import apply_working_start, parse_timestamp, utcnow
from .client import (
    ANTIGRAVITY_CLI_SOURCE_TYPE,
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
    is_tool_result_step,
    model_from_settings,
    parse_settings_change,
    parse_steps,
    step_to_messages,
    step_tool_calls,
    to_compaction_event,
    to_info_event,
    to_model_event,
    unknown_tool_call,
)

if TYPE_CHECKING:
    from inspect_scout import Transcript

logger = getLogger(__name__)

_MAX_SUBAGENT_DEPTH = 5

_SPAWN_RESULT_MARKER = "Created the following subagents:"
_CONVERSATION_ID_RE = re.compile(r'"conversationId"\s*:\s*"([0-9a-fA-F-]{36})"')


async def antigravity_cli(
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
        and not yielded at the top level. ``model`` falls back to the
        display name from session settings, and ``total_tokens`` is None,
        when the conversation store (``conversations/<id>.db``) is absent
        or undecodable.
    """
    # Discover everything and apply the time window only to what is
    # yielded: the child lookup map and the child-id pre-scan must see
    # conversations outside the window, since a parent keeps writing after
    # its sub-agents finish (a window can hold the child but not the parent,
    # or vice versa).
    records = discover_conversations(path=path)
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
            continue
        matched += 1
        if from_time is not None and record.mtime < from_time.timestamp():
            continue
        if to_time is not None and record.mtime >= to_time.timestamp():
            continue
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
    except (OSError, ValueError) as e:
        # ValueError covers UnicodeDecodeError from non-UTF-8 bytes
        logger.warning("Skipping unreadable file %s: %s", record.transcript_path, e)
        return []
    return parse_steps(raw_steps)


def _spawn_result_content(step: Step, call: ToolCall | None) -> str | None:
    """The content of an ``invoke_subagent`` result, or None for any other step.

    The marker text alone is not evidence of a spawn: ordinary tool output
    (a command that greps these very logs) can quote it, and acting on that
    would hide an unrelated conversation from the top level and inline it
    under the wrong parent. The step must be a typed ``INVOKE_SUBAGENT``
    result or pair positionally with an ``invoke_subagent`` call.
    """
    if not is_tool_result_step(step):
        return None
    spawned = step.type == "INVOKE_SUBAGENT" or (
        call is not None and call.function == "invoke_subagent"
    )
    if spawned and step.content and _SPAWN_RESULT_MARKER in step.content:
        return step.content
    return None


def _extract_child_conversation_ids(steps: list[Step]) -> list[str]:
    """Extract child conversation ids from invoke_subagent result steps."""
    ids: list[str] = []
    pairer = ToolCallPairer()
    for step in steps:
        tool_calls = step_tool_calls(step) if step.type == "PLANNER_RESPONSE" else []
        pairing = pairer.advance(step, tool_calls)
        content = _spawn_result_content(step, pairing.call)
        if content:
            ids.extend(_CONVERSATION_ID_RE.findall(content))
    return ids


def _extract_subagent_role_names(call: ToolCall | None) -> list[str | None]:
    """Extract subagent role names from an ``invoke_subagent`` call.

    Its args carry ``Subagents: [{"Role", "Prompt", …}]``, ordered to match
    the ``conversationId`` order in the spawn result. Entries without a
    ``Role`` yield None to keep that alignment. A typed spawn result that
    paired with no call (``call`` None) yields no names.
    """
    if call is None or call.function != "invoke_subagent":
        return []
    subagents = call.arguments.get("Subagents")
    if not isinstance(subagents, list):
        return []
    roles: list[str | None] = []
    for sa in subagents:
        role = sa.get("Role") if isinstance(sa, dict) else None
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
        conversation_id=record.conversation_id,
        records_by_id=records_by_id,
        roles=roles,
        depth=0,
        inlining=frozenset({record.conversation_id}),
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
        source_type=ANTIGRAVITY_CLI_SOURCE_TYPE,
        source_id=record.conversation_id,
        source_uri=str(record.transcript_path),
        date=info.first_timestamp,
        agent="antigravity-cli",
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
    """The first `Model Selection` (the transcript-level model fallback)."""

    compaction_count: int = 0
    child_ids: list[str] = field(default_factory=list)
    first_timestamp: str | None = None


def _convert_steps(
    steps: list[Step],
    generations: list[GenerationInfo],
    *,
    conversation_id: str,
    records_by_id: dict[str, ConversationRecord],
    roles: dict[str, str],
    depth: int,
    inlining: frozenset[str],
) -> tuple[list[ChatMessage], list[Event], _ConversionInfo]:
    """Convert a conversation's steps to messages and events.

    Sub-agent spawns are inlined as agent spans at the point of the spawn
    result. ``inlining`` holds the conversation ids on the current inlining
    path (the root plus every enclosing sub-agent), so a spawn result naming
    an ancestor is skipped rather than nested into a cycle; ``depth`` bounds
    legitimate nesting.
    """
    # `messages` is the complete transcript history; `context` is what the
    # model currently sees, which a compaction replaces with the checkpoint
    # summary. ModelEvent.input takes `context` so span_messages() can
    # reconstruct each compaction region without repeating earlier ones.
    messages: list[ChatMessage] = []
    context: list[ChatMessage] = []
    events: list[Event] = []
    info = _ConversionInfo()
    pairer = ToolCallPairer()
    # The most recent `Model Selection`: the per-event model fallback when
    # generation metadata is unavailable (info.settings_model keeps the first)
    current_model: str | None = None

    # gen_metadata has one row per planner step, matched by ordinal. A
    # dropped planner step (unparseable line) shifts every later row onto
    # the wrong step, and a step_index gap is the only evidence of where.
    # When the counts agree no planner step is missing, so gaps are result
    # steps and the ordinals stay valid.
    generation_ordinal = 0
    planner_count = sum(1 for step in steps if step.type == "PLANNER_RESPONSE")
    generations_aligned = len(generations) == planner_count
    trusted_generations = generations

    for step in steps:
        if info.first_timestamp is None and step.created_at:
            info.first_timestamp = step.created_at

        tool_calls = step_tool_calls(step) if step.type == "PLANNER_RESPONSE" else []
        pairing = pairer.advance(step, tool_calls)
        if pairing.gap:
            # Routine when a declined call or interrupted turn left no result
            # step (see ToolCallPairer); the parse sites already warn when a
            # line was actually dropped.
            if pairing.abandoned:
                logger.debug(
                    "Step(s) missing before step %d of %s; %d pending tool call(s) "
                    "left unattributed",
                    step.step_index,
                    conversation_id,
                    len(pairing.abandoned),
                )
            if trusted_generations and not generations_aligned:
                logger.warning(
                    "Step(s) missing before step %d of %s; generation metadata "
                    "no longer aligned from here",
                    step.step_index,
                    conversation_id,
                )
                trusted_generations = []
        for call in pairing.abandoned:
            events.extend(
                _create_tool_span_events(call, None, pairing.started, conversation_id)
            )

        if step.type == "CHECKPOINT":
            # `{{ CHECKPOINT 0 }}` opens every conversation (a session-start
            # preamble); later checkpoints are real compaction boundaries.
            # Their content is the replacement context the model saw, so it
            # enters the message stream (matching claude_code), with the
            # CompactionEvent as the boundary marker.
            index = checkpoint_index(step)
            if index is None:
                logger.warning(
                    "Dropping CHECKPOINT step %d without a {{ CHECKPOINT N }} marker",
                    step.step_index,
                )
            elif index > 0:
                info.compaction_count += 1
                events.append(to_compaction_event(step))
                context = []
                if step.content:
                    summary = ChatMessageSystem(content=step.content)
                    messages.append(summary)
                    context.append(summary)
            continue

        if step.type == "USER_INPUT" and step.content:
            settings = parse_settings_change(step.content)
            selected = model_from_settings(settings) if settings else None
            if selected:
                current_model = selected
                if info.settings_model is None:
                    info.settings_model = selected

        new_messages = step_to_messages(step, tool_calls, pairing.call)

        if step.type == "PLANNER_RESPONSE":
            generation = (
                trusted_generations[generation_ordinal]
                if generation_ordinal < len(trusted_generations)
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
                        prior_messages=context,
                        assistant_message=assistant,
                        model=(generation.model if generation else None)
                        or current_model
                        or "unknown",
                        usage=generation.usage if generation else None,
                    )
                )
        elif is_tool_result_step(step):
            call = pairing.call or unknown_tool_call(step)
            events.extend(
                _create_tool_span_events(
                    call,
                    step,
                    pairing.started if pairing.call else None,
                    conversation_id,
                )
            )
        elif step.type in ("SYSTEM_MESSAGE", "ERROR_MESSAGE"):
            events.append(to_info_event(step))

        messages.extend(new_messages)
        context.extend(new_messages)

        # Inline spawned sub-agents as agent spans at the spawn result.
        spawn_result = _spawn_result_content(step, pairing.call)
        if spawn_result:
            role_names = deque(_extract_subagent_role_names(pairing.call))
            for child_id in _CONVERSATION_ID_RE.findall(spawn_result):
                if child_id in info.child_ids:
                    # Resume seams can duplicate steps verbatim; inlining the
                    # same child twice would emit colliding span ids.
                    continue
                role = role_names.popleft() if role_names else None
                if role is not None:
                    roles[child_id] = role
                info.child_ids.append(child_id)
                events.extend(
                    _create_subagent_span_events(
                        child_id,
                        records_by_id=records_by_id,
                        roles=roles,
                        depth=depth,
                        inlining=inlining,
                    )
                )

    final = pairer.finish()
    for call in final.abandoned:
        events.extend(
            _create_tool_span_events(call, None, final.started, conversation_id)
        )

    return messages, events, info


def _create_tool_span_events(
    call: ToolCall,
    result_step: Step | None,
    started: datetime | None,
    conversation_id: str,
) -> list[Event]:
    """Wrap a tool call and its result in a tool span (matching claude_code).

    Produces ``SpanBeginEvent(type="tool")`` / ``ToolEvent`` / ``SpanEndEvent``.
    ``started`` is the planner step's timestamp (the JSONL records when a
    call was issued, not when the tool began). ``result_step`` is None for a
    call that never received a result; its ToolEvent then has an empty
    result and ``completed`` equal to its start, so the missing result is
    visible in the timeline rather than silently absent. Call ids restart
    per conversation, so the span id is scoped by ``conversation_id`` to stay
    unique across inlined sub-agents.
    """
    completed = parse_timestamp(result_step.created_at) if result_step else None
    timestamp = started or completed or utcnow()
    completed = completed or timestamp
    span_id = f"tool-{conversation_id}-{call.id}"
    return [
        SpanBeginEvent(
            id=span_id, type="tool", name=call.function, timestamp=timestamp
        ),
        ToolEvent(
            id=call.id,
            function=call.function,
            arguments=call.arguments,
            result=(result_step.content or "") if result_step else "",
            timestamp=timestamp,
            completed=completed,
            span_id=span_id,
        ),
        SpanEndEvent(id=span_id, timestamp=completed),
    ]


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
    inlining: frozenset[str],
) -> list[Event]:
    """Convert a child conversation to an agent span's events.

    Produces ``SpanBeginEvent(type="agent")`` / child events /
    ``SpanEndEvent``. A child with no local data (e.g. a cancelled spawn),
    or one already on the inlining path (a spawn cycle), produces no events.
    """
    if child_id in inlining:
        logger.warning("Sub-agent %s spawns an ancestor of itself; skipping", child_id)
        return []
    if depth >= _MAX_SUBAGENT_DEPTH:
        logger.warning("Max sub-agent depth reached at %s", child_id)
        return []
    child = records_by_id.get(child_id)
    if child is None:
        logger.warning("Sub-agent conversation %s not found on disk", child_id)
        return []

    agent_span_id = f"agent-{child_id}"
    child_steps = _read_steps(child)
    sub_begin, sub_end = _conversation_time_bounds(child_steps)
    begin_ts = sub_begin or utcnow()
    end_ts = sub_end or begin_ts

    child_generations = read_generation_metadata(child.db_path) if child.db_path else []
    _, agent_events, _ = _convert_steps(
        child_steps,
        child_generations,
        conversation_id=child_id,
        records_by_id=records_by_id,
        roles=roles,
        depth=depth + 1,
        inlining=inlining | {child_id},
    )
    # Re-parent top-level items so event_tree() nests them under the agent
    # span (matching atif)
    for evt in agent_events:
        if isinstance(evt, SpanBeginEvent):
            if evt.parent_id is None:
                evt.parent_id = agent_span_id
        elif not isinstance(evt, SpanEndEvent):
            if evt.span_id is None:
                evt.span_id = agent_span_id

    span_begin = SpanBeginEvent(
        id=agent_span_id,
        type="agent",
        name=roles.get(child_id, "subagent"),
        timestamp=begin_ts,
    )
    span_end = SpanEndEvent(id=agent_span_id, timestamp=end_ts)
    return [span_begin, *agent_events, span_end]
