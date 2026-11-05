"""Codex CLI rollout file discovery and reading.

Codex sessions ("rollouts") are stored at:
    $CODEX_HOME/sessions/YYYY/MM/DD/rollout-<timestamp>-<thread-uuid>.jsonl

with ``CODEX_HOME`` defaulting to ``~/.codex``. Archived sessions move to
``$CODEX_HOME/archived_sessions/`` (same format). Rollout files idle for a
while are zstd-compressed in place (``rollout-*.jsonl.zst``); readers handle
both forms transparently.
"""

import io
import json
import os
import re
import sys
from collections.abc import Iterator
from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any, TextIO

from .._util import filter_and_sort_by_mtime, iter_jsonl_values

if sys.version_info >= (3, 14):
    from compression.zstd import ZstdError
else:
    from zstandard import ZstdError

logger = getLogger(__name__)

CODEX_SOURCE_TYPE = "codex_cli"

SESSIONS_SUBDIR = "sessions"
ARCHIVED_SESSIONS_SUBDIR = "archived_sessions"

_ROLLOUT_FILE_RE = re.compile(
    r"^rollout-.*-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.jsonl(\.zst)?$"
)

# Errors reading a rollout file can raise: filesystem failures, corrupt zstd
# frames, and non-UTF-8 content.
_ROLLOUT_READ_ERRORS = (OSError, ZstdError, UnicodeDecodeError)


def default_codex_home() -> Path:
    """The Codex home directory ($CODEX_HOME, defaulting to ~/.codex)."""
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser()
    return Path.home() / ".codex"


def rollout_thread_id(rollout_file: Path) -> str | None:
    """Extract the thread id (UUID) from a rollout filename."""
    match = _ROLLOUT_FILE_RE.match(rollout_file.name)
    return match.group(1) if match else None


def discover_rollout_files(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    include_archived: bool = False,
) -> list[Path]:
    """Discover Codex rollout files.

    Args:
        path: Path to search. Can be:
            - None: scan $CODEX_HOME/sessions (and archived_sessions when
              include_archived is True)
            - a directory: scanned recursively for rollout files
            - a specific .jsonl / .jsonl.zst file
        session_id: If provided, only return the rollout for this thread id
        from_time: Only return files modified on or after this time
        to_time: Only return files modified before this time
        include_archived: Also scan $CODEX_HOME/archived_sessions (only
            applies when path is None)

    Returns:
        List of rollout file paths, sorted by modification time (newest first)
    """
    rollout_files: list[Path] = []

    if path is None:
        codex_home = default_codex_home()
        roots = [codex_home / SESSIONS_SUBDIR]
        if include_archived:
            roots.append(codex_home / ARCHIVED_SESSIONS_SUBDIR)
        if not roots[0].exists():
            logger.warning(f"Codex sessions directory not found: {roots[0]}")
        for root in roots:
            if root.exists():
                rollout_files.extend(_find_rollouts_in_directory(root))
    else:
        search_path = Path(path)
        if not search_path.exists():
            logger.warning(f"Path does not exist: {search_path}")
            return []
        if search_path.is_file():
            rollout_files.append(search_path)
        elif search_path.is_dir():
            rollout_files.extend(_find_rollouts_in_directory(search_path))

    if session_id:
        rollout_files = [f for f in rollout_files if rollout_thread_id(f) == session_id]

    return filter_and_sort_by_mtime(rollout_files, from_time, to_time)


def _find_rollouts_in_directory(directory: Path) -> list[Path]:
    """Recursively find rollout files under a directory."""
    return [
        f
        for f in directory.rglob("rollout-*.jsonl*")
        if f.is_file() and rollout_thread_id(f) is not None
    ]


class RolloutFinder:
    """Locates rollout files by thread id.

    Child threads may live in a different date partition than their parent,
    so each search root is scanned recursively — once, on first lookup — and
    subsequent lookups are dict hits. Prefers the uncompressed file when
    both forms exist.
    """

    def __init__(self, search_roots: list[Path]) -> None:
        self._search_roots = search_roots
        self._index: dict[str, Path] | None = None

    def find(self, thread_id: str) -> Path | None:
        if self._index is None:
            self._index = {}
            for root in self._search_roots:
                if not root.is_dir():
                    continue
                for f in _find_rollouts_in_directory(root):
                    tid = rollout_thread_id(f)
                    assert tid is not None  # guaranteed by _find_rollouts_in_directory
                    existing = self._index.get(tid)
                    if existing is None or (
                        existing.name.endswith(".zst") and not f.name.endswith(".zst")
                    ):
                        self._index[tid] = f
        return self._index.get(thread_id)


