"""Codex CLI transcript import functionality.

This module provides functions to import transcripts from Codex CLI
rollout files into an Inspect Scout transcript database.

Codex sessions are stored at:
    $CODEX_HOME/sessions/YYYY/MM/DD/rollout-<timestamp>-<thread-uuid>.jsonl

Each rollout file is one thread: resuming a session appends to the same
file, while forks and spawned sub-agents create new files linked by
forked_from_id / parent_thread_id.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, stable_message_ids

if TYPE_CHECKING:
    from inspect_scout import Transcript

from inspect_swe._codex_cli._events.rollout_extraction import sum_scout_tokens
from inspect_swe._codex_cli._events.rollout_models import (
    RolloutEvent,
    SessionMetaEvent,
    TurnContextEvent,
    parse_rollout_events,
)

from .client import (
    CODEX_SOURCE_TYPE,
    discover_rollout_files,
    find_rollout_by_thread_id,
    get_source_uri,
    load_thread_names,
    peek_session_meta,
    read_rollout_lines,
    rollout_thread_id,
    sessions_root_for,
)
from .events import process_rollout_events

logger = getLogger(__name__)


async def codex(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
    include_archived: bool = False,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from Codex CLI sessions.

    Each Codex thread is one rollout file and becomes one Scout transcript.
    Sub-agent threads spawned via spawn_agent are nested inside their
    parent's transcript (and excluded from top-level import); review-mode
    threads are imported as standalone transcripts; internal threads
    (compaction, memory consolidation) are skipped.

    Forked threads are imported as separate transcripts, with
    ``forked_from_id`` recorded in metadata. Threads that inherit a parent
    history prefix by reference (paginated ``history_base``) have that
    prefix resolved from the parent rollout so the transcript is complete.

    Args:
        path: Path to a Codex sessions directory or specific rollout file.
            If None, scans $CODEX_HOME/sessions
        session_id: Specific thread UUID to import
        from_time: Only fetch sessions modified on or after this time
        to_time: Only fetch sessions modified before this time
        limit: Maximum number of transcripts to yield
        include_archived: Also scan $CODEX_HOME/archived_sessions
            (only applies when path is None)

    Yields:
        Transcript objects ready for insertion into transcript database
    """
    rollout_files = discover_rollout_files(
        path, session_id, from_time, to_time, include_archived
    )

    if not rollout_files:
        logger.info("No Codex rollout files found")
        return

    thread_names = load_thread_names()
    count = 0

    for rollout_file in rollout_files:
        if limit is not None and count >= limit:
            return

        meta = _peek_meta_event(rollout_file)
        if meta is None:
            logger.warning(
                f"Skipping file without a session_meta line "
                f"(not a supported codex rollout): {rollout_file}"
            )
            continue

        if _skip_for_source(meta, rollout_file):
            continue

        transcript = await _process_rollout_file(rollout_file, meta, thread_names)
        if transcript is not None:
            yield transcript
            count += 1


def _peek_meta_event(rollout_file: Path) -> SessionMetaEvent | None:
    """Parse the session_meta line of a rollout file."""
    from inspect_swe._codex_cli._events.rollout_models import parse_rollout_event

    raw = peek_session_meta(rollout_file)
    if raw is None:
        return None
    event = parse_rollout_event(raw)
    return event if isinstance(event, SessionMetaEvent) else None


def _skip_for_source(meta: SessionMetaEvent, rollout_file: Path) -> bool:
    """Whether to skip a rollout at top level based on its source.

    - thread_spawn sub-agents: nested inside their parent's transcript
    - compaction / memory-consolidation / other internal threads: skipped
    - review threads: imported standalone (their parent has no anchoring
      tool call to nest them under)
    """
    if isinstance(meta.source, dict) and "internal" in meta.source:
        logger.debug(f"Skipping internal rollout: {rollout_file}")
        return True
    subagent = meta.subagent_source()
    if subagent is None:
        return False
    if isinstance(subagent, dict):
        if "thread_spawn" in subagent:
            logger.debug(f"Skipping spawned sub-agent rollout: {rollout_file}")
            return True
        return False
    if subagent == "review":
        return False
    logger.debug(f"Skipping internal subagent rollout ({subagent}): {rollout_file}")
    return True


async def _process_rollout_file(
    rollout_file: Path,
    meta: SessionMetaEvent,
    thread_names: dict[str, str],
) -> "Transcript" | None:
    """Process a single rollout file into a transcript."""
    raw_lines = read_rollout_lines(rollout_file)
    if not raw_lines:
        return None

    search_roots = [sessions_root_for(rollout_file)]

    # Resolve a referenced parent-history prefix (paginated forks) so the
    # transcript is complete. Copied forks inline the prefix and need nothing.
    if meta.history_base is not None:
        prefix = _resolve_history_base(
            meta.history_base.thread_id,
            meta.history_base.end_ordinal_exclusive,
            search_roots,
        )
        raw_lines = prefix + raw_lines

    events = parse_rollout_events(raw_lines)
    if not events:
        return None

    return await _create_transcript(
        events, rollout_file, meta, thread_names, search_roots
    )


