"""Shared helpers for filesystem-based transcript sources."""

import json
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any, TextIO

from inspect_ai.event import Event, ModelEvent, TimelineSpan
from inspect_ai.model import ChatMessage, stable_message_ids

logger = getLogger(__name__)


def filter_and_sort_by_mtime(
    files: list[Path],
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[Path]:
    """Filter files by modification time and sort newest first.

    Accepts both naive and timezone-aware bounds: naive bounds are
    interpreted in local time, aware bounds are compared exactly.

    Args:
        files: Files to filter.
        from_time: Only keep files modified on or after this time.
        to_time: Only keep files modified before this time.

    Returns:
        Files within the time range, sorted by modification time (newest first).
    """

    def as_aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else dt.astimezone()

    from_aware = as_aware(from_time) if from_time else None
    to_aware = as_aware(to_time) if to_time else None

    def in_range(mtime: float) -> bool:
        modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
        if from_aware is not None and modified < from_aware:
            return False
        if to_aware is not None and modified >= to_aware:
            return False
        return True

    stamped = [(f.stat().st_mtime, f) for f in files]
    stamped = [(mtime, file) for mtime, file in stamped if in_range(mtime)]
    stamped.sort(key=lambda pair: pair[0], reverse=True)
    return [file for _, file in stamped]


def iter_jsonl_values(f: TextIO, path: Path) -> Iterator[Any]:
    """Yield parsed JSON values from an open JSONL file.

    Blank lines are skipped; malformed lines are skipped with a warning.

    Args:
        f: Open text file to read lines from.
        path: Path of the file (used in warning messages).
    """
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON at {path}:{line_num}: {e}")


def get_source_uri(session_file: Path, fragment_id: str | None = None) -> str:
    """Generate a file:// source URI for a session file.

    Args:
        session_file: Path to the session file.
        fragment_id: Optional identifier appended as a URI fragment (e.g. a
            transcript id within the file).
    """
    uri = f"file://{session_file}"
    if fragment_id:
        uri += f"#{fragment_id}"
    return uri


def apply_stable_message_ids(
    events: Sequence[Event], messages: list[ChatMessage]
) -> None:
    """Apply stable message IDs to model events and transcript messages.

    Args:
        events: Transcript events; ModelEvents get stable input/output ids.
        messages: Transcript messages; assigned ids consistent with events.
    """
    apply_ids = stable_message_ids()
    for event in events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)


def total_active_time(root: TimelineSpan) -> float:
    """Wall-clock duration of a timeline root minus its idle time, in seconds.

    Args:
        root: Root span of a built timeline.
    """
    wall_clock = (root.end_time() - root.start_time()).total_seconds()
    return wall_clock - root.idle_time()
