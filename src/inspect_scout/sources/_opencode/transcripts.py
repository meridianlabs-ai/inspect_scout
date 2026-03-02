"""OpenCode transcript import functionality.

Reads sessions from OpenCode's SQLite database and yields
Transcript objects compatible with Inspect Scout.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, stable_message_ids

if TYPE_CHECKING:
    from inspect_scout import Transcript

from .client import (
    DEFAULT_DB_PATH,
    OPENCODE_SOURCE_TYPE,
    _ms_to_iso,
    discover_sessions,
    read_messages,
    read_parts,
)
from .events import process_session

logger = getLogger(__name__)


async def opencode(
    db_path: Path | str | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from OpenCode sessions.

    Args:
        db_path: Path to opencode.db. Defaults to ~/.local/share/opencode/opencode.db
        session_id: Specific session ID to import
        from_time: Only fetch sessions updated on or after this time
        to_time: Only fetch sessions updated before this time
        limit: Maximum number of transcripts to yield

    Yields:
        Transcript objects ready for insertion into transcript database
    """
    resolved_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    if not resolved_path.exists():
        logger.info(f"OpenCode database not found: {resolved_path}")
        return

    sessions = discover_sessions(
        db_path=resolved_path,
        session_id=session_id,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
    )

    if not sessions:
        logger.info("No OpenCode sessions found")
        return

    count = 0
    for session in sessions:
        if limit and count >= limit:
            return

        transcript = await _process_session(resolved_path, session.id)
        if transcript:
            yield transcript
            count += 1


async def _process_session(
    db_path: Path,
    session_id: str,
) -> "Transcript | None":
    """Process a single session into a Transcript.

    Args:
        db_path: Path to opencode.db
        session_id: The session ID to process

    Returns:
        Transcript object, or None if the session has no content
    """
    from inspect_scout import Transcript
    from inspect_scout._transcript.messages import span_messages
    from inspect_scout._transcript.timeline import build_timeline

    from .client import read_session

    session = read_session(db_path, session_id)
    if not session:
        return None

    messages_rows = read_messages(db_path, session_id)
    parts_rows = read_parts(db_path, session_id)

    if not messages_rows:
        return None

    # Convert to Inspect AI events
    scout_events: list[Event] = await process_session(
        messages_rows,
        parts_rows,
        db_path=db_path,
    )

    if not scout_events:
        return None

    # Extract messages via timeline
    timeline = build_timeline(scout_events)
    chat_messages: list[ChatMessage] = span_messages(timeline.root, compaction="all")

    if not chat_messages:
        return None

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for event in scout_events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(chat_messages)

    # Extract metadata from session and messages
    model_name = _extract_model_name(messages_rows)
    total_tokens = _sum_tokens(parts_rows)
    total_time = _calc_total_time(session.time_created, session.time_updated)

    source_uri = f"sqlite://{db_path}#{session_id}"

    metadata: dict[str, object] = {
        "title": session.title,
        "version": session.version,
        "directory": session.directory,
    }
    if session.slug:
        metadata["slug"] = session.slug

    return Transcript(
        transcript_id=session_id,
        source_type=OPENCODE_SOURCE_TYPE,
        source_id=session_id,
        source_uri=source_uri,
        date=_ms_to_iso(session.time_created),
        task_set=session.directory,
        task_id=session.slug or session.title,
        task_repeat=1,
        agent="opencode",
        agent_args=None,
        model=model_name,
        model_options=None,
        score=None,
        success=None,
        message_count=len(chat_messages),
        total_tokens=total_tokens if total_tokens > 0 else None,
        total_time=total_time if total_time > 0 else None,
        error=None,
        limit=None,
        messages=chat_messages,
        events=scout_events,
        metadata=metadata,
    )


def _extract_model_name(messages: list) -> str:
    """Extract model name from the first assistant message."""
    for msg in messages:
        if msg.data.get("role") == "assistant":
            model_id = msg.data.get("modelID", "")
            if model_id:
                return model_id
    return "unknown"


def _sum_tokens(parts: list) -> int:
    """Sum total tokens from step-finish parts."""
    total = 0
    for part in parts:
        if part.data.get("type") == "step-finish":
            tokens = part.data.get("tokens", {})
            total += tokens.get("total", 0)
    return total


def _calc_total_time(time_created_ms: int, time_updated_ms: int) -> float:
    """Calculate total time in seconds from session timestamps."""
    return (time_updated_ms - time_created_ms) / 1000.0
