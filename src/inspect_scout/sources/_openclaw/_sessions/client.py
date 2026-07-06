"""OpenClaw native session file discovery and reading utilities.

Native sessions live at ``~/.openclaw/agents/<agent>/sessions/``: one
``<sessionId>.jsonl`` per session, sibling ``*.trajectory.jsonl`` /
``*.trajectory-path.json`` runtime traces (never consumed), and one shared
``sessions.json`` registry carrying the authoritative topology.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

OPENCLAW_SOURCE_TYPE = "openclaw"

DEFAULT_OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"

_TRAJECTORY_SUFFIX = ".trajectory.jsonl"


def read_session_records(path: Path) -> list[dict[str, Any]]:
    """Read raw records from a session JSONL file.

    Malformed lines (e.g. a torn final line from a crash mid-append) are
    skipped with a warning, matching the Claude Code importer.
    """
    records: list[dict[str, Any]] = []
    n_bad = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            if isinstance(record, dict):
                records.append(record)
    if n_bad:
        logger.warning("Skipped %d malformed JSONL line(s) in %s", n_bad, path)
    return records


@dataclass(frozen=True)
class RegistryEntry:
    """One ``sessions.json`` entry (keyed by runtime sessionKey)."""

    session_key: str
    session_id: str
    spawned_by: str | None
    parent_session_key: str | None
    label: str | None
    status: str | None
    raw: dict[str, Any]


def load_registry(sessions_dir: Path) -> dict[str, RegistryEntry] | None:
    """Load ``sessions.json`` from a sessions directory.

    Returns ``None`` when the registry is missing or unreadable (the caller
    degrades to standalone per-file imports). Entries are NOT filtered against
    files on disk here — the sub-agent join checks file existence itself.
    """
    registry_path = sessions_dir / "sessions.json"
    if not registry_path.is_file():
        return None
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        logger.warning("Could not read %s: %s", registry_path, ex)
        return None
    if not isinstance(data, dict):
        logger.warning("Unexpected sessions.json shape in %s", registry_path)
        return None
    entries: dict[str, RegistryEntry] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        session_id = value.get("sessionId")
        if not session_id:
            continue
        entries[key] = RegistryEntry(
            session_key=key,
            session_id=str(session_id),
            spawned_by=_opt_str(value.get("spawnedBy")),
            parent_session_key=_opt_str(value.get("parentSessionKey")),
            label=_opt_str(value.get("label")),
            status=_opt_str(value.get("status")),
            raw=value,
        )
    return entries


def entry_for_session_id(
    registry: dict[str, RegistryEntry], session_id: str
) -> RegistryEntry | None:
    """The registry entry whose ``sessionId`` matches, or ``None``."""
    for entry in registry.values():
        if entry.session_id == session_id:
            return entry
    return None


def _opt_str(value: Any) -> str | None:
    return str(value) if value else None


def is_session_file(path: Path) -> bool:
    """Whether a path is a session conversation file (not a trajectory)."""
    return path.suffix == ".jsonl" and not path.name.endswith(_TRAJECTORY_SUFFIX)


def discover_session_files(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[Path]:
    """Discover OpenClaw native session files.

    Args:
        path: Path to search. Can be:
            - None: scan all agents in ~/.openclaw/agents/*/sessions/
            - a sessions directory (contains session .jsonl files)
            - a parent directory (e.g. ~/.openclaw or ~/.openclaw/agents)
            - a specific session .jsonl file
        session_id: If provided, only return the file with this session id
        from_time: Only return files modified on or after this time
        to_time: Only return files modified before this time

    Returns:
        Session file paths, sorted by modification time (newest first).
    """
    files: list[Path] = []
    if path is None:
        if not DEFAULT_OPENCLAW_AGENTS_DIR.is_dir():
            logger.warning(
                "OpenClaw agents directory not found: %s", DEFAULT_OPENCLAW_AGENTS_DIR
            )
            return []
        files = _scan_agent_dirs(DEFAULT_OPENCLAW_AGENTS_DIR)
    else:
        p = Path(path).expanduser()
        if not p.exists():
            logger.warning("Path does not exist: %s", p)
            return []
        if p.is_file():
            files = [p] if is_session_file(p) else []
        else:
            files = _find_sessions_in_directory(p)
            if not files:
                agents = p / "agents"
                files = _scan_agent_dirs(agents if agents.is_dir() else p)

    if session_id:
        files = [f for f in files if f.stem == session_id]

    if from_time or to_time:
        filtered: list[Path] = []
        for f in files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if from_time and mtime < from_time:
                continue
            if to_time and mtime >= to_time:
                continue
            filtered.append(f)
        files = filtered

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def _find_sessions_in_directory(directory: Path) -> list[Path]:
    """Session files directly in a directory."""
    return [f for f in directory.glob("*.jsonl") if is_session_file(f)]


def _scan_agent_dirs(base: Path) -> list[Path]:
    """Session files under ``<base>/*/sessions/`` (the per-agent layout)."""
    found: list[Path] = []
    for agent_dir in sorted(base.iterdir()):
        sessions_dir = agent_dir / "sessions"
        if sessions_dir.is_dir():
            found.extend(_find_sessions_in_directory(sessions_dir))
    return found
