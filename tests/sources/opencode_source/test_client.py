"""Tests for OpenCode SQLite client (client.py)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from inspect_scout.sources._opencode.client import (
    discover_sessions,
    extract_child_session_id,
    find_child_sessions,
    read_messages,
    read_parts,
    read_session,
)

from .conftest import (
    T0,
    T1,
    T2,
    T_END,
    insert_session,
    make_session,
)


class TestDiscoverSessions:
    """Tests for discover_sessions()."""

    def test_returns_top_level_excludes_archived_and_children(
        self, db_path: pytest.fixture
    ) -> None:
        """Returns top-level sessions; excludes archived and child sessions."""
        insert_session(db_path, make_session("ses_top"))
        insert_session(
            db_path, make_session("ses_archived", slug="a", time_archived=T_END)
        )
        insert_session(
            db_path, make_session("ses_child", slug="c", parent_id="ses_top")
        )

        sessions = discover_sessions(db_path=db_path)
        assert [s.id for s in sessions] == ["ses_top"]

    def test_filters_and_ordering(self, db_path: pytest.fixture) -> None:
        """Filters by session_id, time range, limit; returns newest first."""
        insert_session(db_path, make_session("ses_old", time_updated=T0))
        insert_session(db_path, make_session("ses_new", slug="new", time_updated=T_END))

        # Newest first
        all_sessions = discover_sessions(db_path=db_path)
        assert [s.id for s in all_sessions] == ["ses_new", "ses_old"]

        # session_id filter
        by_id = discover_sessions(db_path=db_path, session_id="ses_old")
        assert [s.id for s in by_id] == ["ses_old"]

        # Time range: only ses_new updated at T_END
        cutoff = datetime.fromtimestamp(T_END / 1000, tz=timezone.utc)
        by_time = discover_sessions(db_path=db_path, from_time=cutoff)
        assert [s.id for s in by_time] == ["ses_new"]

        # Limit
        limited = discover_sessions(db_path=db_path, limit=1)
        assert len(limited) == 1

    def test_nonexistent_db_returns_empty(self, tmp_path: pytest.fixture) -> None:
        """Non-existent database path returns empty list."""
        assert discover_sessions(db_path=tmp_path / "nope.db") == []


class TestReadSessionAndData:
    """Tests for read_session(), read_messages(), read_parts()."""

    def test_reads_session_fields(self, simple_session_db: pytest.fixture) -> None:
        """Reads session fields correctly; returns None for missing ID."""
        session = read_session(simple_session_db, "ses_001")
        assert session is not None
        assert session.slug == "test-session"
        assert session.directory == "/home/user/project"
        assert read_session(simple_session_db, "nonexistent") is None

    def test_reads_messages_chronologically_with_parsed_json(
        self, simple_session_db: pytest.fixture
    ) -> None:
        """Messages returned in order with parsed JSON data."""
        messages = read_messages(simple_session_db, "ses_001")
        assert len(messages) == 2
        assert messages[0].data["role"] == "user"
        assert messages[1].data["role"] == "assistant"
        assert messages[1].data["modelID"] == "claude-sonnet-4-20250514"

    def test_reads_parts_chronologically_with_parsed_json(
        self, simple_session_db: pytest.fixture
    ) -> None:
        """Parts returned in order with parsed JSON data."""
        parts = read_parts(simple_session_db, "ses_001")
        assert len(parts) == 4
        text_parts = [p for p in parts if p.data.get("type") == "text"]
        assert text_parts[0].data["text"] == "Hello, help me with code"
        for i in range(len(parts) - 1):
            assert parts[i].time_created <= parts[i + 1].time_created


class TestFindChildSessions:
    """Tests for find_child_sessions()."""

    def test_finds_children_in_order(self, db_path: pytest.fixture) -> None:
        """Returns child sessions ordered by time_created."""
        insert_session(db_path, make_session("ses_parent"))
        insert_session(
            db_path,
            make_session(
                "ses_child1", parent_id="ses_parent", time_created=T1, slug="c1"
            ),
        )
        insert_session(
            db_path,
            make_session(
                "ses_child2", parent_id="ses_parent", time_created=T2, slug="c2"
            ),
        )
        children = find_child_sessions(db_path, "ses_parent")
        assert [c.id for c in children] == ["ses_child1", "ses_child2"]

    def test_no_children_returns_empty(self, db_path: pytest.fixture) -> None:
        """Parent with no children returns empty list."""
        insert_session(db_path, make_session("ses_lonely"))
        assert find_child_sessions(db_path, "ses_lonely") == []


class TestExtractChildSessionId:
    """Tests for extract_child_session_id()."""

    def test_extracts_session_id(self) -> None:
        """Extracts session ID from typical task tool output."""
        output = "Result done.\ntask_id: ses_391bce77dffey5Cb (for resuming ...)"
        assert extract_child_session_id(output) == "ses_391bce77dffey5Cb"

    def test_no_match_returns_none(self) -> None:
        """No session ID pattern → None."""
        assert extract_child_session_id("Some regular output text") is None
        assert extract_child_session_id("") is None
