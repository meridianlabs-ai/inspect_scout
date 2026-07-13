# OpenClaw Native Session Importer Implementation Plan

> **Superseded — historical record.** This plan was written when the
> `openclaw-telemetry-hal` importer lived in the package alongside the native
> importer and the two shared code. Since then, telemetry-hal has been
> relocated to a self-contained example under `examples/sources/`, and the
> "promote extraction helpers to a shared module" phase was dropped:
> `extraction.py` now belongs solely to the native session importer. Steps
> below that touch `_telemetry_hal/`, register `openclaw_telemetry_hal`, or
> describe `extraction.py` as *shared* reflect that original approach, not the
> delivered code. The authoritative behavior spec is `design/openclaw-sessions.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `openclaw()` transcript source that imports native OpenClaw session bundles (`~/.openclaw/agents/*/sessions/`) into Scout, per the spec in `design/openclaw-sessions.md`.

**Architecture:** New subpackage `src/inspect_scout/sources/_openclaw/_sessions/` mirroring the telemetry-hal layout: `client.py` (discovery, registry, file reading) → `parse.py` (raw JSONL records → typed intermediate) → `events.py` (intermediate → Inspect events + messages, with sub-agent files recursively nested as agent spans) → `transcripts.py` (the `openclaw()` entry point and `Transcript` assembly). Value-coercion helpers shared with the telemetry-hal importer move up to `sources/_openclaw/extraction.py`.

**Tech Stack:** Python 3.11+, `inspect_ai` event/model types, pytest + pytest-asyncio, mypy (strict), ruff.

**Read first:** `design/openclaw-sessions.md` (the spec — authoritative for all behavior), `src/inspect_scout/sources/_openclaw/_telemetry_hal/events.py` (the sibling importer this mirrors), `CLAUDE.md` (venv usage: always `.venv/bin/python -m pytest`, never `uv run`).

**Sample data (dev-time only, untracked):** `.dev/data/fx-demo/sessions/` (small bundle: orchestrator `cfabe24d-…` + 3 sub-agents + `sessions.json`) and `.dev/data/openclaw-sessions/` (15 sessions incl. a `compaction` record in `b2e732c1-…`). Committed fixtures are created in Task 2.

---

## File structure

| File | Responsibility |
|---|---|
| `src/inspect_scout/sources/_openclaw/extraction.py` | **Moved** from `_telemetry_hal/extraction.py` + 4 helpers promoted from `_telemetry_hal/events.py`. Stateless value coercion shared by both OpenClaw importers |
| `src/inspect_scout/sources/_openclaw/_sessions/__init__.py` | Exports `openclaw`, `OPENCLAW_SOURCE_TYPE` |
| `src/inspect_scout/sources/_openclaw/_sessions/client.py` | Source-type constant, session-file reading, `sessions.json` registry loading, file discovery |
| `src/inspect_scout/sources/_openclaw/_sessions/parse.py` | Raw records → `ParsedSession` typed intermediate; all schema strictness lives here |
| `src/inspect_scout/sources/_openclaw/_sessions/events.py` | `ParsedSession` → events + messages; sub-agent span nesting + recursion |
| `src/inspect_scout/sources/_openclaw/_sessions/transcripts.py` | `openclaw()` entry point, classification, `Transcript` assembly |
| `src/inspect_scout/sources/_openclaw/__init__.py` | Add `_sessions` exports |
| `src/inspect_scout/sources/__init__.py` | Register `openclaw` in `__all__` (auto-registers with `scout import`) |
| `tests/sources/openclaw_source/sessions/` | `__init__.py`, `fixtures/`, `test_client.py`, `test_parse.py`, `test_events.py`, `test_openclaw.py` |
| `docs/db_importing.qmd`, `docs/reference/sources.qmd` | User docs for the new source |

---

### Task 1: Promote shared extraction helpers to `sources/_openclaw/extraction.py`

The native importer needs `usage_to_inspect`, `tokens_from_usage`, `content_to_text`, `content_blocks`, `toolcalls_of`, `rich_or_text` (currently `_telemetry_hal/extraction.py`) and `_to_tool_call`, `_tool_call_view`, `_ts_to_datetime`, `_short_description` (currently private in `_telemetry_hal/events.py`). The message-content shapes are identical between the two formats, so these are genuinely shared. Pure refactor — the existing telemetry-hal test suite is the safety net.

**Files:**
- Create: `src/inspect_scout/sources/_openclaw/extraction.py` (via `git mv`)
- Modify: `src/inspect_scout/sources/_openclaw/_telemetry_hal/events.py`
- Modify: `src/inspect_scout/sources/_openclaw/_telemetry_hal/transcripts.py`
- Modify: `tests/sources/openclaw_source/telemetry_hal/test_telemetry_hal.py`

- [ ] **Step 1: Move the module**

```bash
cd /Users/work/r/inspect_scout
git mv src/inspect_scout/sources/_openclaw/_telemetry_hal/extraction.py src/inspect_scout/sources/_openclaw/extraction.py
```

- [ ] **Step 2: Update the module docstring and add the four promoted helpers**

In `src/inspect_scout/sources/_openclaw/extraction.py`, change the first docstring line to:

```python
"""Value coercion from OpenClaw content/usage structures into Inspect shapes.

Shared by the OpenClaw importers (``_telemetry_hal`` and ``_sessions``): both
formats carry the same message ``content`` block shapes (``text`` / ``thinking``
/ ``image`` / ``toolCall``) and the same ``usage`` keys. Stateless helpers that
pull a value out of a single raw OpenClaw structure; they hold no importer-wide
state and do no structural reconstruction — that belongs to each importer's
``parse`` module.
"""
```

Then **cut** these four functions out of `_telemetry_hal/events.py` and paste them into `extraction.py`, renamed public (drop the leading underscore): `_ts_to_datetime` → `ts_to_datetime`, `_short_description` → `short_description`, `_tool_call_view` → `tool_call_view`, `_to_tool_call` → `to_tool_call`. Function bodies are unchanged except `_to_tool_call`'s call to `_tool_call_view` becomes `tool_call_view`. Move their imports along with them (`datetime`/`timezone`, `ToolCall`, `ToolCallContent` — `from inspect_ai.tool import ToolCall, ToolCallContent`).

- [ ] **Step 3: Update telemetry-hal imports**

In `src/inspect_scout/sources/_openclaw/_telemetry_hal/events.py`, replace the `from .extraction import (...)` block with:

```python
from ..extraction import (
    content_blocks,
    rich_or_text,
    short_description,
    to_tool_call,
    tool_call_view,
    toolcalls_of,
    ts_to_datetime,
    usage_to_inspect,
)
```

and replace every use of `_ts_to_datetime` → `ts_to_datetime`, `_short_description` → `short_description`, `_tool_call_view` → `tool_call_view`, `_to_tool_call` → `to_tool_call` in that file. Remove the now-unused `ToolCall`/`ToolCallContent` imports if nothing else in the file uses them.

In `src/inspect_scout/sources/_openclaw/_telemetry_hal/transcripts.py`, change `from .extraction import tokens_from_usage` → `from ..extraction import tokens_from_usage`.

In `src/inspect_scout/sources/_openclaw/_telemetry_hal/parse.py` (line ~63), change its `from .extraction import (...)` to `from ..extraction import (...)` with the same names. Then verify nothing else references the old module path:

```bash
grep -rn "_telemetry_hal.extraction\|from .extraction" src tests
```

Expected: only the updated `from ..extraction` lines (no `.extraction`/`_telemetry_hal.extraction` matches remain).

In `tests/sources/openclaw_source/telemetry_hal/test_telemetry_hal.py`, change

```python
from inspect_scout.sources._openclaw._telemetry_hal.extraction import (
    content_to_text,
    tokens_from_usage,
)
```

to

```python
from inspect_scout.sources._openclaw.extraction import (
    content_to_text,
    tokens_from_usage,
)
```

- [ ] **Step 4: Run the telemetry-hal tests and type check**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/telemetry_hal/ -q
.venv/bin/python -m mypy src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
```

Expected: all tests PASS, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add -A src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
git commit -m "Promote OpenClaw extraction helpers to shared _openclaw module."
```

---

### Task 2: Fixtures + `_sessions` package skeleton + file reading & registry loading

**Files:**
- Create: `tests/sources/openclaw_source/sessions/__init__.py` (empty)
- Create: `tests/sources/openclaw_source/sessions/fixtures/fx_demo/` (copied bundle)
- Create: `tests/sources/openclaw_source/sessions/fixtures/compaction_session.jsonl`
- Create: `src/inspect_scout/sources/_openclaw/_sessions/__init__.py`
- Create: `src/inspect_scout/sources/_openclaw/_sessions/client.py`
- Test: `tests/sources/openclaw_source/sessions/test_client.py`

- [ ] **Step 1: Create the fx-demo fixture bundle**

Copy the four session files and the registry (NOT the large trajectory files), and create one dummy trajectory file + one trajectory-path file to exercise discovery exclusion:

```bash
cd /Users/work/r/inspect_scout
FIX=tests/sources/openclaw_source/sessions/fixtures/fx_demo
mkdir -p $FIX
SRC=.dev/data/fx-demo/sessions
cp $SRC/cfabe24d-8b34-4031-a393-689524b2028f.jsonl $FIX/
cp $SRC/63f16c5a-1a2e-4284-90fc-96a3d22843f7.jsonl $FIX/
cp $SRC/8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl $FIX/
cp $SRC/a35ff69f-56ae-453f-b290-d369e251e64d.jsonl $FIX/
cp $SRC/sessions.json $FIX/
cp $SRC/cfabe24d-8b34-4031-a393-689524b2028f.trajectory-path.json $FIX/
printf '%s\n' '{"traceSchema":"openclaw-trajectory","type":"session.started","sessionId":"cfabe24d-8b34-4031-a393-689524b2028f"}' > $FIX/cfabe24d-8b34-4031-a393-689524b2028f.trajectory.jsonl
touch tests/sources/openclaw_source/sessions/__init__.py
```

- [ ] **Step 2: Create the compaction fixture**

Write `tests/sources/openclaw_source/sessions/fixtures/compaction_session.jsonl` with exactly these 7 lines (shape copied from the real compaction record in `.dev/data/openclaw-sessions/b2e732c1-…jsonl`):

```json
{"type":"session","version":3,"id":"aaaaaaaa-0000-0000-0000-000000000001","timestamp":"2026-07-06T10:00:00.000Z","cwd":"/workspace"}
{"type":"model_change","id":"m1","parentId":null,"timestamp":"2026-07-06T10:00:01.000Z","provider":"anthropic","modelId":"claude-opus-4-8"}
{"type":"message","id":"u1","parentId":"m1","timestamp":"2026-07-06T10:00:02.000Z","message":{"role":"user","content":"Start the task.","timestamp":1783418402000}}
{"type":"message","id":"a1","parentId":"u1","timestamp":"2026-07-06T10:00:05.000Z","message":{"role":"assistant","content":[{"type":"text","text":"Working on it."}],"api":"anthropic-messages","provider":"anthropic","model":"claude-opus-4-8","usage":{"input":10,"output":20,"cacheRead":0,"cacheWrite":0,"totalTokens":30},"stopReason":"stop","timestamp":1783418405000}}
{"type":"compaction","id":"c1","parentId":"a1","timestamp":"2026-07-06T10:01:00.000Z","summary":"## Goal\nCompact test summary.","firstKeptEntryId":"c1","tokensBefore":81290,"details":{"readFiles":[],"modifiedFiles":["/workspace/SPEC.md"]},"fromHook":false}
{"type":"message","id":"u2","parentId":"c1","timestamp":"2026-07-06T10:01:05.000Z","message":{"role":"user","content":"Continue.","timestamp":1783418465000}}
{"type":"message","id":"a2","parentId":"u2","timestamp":"2026-07-06T10:01:10.000Z","message":{"role":"assistant","content":[{"type":"text","text":"Done."}],"api":"anthropic-messages","provider":"anthropic","model":"claude-opus-4-8","usage":{"input":15,"output":5,"cacheRead":100,"cacheWrite":0,"totalTokens":120},"stopReason":"stop","timestamp":1783418470000}}
```

- [ ] **Step 3: Write the failing tests for reading + registry**

Create `tests/sources/openclaw_source/sessions/test_client.py`:

```python
"""Tests for OpenClaw native session file reading, registry, and discovery."""

from __future__ import annotations

import json
from pathlib import Path

from inspect_scout.sources._openclaw._sessions.client import (
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
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_client.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'inspect_scout.sources._openclaw._sessions'`

- [ ] **Step 5: Implement the package skeleton and client reading/registry**

Create `src/inspect_scout/sources/_openclaw/_sessions/__init__.py`:

```python
"""OpenClaw native session importer.

Imports the session bundles OpenClaw writes under
``~/.openclaw/agents/<agent>/sessions/``. See the design doc
``design/openclaw-sessions.md`` for the schema analysis and decisions.
"""

from .client import OPENCLAW_SOURCE_TYPE
from .transcripts import openclaw

__all__ = ["openclaw", "OPENCLAW_SOURCE_TYPE"]
```

(`transcripts.py` doesn't exist until Task 6 — for now create a stub `src/inspect_scout/sources/_openclaw/_sessions/transcripts.py` so the package imports:)

```python
"""OpenClaw native session transcript import functionality."""

from __future__ import annotations

from datetime import datetime
from os import PathLike
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from inspect_scout import Transcript


async def openclaw(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from native OpenClaw session files."""
    raise NotImplementedError
    yield  # pragma: no cover — marks this as an async generator
```

Create `src/inspect_scout/sources/_openclaw/_sessions/client.py`:

```python
"""OpenClaw native session file discovery and reading utilities.

Native sessions live at ``~/.openclaw/agents/<agent>/sessions/``: one
``<sessionId>.jsonl`` per session, sibling ``*.trajectory.jsonl`` /
``*.trajectory-path.json`` runtime traces (never consumed), and one shared
``sessions.json`` registry carrying the authoritative topology.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any

logger = getLogger(__name__)

OPENCLAW_SOURCE_TYPE = "openclaw"

DEFAULT_OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"

_TRAJECTORY_SUFFIX = ".trajectory.jsonl"


def read_session_records(path: Path) -> list[dict[str, Any]]:
    """Read raw records from a session JSONL file.

    Malformed lines (e.g. a torn final line from a crash mid-append) are
    skipped with a warning, matching the Claude Code importer.
    """
    records: list[dict[str, Any]] = []
    n_bad = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            if isinstance(record, dict):
                records.append(record)
    if n_bad:
        logger.warning("Skipped %d malformed JSONL line(s) in %s", n_bad, path)
    return records


@dataclass(frozen=True)
class RegistryEntry:
    """One ``sessions.json`` entry (keyed by runtime sessionKey)."""

    session_key: str
    session_id: str
    spawned_by: str | None
    parent_session_key: str | None
    label: str | None
    status: str | None
    raw: dict[str, Any]


def load_registry(sessions_dir: Path) -> dict[str, RegistryEntry] | None:
    """Load ``sessions.json`` from a sessions directory.

    Returns ``None`` when the registry is missing or unreadable (the caller
    degrades to standalone per-file imports). Entries are NOT filtered against
    files on disk here — the sub-agent join checks file existence itself.
    """
    registry_path = sessions_dir / "sessions.json"
    if not registry_path.is_file():
        return None
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        logger.warning("Could not read %s: %s", registry_path, ex)
        return None
    if not isinstance(data, dict):
        logger.warning("Unexpected sessions.json shape in %s", registry_path)
        return None
    entries: dict[str, RegistryEntry] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        session_id = value.get("sessionId")
        if not session_id:
            continue
        entries[key] = RegistryEntry(
            session_key=key,
            session_id=str(session_id),
            spawned_by=_opt_str(value.get("spawnedBy")),
            parent_session_key=_opt_str(value.get("parentSessionKey")),
            label=_opt_str(value.get("label")),
            status=_opt_str(value.get("status")),
            raw=value,
        )
    return entries


def entry_for_session_id(
    registry: dict[str, RegistryEntry], session_id: str
) -> RegistryEntry | None:
    """The registry entry whose ``sessionId`` matches, or ``None``."""
    for entry in registry.values():
        if entry.session_id == session_id:
            return entry
    return None


def _opt_str(value: Any) -> str | None:
    return str(value) if value else None
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_client.py -q
.venv/bin/python -m mypy src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
```

Expected: PASS, mypy clean. (If `read_session_records` count of 40 fails, run `wc -l` on the fixture and correct the expected count in the test — it must equal the line count.)

- [ ] **Step 7: Commit**

```bash
git add -A src/inspect_scout/sources/_openclaw/_sessions tests/sources/openclaw_source/sessions
git commit -m "Add OpenClaw native session client: record reading + registry loading."
```

---

### Task 3: Discovery

**Files:**
- Modify: `src/inspect_scout/sources/_openclaw/_sessions/client.py`
- Test: `tests/sources/openclaw_source/sessions/test_client.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/sources/openclaw_source/sessions/test_client.py` (and add `import os`, `import shutil`, and `from inspect_scout.sources._openclaw._sessions.client import discover_session_files` to the imports):

```python
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

        from datetime import datetime

        cutoff = datetime.fromtimestamp(1_650_000_000)
        assert [
            f.name for f in discover_session_files(tmp_path, from_time=cutoff)
        ] == ["new.jsonl"]
        assert [f.name for f in discover_session_files(tmp_path, to_time=cutoff)] == [
            "old.jsonl"
        ]

    def test_nonexistent_path_returns_empty(self, tmp_path: Path) -> None:
        assert discover_session_files(tmp_path / "nope") == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_client.py -q
```

Expected: FAIL with `ImportError: cannot import name 'discover_session_files'`

- [ ] **Step 3: Implement discovery in `client.py`**

Append to `src/inspect_scout/sources/_openclaw/_sessions/client.py`:

```python
def is_session_file(path: Path) -> bool:
    """Whether a path is a session conversation file (not a trajectory)."""
    return path.suffix == ".jsonl" and not path.name.endswith(_TRAJECTORY_SUFFIX)


def discover_session_files(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[Path]:
    """Discover OpenClaw native session files.

    Args:
        path: Path to search. Can be:
            - None: scan all agents in ~/.openclaw/agents/*/sessions/
            - a sessions directory (contains session .jsonl files)
            - a parent directory (e.g. ~/.openclaw or ~/.openclaw/agents)
            - a specific session .jsonl file
        session_id: If provided, only return the file with this session id
        from_time: Only return files modified on or after this time
        to_time: Only return files modified before this time

    Returns:
        Session file paths, sorted by modification time (newest first).
    """
    files: list[Path] = []
    if path is None:
        if not DEFAULT_OPENCLAW_AGENTS_DIR.is_dir():
            logger.warning(
                "OpenClaw agents directory not found: %s", DEFAULT_OPENCLAW_AGENTS_DIR
            )
            return []
        files = _scan_agent_dirs(DEFAULT_OPENCLAW_AGENTS_DIR, session_id)
    else:
        p = Path(path).expanduser()
        if not p.exists():
            logger.warning("Path does not exist: %s", p)
            return []
        if p.is_file():
            files = [p] if is_session_file(p) else []
        else:
            files = _find_sessions_in_directory(p, session_id)
            if not files:
                agents = p / "agents"
                files = _scan_agent_dirs(agents if agents.is_dir() else p, session_id)

    if session_id:
        files = [f for f in files if f.stem == session_id]

    if from_time or to_time:
        filtered: list[Path] = []
        for f in files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if from_time and mtime < from_time:
                continue
            if to_time and mtime >= to_time:
                continue
            filtered.append(f)
        files = filtered

    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return files


def _find_sessions_in_directory(
    directory: Path, session_id: str | None = None
) -> list[Path]:
    """Session files directly in a directory, optionally filtered by id."""
    return [
        f
        for f in directory.glob("*.jsonl")
        if is_session_file(f) and (session_id is None or f.stem == session_id)
    ]


def _scan_agent_dirs(base: Path, session_id: str | None = None) -> list[Path]:
    """Session files under ``<base>/*/sessions/`` (the per-agent layout)."""
    found: list[Path] = []
    for agent_dir in sorted(base.iterdir()):
        sessions_dir = agent_dir / "sessions"
        if sessions_dir.is_dir():
            found.extend(_find_sessions_in_directory(sessions_dir, session_id))
    return found
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_client.py -q
.venv/bin/python -m mypy src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
```

Expected: PASS, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add -A src/inspect_scout/sources/_openclaw/_sessions tests/sources/openclaw_source/sessions
git commit -m "Add OpenClaw native session file discovery."
```

---

### Task 4: `parse.py` — records → typed intermediate

All schema strictness lives here: unknown record types, unknown message roles, and divergent branches fail loudly (see spec "Record mapping").

**Files:**
- Create: `src/inspect_scout/sources/_openclaw/_sessions/parse.py`
- Test: `tests/sources/openclaw_source/sessions/test_parse.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/sources/openclaw_source/sessions/test_parse.py`:

```python
"""Tests for OpenClaw native session record parsing."""

from __future__ import annotations

import json
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


HEADER = {"type": "session", "version": 3, "id": "s1", "timestamp": "2026-07-06T10:00:00.000Z", "cwd": "/w"}


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
        assert (
            sum(1 for r in parsed.records if isinstance(r, AssistantTurn)) == 11
        )
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
        records = [dict(HEADER), {"type": "wibble", "id": "w1"}]
        with pytest.raises(ValueError, match="wibble"):
            parse_session(records, "test")

    def test_unknown_role_raises(self) -> None:
        records = [dict(HEADER), make_message("m1", "s1", "narrator", "hi")]
        with pytest.raises(ValueError, match="narrator"):
            parse_session(records, "test")

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_parse.py -q
```

Expected: FAIL with `ModuleNotFoundError` / `ImportError` on `parse`.

- [ ] **Step 3: Implement `parse.py`**

Create `src/inspect_scout/sources/_openclaw/_sessions/parse.py`:

```python
"""OpenClaw native session record parsing.

Turns the raw JSONL records of one session file into a typed
:class:`ParsedSession`. Records are kept in file order (append order, hence
chronological). All schema strictness lives here: unknown record types,
unknown message roles, and divergent branches fail the import loudly rather
than silently dropping content — see ``design/openclaw-sessions.md``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from ..extraction import ts_to_datetime

_EPOCH = datetime.fromtimestamp(0, tz=timezone.utc)


@dataclass(frozen=True)
class SessionHeader:
    """The ``session`` record that opens every session file."""

    session_id: str
    version: int | None
    timestamp: datetime | None
    cwd: str | None


@dataclass(frozen=True)
class UserTurn:
    """A user message (``injected=True`` for runtime ``custom_message``s)."""

    content: Any
    timestamp: datetime
    injected: bool = False


@dataclass(frozen=True)
class AssistantTurn:
    """An assistant message with its per-turn model and usage."""

    content: Any
    model: str
    usage: dict[str, Any]
    timestamp: datetime


@dataclass(frozen=True)
class ToolResultMsg:
    """A ``toolResult`` message, keyed by ``toolCallId``."""

    tool_call_id: str
    tool_name: str | None
    content: Any
    is_error: bool | None
    details: dict[str, Any] | None
    timestamp: datetime


@dataclass(frozen=True)
class CompactionRecord:
    """A ``compaction`` record (context compaction with summary)."""

    summary: str | None
    first_kept_entry_id: str | None
    tokens_before: int | None
    details: dict[str, Any] | None
    from_hook: bool | None
    timestamp: datetime


@dataclass(frozen=True)
class ConfigChange:
    """A ``model_change`` or ``thinking_level_change`` record."""

    change: Literal["model_change", "thinking_level_change"]
    data: dict[str, Any]
    timestamp: datetime


SessionRecord = UserTurn | AssistantTurn | CompactionRecord | ConfigChange


@dataclass
class ParsedSession:
    """One session file, parsed: the thread records plus id-keyed tool results.

    ``records`` holds the content-bearing thread in file order; ``toolResult``
    messages are not in it — they are joined back to their calls via
    ``result_by_callid`` when events are built. ``model`` is the most recent
    assistant turn's model, seeded by ``model_change`` when no turn exists.
    """

    header: SessionHeader
    records: list[SessionRecord]
    result_by_callid: dict[str, ToolResultMsg]
    model: str | None


def parse_session(raw_records: list[dict[str, Any]], source: str) -> ParsedSession:
    """Parse one session file's raw records.

    Args:
        raw_records: Records as read by ``read_session_records`` (file order).
        source: Where the records came from, for error messages.

    Raises:
        ValueError: On an empty record list, a missing/duplicate ``session``
            header, an unknown record type, an unknown message role, or a
            divergent branch (two thread records sharing a parent).
    """
    if not raw_records:
        raise ValueError(f"Empty OpenClaw session: {source}")
    header_rec = raw_records[0]
    if header_rec.get("type") != "session":
        raise ValueError(
            f"Expected a 'session' header as the first record of {source}, "
            f"got '{header_rec.get('type')}'"
        )
    version = header_rec.get("version")
    header = SessionHeader(
        session_id=str(header_rec.get("id") or ""),
        version=int(version) if version is not None else None,
        timestamp=_parse_iso(header_rec.get("timestamp")),
        cwd=str(header_rec["cwd"]) if header_rec.get("cwd") else None,
    )

    records: list[SessionRecord] = []
    result_by_callid: dict[str, ToolResultMsg] = {}
    model: str | None = None
    # Divergence check: count thread records (message/compaction — not
    # leaf/custom bookkeeping) claiming each parent. >1 means the tree
    # branches, which we do not know how to linearize — fail, don't guess.
    thread_children: Counter[str] = Counter()
    last_ts = header.timestamp or _EPOCH

    for rec in raw_records[1:]:
        rtype = rec.get("type")
        ts = _parse_iso(rec.get("timestamp")) or last_ts
        last_ts = ts

        if rtype == "message":
            _count_parent(rec, thread_children)
            msg = rec.get("message") or {}
            role = msg.get("role")
            msg_ts = ts_to_datetime(msg.get("timestamp")) or ts
            if role == "user":
                records.append(UserTurn(content=msg.get("content"), timestamp=msg_ts))
            elif role == "assistant":
                turn_model = msg.get("model")
                if not turn_model:
                    raise ValueError(
                        f"Assistant message without a model in {source}"
                    )
                model = str(turn_model)
                records.append(
                    AssistantTurn(
                        content=msg.get("content"),
                        model=model,
                        usage=msg.get("usage") or {},
                        timestamp=msg_ts,
                    )
                )
            elif role == "toolResult":
                details = msg.get("details")
                result = ToolResultMsg(
                    tool_call_id=str(msg.get("toolCallId") or ""),
                    tool_name=str(msg["toolName"]) if msg.get("toolName") else None,
                    content=msg.get("content"),
                    is_error=msg.get("isError")
                    if isinstance(msg.get("isError"), bool)
                    else None,
                    details=details if isinstance(details, dict) else None,
                    timestamp=msg_ts,
                )
                if result.tool_call_id:
                    result_by_callid[result.tool_call_id] = result
            else:
                raise ValueError(
                    f"Unknown OpenClaw message role '{role}' in {source}"
                )
        elif rtype == "custom_message":
            records.append(
                UserTurn(content=rec.get("content"), timestamp=ts, injected=True)
            )
        elif rtype == "compaction":
            _count_parent(rec, thread_children)
            tokens_before = rec.get("tokensBefore")
            details = rec.get("details")
            records.append(
                CompactionRecord(
                    summary=str(rec["summary"]) if rec.get("summary") else None,
                    first_kept_entry_id=str(rec["firstKeptEntryId"])
                    if rec.get("firstKeptEntryId")
                    else None,
                    tokens_before=int(tokens_before)
                    if tokens_before is not None
                    else None,
                    details=details if isinstance(details, dict) else None,
                    from_hook=rec.get("fromHook")
                    if isinstance(rec.get("fromHook"), bool)
                    else None,
                    timestamp=ts,
                )
            )
        elif rtype == "model_change":
            if model is None and rec.get("modelId"):
                model = str(rec["modelId"])
            records.append(
                ConfigChange(
                    change="model_change",
                    data={"provider": rec.get("provider"), "model": rec.get("modelId")},
                    timestamp=ts,
                )
            )
        elif rtype == "thinking_level_change":
            records.append(
                ConfigChange(
                    change="thinking_level_change",
                    data={"thinking_level": rec.get("thinkingLevel")},
                    timestamp=ts,
                )
            )
        elif rtype in ("custom", "leaf"):
            continue  # run-boundary / branch bookkeeping — no content
        elif rtype == "session":
            raise ValueError(f"Unexpected second 'session' header in {source}")
        else:
            raise ValueError(
                f"Unknown OpenClaw session record type '{rtype}' in {source}. "
                "This importer fails on unrecognized records rather than "
                "dropping them; please report the record type."
            )

    divergent = sorted(p for p, n in thread_children.items() if n > 1)
    if divergent:
        raise ValueError(
            f"OpenClaw session {source} has divergent branches at parent "
            f"id(s) {divergent}; branch linearization is not supported"
        )

    return ParsedSession(
        header=header,
        records=records,
        result_by_callid=result_by_callid,
        model=model,
    )


def _count_parent(rec: dict[str, Any], counter: Counter[str]) -> None:
    parent_id = rec.get("parentId")
    if isinstance(parent_id, str) and parent_id:
        counter[parent_id] += 1


def _parse_iso(value: Any) -> datetime | None:
    """Parse a record-level ISO-8601 timestamp (returns aware UTC)."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_parse.py -q
.venv/bin/python -m mypy src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
```

Expected: PASS, mypy clean. (`ts_to_datetime` accepts epoch-ms ints — moved to shared extraction in Task 1.)

- [ ] **Step 5: Commit**

```bash
git add -A src/inspect_scout/sources/_openclaw/_sessions tests/sources/openclaw_source/sessions
git commit -m "Add OpenClaw native session record parsing."
```

---

### Task 5: `events.py` — the session thread (no sub-agents yet)

**Files:**
- Create: `src/inspect_scout/sources/_openclaw/_sessions/events.py`
- Test: `tests/sources/openclaw_source/sessions/test_events.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/sources/openclaw_source/sessions/test_events.py`. These use a sub-agent fixture file (linear, no spawns) and the compaction fixture; sub-agent spans are Task 6's tests.

```python
"""Tests for OpenClaw native session event/message construction."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from inspect_ai.event import (
    CompactionEvent,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    ToolEvent,
)
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, ChatMessageUser

from inspect_scout.sources._openclaw._sessions.client import read_session_records
from inspect_scout.sources._openclaw._sessions.events import (
    BuildContext,
    build_content,
)
from inspect_scout.sources._openclaw._sessions.parse import parse_session

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
SUBAGENT = FX_DEMO / "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl"


def build_fixture(path: Path) -> tuple[list, list]:
    parsed = parse_session(read_session_records(path), str(path))
    ctx = BuildContext(sessions_dir=path.parent, registry=None)
    events, messages = build_content(parsed, ctx)
    return events, messages


class TestThreadContent:
    def test_model_events_thread_input(self) -> None:
        events, messages = build_fixture(SUBAGENT)
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert len(model_events) == 3
        # each input is the running conversation up to (excluding) that turn
        assert len(model_events[0].input) == 1  # the [Subagent Context] prompt
        assert all(
            len(e.input) < len(messages) for e in model_events
        )
        assert model_events[0].output.usage is not None
        assert model_events[0].output.usage.total_tokens > 0
        assert model_events[0].model == "claude-opus-4-8"

    def test_tool_events_join_results(self) -> None:
        events, _ = build_fixture(SUBAGENT)
        tool_events = [e for e in events if isinstance(e, ToolEvent)]
        assert len(tool_events) == 2
        for te in tool_events:
            assert te.result != ""  # result joined by toolCallId
            assert te.failed is False
            assert te.completed is not None and te.completed >= te.timestamp

    def test_message_thread_roles(self) -> None:
        _, messages = build_fixture(SUBAGENT)
        roles = Counter(type(m).__name__ for m in messages)
        assert roles == Counter(
            ChatMessageUser=1, ChatMessageAssistant=3, ChatMessageTool=2
        )

    def test_config_changes_become_info_events(self) -> None:
        events, _ = build_fixture(SUBAGENT)
        infos = [e for e in events if isinstance(e, InfoEvent)]
        assert len(infos) == 2
        assert infos[0].source == "openclaw"
        data = infos[0].data
        assert isinstance(data, dict)
        assert data["type"] == "model_change"
        assert data["model"] == "claude-opus-4-8"
        data1 = infos[1].data
        assert isinstance(data1, dict)
        assert data1["type"] == "thinking_level_change"

    def test_working_start_is_monotonic(self) -> None:
        events, _ = build_fixture(SUBAGENT)
        starts = [e.working_start for e in events]
        assert starts == sorted(starts)

    def test_no_spans_without_registry(self) -> None:
        orchestrator = FX_DEMO / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"
        events, messages = build_fixture(orchestrator)
        assert not any(isinstance(e, SpanBeginEvent) for e in events)
        # spawn calls degrade to plain tool events; thread intact
        roles = Counter(type(m).__name__ for m in messages)
        assert roles == Counter(
            ChatMessageUser=7, ChatMessageAssistant=11, ChatMessageTool=11
        )


class TestCompaction:
    def test_compaction_event(self) -> None:
        events, messages = build_fixture(FIXTURES / "compaction_session.jsonl")
        compactions = [e for e in events if isinstance(e, CompactionEvent)]
        assert len(compactions) == 1
        c = compactions[0]
        assert c.source == "openclaw"
        assert c.tokens_before == 81290
        assert c.tokens_after is None
        assert c.metadata is not None
        assert c.metadata["summary"].startswith("## Goal")
        assert c.metadata["first_kept_entry_id"] == "c1"
        assert c.metadata["from_hook"] is False
        # thread unaffected: 2 user + 2 assistant
        assert len(messages) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_events.py -q
```

Expected: FAIL with `ModuleNotFoundError` on `events`.

- [ ] **Step 3: Implement `events.py` (thread only; spawn resolution stubbed off)**

Create `src/inspect_scout/sources/_openclaw/_sessions/events.py`:

```python
"""OpenClaw native session event + message conversion.

Builds the Inspect AI event stream and the main-thread ``ChatMessage`` list
from a :class:`~.parse.ParsedSession`.

Mapping (mirrors the Claude Code and telemetry-hal importers):

- The session's own thread is the spine: user/assistant/toolResult records
  become the ``ModelEvent`` / ``ToolEvent`` / ``CompactionEvent`` stream and
  the ``messages`` thread; ``model_change`` / ``thinking_level_change`` become
  ``InfoEvent`` timeline markers.
- Each spawned sub-agent becomes a nested agent span (``SpanBeginEvent`` /
  ``SpanEndEvent``, ``type="agent"``) anchored at the spawning tool call, its
  file located via the ``sessions.json`` registry and parsed recursively.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator, cast

from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    ToolEvent,
)
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    ModelOutput,
    ModelUsage,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool import ToolCallError
from inspect_ai.tool import ToolResult as ToolResultContent

from ..extraction import (
    content_blocks,
    content_to_text,
    rich_or_text,
    to_tool_call,
    toolcalls_of,
    usage_to_inspect,
)
from .client import RegistryEntry
from .parse import (
    AssistantTurn,
    CompactionRecord,
    ConfigChange,
    ParsedSession,
    ToolResultMsg,
    UserTurn,
)

logger = getLogger(__name__)

_EPOCH = datetime.fromtimestamp(0, tz=timezone.utc)

# toolResult.details keys surfaced into ToolEvent.metadata. Selected small
# scalars only: the full details can duplicate the entire result body (e.g.
# ``exec``'s ``aggregated`` output).
_DETAIL_METADATA_KEYS = ("status", "exitCode", "durationMs", "tookMs")


@dataclass
class BuildContext:
    """Cross-file context for building one transcript's content.

    ``registry``/``sessions_dir`` locate spawned sub-agent session files;
    with either absent, spawn calls degrade to plain tool events.
    """

    sessions_dir: Path | None
    registry: dict[str, RegistryEntry] | None
    max_depth: int = 5


def build_content(
    parsed: ParsedSession, ctx: BuildContext
) -> tuple[list[Event], list[ChatMessage]]:
    """Build the event stream and main-thread messages for one session.

    A single running conversation is threaded through both outputs: each
    ``ModelEvent.input`` carries the conversation up to that turn, and the
    final running list is the message thread. Sub-agent spans are emitted
    inline at their spawning tool call; their messages stay out of the thread.
    """
    events: list[Event] = []
    messages: list[ChatMessage] = []
    order = count()
    _build_thread(parsed, ctx, ctx.max_depth, events, messages, None, order)
    return events, messages


def _build_thread(
    parsed: ParsedSession,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    messages: list[ChatMessage],
    span_id: str | None,
    order: Iterator[int],
) -> datetime:
    """Emit one session's records into ``events``/``messages``.

    Returns the last timestamp seen (used as the enclosing span's end time).
    """
    last_ts = parsed.header.timestamp or _EPOCH
    for record in parsed.records:
        last_ts = max(last_ts, record.timestamp)
        if isinstance(record, UserTurn):
            messages.append(
                ChatMessageUser(content=rich_or_text(record.content))
            )
        elif isinstance(record, ConfigChange):
            events.append(
                InfoEvent(
                    source="openclaw",
                    data={"type": record.change, **record.data},
                    timestamp=record.timestamp,
                    working_start=float(next(order)),
                    span_id=span_id,
                )
            )
        elif isinstance(record, CompactionRecord):
            metadata = {
                key: value
                for key, value in (
                    ("summary", record.summary),
                    ("first_kept_entry_id", record.first_kept_entry_id),
                    ("details", record.details),
                    ("from_hook", record.from_hook),
                )
                if value is not None
            }
            events.append(
                CompactionEvent(
                    source="openclaw",
                    tokens_before=record.tokens_before,
                    tokens_after=None,
                    timestamp=record.timestamp,
                    working_start=float(next(order)),
                    span_id=span_id,
                    metadata=metadata or None,
                )
            )
        elif isinstance(record, AssistantTurn):
            turn_end = _emit_assistant_turn(
                record, parsed, ctx, depth, events, messages, span_id, order
            )
            last_ts = max(last_ts, turn_end)
    return last_ts


def _emit_assistant_turn(
    turn: AssistantTurn,
    parsed: ParsedSession,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    messages: list[ChatMessage],
    span_id: str | None,
    order: Iterator[int],
) -> datetime:
    """Emit a model event, then a tool event (or agent span) per tool call."""
    toolcalls = toolcalls_of(turn.content)
    tool_calls = [to_tool_call(tc) for tc in toolcalls]
    assistant_msg = ChatMessageAssistant(
        content=content_blocks(turn.content),
        tool_calls=tool_calls or None,
        model=turn.model,
    )
    output = ModelOutput(
        model=turn.model,
        choices=[
            ChatCompletionChoice(
                message=assistant_msg,
                stop_reason="tool_calls" if tool_calls else "stop",
            )
        ],
        usage=ModelUsage(**usage_to_inspect(turn.usage)),
    )
    events.append(
        ModelEvent(
            model=turn.model,
            input=list(messages),  # conversation up to (not including) this turn
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=output,
            timestamp=turn.timestamp,
            completed=turn.timestamp,
            working_start=float(next(order)),
            span_id=span_id,
        )
    )
    messages.append(assistant_msg)
    last_ts = turn.timestamp

    for tc in toolcalls:
        tc_id = str(tc.get("id") or "")
        function = str(tc.get("name") or "unknown")
        arguments = tc.get("arguments") or {}
        arguments = arguments if isinstance(arguments, dict) else {}
        result = parsed.result_by_callid.get(tc_id)
        result_content, completed, error, failed = _tool_result_fields(
            result, turn.timestamp
        )
        child = _resolve_spawned_child(result, ctx, depth)
        if child is not None:
            span_end = _emit_subagent_span(
                child[0],
                child[1],
                tc,
                result,
                ctx,
                depth,
                events,
                span_id,
                order,
                turn.timestamp,
            )
            last_ts = max(last_ts, span_end)
        else:
            events.append(
                ToolEvent(
                    id=tc_id,
                    function=function,
                    arguments=arguments,
                    result=cast(ToolResultContent, result_content),
                    error=error,
                    failed=failed,
                    timestamp=turn.timestamp,
                    completed=completed,
                    working_start=float(next(order)),
                    span_id=span_id,
                    metadata=_result_metadata(result),
                )
            )
        # The tool result belongs in the message thread either way.
        messages.append(
            ChatMessageTool(
                content=result_content,
                tool_call_id=tc_id,
                function=function,
                error=error,
            )
        )
        last_ts = max(last_ts, completed)
    return last_ts


def _resolve_spawned_child(
    result: ToolResultMsg | None, ctx: BuildContext, depth: int
) -> tuple[ParsedSession, RegistryEntry] | None:
    """Resolve a spawn tool result to its child session, if any.

    Implemented in the sub-agent span task; the thread-only build always
    returns ``None``.
    """
    return None


def _emit_subagent_span(
    child: ParsedSession,
    entry: RegistryEntry,
    spawn_tool: dict[str, Any],
    spawn_result: ToolResultMsg | None,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    parent_span_id: str | None,
    order: Iterator[int],
    spawn_ts: datetime,
) -> datetime:
    """Implemented in the sub-agent span task."""
    raise NotImplementedError


def _tool_result_fields(
    result: ToolResultMsg | None, started: datetime
) -> tuple[Any, datetime, ToolCallError | None, bool | None]:
    """Resolve a tool result into ``ToolEvent`` fields.

    Returns ``(content, completed, error, failed)``. The completion time is
    the result's own timestamp (a real call→result span); a call with no
    recorded result (e.g. an aborted run) gets an empty result completing at
    the turn's own time with ``failed`` unknown.
    """
    if result is None:
        return "", started, None, None
    result_content = rich_or_text(result.content)
    if result.is_error:
        return (
            result_content,
            result.timestamp,
            ToolCallError("unknown", content_to_text(result.content)),
            True,
        )
    failed = False if result.is_error is False else None
    return result_content, result.timestamp, None, failed


def _result_metadata(result: ToolResultMsg | None) -> dict[str, Any] | None:
    """Small scalar ``details`` fields worth carrying on the tool event."""
    if result is None or result.details is None:
        return None
    metadata = {
        key: result.details[key]
        for key in _DETAIL_METADATA_KEYS
        if result.details.get(key) is not None
    }
    return metadata or None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_events.py tests/sources/openclaw_source/sessions/test_parse.py -q
.venv/bin/python -m mypy src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
```

Expected: PASS, mypy clean, `ruff check` clean (`.venv/bin/ruff check src/inspect_scout/sources/_openclaw`). The two stubs (`_resolve_spawned_child`, `_emit_subagent_span`) are replaced with real implementations in the next task — do not add anything to them now.

- [ ] **Step 5: Commit**

```bash
git add -A src/inspect_scout/sources/_openclaw/_sessions tests/sources/openclaw_source/sessions
git commit -m "Add OpenClaw native session event/message construction (thread only)."
```

---

### Task 6: Sub-agent spans + recursion

**Files:**
- Modify: `src/inspect_scout/sources/_openclaw/_sessions/events.py`
- Test: `tests/sources/openclaw_source/sessions/test_events.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/sources/openclaw_source/sessions/test_events.py` (add `SpanEndEvent` to the `inspect_ai.event` import and `load_registry` to the client import):

```python
class TestSubagentSpans:
    def build_orchestrator(self) -> tuple[list, list]:
        path = FX_DEMO / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"
        parsed = parse_session(read_session_records(path), str(path))
        ctx = BuildContext(sessions_dir=FX_DEMO, registry=load_registry(FX_DEMO))
        return build_content(parsed, ctx)

    def test_three_agent_spans(self) -> None:
        events, _ = self.build_orchestrator()
        begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        ends = [e for e in events if isinstance(e, SpanEndEvent)]
        assert len(begins) == len(ends) == 3
        assert all(b.type == "agent" for b in begins)
        assert sorted(b.name for b in begins) == ["usd-eur", "usd-gbp", "usd-jpy"]
        for b in begins:
            assert b.metadata is not None
            assert b.metadata["session_id"] in {
                "8c6aeab3-993e-43d5-934a-04aa4a5f3804",
                "a35ff69f-56ae-453f-b290-d369e251e64d",
                "63f16c5a-1a2e-4284-90fc-96a3d22843f7",
            }
            assert b.metadata["status"] == "done"

    def test_spawn_tool_folded_into_span(self) -> None:
        events, _ = self.build_orchestrator()
        spawn_events = [
            e
            for e in events
            if isinstance(e, ToolEvent) and e.function == "sessions_spawn"
        ]
        assert len(spawn_events) == 3
        for te in spawn_events:
            assert te.agent_span_id is not None
            assert te.span_id == te.agent_span_id
            assert te.view is not None

    def test_child_events_carry_span_id(self) -> None:
        events, _ = self.build_orchestrator()
        span_ids = {e.id for e in events if isinstance(e, SpanBeginEvent)}
        child_model_events = [
            e
            for e in events
            if isinstance(e, ModelEvent) and e.span_id in span_ids
        ]
        # 3 sub-agents x 3 assistant turns each
        assert len(child_model_events) == 9
        # root thread model events carry no span id
        root_model_events = [
            e for e in events if isinstance(e, ModelEvent) and e.span_id is None
        ]
        assert len(root_model_events) == 11

    def test_child_messages_not_in_main_thread(self) -> None:
        _, messages = self.build_orchestrator()
        roles = Counter(type(m).__name__ for m in messages)
        # same thread as the registry-less build: sub-agents excluded
        assert roles == Counter(
            ChatMessageUser=7, ChatMessageAssistant=11, ChatMessageTool=11
        )

    def test_missing_child_file_skips_span(self, tmp_path: Path) -> None:
        import shutil

        for name in (
            "cfabe24d-8b34-4031-a393-689524b2028f.jsonl",
            "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl",
            "a35ff69f-56ae-453f-b290-d369e251e64d.jsonl",
            "sessions.json",
        ):  # 63f16c5a (usd-jpy) intentionally omitted
            shutil.copy(FX_DEMO / name, tmp_path / name)
        path = tmp_path / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"
        parsed = parse_session(read_session_records(path), str(path))
        ctx = BuildContext(sessions_dir=tmp_path, registry=load_registry(tmp_path))
        events, messages = build_content(parsed, ctx)
        begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        assert sorted(b.name for b in begins) == ["usd-eur", "usd-gbp"]
        # the skipped spawn is still a plain tool event + thread message
        roles = Counter(type(m).__name__ for m in messages)
        assert roles["ChatMessageTool"] == 11
```

(Also add `from pathlib import Path` usage is already present; ensure `ToolEvent` is imported.)

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_events.py -q
```

Expected: `TestSubagentSpans` FAILs (no spans emitted — resolver returns None); `TestThreadContent`/`TestCompaction` still PASS.

- [ ] **Step 3: Implement spawn resolution and span emission**

In `src/inspect_scout/sources/_openclaw/_sessions/events.py`, first extend the imports (these are used only by the code added in this task):

```python
import json  # with the other stdlib imports

# add to the inspect_ai.event import block:
#   SpanBeginEvent, SpanEndEvent
# add to the ..extraction import block:
#   short_description, tool_call_view
# change the .client import to:
from .client import RegistryEntry, read_session_records
# add to the .parse import block:
#   parse_session
```

Then replace the `_resolve_spawned_child` stub with:

```python
def _resolve_spawned_child(
    result: ToolResultMsg | None, ctx: BuildContext, depth: int
) -> tuple[ParsedSession, RegistryEntry] | None:
    """Resolve a spawn tool result to its parsed child session, if any.

    A tool call spawned a sub-agent iff its result is an ``accepted`` JSON
    naming a ``childSessionKey``. Resolution is two id-keyed lookups (result →
    registry → sibling file); a child that cannot be resolved degrades to a
    plain tool event with a warning — never a content heuristic.
    """
    if result is None or ctx.registry is None or ctx.sessions_dir is None:
        return None
    child_key = _spawned_child_key(result)
    if child_key is None:
        return None
    entry = ctx.registry.get(child_key)
    if entry is None:
        logger.warning(
            "OpenClaw spawn '%s' not in sessions.json; skipping agent span",
            child_key,
        )
        return None
    child_file = ctx.sessions_dir / f"{entry.session_id}.jsonl"
    if not child_file.is_file():
        logger.warning(
            "OpenClaw sub-agent session file missing: %s; skipping agent span",
            child_file,
        )
        return None
    if depth <= 0:
        logger.warning(
            "OpenClaw sub-agent recursion limit reached at '%s'; "
            "skipping agent span",
            child_key,
        )
        return None
    raw = read_session_records(child_file)
    if not raw:
        return None
    return parse_session(raw, str(child_file)), entry


def _spawned_child_key(result: ToolResultMsg) -> str | None:
    """``childSessionKey`` from an accepted spawn result, else ``None``."""
    try:
        parsed = json.loads(content_to_text(result.content))
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict) and parsed.get("status") == "accepted":
        child_key = parsed.get("childSessionKey")
        return str(child_key) if child_key else None
    return None
```

and replace the `_emit_subagent_span` stub with:

```python
def _emit_subagent_span(
    child: ParsedSession,
    entry: RegistryEntry,
    spawn_tool: dict[str, Any],
    spawn_result: ToolResultMsg | None,
    ctx: BuildContext,
    depth: int,
    events: list[Event],
    parent_span_id: str | None,
    order: Iterator[int],
    spawn_ts: datetime,
) -> datetime:
    """Emit a spawned sub-agent as a nested agent span; returns its end time.

    Mirrors the Claude Code and telemetry-hal importers: the span
    (``type="agent"``) wraps the sub-agent's own thread, and the spawning tool
    call is emitted as the span's FIRST child, tagged ``agent_span_id`` so the
    view folds it into the agent header rather than drawing a standalone tool
    row. The child's messages go to a scratch list — never the main thread.
    """
    span_id = entry.session_key
    arguments = spawn_tool.get("arguments") or {}
    arguments = arguments if isinstance(arguments, dict) else {}
    task = str(arguments.get("task") or "") or None
    label = str(arguments.get("label") or "") or entry.label
    events.append(
        SpanBeginEvent(
            id=span_id,
            name=label or "subagent",
            type="agent",
            timestamp=spawn_ts,
            working_start=float(next(order)),
            span_id=parent_span_id,
            metadata={
                "session_key": entry.session_key,
                "session_id": entry.session_id,
                "description": short_description(task),
                "task": task,
                "status": entry.status,
            },
        )
    )

    spawn_id = str(spawn_tool.get("id") or "")
    spawn_function = str(spawn_tool.get("name") or "sessions_spawn")
    result_content, completed, error, failed = _tool_result_fields(
        spawn_result, spawn_ts
    )
    events.append(
        ToolEvent(
            id=spawn_id,
            function=spawn_function,
            arguments=arguments,
            result=cast(ToolResultContent, result_content),
            error=error,
            failed=failed,
            timestamp=spawn_ts,
            completed=completed,
            working_start=float(next(order)),
            span_id=span_id,
            agent_span_id=span_id,
            view=tool_call_view(spawn_function, arguments),
        )
    )

    sub_messages: list[ChatMessage] = []
    end_ts = _build_thread(
        child, ctx, depth - 1, events, sub_messages, span_id, order
    )
    end_ts = max(end_ts, completed)
    events.append(
        SpanEndEvent(
            id=span_id,
            timestamp=end_ts,
            working_start=float(next(order)),
            span_id=parent_span_id,
        )
    )
    return end_ts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/ -q
.venv/bin/python -m mypy src/inspect_scout/sources/_openclaw tests/sources/openclaw_source
```

Expected: PASS, mypy clean.

- [ ] **Step 5: Commit**

```bash
git add -A src/inspect_scout/sources/_openclaw/_sessions tests/sources/openclaw_source/sessions
git commit -m "Nest OpenClaw sub-agent sessions as agent spans."
```

---

### Task 7: `transcripts.py` — the `openclaw()` entry point

**Files:**
- Modify: `src/inspect_scout/sources/_openclaw/_sessions/transcripts.py` (replace the Task 2 stub)
- Test: `tests/sources/openclaw_source/sessions/test_openclaw.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/sources/openclaw_source/sessions/test_openclaw.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/test_openclaw.py -q
```

Expected: FAIL — `NotImplementedError` from the stub and `AssertionError` on registration.

- [ ] **Step 3: Implement `transcripts.py`**

Replace the stub `src/inspect_scout/sources/_openclaw/_sessions/transcripts.py` with:

```python
"""OpenClaw native session transcript import functionality.

Provides the ``openclaw`` source function: an async generator that yields
``Transcript`` objects for insertion into an Inspect Scout transcript
database. See ``design/openclaw-sessions.md``.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from inspect_ai.event import Event, ModelEvent, SpanBeginEvent
from inspect_ai.model import stable_message_ids

from .client import (
    OPENCLAW_SOURCE_TYPE,
    RegistryEntry,
    discover_session_files,
    entry_for_session_id,
    load_registry,
    read_session_records,
)
from .events import BuildContext, build_content
from .parse import ParsedSession, parse_session

if TYPE_CHECKING:
    from inspect_scout import Transcript

logger = getLogger(__name__)


async def openclaw(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from native OpenClaw session files.

    These are the session bundles OpenClaw itself writes under
    ``~/.openclaw/agents/<agent>/sessions/`` — one ``<sessionId>.jsonl`` per
    session plus a shared ``sessions.json`` registry. Each non-sub-agent
    session file becomes one transcript; sessions spawned as sub-agents are
    nested inside their parent transcript as agent spans (and are not yielded
    standalone). Without a ``sessions.json`` alongside the files, topology is
    unknown: every file imports as a standalone transcript.

    This is distinct from ``openclaw_telemetry_hal``, which imports the JSONL
    telemetry written by the third-party ``openclaw-telemetry-hal`` plugin.

    Args:
        path: Path to an OpenClaw root (``~/.openclaw``), an agent sessions
            directory, or a specific session ``.jsonl`` file. If None, scans
            all agents under ``~/.openclaw/agents/``.
        session_id: Specific session id to import.
        from_time: Only import sessions modified on or after this time.
        to_time: Only import sessions modified before this time.
        limit: Maximum number of transcripts to yield.

    Yields:
        Transcript objects ready for insertion into a transcript database.
    """
    session_files = discover_session_files(path, session_id, from_time, to_time)
    if not session_files:
        logger.info("No OpenClaw session files found")
        return

    explicit_file = path is not None and Path(path).expanduser().is_file()
    registries: dict[Path, dict[str, RegistryEntry] | None] = {}
    n = 0
    for session_file in session_files:
        directory = session_file.parent
        if directory not in registries:
            registries[directory] = load_registry(directory)
            if registries[directory] is None:
                logger.warning(
                    "No sessions.json found in %s: importing every session "
                    "file standalone (no sub-agent spans)",
                    directory,
                )
        registry = registries[directory]

        # Sub-agent sessions are nested in their parent's transcript — skip
        # them here (unless the user pointed at the file explicitly).
        if not explicit_file and registry is not None:
            entry = entry_for_session_id(registry, session_file.stem)
            if entry is not None and entry.spawned_by:
                continue

        transcript = _process_session_file(session_file, registry)
        if transcript is not None:
            yield transcript
            n += 1
            if limit is not None and n >= limit:
                return


def _process_session_file(
    session_file: Path, registry: dict[str, RegistryEntry] | None
) -> "Transcript" | None:
    """Process a single session file into a transcript (None if empty)."""
    from inspect_scout import Transcript

    raw = read_session_records(session_file)
    if not raw:
        return None
    parsed = parse_session(raw, str(session_file))

    session_id = parsed.header.session_id or session_file.stem
    if parsed.header.session_id and parsed.header.session_id != session_file.stem:
        logger.warning(
            "OpenClaw session id %s does not match file name %s; "
            "using the header id",
            parsed.header.session_id,
            session_file.name,
        )

    ctx = BuildContext(sessions_dir=session_file.parent, registry=registry)
    events, messages = build_content(parsed, ctx)
    if not messages:
        return None

    # Stable ids across model events and the message thread (as in the
    # Claude Code and telemetry-hal importers).
    apply_ids = stable_message_ids()
    for event in events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    # Billable per-call spend summed over every model call (orchestrator and
    # sub-agents): OpenClaw's totalTokens == input + output + cacheRead +
    # cacheWrite per turn, the convention shared by the other importers.
    total_tokens = sum(
        event.output.usage.total_tokens
        for event in events
        if isinstance(event, ModelEvent) and event.output.usage is not None
    )

    date = parsed.records[0].timestamp.isoformat() if parsed.records else None
    total_time = _total_time(events, parsed)

    agent_spans = [
        e for e in events if isinstance(e, SpanBeginEvent) and e.type == "agent"
    ]
    entry = entry_for_session_id(registry, session_id) if registry else None

    metadata: dict[str, Any] = {
        "cwd": parsed.header.cwd,
        "session_version": parsed.header.version,
        "n_subagents": len(agent_spans),
        "subagent_session_ids": [
            sid for e in agent_spans if (sid := (e.metadata or {}).get("session_id"))
        ],
    }
    if entry is not None:
        metadata.update(
            {
                "session_key": entry.session_key,
                "parent_session_key": entry.parent_session_key,
                "label": entry.label,
                "status": entry.status,
                "origin": entry.raw.get("origin"),
                "system_prompt_report": entry.raw.get("systemPromptReport"),
            }
        )
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return Transcript(
        transcript_id=session_id,
        source_type=OPENCLAW_SOURCE_TYPE,
        source_id=session_id,
        source_uri=str(session_file),
        date=date,
        task_set=None,
        task_id=session_id,
        task_repeat=1,
        # The agent that produced the run, not the importer/format — the
        # telemetry-hal importer carries the same value.
        agent="openclaw",
        agent_args=None,
        model=parsed.model,
        model_options=None,
        score=None,
        success=None,
        message_count=len(messages),
        total_tokens=total_tokens if total_tokens > 0 else None,
        total_time=total_time if total_time and total_time > 0 else None,
        error=None,
        limit=None,
        messages=messages,
        events=events,
        metadata=metadata,
    )


def _total_time(events: list[Event], parsed: ParsedSession) -> float | None:
    """Wall clock minus idle time from the built timeline.

    Falls back to first→last record timestamps when the timeline yields no
    root content (mirrors the Claude Code importer's guard).
    """
    from inspect_ai.event import timeline_build

    timeline = timeline_build(events)
    root = timeline.root
    if root.content:
        wall_clock = (root.end_time() - root.start_time()).total_seconds()
        return wall_clock - root.idle_time()
    timestamps = [record.timestamp for record in parsed.records]
    if len(timestamps) >= 2:
        return (max(timestamps) - min(timestamps)).total_seconds()
    return None
```

- [ ] **Step 4: Register the source**

In `src/inspect_scout/sources/_openclaw/__init__.py`, replace the contents with:

```python
"""OpenClaw import sources.

Hosts the family of OpenClaw importers: ``_sessions`` (native session bundles
under ``~/.openclaw/`` — the canonical format, entry point ``openclaw``) and
``_telemetry_hal`` (JSONL telemetry written by the ``openclaw-telemetry-hal``
plugin). Both set ``agent="openclaw"`` and coexist in one database,
distinguished by ``source_type``.
"""

from ._sessions import OPENCLAW_SOURCE_TYPE, openclaw
from ._telemetry_hal import (
    OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE,
    openclaw_telemetry_hal,
)

__all__ = [
    "openclaw",
    "OPENCLAW_SOURCE_TYPE",
    "openclaw_telemetry_hal",
    "OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE",
]
```

In `src/inspect_scout/sources/__init__.py`: change the `_openclaw` import line to `from ._openclaw import openclaw, openclaw_telemetry_hal` and add `"openclaw",` to `__all__` (keep the list's existing order style).

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/sources/openclaw_source/sessions/ -q
.venv/bin/python -m mypy src/inspect_scout/sources tests/sources/openclaw_source
```

Expected: PASS, mypy clean. (If `message_count == 29` fails, recount: 7 user + 11 assistant + 11 tool = 29 per the events tests — investigate rather than adjust blindly.)

- [ ] **Step 6: Commit**

```bash
git add -A src/inspect_scout/sources tests/sources/openclaw_source/sessions
git commit -m "Add openclaw() native session transcript source."
```

---

### Task 8: User docs

**Files:**
- Modify: `docs/db_importing.qmd`
- Modify: `docs/reference/sources.qmd`

- [ ] **Step 1: Update `docs/db_importing.qmd`**

Read the file first; it has a numbered source list near the top and an `## OpenClaw` section (~line 280) documenting the telemetry importer, ending with "Native OpenClaw session files (the bundles under `~/.openclaw/`) are not yet supported."

Changes:
1. In the intro numbered list, replace item 4 (currently `4. [OpenClaw](#openclaw): Read transcript data from OpenClaw telemetry files captured with the \`openclaw-telemetry-hal\` plugin.`) with two items, renumbering any that follow:

```markdown
4. [OpenClaw](#openclaw): Read transcript data from native OpenClaw session files (`~/.openclaw/agents/*/sessions/`).
5. [OpenClaw Telemetry](#openclaw-telemetry): Read transcript data from OpenClaw telemetry files captured with the `openclaw-telemetry-hal` plugin.
```

