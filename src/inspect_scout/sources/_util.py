"""Shared helpers for filesystem-based transcript sources."""

from datetime import datetime, timezone
from pathlib import Path


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

    stamped = [(f.stat().st_mtime, f) for f in files]
    if from_aware is not None or to_aware is not None:
        filtered = []
        for mtime, file in stamped:
            modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
            if from_aware is not None and modified < from_aware:
                continue
            if to_aware is not None and modified >= to_aware:
                continue
            filtered.append((mtime, file))
        stamped = filtered

    stamped.sort(key=lambda pair: pair[0], reverse=True)
    return [file for _, file in stamped]
