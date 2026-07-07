"""End-to-end tests for the openclaw() native session source."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent, SpanBeginEvent, ToolEvent
from inspect_scout import Transcript
from inspect_scout.sources._openclaw import OPENCLAW_SOURCE_TYPE, openclaw

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
ORCHESTRATOR_ID = "cfabe24d-8b34-4031-a393-689524b2028f"

# A real captured OpenClaw bundle (an "LRU cache" coding session that fans out
# to per-language specialists and L1 dispatchers, some of which spawn their own
# grandchildren). Kept as a regression corpus for debugging future changes
# against genuine session data. The orchestrator and its complete descendant
# tree (9 direct children + 10 deeper grandchildren) are copied.
FX_LRU = FIXTURES / "lru_demo"
LRU_ORCHESTRATOR_ID = "b2e732c1-5f16-4ebe-ba84-0a11adc45c66"


async def collect(path: Path) -> list[Transcript]:
    return [t async for t in openclaw(path)]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _header(session_id: str, timestamp: str) -> dict[str, Any]:
    return {
        "type": "session",
        "version": 3,
        "id": session_id,
        "timestamp": timestamp,
        "cwd": "/w",
    }


def _user(rec_id: str, parent_id: str | None, timestamp: str) -> dict[str, Any]:
    return {
        "type": "message",
        "id": rec_id,
        "parentId": parent_id,
        "timestamp": timestamp,
        "message": {"role": "user", "content": "hello", "timestamp": 0},
    }


def _assistant(
    rec_id: str, parent_id: str, timestamp: str, content: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "type": "message",
        "id": rec_id,
        "parentId": parent_id,
        "timestamp": timestamp,
        "message": {
            "role": "assistant",
            "content": content,
            "api": "anthropic-messages",
            "provider": "anthropic",
            "model": "claude-opus-4-8",
            "usage": {
                "input": 10,
                "output": 20,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 30,
            },
            "stopReason": "toolUse",
            "timestamp": 0,
        },
    }


def _spawn_result(
    rec_id: str, parent_id: str, timestamp: str, call_id: str, child_key: str
) -> dict[str, Any]:
    accepted = json.dumps({"status": "accepted", "childSessionKey": child_key})
    return {
        "type": "message",
        "id": rec_id,
        "parentId": parent_id,
        "timestamp": timestamp,
        "message": {
            "role": "toolResult",
            "toolCallId": call_id,
            "toolName": "sessions_spawn",
            "content": [{"type": "text", "text": accepted}],
            "isError": False,
            "timestamp": 0,
        },
    }


def _spawning_session(
    session_id: str, call_id: str, child_key: str, child_label: str
) -> list[dict[str, Any]]:
    """A session that spawns one sub-agent via sessions_spawn."""
    return [
        _header(session_id, "2026-07-06T10:00:00.000Z"),
        _user("u1", None, "2026-07-06T10:00:01.000Z"),
        _assistant(
            "a1",
            "u1",
            "2026-07-06T10:00:02.000Z",
            [
                {"type": "text", "text": "spawning"},
                {
                    "type": "toolCall",
                    "id": call_id,
                    "name": "sessions_spawn",
                    "arguments": {
                        "task": "do work",
                        "label": child_label,
                        "mode": "run",
                    },
                },
            ],
        ),
        _spawn_result("r1", "a1", "2026-07-06T10:00:03.000Z", call_id, child_key),
    ]


def _spawning_session_with_result(
    session_id: str, call_id: str, result_json: dict[str, Any]
) -> list[dict[str, Any]]:
    """Like ``_spawning_session`` but with an arbitrary spawn result payload."""
    return [
        _header(session_id, "2026-07-06T10:00:00.000Z"),
        _user("u1", None, "2026-07-06T10:00:01.000Z"),
        _assistant(
            "a1",
            "u1",
            "2026-07-06T10:00:02.000Z",
            [
                {"type": "text", "text": "spawning"},
                {
                    "type": "toolCall",
                    "id": call_id,
                    "name": "sessions_spawn",
                    "arguments": {"task": "do work", "label": "child", "mode": "run"},
                },
            ],
        ),
        {
            "type": "message",
            "id": "r1",
            "parentId": "a1",
            "timestamp": "2026-07-06T10:00:03.000Z",
            "message": {
                "role": "toolResult",
                "toolCallId": call_id,
                "toolName": "sessions_spawn",
                "content": [{"type": "text", "text": json.dumps(result_json)}],
                "isError": False,
                "timestamp": 0,
            },
        },
    ]


def _write_nested_bundle(tmp_path: Path) -> tuple[str, str]:
    """Write an orchestrator → child → grandchild spawn chain with registry.

    Returns ``(orch_id, child_id)``.
    """
    orch_id = "00000000-0000-0000-0000-00000000000a"
    child_id = "00000000-0000-0000-0000-00000000000b"
    grandchild_id = "00000000-0000-0000-0000-00000000000c"
    child_key = "agent:main:subagent:child1"
    grandchild_key = "agent:main:subagent:child2"
    registry = {
        "agent:main:main": {"sessionId": orch_id},
        child_key: {
            "sessionId": child_id,
            "spawnedBy": "agent:main:main",
            "label": "child",
            "status": "done",
        },
        grandchild_key: {
            "sessionId": grandchild_id,
            "spawnedBy": child_key,
            "label": "grandchild",
            "status": "done",
        },
    }
    (tmp_path / "sessions.json").write_text(json.dumps(registry), encoding="utf-8")
    _write_jsonl(
        tmp_path / f"{orch_id}.jsonl",
        _spawning_session(orch_id, "tc-orch", child_key, "child"),
    )
    _write_jsonl(
        tmp_path / f"{child_id}.jsonl",
        _spawning_session(child_id, "tc-child", grandchild_key, "grandchild"),
    )
    _write_jsonl(
        tmp_path / f"{grandchild_id}.jsonl",
        [
            _header(grandchild_id, "2026-07-06T10:00:00.000Z"),
            _user("u1", None, "2026-07-06T10:00:01.000Z"),
            _assistant(
                "a1",
                "u1",
                "2026-07-06T10:00:02.000Z",
                [{"type": "text", "text": "done"}],
            ),
        ],
    )
    return orch_id, child_id


class TestOpenclawSource:
    @pytest.mark.asyncio
    async def test_bundle_yields_one_orchestrator_transcript(self) -> None:
        transcripts = await collect(FX_DEMO)
        assert len(transcripts) == 1
        t = transcripts[0]
        assert t.transcript_id == ORCHESTRATOR_ID
        assert t.source_id == ORCHESTRATOR_ID
        assert t.source_type == OPENCLAW_SOURCE_TYPE == "openclaw"
        assert t.agent == "openclaw"
        assert t.model == "claude-opus-4-8"
        assert t.task_id == ORCHESTRATOR_ID
        assert t.message_count == len(t.messages) == 29
        assert t.total_tokens is not None and t.total_tokens > 0
        assert t.total_time is not None and t.total_time > 0
        assert t.date is not None and t.date.startswith("2026-06-29")

    @pytest.mark.asyncio
    async def test_transcript_metadata(self) -> None:
        (t,) = await collect(FX_DEMO)
        assert t.metadata["n_subagents"] == 3
        assert len(t.metadata["subagent_session_ids"]) == 3
        assert t.metadata["session_key"] == (
            "agent:main:dashboard:e6746281-f3cd-4be5-9d0c-633772cdcace"
        )
        assert t.metadata["parent_session_key"] == (
            "agent:main:dashboard:9174711d-0a3b-42df-856b-0f07fbb91d63"
        )
        assert t.metadata["cwd"] == "/home/ubuntu/.openclaw/workspace"
        assert t.metadata["session_version"] == 3
        assert t.metadata["status"] == "done"
        assert t.metadata["channel"] == "webchat"
        assert "systemPrompt" in t.metadata["system_prompt_report"]

    @pytest.mark.asyncio
    async def test_stable_message_ids_applied(self) -> None:
        (t,) = await collect(FX_DEMO)
        ids = [m.id for m in t.messages]
        assert len(ids) == len(set(ids))
        model_events = [e for e in t.events if isinstance(e, ModelEvent)]
        # thread prefix ids match between model event inputs and the thread
        assert model_events[1].input[0].id == t.messages[0].id

    @pytest.mark.asyncio
    async def test_explicit_subagent_file_imports_standalone(self) -> None:
        path = FX_DEMO / "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl"
        transcripts = [t async for t in openclaw(path)]
        assert len(transcripts) == 1
        assert transcripts[0].transcript_id == "8c6aeab3-993e-43d5-934a-04aa4a5f3804"

    @pytest.mark.asyncio
    async def test_session_id_subagent_imports_standalone(self) -> None:
        session_id = "8c6aeab3-993e-43d5-934a-04aa4a5f3804"
        transcripts = [t async for t in openclaw(FX_DEMO, session_id=session_id)]
        assert len(transcripts) == 1
        assert transcripts[0].transcript_id == session_id

    @pytest.mark.asyncio
    async def test_no_registry_imports_all_standalone(self, tmp_path: Path) -> None:
        for f in FX_DEMO.glob("*.jsonl"):
            if not f.name.endswith(".trajectory.jsonl"):
                shutil.copy(f, tmp_path / f.name)
        transcripts = [t async for t in openclaw(tmp_path)]
        assert len(transcripts) == 4
        assert all(t.metadata.get("n_subagents") == 0 for t in transcripts)

    @pytest.mark.asyncio
    async def test_limit(self, tmp_path: Path) -> None:
        for f in FX_DEMO.glob("*.jsonl"):
            if not f.name.endswith(".trajectory.jsonl"):
                shutil.copy(f, tmp_path / f.name)
        transcripts = [t async for t in openclaw(tmp_path, limit=2)]
        assert len(transcripts) == 2

    @pytest.mark.asyncio
    async def test_empty_dir_yields_nothing(self, tmp_path: Path) -> None:
        assert await collect(tmp_path) == []

    @pytest.mark.asyncio
    async def test_stray_non_session_file_skipped_with_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # a foreign .jsonl (e.g. a telemetry log) sharing the directory must
        # not abort the import of the valid session bundle beside it
        for name in ("sessions.json", *(f.name for f in FX_DEMO.glob("*.jsonl"))):
            if not name.endswith(".trajectory.jsonl"):
                shutil.copy(FX_DEMO / name, tmp_path / name)
        stray = tmp_path / "telemetry.jsonl"
        stray.write_text('{"type":"message.in","payload":{}}\n', encoding="utf-8")
        with caplog.at_level(logging.WARNING):
            transcripts = await collect(tmp_path)
        assert [t.transcript_id for t in transcripts] == [ORCHESTRATOR_ID]
        assert any("telemetry.jsonl" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_nested_spawn_counts_direct_children_only(
        self, tmp_path: Path
    ) -> None:
        orch_id, child_id = _write_nested_bundle(tmp_path)

        transcripts = await collect(tmp_path)
        # child + grandchild are spawnedBy others — only the orchestrator yields
        assert len(transcripts) == 1
        t = transcripts[0]
        assert t.transcript_id == orch_id
        # recursion DID happen: both nested spans exist in the event stream...
        agent_begins = [
            e for e in t.events if isinstance(e, SpanBeginEvent) and e.type == "agent"
        ]
        assert len(agent_begins) == 2
        # ...but the metadata counts only the orchestrator's DIRECT children
        assert t.metadata["n_subagents"] == 1
        assert t.metadata["subagent_session_ids"] == [child_id]

    @pytest.mark.asyncio
    async def test_nested_spawn_spans_nest_by_parent_id(self, tmp_path: Path) -> None:
        from inspect_ai.event import EventTreeSpan, event_tree

        _write_nested_bundle(tmp_path)
        (t,) = await collect(tmp_path)
        begins = {
            str(e.name): e
            for e in t.events
            if isinstance(e, SpanBeginEvent) and e.type == "agent"
        }
        # the tree nests spans by parent_id: the child span is a root span,
        # the grandchild's parent_id points at the child span
        assert begins["child"].parent_id is None
        assert begins["grandchild"].parent_id == begins["child"].id
        root_spans = [n for n in event_tree(t.events) if isinstance(n, EventTreeSpan)]
        assert [n.name for n in root_spans] == ["child"]
        nested_spans = [
            n for n in root_spans[0].children if isinstance(n, EventTreeSpan)
        ]
        assert [n.name for n in nested_spans] == ["grandchild"]

    @pytest.mark.asyncio
    async def test_date_is_first_message_timestamp_not_leading_config_change(
        self, tmp_path: Path
    ) -> None:
        session_id = "00000000-0000-0000-0000-0000000000d1"
        _write_jsonl(
            tmp_path / f"{session_id}.jsonl",
            [
                _header(session_id, "2026-07-01T00:00:00.000Z"),
                {
                    "type": "model_change",
                    "id": "mc1",
                    "parentId": None,
                    "timestamp": "2026-07-02T00:00:00.000Z",
                    "provider": "anthropic",
                    "modelId": "claude-opus-4-8",
                },
                _user("u1", "mc1", "2026-07-03T00:00:00.000Z"),
                _assistant(
                    "a1",
                    "u1",
                    "2026-07-04T00:00:00.000Z",
                    [{"type": "text", "text": "hi"}],
                ),
            ],
        )
        (t,) = await collect(tmp_path)
        assert t.date is not None and t.date.startswith("2026-07-03")

    @pytest.mark.asyncio
    async def test_total_time_fallback_without_events(self, tmp_path: Path) -> None:
        session_id = "00000000-0000-0000-0000-0000000000f0"
        _write_jsonl(
            tmp_path / f"{session_id}.jsonl",
            [
                _header(session_id, "2026-07-06T10:00:00.000Z"),
                _user("u1", None, "2026-07-06T10:00:00.000Z"),
                _user("u2", "u1", "2026-07-06T10:01:00.000Z"),
            ],
        )
        transcripts = await collect(tmp_path)
        assert len(transcripts) == 1
        assert transcripts[0].total_time == pytest.approx(60.0)

    @pytest.mark.asyncio
    async def test_header_only_session_skipped_with_log(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        (tmp_path / "e0000000-0000-0000-0000-000000000001.jsonl").write_text(
            json.dumps(
                {
                    "type": "session",
                    "version": 3,
                    "id": "e0000000-0000-0000-0000-000000000001",
                    "timestamp": "2026-07-06T10:00:00.000Z",
                    "cwd": "/w",
                }
            )
            + "\n"
        )
        with caplog.at_level(logging.INFO):
            transcripts = [t async for t in openclaw(tmp_path)]
        assert transcripts == []
        assert any(
            "e0000000-0000-0000-0000-000000000001" in rec.message
            for rec in caplog.records
        )

    @pytest.mark.asyncio
    async def test_recursion_bound_degrades_to_plain_tool_event(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # orchestrator + 6 descendants, each spawning the next: chain length
        # exceeds max_depth=5, so the 6th spawn degrades to a plain tool event.
        n = 7
        ids = [f"00000000-0000-0000-0000-0000000000{i:02d}" for i in range(n)]
        keys = [f"agent:main:subagent:s{i}" for i in range(n)]
        registry: dict[str, Any] = {"agent:main:main": {"sessionId": ids[0]}}
        for i in range(1, n):
            registry[keys[i]] = {
                "sessionId": ids[i],
                "spawnedBy": "agent:main:main" if i == 1 else keys[i - 1],
                "label": f"child{i}",
                "status": "done",
            }
        (tmp_path / "sessions.json").write_text(json.dumps(registry), encoding="utf-8")
        for i in range(n - 1):
            _write_jsonl(
                tmp_path / f"{ids[i]}.jsonl",
                _spawning_session(ids[i], f"tc-{i}", keys[i + 1], f"child{i + 1}"),
            )
        _write_jsonl(
            tmp_path / f"{ids[n - 1]}.jsonl",
            [
                _header(ids[n - 1], "2026-07-06T10:00:00.000Z"),
                _user("u1", None, "2026-07-06T10:00:01.000Z"),
                _assistant(
                    "a1",
                    "u1",
                    "2026-07-06T10:00:02.000Z",
                    [{"type": "text", "text": "done"}],
                ),
            ],
        )

        with caplog.at_level(logging.WARNING):
            transcripts = await collect(tmp_path)
        assert len(transcripts) == 1
        t = transcripts[0]
        agent_begins = [
            e for e in t.events if isinstance(e, SpanBeginEvent) and e.type == "agent"
        ]
        assert len(agent_begins) == 5
        spawn_tool_events = [
            e
            for e in t.events
            if isinstance(e, ToolEvent) and e.function == "sessions_spawn"
        ]
        # 6 spawns total: 5 folded into spans, 1 degraded to a plain tool event
        assert len(spawn_tool_events) == 6
        degraded = [e for e in spawn_tool_events if e.agent_span_id is None]
        assert len(degraded) == 1
        assert any("recursion" in rec.message.lower() for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_failed_spawn_yields_plain_tool_event_no_span(
        self, tmp_path: Path
    ) -> None:
        orch_id = "00000000-0000-0000-0000-0000000000f1"
        _write_jsonl(
            tmp_path / f"{orch_id}.jsonl",
            _spawning_session_with_result(
                orch_id, "tc-fail", {"status": "error", "error": "spawn failed"}
            ),
        )

        transcripts = await collect(tmp_path)
        assert len(transcripts) == 1
        t = transcripts[0]
        assert not any(
            isinstance(e, SpanBeginEvent) and e.type == "agent" for e in t.events
        )
        spawn_tool_events = [
            e
            for e in t.events
            if isinstance(e, ToolEvent) and e.function == "sessions_spawn"
        ]
        assert len(spawn_tool_events) == 1
        assert spawn_tool_events[0].agent_span_id is None

    @pytest.mark.asyncio
    async def test_child_key_not_in_registry_warns_no_span(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        orch_id = "00000000-0000-0000-0000-0000000000f2"
        ghost_key = "agent:main:subagent:ghost"
        registry = {"agent:main:main": {"sessionId": orch_id}}
        (tmp_path / "sessions.json").write_text(json.dumps(registry), encoding="utf-8")
        _write_jsonl(
            tmp_path / f"{orch_id}.jsonl",
            _spawning_session_with_result(
                orch_id,
                "tc-ghost",
                {"status": "accepted", "childSessionKey": ghost_key},
            ),
        )

        with caplog.at_level(logging.WARNING):
            transcripts = await collect(tmp_path)
        assert len(transcripts) == 1
        t = transcripts[0]
        assert not any(
            isinstance(e, SpanBeginEvent) and e.type == "agent" for e in t.events
        )
        spawn_tool_events = [
            e
            for e in t.events
            if isinstance(e, ToolEvent) and e.function == "sessions_spawn"
        ]
        assert len(spawn_tool_events) == 1
        assert spawn_tool_events[0].agent_span_id is None
        assert any(ghost_key in rec.message for rec in caplog.records)


class TestLruDemoFixture:
    """Smoke test that the captured real-world LRU bundle imports."""

    @pytest.mark.asyncio
    async def test_real_bundle_imports_with_full_descendant_tree(self) -> None:
        transcripts = await collect(FX_LRU)
        # Only the orchestrator yields; its spawned children fold in as spans.
        assert len(transcripts) == 1
        t = transcripts[0]
        assert t.transcript_id == LRU_ORCHESTRATOR_ID
        assert t.source_type == OPENCLAW_SOURCE_TYPE
        assert t.message_count == len(t.messages) > 0
        assert t.total_tokens is not None and t.total_tokens > 0
        # n_subagents counts the orchestrator's DIRECT children only...
        assert t.metadata["n_subagents"] == 9
        assert len(t.metadata["subagent_session_ids"]) == 9
        # ...but the whole tree folds in: 9 direct + 10 nested grandchildren,
        # all resolved from files on disk (no degraded/missing spawns).
        agent_spans = [
            e for e in t.events if isinstance(e, SpanBeginEvent) and e.type == "agent"
        ]
        assert len(agent_spans) == 19


class TestRegistration:
    def test_registered_in_sources(self) -> None:
        import inspect_scout.sources as sources

        assert "openclaw" in sources.__all__
        assert callable(sources.openclaw)
