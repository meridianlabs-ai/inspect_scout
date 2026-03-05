"""Shared fixtures for opencode source tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from inspect_scout.sources._opencode.client import MessageRow, PartRow, SessionRow

# ---------------------------------------------------------------------------
# Timestamps (millisecond epoch)
# ---------------------------------------------------------------------------
T0 = 1_706_745_600_000  # 2024-02-01 00:00:00 UTC
T1 = T0 + 1_000  # +1 s
T2 = T0 + 2_000
T3 = T0 + 3_000
T4 = T0 + 4_000
T5 = T0 + 5_000
T6 = T0 + 6_000
T_END = T0 + 60_000  # +60 s


# ---------------------------------------------------------------------------
# Temporary database helper
# ---------------------------------------------------------------------------


def create_opencode_db(db_path: Path) -> Path:
    """Create an OpenCode-schema SQLite database at *db_path*."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE session (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            parent_id TEXT,
            slug TEXT NOT NULL,
            directory TEXT NOT NULL,
            title TEXT NOT NULL,
            version TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            time_updated INTEGER NOT NULL,
            time_archived INTEGER
        );
        CREATE TABLE message (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        CREATE TABLE part (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        """
    )
    conn.close()
    return db_path


def insert_session(db_path: Path, session: SessionRow) -> None:
    """Insert a SessionRow into the database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO session VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session.id,
            session.project_id,
            session.parent_id,
            session.slug,
            session.directory,
            session.title,
            session.version,
            session.time_created,
            session.time_updated,
            session.time_archived,
        ),
    )
    conn.commit()
    conn.close()


def insert_message(db_path: Path, msg: MessageRow) -> None:
    """Insert a MessageRow into the database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO message VALUES (?, ?, ?, ?)",
        (msg.id, msg.session_id, msg.time_created, json.dumps(msg.data)),
    )
    conn.commit()
    conn.close()


def insert_part(db_path: Path, part: PartRow) -> None:
    """Insert a PartRow into the database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO part VALUES (?, ?, ?, ?, ?)",
        (
            part.id,
            part.message_id,
            part.session_id,
            part.time_created,
            json.dumps(part.data),
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Row factories
# ---------------------------------------------------------------------------


def make_session(
    session_id: str = "ses_001",
    *,
    slug: str = "test-session",
    directory: str = "/home/user/project",
    title: str = "Test Session",
    version: str = "0.1.0",
    time_created: int = T0,
    time_updated: int = T_END,
    parent_id: str | None = None,
    project_id: str | None = None,
    time_archived: int | None = None,
) -> SessionRow:
    return SessionRow(
        id=session_id,
        project_id=project_id,
        parent_id=parent_id,
        slug=slug,
        directory=directory,
        title=title,
        version=version,
        time_created=time_created,
        time_updated=time_updated,
        time_archived=time_archived,
    )


def make_message(
    msg_id: str,
    session_id: str,
    time_created: int,
    data: dict[str, Any],
) -> MessageRow:
    return MessageRow(
        id=msg_id, session_id=session_id, time_created=time_created, data=data
    )


def make_part(
    part_id: str,
    message_id: str,
    session_id: str,
    time_created: int,
    data: dict[str, Any],
) -> PartRow:
    return PartRow(
        id=part_id,
        message_id=message_id,
        session_id=session_id,
        time_created=time_created,
        data=data,
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fresh, empty OpenCode database."""
    return create_opencode_db(tmp_path / "opencode.db")


@pytest.fixture
def simple_session_db(db_path: Path) -> Path:
    """Database with one simple user→assistant session.

    Contains:
      - 1 session (ses_001)
      - 2 messages (user + assistant)
      - 3 parts (user text, step-start, text, step-finish)
    """
    session = make_session()
    insert_session(db_path, session)

    # User message
    user_msg = make_message("msg_u1", "ses_001", T1, {"role": "user"})
    insert_message(db_path, user_msg)
    insert_part(
        db_path,
        make_part(
            "p_u1",
            "msg_u1",
            "ses_001",
            T1,
            {"type": "text", "text": "Hello, help me with code"},
        ),
    )

    # Assistant message
    asst_msg = make_message(
        "msg_a1",
        "ses_001",
        T2,
        {"role": "assistant", "modelID": "claude-sonnet-4-20250514"},
    )
    insert_message(db_path, asst_msg)
    insert_part(
        db_path, make_part("p_ss1", "msg_a1", "ses_001", T2, {"type": "step-start"})
    )
    insert_part(
        db_path,
        make_part(
            "p_a1",
            "msg_a1",
            "ses_001",
            T3,
            {"type": "text", "text": "Sure, I can help!"},
        ),
    )
    insert_part(
        db_path,
        make_part(
            "p_sf1",
            "msg_a1",
            "ses_001",
            T4,
            {
                "type": "step-finish",
                "tokens": {
                    "input": 100,
                    "output": 20,
                    "reasoning": 0,
                    "total": 120,
                    "cache": {"read": 0, "write": 0},
                },
            },
        ),
    )

    return db_path
