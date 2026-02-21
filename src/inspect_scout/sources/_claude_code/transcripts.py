"""Claude Code transcript import functionality.

This module provides functions to import transcripts from Claude Code
session files into an Inspect Scout transcript database.

Claude Code sessions are stored at:
    ~/.claude/projects/[encoded-path]/[session-uuid].jsonl

Each session file contains JSONL events representing user messages,
assistant responses, tool calls, and system events. Sessions can be
split by /clear commands into multiple transcripts.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, stable_message_ids

if TYPE_CHECKING:
    from inspect_scout import Transcript

from .client import (
    CLAUDE_CODE_SOURCE_TYPE,
    _find_sessions_in_directory,
    discover_session_files,
    get_project_path_from_file,
    get_source_uri,
    peek_first_timestamp,
    peek_slug,
    read_jsonl_events,
)
from .detection import get_session_id
from .events import process_parsed_events
from .extraction import (
    extract_model_name,
    extract_session_metadata,
    get_first_timestamp,
    sum_latency,
    sum_scout_tokens,
)
from .models import BaseEvent, consolidate_assistant_events, parse_events
from .tree import (
    build_event_tree,
    flatten_tree_chronological,
    get_conversation_events,
    split_on_clear,
)

logger = getLogger(__name__)


async def claude_code(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from Claude Code sessions.

    Each Claude Code session can contain multiple conversations separated
    by /clear commands. Each conversation becomes one Scout transcript.

    When Claude Code enters plan mode and executes a plan, it creates
    separate session files that share the same slug. These related sessions
    are merged into a single transcript.

    Args:
        path: Path to Claude Code project directory or specific session file.
            If None, scans all projects in ~/.claude/projects/
        session_id: Specific session UUID to import
        from_time: Only fetch sessions modified on or after this time
        to_time: Only fetch sessions modified before this time
        limit: Maximum number of transcripts to yield

    Yields:
        Transcript objects ready for insertion into transcript database
    """
    # Discover session files
    session_files = discover_session_files(path, session_id, from_time, to_time)

    if not session_files:
        logger.info("No Claude Code session files found")
        return

    # Group files by slug for merging plan+execute sessions
    slug_groups: dict[str | None, list[Path]] = {}
    for f in session_files:
        slug = peek_slug(f)
        slug_groups.setdefault(slug, []).append(f)

    # Backfill missing slug partners from sibling files in the same project dir
    _backfill_slug_groups(slug_groups, session_files)

    # Iterate files in mtime order (newest first, as returned by
    # discover_session_files).  For each file we either process it
    # directly (no slug / single-file slug) or process the full merged
    # slug group the first time we encounter it.  This lets us stop
    # early when limit is set — the newest transcripts come from the
    # newest files so we avoid touching old ones entirely.
    processed_slugs: set[str] = set()
    count = 0

    for f in session_files:
        if limit and count >= limit:
            return

        slug = peek_slug(f)

        if slug is not None and slug in processed_slugs:
            # Already handled as part of a merged slug group
            continue

        if slug is not None and len(slug_groups.get(slug, [])) > 1:
            # Multi-file slug group — merge and mark as processed
            processed_slugs.add(slug)
            merged = await _merge_slug_group(slug_groups[slug], slug)
            if merged:
                yield merged
                count += 1
        else:
            # Single file (no slug or only one file for this slug)
            if slug is not None:
                processed_slugs.add(slug)
            async for transcript in _process_session_file(f):
                yield transcript
                count += 1
                if limit and count >= limit:
                    return


def _backfill_slug_groups(
    slug_groups: dict[str | None, list[Path]],
    session_files: list[Path],
) -> None:
    """Backfill missing slug partners from sibling files in the same project dir.

    When time filters, session_id filters, or specific file paths cause only
    one half of a slug pair to be discovered, this function scans sibling
    files in the same project directory to find the missing partners.

    Mutates slug_groups in place.

    Args:
        slug_groups: Mapping of slug → list of discovered file paths
        session_files: All originally discovered session files
    """
    discovered_paths = {f.resolve() for f in session_files}
    dir_cache: dict[Path, list[Path]] = {}
    slug_cache: dict[Path, str | None] = {}

    for slug, files in list(slug_groups.items()):
        if slug is None:
            continue

        # Collect project directories for this slug group
        project_dirs = {f.parent for f in files}

        for project_dir in project_dirs:
            if project_dir not in dir_cache:
                dir_cache[project_dir] = _find_sessions_in_directory(project_dir)

            for sibling in dir_cache[project_dir]:
                resolved = sibling.resolve()
                if resolved in discovered_paths:
                    continue
                if sibling not in slug_cache:
                    slug_cache[sibling] = peek_slug(sibling)
                if slug_cache[sibling] == slug:
                    files.append(sibling)
                    discovered_paths.add(resolved)


