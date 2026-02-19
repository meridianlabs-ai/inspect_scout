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
    discover_session_files,
    get_project_path_from_file,
    get_source_uri,
    read_jsonl_events,
)
from .detection import get_session_id
from .events import process_parsed_events
from .extraction import (
    extract_messages_from_scout_events,
    extract_model_name,
    extract_session_metadata,
    get_first_timestamp,
    sum_latency,
    sum_tokens,
)
from .models import BaseEvent, parse_events
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

    count = 0

    for session_file in session_files:
        if limit and count >= limit:
            return

        async for transcript in _process_session_file(session_file):
            yield transcript
            count += 1

            if limit and count >= limit:
                return


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

    # Extract messages from Scout events
    messages: list[ChatMessage] = extract_messages_from_scout_events(scout_events)

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
    total_tokens = sum_tokens(events)
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
        task_repeat=segment_index,
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
