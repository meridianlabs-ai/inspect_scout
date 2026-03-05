"""OpenCode SQLite data access layer.

OpenCode stores session data in a SQLite database at
~/.local/share/opencode/opencode.db with three core tables:
session, message, and part.
"""

import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

OPENCODE_SOURCE_TYPE = "opencode"

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _ms_to_datetime(ms: int | float | None) -> datetime:
    """Convert millisecond epoch timestamp to timezone-aware datetime.

    Returns the Unix epoch for None or non-positive values.
    """
    if ms is None or ms <= 0:
        return _EPOCH
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _ms_to_iso(ms: int | float) -> str:
    """Convert millisecond epoch timestamp to ISO 8601 string."""
    return _ms_to_datetime(ms).isoformat()


@dataclass
class SessionRow:
    """A row from the session table."""

    id: str
    project_id: str | None
    parent_id: str | None
    slug: str
    directory: str
    title: str
    version: str
    time_created: int
    time_updated: int
    time_archived: int | None = None


@dataclass
class MessageRow:
    """A row from the message table."""

    id: str
    session_id: str
    time_created: int
    data: dict[str, Any]


@dataclass
class PartRow:
    """A row from the part table."""

    id: str
    message_id: str
    session_id: str
    time_created: int
    data: dict[str, Any]


@contextmanager
def _open_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a read-only SQLite connection as a context manager."""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        yield conn
    finally:
        conn.close()


def discover_sessions(
    db_path: Path | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> list[SessionRow]:
    """Discover top-level OpenCode sessions.

    Excludes archived sessions and child sessions (subagents).

    Args:
        db_path: Path to opencode.db. Defaults to ~/.local/share/opencode/opencode.db
        session_id: If provided, only return this specific session
        from_time: Only return sessions updated on or after this time
        to_time: Only return sessions updated before this time
        limit: Maximum number of sessions to return

    Returns:
        List of SessionRow, sorted by time_updated descending (newest first)
    """
    db_path = db_path or DEFAULT_DB_PATH
    if not db_path.exists():
        logger.warning(f"OpenCode database not found: {db_path}")
        return []

    clauses = ["time_archived IS NULL", "parent_id IS NULL"]
    params: list[Any] = []

    if session_id:
        clauses.append("id = ?")
        params.append(session_id)

    if from_time:
        clauses.append("time_updated >= ?")
        params.append(int(from_time.timestamp() * 1000))

    if to_time:
        clauses.append("time_updated < ?")
        params.append(int(to_time.timestamp() * 1000))

    where = " AND ".join(clauses)
    query = f"""
        SELECT id, project_id, parent_id, slug, directory, title,
               version, time_created, time_updated, time_archived
        FROM session
        WHERE {where}
        ORDER BY time_updated DESC
    """
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with _open_db(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [
            SessionRow(
                id=r[0],
                project_id=r[1],
                parent_id=r[2],
                slug=r[3],
                directory=r[4],
                title=r[5],
                version=r[6],
                time_created=r[7],
                time_updated=r[8],
                time_archived=r[9],
            )
            for r in rows
        ]


def _session_from_row(row: tuple[Any, ...]) -> SessionRow:
    """Build a SessionRow from a raw SQL row tuple."""
    return SessionRow(
        id=row[0],
        project_id=row[1],
        parent_id=row[2],
        slug=row[3],
        directory=row[4],
        title=row[5],
        version=row[6],
        time_created=row[7],
        time_updated=row[8],
        time_archived=row[9],
    )


_SESSION_COLS = """id, project_id, parent_id, slug, directory, title,
               version, time_created, time_updated, time_archived"""


def read_session(
    db_path: Path,
    session_id: str,
    conn: sqlite3.Connection | None = None,
) -> SessionRow | None:
    """Read a single session by ID (including child sessions).

    Args:
        db_path: Path to opencode.db
        session_id: The session ID to read
        conn: Optional existing connection to reuse

    Returns:
        SessionRow or None if not found
    """

    def _query(c: sqlite3.Connection) -> SessionRow | None:
        row = c.execute(
            f"SELECT {_SESSION_COLS} FROM session WHERE id = ?",
            (session_id,),
        ).fetchone()
        return _session_from_row(row) if row else None

    if conn is not None:
        return _query(conn)
    with _open_db(db_path) as c:
        return _query(c)


def read_messages(
    db_path: Path,
    session_id: str,
    conn: sqlite3.Connection | None = None,
) -> list[MessageRow]:
    """Read all messages for a session, ordered by time_created.

    Args:
        db_path: Path to opencode.db
        session_id: The session to read messages for
        conn: Optional existing connection to reuse

    Returns:
        List of MessageRow ordered chronologically
    """

    def _query(c: sqlite3.Connection) -> list[MessageRow]:
        rows = c.execute(
            """SELECT id, session_id, time_created, data
               FROM message
               WHERE session_id = ?
               ORDER BY time_created""",
            (session_id,),
        ).fetchall()
        return [
            MessageRow(
                id=r[0],
                session_id=r[1],
                time_created=r[2],
                data=json.loads(r[3]),
            )
            for r in rows
        ]

    if conn is not None:
        return _query(conn)
    with _open_db(db_path) as c:
        return _query(c)


def read_parts(
    db_path: Path,
    session_id: str,
    conn: sqlite3.Connection | None = None,
) -> list[PartRow]:
    """Read all parts for a session, ordered by time_created.

    Args:
        db_path: Path to opencode.db
        session_id: The session to read parts for
        conn: Optional existing connection to reuse

    Returns:
        List of PartRow ordered chronologically
    """

    def _query(c: sqlite3.Connection) -> list[PartRow]:
        rows = c.execute(
            """SELECT id, message_id, session_id, time_created, data
               FROM part
               WHERE session_id = ?
               ORDER BY time_created""",
            (session_id,),
        ).fetchall()
        return [
            PartRow(
                id=r[0],
                message_id=r[1],
                session_id=r[2],
                time_created=r[3],
                data=json.loads(r[4]),
            )
            for r in rows
        ]

    if conn is not None:
        return _query(conn)
    with _open_db(db_path) as c:
        return _query(c)


def find_child_sessions(
    db_path: Path,
    parent_id: str,
    conn: sqlite3.Connection | None = None,
) -> list[SessionRow]:
    """Find child sessions (subagents) for a parent session.

    Args:
        db_path: Path to opencode.db
        parent_id: The parent session ID
        conn: Optional existing connection to reuse

    Returns:
        List of child SessionRow ordered by time_created
    """

    def _query(c: sqlite3.Connection) -> list[SessionRow]:
        rows = c.execute(
            f"""SELECT {_SESSION_COLS}
               FROM session
               WHERE parent_id = ?
               ORDER BY time_created""",
            (parent_id,),
        ).fetchall()
        return [_session_from_row(r) for r in rows]

    if conn is not None:
        return _query(conn)
    with _open_db(db_path) as c:
        return _query(c)


def extract_child_session_id(tool_output: str) -> str | None:
    """Extract child session ID from a task tool's output string.

    OpenCode task tool outputs contain lines like:
        task_id: ses_391bce77dffey5Cb7gLxj5gfKD (for resuming ...)

    Args:
        tool_output: The tool's output string

    Returns:
        The session ID if found, None otherwise
    """
    match = re.search(r"task_id:\s*(ses_\w+)", tool_output)
    return match.group(1) if match else None