async def _merge_slug_group(
    files: list[Path],
    slug: str,
) -> "Transcript" | None:
    """Merge multiple session files sharing the same slug into one transcript.

    When Claude Code enters plan mode and executes the plan, it creates
    separate session files with different sessionIds but the same slug.
    This function merges them into a single transcript.

    Args:
        files: List of session file paths sharing the same slug
        slug: The shared slug identifier

    Returns:
        Merged Transcript, or None if no valid transcripts produced
    """
    from inspect_ai.event import InfoEvent

    from .util import parse_timestamp

    # Sort files by first event timestamp (chronological order)
    files_sorted = sorted(files, key=lambda f: peek_first_timestamp(f) or "")

    # Process each file through existing pipeline to get transcripts
    all_transcripts: list["Transcript"] = []
    for f in files_sorted:
        async for transcript in _process_session_file(f):
            all_transcripts.append(transcript)

    if not all_transcripts:
        return None

    if len(all_transcripts) == 1:
        return all_transcripts[0]

    # Merge transcripts
    first = all_transcripts[0]
    merged_events: list[Event] = list(first.events)
    merged_messages: list[ChatMessage] = list(first.messages)
    total_tokens = first.total_tokens or 0
    total_time = first.total_time or 0.0
    session_ids = [first.source_id] if first.source_id else []

    for i, transcript in enumerate(all_transcripts[1:], start=2):
        # Insert session boundary InfoEvent
        boundary_ts = parse_timestamp(transcript.date) or datetime.now()
        boundary_event = InfoEvent(
            source="claude-code",
            data=f"---\n\n*Context reset — session {i} of {len(all_transcripts)}*\n\n---",
            timestamp=boundary_ts,
        )
        merged_events.append(boundary_event)
        merged_events.extend(transcript.events)
        merged_messages.extend(transcript.messages)

        if transcript.total_tokens:
            total_tokens += transcript.total_tokens
        if transcript.total_time:
            total_time += transcript.total_time
        if transcript.source_id:
            session_ids.append(transcript.source_id)

    # Rebuild unified timeline from merged events
    from inspect_scout._transcript.timeline import build_timeline

    build_timeline(merged_events)

    # Build merged metadata
    metadata = dict(first.metadata)
    metadata["session_ids"] = session_ids

    from inspect_scout import Transcript

    return Transcript(
        transcript_id=first.transcript_id,
        source_type=CLAUDE_CODE_SOURCE_TYPE,
        source_id=first.source_id,
        source_uri=first.source_uri,
        date=first.date,
        task_set=first.task_set,
        task_id=slug,
        task_repeat=1,
        agent="claude-code",
        agent_args=None,
        model=first.model,
        model_options=None,
        score=None,
        success=None,
        message_count=len(merged_messages),
        total_tokens=total_tokens if total_tokens > 0 else None,
        total_time=total_time if total_time > 0.0 else None,
        error=None,
        limit=None,
        messages=merged_messages,
        events=merged_events,
        metadata=metadata,
    )


async def _process_session_file(
    session_file: Path,
) -> AsyncIterator["Transcript"]:
    """Process a single session file into transcripts.

    Handles /clear splitting - each segment becomes a separate transcript.

    Args:
        session_file: Path to the JSONL session file

    Yields:
        Transcript objects
    """
    session_path = session_file

    raw_events = read_jsonl_events(session_path)
    if not raw_events:
        return

    # Parse raw events to Pydantic models (validates format)
    events = parse_events(raw_events)
    events = consolidate_assistant_events(events)

    # Build tree and flatten for proper ordering
    tree = build_event_tree(events)
    flat_events = flatten_tree_chronological(tree)

    if not flat_events:
        return

    # Split on /clear commands BEFORE filtering (since filtering removes /clear)
    segments = split_on_clear(flat_events)

    # Extract session ID from events (more reliable than filename)
    base_session_id = None
    for event in events:
        sid = get_session_id(event)
        if sid:
            base_session_id = sid
            break
    if not base_session_id:
        # Fall back to filename
        base_session_id = session_path.stem

    # Process each segment as a separate transcript
    for segment_idx, segment_events in enumerate(segments):
        if not segment_events:
            continue

        # Filter to conversation events for this segment
        conversation_events = get_conversation_events(segment_events)
        if not conversation_events:
            continue

        transcript = await _create_transcript(
            conversation_events,
            session_path,
            base_session_id,
            segment_idx if len(segments) > 1 else None,
        )
        if transcript:
            yield transcript


async def _create_transcript(
    events: list[BaseEvent],
    session_file: Path,
    base_session_id: str,
    segment_index: int | None,
) -> "Transcript" | None:
    """Create a Transcript from conversation events.

    Args:
        events: List of conversation events (Pydantic models)
        session_file: Path to the source session file
        base_session_id: The session UUID
        segment_index: Index of this segment (if session was split), or None

    Returns:
        Transcript object, or None if creation fails
    """
    from inspect_scout import Transcript
    from inspect_scout._transcript.messages import span_messages
    from inspect_scout._transcript.timeline import build_timeline

    session_path = session_file
    project_dir = session_path.parent

    # Generate transcript ID
    if segment_index is not None:
        transcript_id = f"{base_session_id}-{segment_index}"
    else:
        transcript_id = base_session_id

    # Convert to Scout events using process_parsed_events (already Pydantic models)
    scout_events: list[Event] = []
    async for event in process_parsed_events(
        events, project_dir, session_file=session_path
    ):
        scout_events.append(event)

    # Extract messages via timeline (excludes subagent messages, handles compaction)
    timeline = build_timeline(scout_events)
    messages: list[ChatMessage] = span_messages(timeline.root, compaction="all")

    # Skip transcripts with no messages (e.g., system-only segments)
    if not messages:
        return None

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for event in scout_events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    # Extract metadata
    metadata = extract_session_metadata(events)
    model_name = extract_model_name(events)
    total_tokens = sum_scout_tokens(scout_events)
    total_time = sum_latency(events)
    first_timestamp = get_first_timestamp(events)

    # Get project path for task_set
    project_path = get_project_path_from_file(session_path)

    # Source URI
    source_uri = get_source_uri(session_path, transcript_id)

    return Transcript(
        transcript_id=transcript_id,
        source_type=CLAUDE_CODE_SOURCE_TYPE,
        source_id=base_session_id,
        source_uri=source_uri,
        date=first_timestamp,
        task_set=project_path,
        task_id=metadata.get("slug"),
        task_repeat=1,
        agent="claude-code",
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
        metadata=metadata,
    )


# Re-exports
__all__ = ["claude_code", "CLAUDE_CODE_SOURCE_TYPE"]
