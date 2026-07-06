"""End-to-end tests for the openclaw() native session source."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent, SpanBeginEvent
from inspect_scout import Transcript
from inspect_scout.sources._openclaw import OPENCLAW_SOURCE_TYPE, openclaw

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
ORCHESTRATOR_ID = "cfabe24d-8b34-4031-a393-689524b2028f"


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
    async def test_nested_spawn_counts_direct_children_only(
        self, tmp_path: Path
    ) -> None:
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


class TestRegistration:
    def test_registered_in_sources(self) -> None:
        import inspect_scout.sources as sources

        assert "openclaw" in sources.__all__
        assert callable(sources.openclaw)