2. Retitle the existing `## OpenClaw` section heading to `## OpenClaw Telemetry {#openclaw-telemetry}` and delete its trailing sentence "Native OpenClaw session files (the bundles under `~/.openclaw/`) are not yet supported."
3. Insert a new `## OpenClaw` section *before* it:

```markdown
## OpenClaw {#openclaw}

[OpenClaw](https://openclaw.ai) is an open-source AI assistant. Scout can import the native session files OpenClaw writes under `~/.openclaw/agents/<agent>/sessions/` — one `.jsonl` per session plus a `sessions.json` registry describing how sessions relate.

Use the `openclaw()` transcript source to import sessions:

```python
from inspect_scout.sources import openclaw

async with transcripts_db("transcripts") as db:
    await db.insert(openclaw())  # scans ~/.openclaw/agents/*/sessions/
```

Or from the CLI:

```bash
scout import openclaw
scout import openclaw -P path=/path/to/sessions
```

Each session that is not a spawned sub-agent becomes one transcript; sub-agent sessions are nested inside their parent transcript as agent spans (located via `sessions.json` — without it, every file imports standalone).

| Field | Value |
|---------------|--------------------------|
| `transcript_id` | The OpenClaw session id |
| `source_type` | `"openclaw"` |
| `agent` | `"openclaw"` |
```

