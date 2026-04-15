"""Codex rollout discovery and file utilities."""

from __future__ import annotations

import json
from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

CODEX_SOURCE_TYPE = "codex"
DEFAULT_CODEX_DIR = Path.home() / ".codex" / "sessions"


def discover_rollout_files(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[Path]:
    """Discover Codex rollout files.

    Args:
        path: Path to search. Can be:
            - None: Scan all rollout files in ``~/.codex/sessions/``
            - A directory containing rollout files
            - A specific rollout JSONL file
        session_id: Optional specific Codex session ID to import
        from_time: Only return files modified on or after this time
        to_time: Only return files modified before this time

    Returns:
        List of rollout file paths sorted by modification time, newest first.
    """
    if path is None:
        search_root = DEFAULT_CODEX_DIR
    else:
        search_root = Path(path).expanduser()

    if not search_root.exists():
        logger.warning("Path does not exist: %s", search_root)
        return []

    rollout_files: list[Path] = []
    if search_root.is_file():
        if _is_rollout_file(search_root):
            rollout_files.append(search_root)
    else:
        rollout_files.extend(
            rollout_file
            for rollout_file in search_root.rglob("rollout-*.jsonl")
            if rollout_file.is_file()
        )

    if session_id is not None:
        rollout_files = [
            rollout_file
            for rollout_file in rollout_files
            if peek_session_id(rollout_file) == session_id
        ]

    if from_time is not None or to_time is not None:
        filtered: list[Path] = []
        for rollout_file in rollout_files:
            mtime = datetime.fromtimestamp(rollout_file.stat().st_mtime)
            if from_time is not None and mtime < from_time:
                continue
            if to_time is not None and mtime >= to_time:
                continue
            filtered.append(rollout_file)
        rollout_files = filtered

    rollout_files.sort(
        key=lambda rollout_file: rollout_file.stat().st_mtime, reverse=True
    )
    return rollout_files


def read_jsonl_records(rollout_file: Path) -> list[dict[str, Any]]:
    """Read JSONL records from a Codex rollout file."""
    records: list[dict[str, Any]] = []

    try:
        with open(rollout_file, encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    record = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping invalid JSON in %s line %s", rollout_file, line_number
                    )
                    continue
                if isinstance(record, dict):
                    records.append(record)
    except OSError as ex:
        logger.warning("Error reading rollout file %s: %s", rollout_file, ex)

    return records


def peek_session_id(rollout_file: Path, max_lines: int = 10) -> str | None:
    """Read the session ID from the first few lines of a rollout file."""
    try:
        with open(rollout_file, encoding="utf-8") as file:
            for _, line in zip(range(max_lines), file, strict=False):
                text = line.strip()
                if not text:
                    continue
                try:
                    record = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "session_meta":
                    continue
                payload = record.get("payload")
                if isinstance(payload, dict):
                    session_id = payload.get("id")
                    if isinstance(session_id, str) and session_id:
                        return session_id
    except OSError as ex:
        logger.warning("Error peeking session id for %s: %s", rollout_file, ex)

    return None


def get_source_uri(rollout_file: Path) -> str:
    """Get a stable source URI for a rollout file."""
    return str(rollout_file.resolve())


def _is_rollout_file(path: Path) -> bool:
    """Return whether a path looks like a Codex rollout JSONL file."""
    return path.name.startswith("rollout-") and path.suffix == ".jsonl"
