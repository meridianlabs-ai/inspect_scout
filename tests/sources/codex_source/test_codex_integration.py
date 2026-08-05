"""Integration tests for the Codex CLI import source."""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from inspect_ai.event import (
    CompactionEvent,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    ToolEvent,
)

if TYPE_CHECKING:
    from inspect_scout import Transcript

TID1 = "0199aaaa-0000-7000-8000-000000000001"
TID2 = "0199aaaa-0000-7000-8000-000000000002"
TID3 = "0199aaaa-0000-7000-8000-000000000003"
TID4 = "0199aaaa-0000-7000-8000-000000000004"
TID4C = "0199aaaa-0000-7000-8000-000000000104"
TID5 = "0199aaaa-0000-7000-8000-000000000005"
TID6 = "0199aaaa-0000-7000-8000-000000000006"
TID7 = "0199aaaa-0000-7000-8000-000000000007"
TID8 = "0199aaaa-0000-7000-8000-000000000008"
TID8C = "0199aaaa-0000-7000-8000-000000000108"
TID9 = "0199aaaa-0000-7000-8000-000000000009"
LEGACY_TID = "0199aaaa-0000-7000-8000-00000000000a"


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


def _fixture_file(thread_id: str) -> str:
    fixtures = Path(__file__).parent / "fixtures"
    matches = [f.name for f in fixtures.glob(f"rollout-*{thread_id}.jsonl")]
    assert len(matches) == 1
    return matches[0]


def _copy_fixtures(dest: Path, thread_ids: list[str]) -> Path:
    """Copy fixture files for the given thread ids into an isolated dir."""
    fixtures = Path(__file__).parent / "fixtures"
    dest.mkdir(parents=True, exist_ok=True)
    for tid in thread_ids:
        name = _fixture_file(tid)
        shutil.copy(fixtures / name, dest / name)
    return dest


async def _import_all(path: Path, **kwargs: Any) -> list["Transcript"]:
    from inspect_scout.sources import codex

    return [t async for t in codex(path=path, **kwargs)]


async def _import_one(path: Path, thread_id: str) -> "Transcript":
    transcripts = await _import_all(path, session_id=thread_id)
    assert len(transcripts) == 1
    return transcripts[0]


