"""Shared helpers for transcript sources."""

from __future__ import annotations

from datetime import datetime, timezone
from logging import getLogger

from inspect_ai.event import Event

logger = getLogger(__name__)


def apply_working_start(events: list[Event]) -> None:
    """Set each event's ``working_start`` to its offset from the first event.

    ``working_start`` means "working seconds since sample start", but its
    default factory samples the raw monotonic clock when events are built
    outside a live sample — so synthesized events would otherwise carry
    process-uptime garbage that the transcript viewer renders as absurd
    durations. Derive it from the event timestamps instead.
    """
    if not events:
        return
    start = min(event.timestamp for event in events)
    for event in events:
        event.working_start = (event.timestamp - start).total_seconds()


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string to a tz-aware UTC datetime.

    Handles the common 'Z' suffix.

    Args:
        ts_str: ISO format timestamp string (with optional 'Z' suffix)

    Returns:
        Parsed UTC datetime, or None if parsing fails or input is empty
    """
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Invalid timestamp: %r", ts_str)
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
