"""Tests for OpenClaw native session record parsing."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from inspect_scout.sources._openclaw._sessions.client import read_session_records
from inspect_scout.sources._openclaw._sessions.parse import (
    AssistantTurn,
    CompactionRecord,
    ConfigChange,
    ParsedSession,
    UserTurn,
    parse_session,
)

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
ORCHESTRATOR = FX_DEMO / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"


def parse_fixture(path: Path) -> ParsedSession:
    return parse_session(read_session_records(path), str(path))


HEADER = {
    "type": "session",
    "version": 3,
    "id": "s1",
    "timestamp": "2026-07-06T10:00:00.000Z",
    "cwd": "/w",
}


def make_message(id_: str, parent: str, role: str, content: Any) -> dict[str, Any]:
    return {
        "type": "message",
        "id": id_,
        "parentId": parent,
        "timestamp": "2026-07-06T10:00:01.000Z",
        "message": {"role": role, "content": content},
    }


class TestParseSession:
    def test_orchestrator_happy_path(self) -> None:
        parsed = parse_fixture(ORCHESTRATOR)

        assert parsed.header.session_id == "cfabe24d-8b34-4031-a393-689524b2028f"
        assert parsed.header.version == 3
        assert parsed.header.cwd == "/home/ubuntu/.openclaw/workspace"
        assert parsed.model == "claude-opus-4-8"
        # 4 user + 3 injected custom_message = 7 user turns
        user_turns = [r for r in parsed.records if isinstance(r, UserTurn)]
        assert len(user_turns) == 7
        assert sum(1 for u in user_turns if u.injected) == 3
        assert sum(1 for r in parsed.records if isinstance(r, AssistantTurn)) == 11
        # config changes: model_change + thinking_level_change
        changes = [r for r in parsed.records if isinstance(r, ConfigChange)]
        assert [c.change for c in changes] == ["model_change", "thinking_level_change"]
        # all 11 toolResults keyed
        assert len(parsed.result_by_callid) == 11
        # records are in chronological (file) order
        timestamps = [r.timestamp for r in parsed.records]
        assert timestamps == sorted(timestamps)

    def test_assistant_turn_fields(self) -> None:
        parsed = parse_fixture(ORCHESTRATOR)
        first = next(r for r in parsed.records if isinstance(r, AssistantTurn))
        assert first.model == "claude-opus-4-8"
        assert first.usage["totalTokens"] == 28509

    def test_assistant_turn_stop_reason_and_response_id(self) -> None:
        parsed = parse_fixture(
            FIXTURES / "fx_demo" / "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl"
        )

        turns = [r for r in parsed.records if isinstance(r, AssistantTurn)]
        assert [t.stop_reason for t in turns] == ["toolUse", "toolUse", "stop"]
        assert turns[0].response_id == "msg_01D96KRhC582hGM2Wb94vwND"
        assert turns[2].response_id == "msg_01Xd4bRtS2CukorUJbmMVodD"

    def test_assistant_turn_stop_reason_and_response_id_absent(self) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "a1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": "hi",
                },
            },
        ]

        parsed = parse_session(records, "test")

        turn = next(r for r in parsed.records if isinstance(r, AssistantTurn))
        assert turn.stop_reason is None
        assert turn.response_id is None

    def test_tool_result_fields(self) -> None:
        parsed = parse_fixture(ORCHESTRATOR)
        result = parsed.result_by_callid["toolu_01152PyLsTCKsfJT8Q5YNCMn"]
        assert result.tool_name == "exec"
        assert result.is_error is False
        assert result.details is not None
        assert result.details["exitCode"] == 0

    def test_compaction_record(self) -> None:
        parsed = parse_fixture(FIXTURES / "compaction_session.jsonl")
        compactions = [r for r in parsed.records if isinstance(r, CompactionRecord)]
        assert len(compactions) == 1
        c = compactions[0]
        assert c.tokens_before == 81290
        assert c.summary is not None and c.summary.startswith("## Goal")
        assert c.first_kept_entry_id == "c1"
        assert c.from_hook is False

    def test_missing_header_raises(self) -> None:
        records = [make_message("u1", "x", "user", "hi")]
        with pytest.raises(ValueError, match="session"):
            parse_session(records, "test")

    def test_unknown_record_type_raises(self) -> None:
        records: list[dict[str, Any]] = [dict(HEADER), {"type": "wibble", "id": "w1"}]
        with pytest.raises(ValueError, match="wibble"):
            parse_session(records, "test")

    def test_unknown_role_raises(self) -> None:
        records = [dict(HEADER), make_message("m1", "s1", "narrator", "hi")]
        with pytest.raises(ValueError, match="narrator"):
            parse_session(records, "test")

    def test_unknown_assistant_content_block_type_raises(self) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "a1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": [{"type": "video", "data": "abc"}],
                },
            },
        ]

        with pytest.raises(ValueError, match="video"):
            parse_session(records, "test")

    @pytest.mark.parametrize(
        "content,match",
        [
            ({"weird": "dict"}, "content shape 'dict'"),
            (42, "content shape 'int'"),
            ([42], "content block 'int'"),
            ([["nested"]], "content block 'list'"),
        ],
    )
    def test_unmappable_assistant_content_raises(
        self, content: Any, match: str
    ) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "a1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": content,
                },
            },
        ]

        with pytest.raises(ValueError, match=match):
            parse_session(records, "test")

    @pytest.mark.parametrize("content", [None, "plain text", ["bare string block"]])
    def test_mappable_assistant_content_accepted(self, content: Any) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "a1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": content,
                },
            },
        ]

        parsed = parse_session(records, "test")

        assert sum(1 for r in parsed.records if isinstance(r, AssistantTurn)) == 1

    def test_non_integer_bookkeeping_fields_coerce_to_none(self) -> None:
        records: list[dict[str, Any]] = [
            {**HEADER, "version": "2.0"},
            {
                "type": "compaction",
                "id": "c1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "summary": "s",
                "tokensBefore": "lots",
            },
        ]

        parsed = parse_session(records, "test")

        assert parsed.header.version is None
        compaction = next(r for r in parsed.records if isinstance(r, CompactionRecord))
        assert compaction.tokens_before is None

    def test_divergent_branch_raises(self) -> None:
        records = [
            dict(HEADER),
            make_message("u1", "s1", "user", "hi"),
            make_message("u2", "u1", "user", "branch one"),
            make_message("u3", "u1", "user", "branch two"),
        ]

        with pytest.raises(ValueError, match="divergent"):
            parse_session(records, "test")

    def test_leaf_does_not_count_as_divergence(self) -> None:
        # A leaf record sharing a parent with a message is bookkeeping, not a branch.
        records = [
            dict(HEADER),
            make_message("u1", "s1", "user", "hi"),
            {"type": "leaf", "id": "l1", "parentId": "u1", "targetId": "s1"},
            make_message("u2", "u1", "user", "continue"),
        ]

        parsed = parse_session(records, "test")

        assert len(parsed.records) == 2

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="[Ee]mpty"):
            parse_session([], "test")

    def test_duplicate_tool_call_id_warns_and_keeps_last(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "t1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "toolResult",
                    "toolCallId": "tc1",
                    "toolName": "exec",
                    "content": "first",
                },
            },
            {
                "type": "message",
                "id": "t2",
                "parentId": "t1",
                "timestamp": "2026-07-06T10:00:02.000Z",
                "message": {
                    "role": "toolResult",
                    "toolCallId": "tc1",
                    "toolName": "exec",
                    "content": "second",
                },
            },
        ]

        with caplog.at_level(logging.WARNING):
            parsed = parse_session(records, "test")

        assert any("tc1" in rec.message for rec in caplog.records)
        assert parsed.result_by_callid["tc1"].content == "second"

    def test_tool_result_without_call_id_warns(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "t1",
                "parentId": "s1",
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "toolResult",
                    "toolName": "exec",
                    "content": "orphan",
                },
            },
        ]

        with caplog.at_level(logging.WARNING):
            parsed = parse_session(records, "test")

        assert any("test" in rec.message for rec in caplog.records)
        assert parsed.result_by_callid == {}