def find_rollout_by_thread_id(thread_id: str, search_roots: list[Path]) -> Path | None:
    """Locate the rollout file for a thread id (single-use RolloutFinder)."""
    return RolloutFinder(search_roots).find(thread_id)


def sessions_root_for(rollout_file: Path) -> Path:
    """The sessions tree root containing a rollout file.

    Walks up from the file looking for a ``sessions`` / ``archived_sessions``
    directory; falls back to the file's own directory (e.g. test fixtures).
    """
    for parent in rollout_file.parents:
        if parent.name in (SESSIONS_SUBDIR, ARCHIVED_SESSIONS_SUBDIR):
            return parent
    return rollout_file.parent


def codex_home_for(rollout_file: Path) -> Path | None:
    """The codex home containing a rollout file, if it lives in a sessions tree.

    Returns None for rollout files outside a ``sessions`` /
    ``archived_sessions`` directory (e.g. a bare directory of copied files),
    where no ``session_index.jsonl`` can be located.
    """
    root = sessions_root_for(rollout_file)
    if root.name in (SESSIONS_SUBDIR, ARCHIVED_SESSIONS_SUBDIR):
        return root.parent
    return None


def related_rollout_roots(rollout_file: Path) -> list[Path]:
    """Roots to search for rollouts related to a file (children, history parents).

    Threads are archived individually, so a related thread may live in the
    other tree of the same codex home: both ``sessions`` and
    ``archived_sessions`` are returned when the file belongs to a codex home.
    Falls back to the file's own directory otherwise.
    """
    home = codex_home_for(rollout_file)
    if home is None:
        return [rollout_file.parent]
    return [
        root
        for root in (home / SESSIONS_SUBDIR, home / ARCHIVED_SESSIONS_SUBDIR)
        if root.is_dir()
    ] or [rollout_file.parent]


def _open_rollout_text(path: Path) -> TextIO:
    """Open a rollout file for text reading, decompressing .zst transparently."""
    if path.name.endswith(".zst"):
        if sys.version_info >= (3, 14):
            from compression import zstd

            return io.TextIOWrapper(zstd.ZstdFile(path, "rb"), encoding="utf-8")
        else:
            import zstandard

            fh = path.open("rb")
            reader = zstandard.ZstdDecompressor().stream_reader(fh, closefd=True)
            return io.TextIOWrapper(reader, encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_rollout_lines(path: Path) -> Iterator[dict[str, Any]]:
    """Lazily read parsed lines from a rollout file, skipping malformed ones."""
    try:
        with _open_rollout_text(path) as f:
            for parsed in iter_jsonl_values(f, path):
                if isinstance(parsed, dict):
                    yield parsed
    except _ROLLOUT_READ_ERRORS as e:
        logger.warning(f"Failed to read rollout file {path}: {e}")


def read_rollout_lines(path: Path) -> list[dict[str, Any]]:
    """Read all lines from a rollout file, skipping malformed ones."""
    return list(iter_rollout_lines(path))


def peek_session_meta(path: Path) -> dict[str, Any] | None:
    """Read the session_meta line (line 1) of a rollout file.

    Returns the raw line dict (envelope + payload), or None if the file is
    not an enveloped codex rollout (e.g. a pre-v0.33 legacy file or an
    unrelated JSONL file).
    """
    try:
        with _open_rollout_text(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    return None
                if (
                    isinstance(parsed, dict)
                    and parsed.get("type") == "session_meta"
                    and isinstance(parsed.get("payload"), dict)
                ):
                    return parsed
                return None
    except _ROLLOUT_READ_ERRORS as e:
        logger.warning(f"Could not read rollout file {path}: {e}")
    return None


def load_thread_names(codex_home: Path | None = None) -> dict[str, str]:
    """Load thread names from $CODEX_HOME/session_index.jsonl.

    The index is append-only ({"id", "thread_name", "updated_at"} per line);
    the last entry for an id wins. Returns an empty mapping when the index
    is missing.
    """
    home = codex_home or default_codex_home()
    index_file = home / "session_index.jsonl"
    names: dict[str, str] = {}
    if not index_file.is_file():
        return names
    try:
        with index_file.open("r", encoding="utf-8") as f:
            for entry in iter_jsonl_values(f, index_file):
                if isinstance(entry, dict):
                    thread_id = entry.get("id")
                    thread_name = entry.get("thread_name")
                    if isinstance(thread_id, str) and isinstance(thread_name, str):
                        names[thread_id] = thread_name
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Could not read session index {index_file}: {e}")
    return names
