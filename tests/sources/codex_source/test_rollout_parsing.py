"""Unit tests for codex rollout parsing and file discovery."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from inspect_scout.sources._codex.client import (
    discover_rollout_files,
    find_rollout_by_thread_id,
    is_rollout_filename,
    load_thread_names,
    peek_session_meta,
    read_rollout_lines,
    rollout_thread_id,
    sessions_root_for,
)
from inspect_swe._codex_cli._events.rollout_models import (
    ResponseFunctionCall,
    ResponseMessage,
    SessionMetaEvent,
    parse_rollout_event,
    parse_rollout_events,
)

THREAD_ID = "0199aaaa-0000-7000-8000-000000000001"
ROLLOUT_NAME = f"rollout-2026-08-01T10-00-00-{THREAD_ID}.jsonl"


def _line(
    type_: str, payload: dict[str, Any], ts: str = "2026-08-01T10:00:00Z"
) -> dict[str, Any]:
    return {"timestamp": ts, "type": type_, "payload": payload}


# ── model parsing ────────────────────────────────────────────────────────


def test_parse_session_meta_backfills_ids() -> None:
    # old files have only id; parse should backfill session_id
    event = parse_rollout_event(_line("session_meta", {"id": THREAD_ID, "cwd": "/x"}))
    assert isinstance(event, SessionMetaEvent)
    assert event.thread_id == THREAD_ID
    assert event.session_id == THREAD_ID
    assert event.timestamp == "2026-08-01T10:00:00Z"

    event = parse_rollout_event(
        {"type": "session_meta", "payload": {"session_id": THREAD_ID}}
    )
    assert isinstance(event, SessionMetaEvent)
    assert event.thread_id == THREAD_ID


def test_subagent_source_classification() -> None:
    review = SessionMetaEvent(id=THREAD_ID, source={"subagent": "review"})
    assert review.subagent_source() == "review"

    spawn = SessionMetaEvent(
        id=THREAD_ID, source={"subagent": {"thread_spawn": {"depth": 1}}}
    )
    subagent = spawn.subagent_source()
    assert isinstance(subagent, dict) and "thread_spawn" in subagent

    cli = SessionMetaEvent(id=THREAD_ID, source="cli")
    assert cli.subagent_source() is None


def test_parse_response_items() -> None:
    events = parse_rollout_events(
        [
            _line(
                "response_item",
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "hi"}],
                },
            ),
            _line(
                "response_item",
                {
                    "type": "function_call",
                    "name": "shell",
                    "arguments": '{"command": ["ls"]}',
                    "call_id": "c1",
                },
            ),
        ]
    )
    assert len(events) == 2
    assert isinstance(events[0], ResponseMessage)
    assert events[0].role == "user"
    assert isinstance(events[1], ResponseFunctionCall)
    assert events[1].call_id == "c1"


def test_unknown_types_dropped() -> None:
    events = parse_rollout_events(
        [
            _line("response_item", {"type": "some_future_item", "data": 1}),
            _line("event_msg", {"type": "some_future_event"}),
            _line("world_state", {"full": True, "state": {}}),
            {"not": "an envelope"},
            _line("response_item", {"type": "message", "role": "user", "content": []}),
        ]
    )
    # only the message survives
    assert len(events) == 1
    assert isinstance(events[0], ResponseMessage)


def test_compaction_alias_parsed() -> None:
    from inspect_swe._codex_cli._events.rollout_models import ResponseCompaction

    for item_type in ("compaction", "compaction_summary", "context_compaction"):
        event = parse_rollout_event(
            _line("response_item", {"type": item_type, "encrypted_content": "xyz"})
        )
        assert isinstance(event, ResponseCompaction)


# ── filenames / discovery ────────────────────────────────────────────────


def test_rollout_thread_id() -> None:
    assert rollout_thread_id(Path(ROLLOUT_NAME)) == THREAD_ID
    assert rollout_thread_id(Path(ROLLOUT_NAME + ".zst")) == THREAD_ID
    assert rollout_thread_id(Path("other.jsonl")) is None
    assert is_rollout_filename(ROLLOUT_NAME)
    assert is_rollout_filename(ROLLOUT_NAME + ".zst")
    assert not is_rollout_filename("agent-abc.jsonl")


def _write_rollout(path: Path, thread_id: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        _line("session_meta", {"id": thread_id, "cwd": "/x"}),
        _line(
            "response_item",
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "hi"}],
            },
        ),
    ]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n")
    return path


def test_discover_rollout_files(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    f1 = _write_rollout(sessions / "2026" / "08" / "01" / ROLLOUT_NAME, THREAD_ID)
    other_id = "0199bbbb-0000-7000-8000-000000000002"
    f2 = _write_rollout(
        sessions
        / "2026"
        / "08"
        / "02"
        / f"rollout-2026-08-02T09-00-00-{other_id}.jsonl",
        other_id,
    )
    # non-rollout file is ignored
    (sessions / "2026" / "08" / "01" / "notes.jsonl").write_text("{}\n")

    found = discover_rollout_files(sessions)
    assert set(found) == {f1, f2}

    # session_id filter
    found = discover_rollout_files(sessions, session_id=other_id)
    assert found == [f2]

    # specific file
    found = discover_rollout_files(f1)
    assert found == [f1]

    # time filters (mtime based)
    import os

    old = datetime(2026, 7, 1, 12, 0, 0)
    os.utime(f1, (old.timestamp(), old.timestamp()))
    found = discover_rollout_files(sessions, from_time=datetime(2026, 7, 15))
    assert found == [f2]
    found = discover_rollout_files(sessions, to_time=datetime(2026, 7, 15))
    assert found == [f1]

    # newest first
    found = discover_rollout_files(sessions)
    assert found == [f2, f1]


def test_find_rollout_by_thread_id(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    f1 = _write_rollout(sessions / "2026" / "08" / "01" / ROLLOUT_NAME, THREAD_ID)
    assert find_rollout_by_thread_id(THREAD_ID, [sessions]) == f1
    assert find_rollout_by_thread_id("missing-id", [sessions]) is None


def test_sessions_root_for(tmp_path: Path) -> None:
    sessions = tmp_path / "sessions"
    f1 = _write_rollout(sessions / "2026" / "08" / "01" / ROLLOUT_NAME, THREAD_ID)
    assert sessions_root_for(f1) == sessions
    # outside a sessions tree: falls back to the file's directory
    f2 = _write_rollout(tmp_path / "fixtures" / ROLLOUT_NAME, THREAD_ID)
    assert sessions_root_for(f2) == tmp_path / "fixtures"


def test_peek_session_meta(tmp_path: Path) -> None:
    f = _write_rollout(tmp_path / ROLLOUT_NAME, THREAD_ID)
    peeked = peek_session_meta(f)
    assert peeked is not None
    assert peeked["payload"]["id"] == THREAD_ID

    # legacy pre-envelope file: no session_meta envelope
    legacy = (
        tmp_path
        / "rollout-2025-01-01T00-00-00-0199aaaa-0000-7000-8000-00000000000b.jsonl"
    )
    legacy.write_text(json.dumps({"id": "x", "timestamp": "2025-01-01"}) + "\n")
    assert peek_session_meta(legacy) is None


def test_read_zst_rollout(tmp_path: Path) -> None:
    import zstandard

    f = _write_rollout(tmp_path / ROLLOUT_NAME, THREAD_ID)
    compressed = tmp_path / (ROLLOUT_NAME + ".zst")
    compressed.write_bytes(zstandard.ZstdCompressor().compress(f.read_bytes()))

    lines = read_rollout_lines(compressed)
    assert len(lines) == 2
    assert lines[0]["payload"]["id"] == THREAD_ID
    peeked = peek_session_meta(compressed)
    assert peeked is not None

    # uncompressed preferred when both forms exist
    assert find_rollout_by_thread_id(THREAD_ID, [tmp_path]) == f
    f.unlink()
    assert find_rollout_by_thread_id(THREAD_ID, [tmp_path]) == compressed


def test_read_rollout_skips_malformed_lines(tmp_path: Path) -> None:
    f = tmp_path / ROLLOUT_NAME
    f.write_text(
        json.dumps(_line("session_meta", {"id": THREAD_ID}))
        + "\nnot json\n"
        + json.dumps(_line("turn_context", {"model": "gpt-5.1-codex"}))
        + "\n"
    )
    lines = read_rollout_lines(f)
    assert len(lines) == 2


def test_load_thread_names(tmp_path: Path) -> None:
    index = tmp_path / "session_index.jsonl"
    index.write_text(
        json.dumps({"id": THREAD_ID, "thread_name": "old-name", "updated_at": 1})
        + "\n"
        + json.dumps({"id": THREAD_ID, "thread_name": "fix-tests", "updated_at": 2})
        + "\n"
    )
    names = load_thread_names(tmp_path)
    assert names == {THREAD_ID: "fix-tests"}  # last entry wins
    assert load_thread_names(tmp_path / "missing") == {}


def test_timestamp_parsing_and_monotonicity() -> None:
    from inspect_swe._codex_cli._events.rollout import _RolloutProcessor
    from inspect_swe._codex_cli._events.rollout_extraction import parse_timestamp

    assert parse_timestamp("2026-08-01T10:00:00.500Z") is not None
    assert parse_timestamp("not a timestamp") is None
    assert parse_timestamp(None) is None

    proc = _RolloutProcessor()
    e1 = ResponseMessage(timestamp="2026-08-01T10:00:01Z", role="user")
    e2 = ResponseMessage(timestamp="2026-08-01T10:00:00Z", role="user")  # earlier!
    t1 = proc.update_timestamp(e1)
    t2 = proc.update_timestamp(e2)
    assert t2 == t1 + timedelta(milliseconds=1)