Match the surrounding sections' exact formatting conventions (heading levels, table style) when editing.

- [ ] **Step 2: Update `docs/reference/sources.qmd`**

The file is a list of bare `### <source_fn>` headings expanded by the reference tooling. Add `### openclaw` between `### claude_code` and `### openclaw_telemetry_hal`:

```markdown
### claude_code
### openclaw
### openclaw_telemetry_hal
```

- [ ] **Step 3: Verify docs mention nothing stale**

```bash
grep -rn "not yet supported" docs/db_importing.qmd
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add docs/db_importing.qmd docs/reference/sources.qmd
git commit -m "Document the openclaw native session source."
```

---

### Task 9: Full verification + manual sanity check

- [ ] **Step 1: Run the full checks and test suite**

```bash
make check
.venv/bin/python -m pytest
```

Expected: all clean / all pass. Fix anything that fails before proceeding.

- [ ] **Step 2: Manual dry-run against the real captures**

```bash
.venv/bin/scout import openclaw -P path=.dev/data/fx-demo/sessions --dry-run
.venv/bin/scout import openclaw -P path=.dev/data/openclaw-sessions --dry-run
```

Expected: fx-demo shows exactly 1 transcript (`cfabe24d-…`, model `claude-opus-4-8`). The larger capture imports with **no failures** — it contains a `compaction` record (session `b2e732c1-…`) and 15 sessions; verify the transcript count equals the number of non-sub-agent sessions and spot-check one transcript's messages/tokens look sane. If an unknown record type fails the import here, that is new schema surface: extend `parse.py` + the spec's record table + a fixture, following the strictness policy in `design/openclaw-sessions.md`.

- [ ] **Step 3: Update the design doc status if anything diverged**

If implementation forced any deviation from `design/openclaw-sessions.md`, update the doc in the same commit and note why.

- [ ] **Step 4: Final commit (if any fixups)**

```bash
git add -A && git commit -m "Fixups from full-suite verification of openclaw source."
```
