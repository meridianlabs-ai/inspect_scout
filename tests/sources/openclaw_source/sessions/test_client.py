"""Tests for OpenClaw native session file reading, registry, and discovery."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from inspect_scout.sources._openclaw._sessions.client import (
    discover_session_files,
    load_registry,
    read_session_records,
)

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
ORCHESTRATOR = FX_DEMO / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"


class TestReadSessionRecords:
    def test_reads_all_records(self) -> None:
        records = read_session_records(ORCHESTRATOR)
        assert len(records) == 40
        assert records[0]["type"] == "session"

    def test_skips_torn_line(self, tmp_path: Path) -> None:
        f = tmp_path / "torn.jsonl"
        f.write_text(
            json.dumps({"type": "session", "id": "x", "version": 3})
            + "\n"
            + '{"type":"message","message":{"role":"us'  # torn mid-write
        )
        records = read_session_records(f)
        assert len(records) == 1


class TestLoadRegistry:
    def test_missing_registry_returns_none(self, tmp_path: Path) -> None:
        assert load_registry(tmp_path) is None

    def test_parses_entries(self) -> None:
        registry = load_registry(FX_DEMO)
        assert registry is not None
        entry = registry["agent:main:subagent:3386c769-c755-44f0-b5f1-caf886ac880a"]
        assert entry.session_id == "8c6aeab3-993e-43d5-934a-04aa4a5f3804"
        assert entry.spawned_by == (
            "agent:main:dashboard:e6746281-f3cd-4be5-9d0c-633772cdcace"
        )
        assert entry.label == "usd-gbp"
        orch = registry["agent:main:dashboard:e6746281-f3cd-4be5-9d0c-633772cdcace"]
        assert orch.spawned_by is None
        assert orch.parent_session_key == (
            "agent:main:dashboard:9174711d-0a3b-42df-856b-0f07fbb91d63"
        )
        assert orch.raw.get("systemPromptReport") is not None

    def test_invalid_json_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "sessions.json").write_text("not json")
        assert load_registry(tmp_path) is None


class TestDiscoverSessionFiles:
    def test_sessions_dir_excludes_trajectories(self) -> None:
        files = discover_session_files(FX_DEMO)
        names = {f.name for f in files}
        assert len(files) == 4
        assert all(not n.endswith(".trajectory.jsonl") for n in names)
        assert "cfabe24d-8b34-4031-a393-689524b2028f.jsonl" in names

    def test_single_file(self) -> None:
        files = discover_session_files(ORCHESTRATOR)
        assert files == [ORCHESTRATOR]

    def test_parent_dir_scans_agent_sessions(self, tmp_path: Path) -> None:
        # ~/.openclaw layout: <root>/agents/<agent>/sessions/*.jsonl
        sessions = tmp_path / "agents" / "main" / "sessions"
        sessions.mkdir(parents=True)
        shutil.copy(ORCHESTRATOR, sessions / ORCHESTRATOR.name)
        for root in (tmp_path, tmp_path / "agents"):
            files = discover_session_files(root)
            assert [f.name for f in files] == [ORCHESTRATOR.name]

    def test_session_id_filter(self) -> None:
        files = discover_session_files(
            FX_DEMO, session_id="8c6aeab3-993e-43d5-934a-04aa4a5f3804"
        )
        assert [f.stem for f in files] == ["8c6aeab3-993e-43d5-934a-04aa4a5f3804"]

    def test_newest_first_and_time_filters(self, tmp_path: Path) -> None:
        old = tmp_path / "old.jsonl"
        new = tmp_path / "new.jsonl"
        old.write_text('{"type":"session","id":"old","version":3}\n')
        new.write_text('{"type":"session","id":"new","version":3}\n')
        os.utime(old, (1_600_000_000, 1_600_000_000))
        os.utime(new, (1_700_000_000, 1_700_000_000))
        files = discover_session_files(tmp_path)
        assert [f.name for f in files] == ["new.jsonl", "old.jsonl"]

        cutoff = datetime.fromtimestamp(1_650_000_000)
        assert [f.name for f in discover_session_files(tmp_path, from_time=cutoff)] == [
            "new.jsonl"
        ]
        assert [f.name for f in discover_session_files(tmp_path, to_time=cutoff)] == [
            "old.jsonl"
        ]

    def test_nonexistent_path_returns_empty(self, tmp_path: Path) -> None:
        assert discover_session_files(tmp_path / "nope") == []