def _resolve_history_base(
    parent_thread_id: str,
    end_ordinal_exclusive: int,
    search_roots: list[Path],
) -> list[dict[str, Any]]:
    """Load the inherited prefix of a parent rollout (by ordinal)."""
    parent_file = find_rollout_by_thread_id(parent_thread_id, search_roots)
    if parent_file is None:
        logger.warning(f"Parent rollout for history_base not found: {parent_thread_id}")
        return []
    prefix: list[dict[str, Any]] = []
    for line in read_rollout_lines(parent_file):
        if line.get("type") == "session_meta":
            continue
        ordinal = line.get("ordinal")
        if isinstance(ordinal, int) and ordinal >= end_ordinal_exclusive:
            break
        prefix.append(line)
    return prefix


async def _create_transcript(
    events: list[RolloutEvent],
    rollout_file: Path,
    meta: SessionMetaEvent,
    thread_names: dict[str, str],
    search_roots: list[Path],
) -> "Transcript" | None:
    """Create a Transcript from parsed rollout events."""
    from inspect_ai.event import timeline_build

    from inspect_scout import Transcript
    from inspect_scout._transcript.messages import span_messages

    thread_id = meta.thread_id or rollout_thread_id(rollout_file)
    if thread_id is None:
        thread_id = rollout_file.name.removesuffix(".zst").removesuffix(".jsonl")

    scout_events: list[Event] = []
    async for event in process_rollout_events(events, search_roots):
        scout_events.append(event)
    if not scout_events:
        return None

    # Extract messages via timeline (excludes sub-agent messages, handles
    # compaction)
    timeline = timeline_build(scout_events)
    messages: list[ChatMessage] = span_messages(timeline.root, compaction="all")

    # Skip transcripts with no messages (e.g. context-only threads)
    if not messages:
        return None

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for event in scout_events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    model_name = _extract_model_name(events)
    total_tokens = sum_scout_tokens(scout_events)
    root = timeline.root
    wall_clock = (root.end_time() - root.start_time()).total_seconds()
    total_time = wall_clock - root.idle_time()
    first_timestamp = meta.timestamp or (events[0].timestamp if events else None)

    return Transcript(
        transcript_id=thread_id,
        source_type=CODEX_SOURCE_TYPE,
        source_id=thread_id,
        source_uri=get_source_uri(rollout_file, thread_id),
        date=first_timestamp,
        task_set=meta.cwd,
        task_id=thread_names.get(thread_id) or thread_id,
        task_repeat=1,
        agent="codex-cli",
        agent_args=None,
        model=model_name,
        model_options=None,
        score=None,
        success=None,
        message_count=len(messages),
        total_tokens=total_tokens if total_tokens > 0 else None,
        total_time=total_time if total_time > 0 else None,
        error=None,
        limit=None,
        messages=messages,
        events=scout_events,
        metadata=_extract_metadata(meta),
    )


def _extract_model_name(events: list[RolloutEvent]) -> str | None:
    """The model in effect at the start of the thread (first turn_context)."""
    for event in events:
        if isinstance(event, TurnContextEvent) and event.model:
            return event.model
    return None


def _extract_metadata(meta: SessionMetaEvent) -> dict[str, Any]:
    """Session-level metadata for the transcript."""
    metadata: dict[str, Any] = {}
    if meta.cwd:
        metadata["cwd"] = meta.cwd
    if meta.originator:
        metadata["originator"] = meta.originator
    if meta.cli_version:
        metadata["version"] = meta.cli_version
    if meta.source is not None:
        metadata["source"] = meta.source
    if meta.model_provider:
        metadata["model_provider"] = meta.model_provider
    if meta.forked_from_id:
        metadata["forked_from_id"] = meta.forked_from_id
    if meta.parent_thread_id:
        metadata["parent_thread_id"] = meta.parent_thread_id
    if meta.history_mode != "legacy":
        metadata["history_mode"] = meta.history_mode
    if meta.history_base is not None:
        metadata["history_base_thread_id"] = meta.history_base.thread_id
    if meta.agent_nickname:
        metadata["agent_nickname"] = meta.agent_nickname
    if meta.agent_role:
        metadata["agent_role"] = meta.agent_role
    if meta.git is not None:
        if meta.git.branch:
            metadata["gitBranch"] = meta.git.branch
        if meta.git.commit_hash:
            metadata["gitCommit"] = meta.git.commit_hash
        if meta.git.repository_url:
            metadata["gitRepository"] = meta.git.repository_url
    return metadata


# Re-exports
__all__ = ["codex", "CODEX_SOURCE_TYPE"]
