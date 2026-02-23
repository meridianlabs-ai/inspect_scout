"""Shared utilities for Claude Code source processing."""

from datetime import datetime


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse an ISO timestamp string to datetime.

    Handles the common 'Z' suffix used in Claude Code event timestamps.

    Args:
        ts_str: ISO format timestamp string (with optional 'Z' suffix)

    Returns:
        Parsed datetime, or None if parsing fails or input is empty
    """
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return None
