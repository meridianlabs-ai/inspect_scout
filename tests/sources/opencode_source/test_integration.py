"""Integration tests for the opencode source — full pipeline from DB to Transcript."""

from __future__ import annotations

from pathlib import Path

import pytest
from inspect_ai.event import ModelEvent, SpanBeginEvent, ToolEvent
from inspect_scout.sources._opencode.transcripts import opencode

from .conftest import (
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    T_END,
    insert_message,
    insert_part,
    insert_session,
    make_message,
    make_part,
    make_session,
)


def _populate_simple_session(db_path: Path) -> None:
    """Populate a single user→assistant session into the DB."""
    insert_session(db_path, make_session("ses_001"))

    insert_message(db_path, make_message("msg_u1", "ses_001", T1, {"role": "user"}))
    insert_part(
        db_path,
        make_part(
            "p_u1", "msg_u1", "ses_001", T1, {"type": "text", "text": "Hello, help me"}
        ),
    )

    insert_message(
        db_path,
        make_message(
            "msg_a1",
            "ses_001",
            T2,
            {"role": "assistant", "modelID": "claude-sonnet-4-20250514"},
        ),
    )
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


def _populate_tool_session(db_path: Path) -> None:
    """Populate a session with a tool call."""
    insert_session(db_path, make_session("ses_tool", slug="tool-session"))

    insert_message(db_path, make_message("msg_u", "ses_tool", T1, {"role": "user"}))
    insert_part(
        db_path,
        make_part(
            "p_u", "msg_u", "ses_tool", T1, {"type": "text", "text": "Read the file"}
        ),
    )

    insert_message(
        db_path,
        make_message(
            "msg_a",
            "ses_tool",
            T2,
            {"role": "assistant", "modelID": "claude-sonnet-4-20250514"},
        ),
    )
    insert_part(
        db_path, make_part("p_ss", "msg_a", "ses_tool", T2, {"type": "step-start"})
    )
    insert_part(
        db_path,
        make_part(
            "p_text",
            "msg_a",
            "ses_tool",
            T3,
            {"type": "text", "text": "Let me read that."},
        ),
    )
    insert_part(
        db_path,
        make_part(
            "p_tool",
            "msg_a",
            "ses_tool",
            T4,
            {
                "type": "tool",
                "tool": "Read",
                "callID": "call_1",
                "state": {
                    "input": {"file_path": "/test.py"},
                    "output": "contents",
                    "status": "completed",
                    "time": {"start": T4, "end": T5},
                },
            },
        ),
    )
    insert_part(
        db_path,
        make_part(
            "p_sf",
            "msg_a",
            "ses_tool",
            T5,
            {
                "type": "step-finish",
                "tokens": {
                    "input": 200,
                    "output": 50,
                    "total": 250,
                    "cache": {"read": 0, "write": 0},
                },
            },
        ),
    )


class TestOpenCodeIntegration:
    """Full pipeline tests: DB → opencode() → Transcript."""

    @pytest.mark.asyncio
    async def test_simple_session_transcript_fields(self, db_path: Path) -> None:
        """Simple session → transcript with correct id, model, metadata, tokens, time, events."""
        _populate_simple_session(db_path)

        transcripts = []
        async for t in opencode(db_path=db_path):
            transcripts.append(t)

        assert len(transcripts) == 1
        t = transcripts[0]

        # Identity
        assert t.transcript_id == "ses_001"
        assert t.source_type == "opencode"
        assert t.source_uri == f"sqlite://{db_path}#ses_001"
        assert t.agent == "opencode"

        # Model and messages
        assert t.model == "claude-sonnet-4-20250514"
        assert t.message_count >= 2

        # Metadata
        assert t.metadata is not None
        assert t.metadata["title"] == "Test Session"
        assert t.metadata["slug"] == "test-session"
        assert t.task_set == "/home/user/project"
        assert t.task_id == "test-session"

        # Tokens and time
        assert t.total_tokens == 120
        assert t.total_time == (T_END - T0) / 1000.0

        # Events
        assert any(isinstance(e, ModelEvent) for e in t.events)

    @pytest.mark.asyncio
    async def test_tool_call_session(self, db_path: Path) -> None:
        """Session with tool call includes tool events and spans."""
        _populate_tool_session(db_path)

        transcripts = []
        async for t in opencode(db_path=db_path):
            transcripts.append(t)

        assert len(transcripts) == 1
        assert any(
            isinstance(e, ToolEvent) and e.function == "Read"
            for e in transcripts[0].events
        )
        assert any(isinstance(e, SpanBeginEvent) for e in transcripts[0].events)

    @pytest.mark.asyncio
    async def test_multiple_sessions_with_limit_and_filter(self, db_path: Path) -> None:
        """Multiple sessions → multiple transcripts; limit and session_id filter work."""
        _populate_simple_session(db_path)
        _populate_tool_session(db_path)

        # All sessions
        all_transcripts = []
        async for t in opencode(db_path=db_path):
            all_transcripts.append(t)
        assert {t.transcript_id for t in all_transcripts} == {"ses_001", "ses_tool"}

        # Limit
        limited = []
        async for t in opencode(db_path=db_path, limit=1):
            limited.append(t)
        assert len(limited) == 1

        # Filter by session_id
        filtered = []
        async for t in opencode(db_path=db_path, session_id="ses_tool"):
            filtered.append(t)
        assert len(filtered) == 1
        assert filtered[0].transcript_id == "ses_tool"

    @pytest.mark.asyncio
    async def test_empty_and_missing_db(self, db_path: Path, tmp_path: Path) -> None:
        """Empty session is skipped; non-existent DB yields nothing; string path works."""
        insert_session(db_path, make_session("ses_empty"))

        transcripts = []
        async for t in opencode(db_path=db_path):
            transcripts.append(t)
        assert transcripts == []

        missing = []
        async for t in opencode(db_path=tmp_path / "nope.db"):
            missing.append(t)
        assert missing == []

        # String path accepted
        _populate_simple_session(db_path)
        from_str = []
        async for t in opencode(db_path=str(db_path)):
            from_str.append(t)
        assert len(from_str) == 1
