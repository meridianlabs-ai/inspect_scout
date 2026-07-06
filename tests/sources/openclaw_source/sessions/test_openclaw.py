"""End-to-end tests for the openclaw() native session source."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout import Transcript
from inspect_scout.sources._openclaw import OPENCLAW_SOURCE_TYPE, openclaw

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
ORCHESTRATOR_ID = "cfabe24d-8b34-4031-a393-689524b2028f"


async def collect(path: Path) -> list[Transcript]:
    return [t async for t in openclaw(path)]


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


class TestRegistration:
    def test_registered_in_sources(self) -> None:
        import inspect_scout.sources as sources

        assert "openclaw" in sources.__all__
        assert callable(sources.openclaw)