# ── basic sessions ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_simple_session(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID1)

    assert t.transcript_id == TID1
    assert t.source_id == TID1
    assert t.source_type == "codex_cli"
    assert t.agent == "codex-cli"
    assert t.model == "gpt-5.1-codex"
    assert t.task_set == "/home/user/testproj"
    assert t.task_id == TID1
    assert t.total_tokens == 120
    assert t.date is not None and t.date.startswith("2026-08-01T10:00:00")
    assert t.source_uri is not None and t.source_uri.endswith(f"#{TID1}")

    assert t.metadata["cwd"] == "/home/user/testproj"
    assert t.metadata["version"] == "0.146.1"
    assert t.metadata["source"] == "cli"
    assert t.metadata["gitBranch"] == "main"
    assert t.metadata["originator"] == "codex_cli_rs"

    # environment context + user question + assistant answer
    assert t.message_count == 3
    assert [m.role for m in t.messages] == ["user", "user", "assistant"]
    assert t.messages[1].text == "What is 2+2?"
    assert t.messages[2].text == "2+2 = 4."

    model_events = [e for e in t.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 1
    # duplicate legacy user_message/agent_message events were not double-counted
    assert len([m for m in t.messages if m.text == "What is 2+2?"]) == 1


@pytest.mark.asyncio
async def test_tool_session(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID2)

    assert t.total_tokens == 600
    model_events = [e for e in t.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 3

    tool_events = [e for e in t.events if isinstance(e, ToolEvent)]
    assert [e.function for e in tool_events] == ["shell", "apply_patch"]
    assert tool_events[0].arguments == {"command": ["pytest", "-x"]}
    assert "FAILED tests/test_x.py" in str(tool_events[0].result)
    # custom tool call: freeform input surfaced as arguments + diff view
    assert "Begin Patch" in str(tool_events[1].arguments.get("input"))
    assert tool_events[1].view is not None

    # user, asst+call, tool, asst+call, tool, asst
    assert [m.role for m in t.messages] == [
        "user",
        "assistant",
        "tool",
        "assistant",
        "tool",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_compaction_session(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID3)

    compactions = [e for e in t.events if isinstance(e, CompactionEvent)]
    assert len(compactions) == 1
    assert compactions[0].tokens_before == 50000
    assert compactions[0].type == "summary"
    assert compactions[0].source == "codex_cli"

    # second model call saw the replacement history, not the raw history
    model_events = [e for e in t.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 2
    assert [m.text for m in model_events[1].input] == [
        "first question",
        "Summary: user asked a first question and it was answered.",
        "second question",
    ]

    # span_messages(compaction="all") stitches across the boundary:
    # both pre- and post-compaction content present in transcript messages
    texts = [m.text for m in t.messages]
    assert "first answer" in texts
    assert "second answer" in texts

    assert t.total_tokens == 40100 + 1000


# ── sub-agents ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spawn_agent_session(tmp_path: Path) -> None:
    session_dir = _copy_fixtures(tmp_path, [TID4, TID4C])
    transcripts = await _import_all(session_dir)

    # child thread is nested, not imported standalone
    assert len(transcripts) == 1
    t = transcripts[0]
    assert t.transcript_id == TID4

    agent_spans = [
        e for e in t.events if isinstance(e, SpanBeginEvent) and e.type == "agent"
    ]
    assert len(agent_spans) == 1
    assert agent_spans[0].name == "zippy"
    assert agent_spans[0].metadata is not None
    assert agent_spans[0].metadata["thread_id"] == TID4C

    # child model call present in events (nested), tokens summed across both
    model_events = [e for e in t.events if isinstance(e, ModelEvent)]
    child_models = [e for e in model_events if e.model == "gpt-5.1-codex-mini"]
    assert len(child_models) == 1
    assert t.total_tokens == 500 + 200 + 150

    # child conversation excluded from top-level messages
    texts = [m.text for m in t.messages]
    assert not any("3 modules: a, b, c" in text for text in texts)
    assert any("subagent found 3 modules" in text for text in texts)


@pytest.mark.asyncio
async def test_review_session_imported_standalone(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID9)
    assert t.metadata["source"] == {"subagent": "review"}
    assert t.metadata["parent_thread_id"] == TID4
    assert [m.role for m in t.messages] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_internal_subagent_skipped(tmp_path: Path) -> None:
    # a compaction subagent thread should not import
    tid = "0199cccc-0000-7000-8000-000000000001"
    lines = [
        {
            "timestamp": "2026-08-01T11:00:00Z",
            "type": "session_meta",
            "payload": {"id": tid, "cwd": "/x", "source": {"subagent": "compact"}},
        },
        {
            "timestamp": "2026-08-01T11:00:01Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "summarize"}],
            },
        },
    ]
    f = tmp_path / f"rollout-2026-08-01T11-00-00-{tid}.jsonl"
    f.write_text("\n".join(json.dumps(ln) for ln in lines))
    assert await _import_all(tmp_path) == []


# ── interruption / rollback ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interrupted_session(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID5)

    tool_events = [e for e in t.events if isinstance(e, ToolEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].error is not None
    assert "interrupted" in tool_events[0].error.message

    info_events = [e for e in t.events if isinstance(e, InfoEvent)]
    assert any(
        isinstance(e.data, dict) and e.data.get("type") == "turn_aborted"
        for e in info_events
    )


@pytest.mark.asyncio
async def test_rollback_session(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID6)

    model_events = [e for e in t.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 3
    # post-undo model call did not see the rolled-back turn
    assert [m.text for m in model_events[2].input] == ["q1", "a1", "q3"]
    # rolled-back events remain in the timeline
    assert any(e.output.choices[0].message.text == "a2" for e in model_events)
    # final messages reflect the model's post-undo view
    texts = [m.text for m in t.messages]
    assert "q2" not in texts and "q3" in texts


# ── forks ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_copied_fork(fixtures_dir: Path) -> None:
    t = await _import_one(fixtures_dir, TID7)

    # first session_meta wins as identity; fork link in metadata
    assert t.transcript_id == TID7
    assert t.metadata["forked_from_id"] == TID6

    texts = [m.text for m in t.messages]
    assert "q1" in texts  # copied prefix present
    assert "forked answer" in texts
    assert t.total_tokens == 100


@pytest.mark.asyncio
async def test_referenced_fork_resolves_history_base(tmp_path: Path) -> None:
    session_dir = _copy_fixtures(tmp_path, [TID8, TID8C])
    t_child = await _import_one(session_dir, TID8C)

    assert t_child.metadata["history_base_thread_id"] == TID8
    assert t_child.metadata["history_mode"] == "paginated"
    texts = [m.text for m in t_child.messages]
    # prefix up to ordinal 4 (exclusive) inherited from parent
    assert "parent q1" in texts and "parent a1" in texts
    assert "parent q2" not in texts
    assert "fork question" in texts and "fork answer" in texts

    # the parent imports as its own complete transcript
    t_parent = await _import_one(session_dir, TID8)
    parent_texts = [m.text for m in t_parent.messages]
    assert "parent q2" in parent_texts


@pytest.mark.asyncio
async def test_referenced_fork_with_missing_parent(tmp_path: Path) -> None:
    # child imports (with a warning) even when the parent file is gone
    session_dir = _copy_fixtures(tmp_path, [TID8C])
    t = await _import_one(session_dir, TID8C)
    texts = [m.text for m in t.messages]
    assert "fork question" in texts
    assert "parent q1" not in texts


# ── format edge cases ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_pre_envelope_file_skipped(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    legacy = next(fixtures.glob(f"rollout-*{LEGACY_TID}.jsonl"))
    shutil.copy(legacy, tmp_path / legacy.name)
    assert await _import_all(tmp_path) == []


@pytest.mark.asyncio
async def test_zst_compressed_rollout(tmp_path: Path) -> None:
    import zstandard

    fixtures = Path(__file__).parent / "fixtures"
    src = fixtures / _fixture_file(TID1)
    compressed = tmp_path / (src.name + ".zst")
    compressed.write_bytes(zstandard.ZstdCompressor().compress(src.read_bytes()))

    transcripts = await _import_all(tmp_path)
    assert len(transcripts) == 1
    assert transcripts[0].transcript_id == TID1
    assert transcripts[0].total_tokens == 120


@pytest.mark.asyncio
async def test_full_fixtures_dir(fixtures_dir: Path) -> None:
    transcripts = await _import_all(fixtures_dir)
    ids = {t.transcript_id for t in transcripts}
    # everything imports except the spawned child (nested) and the legacy file
    assert ids == {TID1, TID2, TID3, TID4, TID5, TID6, TID7, TID8, TID8C, TID9}


# ── promoted parameters ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_limit_with_mtime_ordering(tmp_path: Path) -> None:
    session_dir = _copy_fixtures(tmp_path, [TID1, TID2])
    f1 = session_dir / _fixture_file(TID1)
    f2 = session_dir / _fixture_file(TID2)
    old = datetime(2026, 7, 1).timestamp()
    new = datetime(2026, 8, 1).timestamp()
    os.utime(f1, (old, old))
    os.utime(f2, (new, new))

    transcripts = await _import_all(session_dir, limit=1)
    assert len(transcripts) == 1
    assert transcripts[0].transcript_id == TID2  # newest first


@pytest.mark.asyncio
async def test_time_filters(tmp_path: Path) -> None:
    session_dir = _copy_fixtures(tmp_path, [TID1, TID2])
    f1 = session_dir / _fixture_file(TID1)
    f2 = session_dir / _fixture_file(TID2)
    old = datetime(2026, 7, 1)
    new = datetime(2026, 8, 1)
    os.utime(f1, (old.timestamp(), old.timestamp()))
    os.utime(f2, (new.timestamp(), new.timestamp()))

    transcripts = await _import_all(session_dir, from_time=old + timedelta(days=7))
    assert [t.transcript_id for t in transcripts] == [TID2]

    transcripts = await _import_all(session_dir, to_time=old + timedelta(days=7))
    assert [t.transcript_id for t in transcripts] == [TID1]


@pytest.mark.asyncio
async def test_codex_home_discovery_and_thread_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    codex_home = tmp_path / "codex-home"
    sessions_day = codex_home / "sessions" / "2026" / "08" / "01"
    _copy_fixtures(sessions_day, [TID1])
    archived_day = codex_home / "archived_sessions" / "2026" / "07" / "01"
    _copy_fixtures(archived_day, [TID2])
    (codex_home / "session_index.jsonl").write_text(
        json.dumps({"id": TID1, "thread_name": "quick-arithmetic", "updated_at": 1})
        + "\n"
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    from inspect_scout.sources import codex

    transcripts = [t async for t in codex()]
    assert [t.transcript_id for t in transcripts] == [TID1]
    assert transcripts[0].task_id == "quick-arithmetic"

    transcripts = [t async for t in codex(include_archived=True)]
    assert {t.transcript_id for t in transcripts} == {TID1, TID2}


@pytest.mark.asyncio
async def test_reimport_produces_identical_ids(fixtures_dir: Path) -> None:
    # transcript ids are deterministic (thread id), so re-imports dedup in the DB
    first = await _import_all(fixtures_dir)
    second = await _import_all(fixtures_dir)
    assert {t.transcript_id for t in first} == {t.transcript_id for t in second}

    # identical message content shares an id within a transcript
    t1 = next(t for t in first if t.transcript_id == TID3)
    model_events = [e for e in t1.events if isinstance(e, ModelEvent)]
    first_input_id = model_events[0].input[0].id
    matching = [m for m in t1.messages if m.id == first_input_id]
    assert len(matching) == 1 and matching[0].text == "first question"
