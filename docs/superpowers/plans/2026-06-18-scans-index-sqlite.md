# Scans Index — Persistent SQLite Backend for ScanJobsView Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `DuckDBScanJobsView`'s rebuild-everything-per-request model with a persistent, lazily-refreshed SQLite store behind the existing `ScanJobsView` query protocol.

**Architecture:** A per-location SQLite file in the local cache dir holds one row per scan (the `ScanRow` columns + a `change_token`). On each read, one recursive directory listing yields each scan's change-token (`_summary` etag / `mtime:size`); only new/changed/active scans have their `Status` re-read and upserted, vanished scans are deleted. `select`/`count`/`distinct` run directly against the SQLite file via the existing `"sqlite"` SQL dialect — the same dialect path `EvalLogTranscriptsView` already uses.

**Tech Stack:** Python 3.11+, `sqlite3` (stdlib), `inspect_ai._util.file.filesystem` (listing + `FileInfo`), existing `inspect_scout._query` (`Query`/`Condition`/`OrderBy`, `to_sql_suffix`, `condition_as_sql`), `pytest` + `pytest-asyncio`.

## Global Constraints

- Python: modern syntax (`X | None`, `dict[str, Any]`), full type annotations including tests.
- Use the venv: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/mypy`, `.venv/bin/ruff`. Never `uv run`/`uv sync`.
- No `any`/type-assertion equivalents; no disabling static-analysis warnings.
- The wire protocol (`Condition`/`OrderBy`/`Pagination`/keyset), the `ScanJobsView` ABC, the `ScanRow` model, `scan_row_from_status()`, and all frontend code are **unchanged**.
- Before committing touched code: `.venv/bin/ruff format`, `.venv/bin/ruff check --fix`, `.venv/bin/mypy src tests`.
- Conventional-commit messages; commit at the end of each task.

---

## File Structure

**Create:**
- `src/inspect_scout/_scanjobs/cache_path.py` — resolves the per-location SQLite file path (version dir + location hash). One responsibility: where the index lives.
- `src/inspect_scout/_scanjobs/store.py` — `ScanIndexStore`: schema DDL, `ScanRow` ⇄ SQLite row (de)serialization, upsert/delete/`stored_tokens`, and `select`/`count`/`distinct` over the file via the `"sqlite"` dialect.
- `src/inspect_scout/_scanjobs/refresh.py` — pure delta computation from a directory listing (`listing_to_scans`, `compute_delta`) plus the I/O `refresh_index` that reads `Status` for the delta and applies it to the store.
- `src/inspect_scout/_scanjobs/sqlite.py` — `SqliteScanJobsView(ScanJobsView)` and the new `scan_jobs_view(location)` factory.

**Modify:**
- `src/inspect_scout/_scanjobs/__init__.py` — export `scan_jobs_view` from `.sqlite`.
- `src/inspect_scout/_view/_api_v2_scans.py:36` — import `scan_jobs_view` from `.._scanjobs` (package) instead of `.._scanjobs.duckdb`.

**Create (tests):**
- `tests/scanjobs/test_cache_path.py`
- `tests/scanjobs/test_store.py`
- `tests/scanjobs/test_refresh.py`
- `tests/scanjobs/test_sqlite_view.py`

**Remove (final task):**
- `src/inspect_scout/_scanjobs/duckdb.py` and `tests/scanjobs/test_duckdb.py` — once the factory no longer uses `DuckDBScanJobsView` and nothing else references it.

---

## Task 1: Cache file path resolution

**Files:**
- Create: `src/inspect_scout/_scanjobs/cache_path.py`
- Test: `tests/scanjobs/test_cache_path.py`

**Interfaces:**
- Consumes: `scout_cache_dir` from `inspect_scout._util.appdirs`.
- Produces: `SCANS_INDEX_VERSION: int`; `scans_index_db_path(location: str) -> Path` — returns `<cache>/scans_index/v{VERSION}/<location_hash>/scans.sqlite`, parent dir created. `location_hash` is the first 16 hex chars of `sha256(location.rstrip("/"))`.

- [ ] **Step 1: Write the failing test**

```python
# tests/scanjobs/test_cache_path.py
import hashlib

from inspect_scout._scanjobs.cache_path import (
    SCANS_INDEX_VERSION,
    scans_index_db_path,
)


def test_path_is_deterministic_and_versioned() -> None:
    p1 = scans_index_db_path("/scans/dir")
    p2 = scans_index_db_path("/scans/dir/")  # trailing slash normalized

    assert p1 == p2
    assert p1.name == "scans.sqlite"
    assert p1.parent.parent.name == f"v{SCANS_INDEX_VERSION}"
    assert p1.parent.parent.parent.name == "scans_index"
    assert p1.parent.is_dir()  # parent created


def test_distinct_locations_get_distinct_dirs() -> None:
    a = scans_index_db_path("s3://bucket/scans-a")
    b = scans_index_db_path("s3://bucket/scans-b")

    assert a.parent != b.parent
    expected_hash = hashlib.sha256(b"s3://bucket/scans-a").hexdigest()[:16]
    assert a.parent.name == expected_hash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/scanjobs/test_cache_path.py -v`
Expected: FAIL — `ModuleNotFoundError: inspect_scout._scanjobs.cache_path`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/inspect_scout/_scanjobs/cache_path.py
"""Resolves the per-location SQLite index file path in the local cache."""

import hashlib
from pathlib import Path

from .._util.appdirs import scout_cache_dir

# Bump to invalidate every existing on-disk scans index (e.g. when the
# ScanRow schema in store.py changes).
SCANS_INDEX_VERSION = 1


def scans_index_db_path(location: str) -> Path:
    """Return the SQLite index path for a scans location.

    Layout: ``<cache>/scans_index/v{VERSION}/<location_hash>/scans.sqlite``.
    The parent directory is created. The location is normalized (trailing
    slashes stripped) before hashing so equivalent paths share an index.
    """
    normalized = location.rstrip("/")
    location_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    db_dir = (
        scout_cache_dir("scans_index")
        / f"v{SCANS_INDEX_VERSION}"
        / location_hash
    )
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "scans.sqlite"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/scanjobs/test_cache_path.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/inspect_scout/_scanjobs/cache_path.py tests/scanjobs/test_cache_path.py
git commit -m "feat(scanjobs): add scans index cache path resolver"
```

---

## Task 2: ScanIndexStore — schema, (de)serialization, CRUD, queries

**Files:**
- Create: `src/inspect_scout/_scanjobs/store.py`
- Test: `tests/scanjobs/test_store.py`

**Interfaces:**
- Consumes: `ScanRow` (`.._view._api_v2_types`); `Query`, `ScalarValue` (`.._query`); `Condition` (`.._query.condition`); `condition_as_sql` (`.._query.condition_sql`).
- Produces: `class ScanIndexStore` with:
  - `__init__(self, db_path: str | Path) -> None` (opens the connection, enables WAL, creates the schema if absent)
  - `close(self) -> None`
  - `upsert(self, rows: list[tuple[ScanRow, str]]) -> None` — each item is `(scan_row, change_token)`; insert-or-replace by `scan_id`
  - `delete(self, scan_ids: list[str]) -> None`
  - `stored_tokens(self) -> dict[str, str]` — `scan_id -> change_token`
  - `select(self, query: Query | None) -> list[ScanRow]`
  - `count(self, query: Query | None) -> int`
  - `distinct(self, column: str, condition: Condition | None) -> list[ScalarValue]`
  - module constant `SCAN_JOBS_TABLE = "scan_jobs"`
  - module constant `JSON_COLUMNS = ("packages", "metadata", "scan_args")`

Note: this task uses a **synchronous** `sqlite3` connection. Async ABC methods in Task 4 call these directly (SQLite file ops are microseconds — same call-on-loop convention as `FileRecorder.status` for local buffer reads).

- [ ] **Step 1: Write the failing test**

```python
# tests/scanjobs/test_store.py
from datetime import datetime
from pathlib import Path

from inspect_scout._query import Column, Query
from inspect_scout._query.order_by import OrderBy
from inspect_scout._scanjobs.store import ScanIndexStore
from inspect_scout._view._api_v2_types import ScanRow


def make_row(
    scan_id: str,
    *,
    status: str = "complete",
    scan_name: str = "job",
    timestamp: datetime | None = None,
    total_results: int = 0,
) -> ScanRow:
    return ScanRow(
        scan_id=scan_id,
        scan_name=scan_name,
        scan_file="scan.py",
        timestamp=timestamp or datetime(2025, 1, 1, 0, 0, 0),
        packages={"inspect_scout": "1.0.0"},
        metadata={"k": "v"},
        scan_args={"a": 1},
        location=f"/scans/scan_id={scan_id}",
        status=status,  # type: ignore[arg-type]
        scanners="refusal",
        model="openai/gpt-4",
        tags="",
        revision_version=None,
        revision_commit=None,
        revision_origin=None,
        total_results=total_results,
        total_errors=0,
        total_tokens=0,
        active_completion_pct=None,
        transcript_count=3,
    )


def test_upsert_roundtrip_preserves_json_and_scalars(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    row = make_row("a")
    store.upsert([(row, "tok-a")])

    [got] = store.select(Query())

    assert got == row
    store.close()


def test_upsert_replaces_existing_scan_id(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert([(make_row("a", status="incomplete"), "t1")])
    store.upsert([(make_row("a", status="complete"), "t2")])

    rows = store.select(Query())
    assert len(rows) == 1
    assert rows[0].status == "complete"
    assert store.stored_tokens() == {"a": "t2"}
    store.close()


def test_filter_order_limit(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert(
        [
            (make_row("a", status="complete", total_results=5), "t"),
            (make_row("b", status="incomplete", total_results=9), "t"),
            (make_row("c", status="complete", total_results=1), "t"),
        ]
    )

    complete = store.select(Query(where=[Column("status") == "complete"]))
    assert {r.scan_id for r in complete} == {"a", "c"}
    assert store.count(Query(where=[Column("status") == "complete"])) == 2

    ordered = store.select(Query(order_by=[OrderBy("total_results", "DESC")]))
    assert [r.scan_id for r in ordered] == ["b", "a", "c"]

    assert len(store.select(Query(limit=2))) == 2
    store.close()


def test_delete_and_distinct(tmp_path: Path) -> None:
    store = ScanIndexStore(tmp_path / "scans.sqlite")
    store.upsert(
        [
            (make_row("a", scan_name="x"), "t"),
            (make_row("b", scan_name="y"), "t"),
        ]
    )

    store.delete(["a"])
    assert {r.scan_id for r in store.select(Query())} == {"b"}
    assert store.distinct("scan_name", None) == ["y"]
    store.close()


def test_persists_across_connections(tmp_path: Path) -> None:
    db = tmp_path / "scans.sqlite"
    s1 = ScanIndexStore(db)
    s1.upsert([(make_row("a"), "tok")])
    s1.close()

    s2 = ScanIndexStore(db)
    assert {r.scan_id for r in s2.select(Query())} == {"a"}
    assert s2.stored_tokens() == {"a": "tok"}
    s2.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/scanjobs/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: inspect_scout._scanjobs.store`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/inspect_scout/_scanjobs/store.py
"""Persistent SQLite store for the scan-jobs index.

One row per scan (the ScanRow columns) plus a change_token used by the
lazy refresh in refresh.py. Queries run via the existing "sqlite" SQL
dialect, the same path EvalLogTranscriptsView uses.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .._query import Query, ScalarValue
from .._query.condition import Condition
from .._query.condition_sql import condition_as_sql
from .._view._api_v2_types import ScanRow

SCAN_JOBS_TABLE = "scan_jobs"
JSON_COLUMNS = ("packages", "metadata", "scan_args")

# Columns whose ScanRow value must be stored numerically so SQL ORDER BY /
# comparisons are numeric, not lexical.
_INT_COLUMNS = (
    "total_results",
    "total_errors",
    "total_tokens",
    "active_completion_pct",
    "transcript_count",
)

# DDL: scan_id is the natural key for upsert; timestamp stored as ISO text
# (sorts correctly); JSON columns as TEXT; integer aggregates as INTEGER.
_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {SCAN_JOBS_TABLE} (
    scan_id TEXT PRIMARY KEY,
    scan_name TEXT,
    scan_file TEXT,
    timestamp TEXT,
    packages TEXT,
    metadata TEXT,
    scan_args TEXT,
    location TEXT,
    status TEXT,
    scanners TEXT,
    model TEXT,
    tags TEXT,
    revision_version TEXT,
    revision_commit TEXT,
    revision_origin TEXT,
    total_results INTEGER,
    total_errors INTEGER,
    total_tokens INTEGER,
    active_completion_pct INTEGER,
    transcript_count INTEGER,
    change_token TEXT
)
"""

_SCAN_ROW_COLUMNS = tuple(ScanRow.model_fields.keys())
_ALL_COLUMNS = (*_SCAN_ROW_COLUMNS, "change_token")


class ScanIndexStore:
    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path))
        # WAL: concurrent readers + single writer with retry (view server + CLI).
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert(self, rows: list[tuple[ScanRow, str]]) -> None:
        placeholders = ", ".join(["?"] * len(_ALL_COLUMNS))
        cols = ", ".join(_ALL_COLUMNS)
        sql = (
            f"INSERT OR REPLACE INTO {SCAN_JOBS_TABLE} ({cols}) "
            f"VALUES ({placeholders})"
        )
        self._conn.executemany(
            sql, [self._row_to_tuple(row, token) for row, token in rows]
        )
        self._conn.commit()

    def delete(self, scan_ids: list[str]) -> None:
        if not scan_ids:
            return
        self._conn.executemany(
            f"DELETE FROM {SCAN_JOBS_TABLE} WHERE scan_id = ?",
            [(sid,) for sid in scan_ids],
        )
        self._conn.commit()

    def stored_tokens(self) -> dict[str, str]:
        cursor = self._conn.execute(
            f"SELECT scan_id, change_token FROM {SCAN_JOBS_TABLE}"
        )
        return {scan_id: token for scan_id, token in cursor.fetchall()}

    def select(self, query: Query | None = None) -> list[ScanRow]:
        query = query or Query()
        suffix, params, _ = query.to_sql_suffix("sqlite")
        cols = ", ".join(_SCAN_ROW_COLUMNS)
        cursor = self._conn.execute(
            f"SELECT {cols} FROM {SCAN_JOBS_TABLE}{suffix}", params
        )
        return [self._tuple_to_row(row) for row in cursor.fetchall()]

    def count(self, query: Query | None = None) -> int:
        query = query or Query()
        count_query = Query(where=query.where)
        suffix, params, _ = count_query.to_sql_suffix("sqlite")
        result = self._conn.execute(
            f"SELECT COUNT(*) FROM {SCAN_JOBS_TABLE}{suffix}", params
        ).fetchone()
        return int(result[0])

    def distinct(
        self, column: str, condition: Condition | None
    ) -> list[ScalarValue]:
        if condition is not None:
            where_sql, params = condition_as_sql(condition, "sqlite")
            sql = (
                f'SELECT DISTINCT "{column}" FROM {SCAN_JOBS_TABLE} '
                f'WHERE {where_sql} ORDER BY "{column}" ASC'
            )
        else:
            params = []
            sql = (
                f'SELECT DISTINCT "{column}" FROM {SCAN_JOBS_TABLE} '
                f'ORDER BY "{column}" ASC'
            )
        return [row[0] for row in self._conn.execute(sql, params).fetchall()]

    def _row_to_tuple(self, row: ScanRow, token: str) -> tuple[Any, ...]:
        data = row.model_dump()
        values: list[Any] = []
        for col in _SCAN_ROW_COLUMNS:
            value = data[col]
            if col in JSON_COLUMNS:
                values.append(None if value is None else json.dumps(value))
            elif col == "timestamp":
                values.append(value.isoformat() if value is not None else None)
            else:
                values.append(value)
        values.append(token)
        return tuple(values)

    def _tuple_to_row(self, row: tuple[Any, ...]) -> ScanRow:
        data = dict(zip(_SCAN_ROW_COLUMNS, row, strict=True))
        for col in JSON_COLUMNS:
            if data[col] is not None:
                data[col] = json.loads(data[col])
        if data["timestamp"] is not None:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return ScanRow(**data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/scanjobs/test_store.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/ruff format src/inspect_scout/_scanjobs/store.py tests/scanjobs/test_store.py
.venv/bin/ruff check --fix src/inspect_scout/_scanjobs/store.py tests/scanjobs/test_store.py
.venv/bin/mypy src/inspect_scout/_scanjobs/store.py
git add src/inspect_scout/_scanjobs/store.py tests/scanjobs/test_store.py
git commit -m "feat(scanjobs): add persistent SQLite ScanIndexStore"
```

---

## Task 3: Refresh — listing → delta → apply

**Files:**
- Create: `src/inspect_scout/_scanjobs/refresh.py`
- Test: `tests/scanjobs/test_refresh.py`

**Interfaces:**
- Consumes: `ScanIndexStore` (Task 2); `FileInfo` (`inspect_ai._util.file`); `FileRecorder` (`.._recorder.file`) for `status()`; `scan_row_from_status` (`.convert`); `active_scans_store`, `ActiveScanInfo` (`.._recorder.active_scans_store`).
- Produces:
  - `@dataclass class ScanListing: scan_id: str; dir_path: str; token: str`
  - `@dataclass class IndexDelta: to_read: list[ScanListing]; to_delete: list[str]`
  - `listing_to_scans(location: str, infos: list[FileInfo]) -> dict[str, ScanListing]` — pure; groups files under `scan_id=<id>` dirs, token = the scan's `_summary` `etag` (or `mtime:size`), falling back to `_scan.json`'s, else `"new"`.
  - `compute_delta(listed: dict[str, ScanListing], stored_tokens: dict[str, str], active_scan_ids: set[str]) -> IndexDelta` — pure; `to_read` = listings whose token changed **or** whose scan_id is active; `to_delete` = stored scan_ids not in `listed`.
  - `async def refresh_index(store: ScanIndexStore, location: str) -> None` — I/O; lists the location, computes the delta, reads `Status` for `to_read`, upserts, deletes `to_delete`.

Step 1 tests target the two **pure** functions only (no filesystem), so they are fast and deterministic. `refresh_index` is covered end-to-end in Task 4 through the view.

- [ ] **Step 1: Write the failing test**

```python
# tests/scanjobs/test_refresh.py
from inspect_ai._util.file import FileInfo

from inspect_scout._scanjobs.refresh import (
    ScanListing,
    compute_delta,
    listing_to_scans,
)


def _file(name: str, *, mtime: float, size: int, etag: str | None = None) -> FileInfo:
    return FileInfo(name=name, type="file", size=size, mtime=mtime, etag=etag)


def test_listing_token_prefers_summary_etag() -> None:
    infos = [
        _file("/s/scan_id=a/_scan.json", mtime=1.0, size=10),
        _file("/s/scan_id=a/_summary.json", mtime=2.0, size=20, etag="E"),
        _file("/s/scan_id=a/refusal.parquet", mtime=3.0, size=99),
    ]
    listed = listing_to_scans("/s", infos)

    assert listed["a"] == ScanListing("a", "/s/scan_id=a", "E")


def test_listing_token_falls_back_to_mtime_size_then_scan_json() -> None:
    summary_only = listing_to_scans(
        "/s", [_file("/s/scan_id=a/_summary.json", mtime=2.0, size=20)]
    )
    assert summary_only["a"].token == "2.0:20"

    spec_only = listing_to_scans(
        "/s", [_file("/s/scan_id=b/_scan.json", mtime=5.0, size=7)]
    )
    assert spec_only["b"].token == "5.0:7"


def test_listing_ignores_non_scan_files() -> None:
    listed = listing_to_scans("/s", [_file("/s/_index/foo.idx", mtime=1.0, size=1)])
    assert listed == {}


def test_compute_delta_new_changed_unchanged_deleted_active() -> None:
    listed = {
        "new": ScanListing("new", "/s/scan_id=new", "t-new"),
        "changed": ScanListing("changed", "/s/scan_id=changed", "t2"),
        "same": ScanListing("same", "/s/scan_id=same", "t-same"),
        "active": ScanListing("active", "/s/scan_id=active", "t-active"),
    }
    stored = {
        "changed": "t1",
        "same": "t-same",
        "active": "t-active",
        "gone": "t-gone",
    }

    delta = compute_delta(listed, stored, active_scan_ids={"active"})

    assert {s.scan_id for s in delta.to_read} == {"new", "changed", "active"}
    assert delta.to_delete == ["gone"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/scanjobs/test_refresh.py -v`
Expected: FAIL — `ModuleNotFoundError: inspect_scout._scanjobs.refresh`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/inspect_scout/_scanjobs/refresh.py
"""Lazy incremental refresh of the scan index from a directory listing.

A single recursive listing yields each scan's change-token; only new,
changed, or active scans are re-read from disk and upserted, and scans
whose directories vanished are deleted.
"""

import asyncio
from dataclasses import dataclass

from inspect_ai._util.file import FileInfo, filesystem

from .._recorder.active_scans_store import active_scans_store
from .._recorder.file import FileRecorder
from .convert import scan_row_from_status
from .store import ScanIndexStore

_SCAN_ID_SEGMENT = "scan_id="
_SUMMARY_FILE = "_summary.json"
_SPEC_FILE = "_scan.json"


@dataclass
class ScanListing:
    scan_id: str
    dir_path: str
    token: str


@dataclass
class IndexDelta:
    to_read: list[ScanListing]
    to_delete: list[str]


def _scan_id_and_dir(location: str, file_path: str) -> tuple[str, str] | None:
    """Extract (scan_id, scan_dir) from a file path under a scan_id=<id> dir."""
    parts = file_path.split("/")
    for i, part in enumerate(parts):
        if part.startswith(_SCAN_ID_SEGMENT):
            scan_id = part[len(_SCAN_ID_SEGMENT) :]
            return scan_id, "/".join(parts[: i + 1])
    return None


def _token(info: FileInfo) -> str:
    return info.etag or f"{info.mtime}:{info.size}"


def listing_to_scans(location: str, infos: list[FileInfo]) -> dict[str, ScanListing]:
    # Group files by scan_id, tracking the _summary and _scan.json infos.
    summaries: dict[str, FileInfo] = {}
    specs: dict[str, FileInfo] = {}
    dirs: dict[str, str] = {}
    for info in infos:
        if info.type != "file":
            continue
        parsed = _scan_id_and_dir(location, info.name)
        if parsed is None:
            continue
        scan_id, scan_dir = parsed
        dirs[scan_id] = scan_dir
        basename = info.name.rsplit("/", 1)[-1]
        if basename == _SUMMARY_FILE:
            summaries[scan_id] = info
        elif basename == _SPEC_FILE:
            specs[scan_id] = info

    result: dict[str, ScanListing] = {}
    for scan_id, scan_dir in dirs.items():
        if scan_id in summaries:
            token = _token(summaries[scan_id])
        elif scan_id in specs:
            token = _token(specs[scan_id])
        else:
            token = "new"
        result[scan_id] = ScanListing(scan_id, scan_dir, token)
    return result


def compute_delta(
    listed: dict[str, ScanListing],
    stored_tokens: dict[str, str],
    active_scan_ids: set[str],
) -> IndexDelta:
    to_read = [
        listing
        for scan_id, listing in listed.items()
        if stored_tokens.get(scan_id) != listing.token or scan_id in active_scan_ids
    ]
    to_delete = [scan_id for scan_id in stored_tokens if scan_id not in listed]
    return IndexDelta(to_read=to_read, to_delete=to_delete)


async def refresh_index(store: ScanIndexStore, location: str) -> None:
    fs = filesystem(location)
    try:
        infos = [fi for fi in fs.ls(location, recursive=True) if fi.type == "file"]
    except FileNotFoundError:
        infos = []

    listed = listing_to_scans(location, infos)

    with active_scans_store() as active_store:
        active = active_store.read_all()
    active_ids = {sid for sid in active if sid in listed}

    delta = compute_delta(listed, store.stored_tokens(), active_ids)

    # Read Status for the delta in parallel; missing scans are skipped.
    statuses = await asyncio.gather(
        *(FileRecorder.status(listing.dir_path) for listing in delta.to_read),
        return_exceptions=True,
    )

    rows = []
    for listing, status in zip(delta.to_read, statuses, strict=True):
        if isinstance(status, FileNotFoundError):
            continue
        if isinstance(status, BaseException):
            raise status
        rows.append(
            (
                scan_row_from_status(
                    status, active_scan_info=active.get(listing.scan_id)
                ),
                listing.token,
            )
        )

    store.upsert(rows)
    store.delete(delta.to_delete)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/scanjobs/test_refresh.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/ruff format src/inspect_scout/_scanjobs/refresh.py tests/scanjobs/test_refresh.py
.venv/bin/ruff check --fix src/inspect_scout/_scanjobs/refresh.py tests/scanjobs/test_refresh.py
.venv/bin/mypy src/inspect_scout/_scanjobs/refresh.py
git add src/inspect_scout/_scanjobs/refresh.py tests/scanjobs/test_refresh.py
git commit -m "feat(scanjobs): add lazy incremental index refresh"
```

---

## Task 4: SqliteScanJobsView + factory (end-to-end over real scan dirs)

**Files:**
- Create: `src/inspect_scout/_scanjobs/sqlite.py`
- Modify: `src/inspect_scout/_scanjobs/__init__.py`
- Test: `tests/scanjobs/test_sqlite_view.py`

**Interfaces:**
- Consumes: `ScanJobsView` ABC (`.view`); `ScanIndexStore` (Task 2); `scans_index_db_path` (Task 1); `refresh_index` (Task 3); `Query`, `ScalarValue`, `Condition`; `ScanRow`.
- Produces:
  - `class SqliteScanJobsView(ScanJobsView)` — `connect()` opens the store and runs `refresh_index`; `select`/`count`/`distinct` delegate to the store; `disconnect()` closes the store. `select` returns an `AsyncIterator[ScanRow]` (yields from the store's list).
  - `async def scan_jobs_view(scans_location: str) -> ScanJobsView` — returns `SqliteScanJobsView(scans_location)`.

The view's `select` must be an async generator to satisfy the ABC (`AsyncIterator[ScanRow]`), matching `DuckDBScanJobsView.select`.

- [ ] **Step 1: Write the failing test**

```python
# tests/scanjobs/test_sqlite_view.py
from datetime import datetime
from pathlib import Path

import pytest
from inspect_scout._query import Column, Query
from inspect_scout._query.order_by import OrderBy
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanjobs.sqlite import SqliteScanJobsView, scan_jobs_view
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._view._api_v2_types import ScanRow

# Real recorder filenames (inspect_scout._recorder.buffer / .file).
_SCAN_JSON = "_scan.json"
_SUMMARY_JSON = "_summary.json"


def _write_scan(scans_dir: Path, scan_id: str, *, complete: bool, when: int) -> None:
    """Write a minimal on-disk scan dir using real model serialization.

    ScanSpec requires only scan_name + scanners; everything else defaults.
    """
    scan_dir = scans_dir / f"scan_id={scan_id}"
    scan_dir.mkdir(parents=True)

    spec = ScanSpec(
        scan_id=scan_id,
        scan_name="job",
        scan_file="scan.py",
        timestamp=datetime(2025, 1, 1, when, 0, 0),
        scanners={"refusal": ScannerSpec(name="refusal")},
    )
    (scan_dir / _SCAN_JSON).write_text(spec.model_dump_json())

    summary = Summary(scanners=["refusal"])
    summary.complete = complete
    (scan_dir / _SUMMARY_JSON).write_text(summary.model_dump_json())


@pytest.fixture
def scans_dir(tmp_path: Path) -> Path:
    d = tmp_path / "scans"
    d.mkdir()
    _write_scan(d, "a", complete=True, when=1)
    _write_scan(d, "b", complete=False, when=2)
    _write_scan(d, "c", complete=True, when=3)
    return d


@pytest.mark.asyncio
async def test_select_count_distinct_over_real_dirs(scans_dir: Path) -> None:
    async with await scan_jobs_view(str(scans_dir)) as view:
        rows = [r async for r in view.select(Query())]
        assert {r.scan_id for r in rows} == {"a", "b", "c"}
        assert all(isinstance(r, ScanRow) for r in rows)

        complete = [
            r async for r in view.select(Query(where=[Column("status") == "complete"]))
        ]
        assert {r.scan_id for r in complete} == {"a", "c"}

        assert await view.count(Query()) == 3
        assert await view.distinct("scan_name", None) == ["job"]


@pytest.mark.asyncio
async def test_order_by_timestamp(scans_dir: Path) -> None:
    async with await scan_jobs_view(str(scans_dir)) as view:
        rows = [
            r async for r in view.select(Query(order_by=[OrderBy("timestamp", "ASC")]))
        ]
        assert [r.scan_id for r in rows] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_refresh_picks_up_new_and_removed_scans(scans_dir: Path) -> None:
    async with await scan_jobs_view(str(scans_dir)) as view:
        assert await view.count(Query()) == 3

    # Add one scan, remove another, then reconnect (new view => fresh refresh).
    _write_scan(scans_dir, "d", complete=True, when=4)
    import shutil

    shutil.rmtree(scans_dir / "scan_id=a")

    async with await scan_jobs_view(str(scans_dir)) as view:
        rows = [r async for r in view.select(Query())]
        assert {r.scan_id for r in rows} == {"b", "c", "d"}


@pytest.mark.asyncio
async def test_uses_isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Redirect the cache into tmp so the test never touches the real cache dir.
    cache = tmp_path / "cache"
    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir",
        lambda subdir=None: (cache / subdir if subdir else cache),
    )
    (cache).mkdir(parents=True, exist_ok=True)

    scans = tmp_path / "scans"
    scans.mkdir()
    _write_scan(scans, "a", complete=True, when=1)

    view = SqliteScanJobsView(str(scans))
    await view.connect()
    assert await view.count(Query()) == 1
    await view.disconnect()
```

Note: the `monkeypatch` in the last test guards against polluting the real cache. For the other tests, add an autouse fixture in a new `tests/scanjobs/conftest.py` that redirects `scout_cache_dir` to a tmp dir for the whole module — see Step 3b.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/scanjobs/test_sqlite_view.py -v`
Expected: FAIL — `ModuleNotFoundError: inspect_scout._scanjobs.sqlite`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/inspect_scout/_scanjobs/sqlite.py
"""SQLite-file-backed ScanJobsView with lazy incremental refresh."""

from typing import AsyncIterator

from typing_extensions import override

from .._query import Query, ScalarValue
from .._query.condition import Condition
from .._view._api_v2_types import ScanRow
from .cache_path import scans_index_db_path
from .refresh import refresh_index
from .store import ScanIndexStore
from .view import ScanJobsView


class SqliteScanJobsView(ScanJobsView):
    """Persistent SQLite implementation of ScanJobsView.

    Queries a per-location SQLite index that is lazily refreshed (delta
    only) from the scans directory on connect.
    """

    def __init__(self, scans_location: str) -> None:
        self._scans_location = scans_location
        self._store: ScanIndexStore | None = None

    @override
    async def connect(self) -> None:
        if self._store is not None:
            return
        self._store = ScanIndexStore(scans_index_db_path(self._scans_location))
        await refresh_index(self._store, self._scans_location)

    @override
    async def disconnect(self) -> None:
        if self._store is not None:
            self._store.close()
            self._store = None

    @override
    async def select(self, query: Query | None = None) -> AsyncIterator[ScanRow]:
        assert self._store is not None, "Not connected"
        for row in self._store.select(query):
            yield row

    @override
    async def count(self, query: Query | None = None) -> int:
        assert self._store is not None, "Not connected"
        return self._store.count(query)

    @override
    async def distinct(
        self, column: str, condition: Condition | None
    ) -> list[ScalarValue]:
        assert self._store is not None, "Not connected"
        return self._store.distinct(column, condition)


async def scan_jobs_view(scans_location: str) -> ScanJobsView:
    """Create a persistent SQLite-backed ScanJobsView for a scans location."""
    return SqliteScanJobsView(scans_location)
```

- [ ] **Step 3b: Add the cache-isolation conftest**

```python
# tests/scanjobs/conftest.py
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_scans_cache(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redirect the scout cache dir so scan-index tests never touch the real cache."""
    cache_root = tmp_path_factory.mktemp("scout_cache")

    def fake_cache_dir(subdir: str | None = None) -> Path:
        path = cache_root / subdir if subdir else cache_root
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(
        "inspect_scout._scanjobs.cache_path.scout_cache_dir", fake_cache_dir
    )
```

- [ ] **Step 3c: Update the package exports**

```python
# src/inspect_scout/_scanjobs/__init__.py  (replace the duckdb import line)
from inspect_scout._scanjobs.sqlite import SqliteScanJobsView, scan_jobs_view
from inspect_scout._scanjobs.view import ScanJobsView

__all__ = [
    "ScanJobsView",
    "SqliteScanJobsView",
    "scan_jobs_view",
]
```

(Confirm the real `__all__` contents first with `sed -n '1,20p' src/inspect_scout/_scanjobs/__init__.py` and preserve any other exports.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/scanjobs/test_sqlite_view.py -v`
Expected: PASS (4 passed). The `test_uses_isolated_cache` test's explicit monkeypatch overrides the autouse fixture harmlessly.

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/ruff format src/inspect_scout/_scanjobs/ tests/scanjobs/
.venv/bin/ruff check --fix src/inspect_scout/_scanjobs/ tests/scanjobs/
.venv/bin/mypy src/inspect_scout/_scanjobs/sqlite.py
git add src/inspect_scout/_scanjobs/sqlite.py src/inspect_scout/_scanjobs/__init__.py tests/scanjobs/
git commit -m "feat(scanjobs): add SQLite-backed ScanJobsView with lazy refresh"
```

---

## Task 5: Wire the API to the new factory + integration gate

**Files:**
- Modify: `src/inspect_scout/_view/_api_v2_scans.py:36`
- Test (existing, run as gate): `tests/view/test_v2_api.py`, `tests/view/test_api_scans_pagination.py`, `tests/view/test_api_v2_scans_distinct.py`, `tests/view/test_api_v2_nan_handling.py`

**Interfaces:**
- Consumes: `scan_jobs_view` now from `.._scanjobs` (package), which resolves to `SqliteScanJobsView`.
- Produces: no signature changes — `scans` and `scans_distinct` endpoints behave identically.

The pagination tests exercise keyset cursors over `timestamp`/`scan_id`, which is the **timestamp-as-ISO-text** risk called out below. They are the gate that proves ordering + cursor parity with the old DuckDB path.

- [ ] **Step 1: Change the import**

In `src/inspect_scout/_view/_api_v2_scans.py`, replace line 36:

```python
from .._scanjobs.duckdb import scan_jobs_view
```

with:

```python
from .._scanjobs import scan_jobs_view
```

- [ ] **Step 2: Run the scans API suites**

Run:
```bash
.venv/bin/pytest tests/view/test_v2_api.py tests/view/test_api_scans_pagination.py tests/view/test_api_v2_scans_distinct.py tests/view/test_api_v2_nan_handling.py -v
```
Expected: PASS. Likely fixtures point a scans directory on disk; if any test depended on `DuckDBScanJobsView` internals (e.g. constructing it from `list[Status]`) rather than the HTTP endpoint, note it and adapt the test to the endpoint — do **not** weaken behavior coverage.

- [ ] **Step 3: Investigate any failure before changing code**

If a pagination/ordering test fails on `timestamp`, this is the **known timestamp risk**: the cursor value (a `datetime`) is bound as a SQL param against an ISO-text column. Use `superpowers:systematic-debugging`. Likely fix: in `store.py`, bind cursor/order comparisons consistently — store timestamp as ISO text (already done) and ensure any `datetime` param is serialized to `.isoformat()` before reaching SQLite (add a param adapter in `ScanIndexStore.__init__` via `sqlite3.register_adapter(datetime, lambda d: d.isoformat())`). Add a regression test in `tests/scanjobs/test_store.py` for `order_by=timestamp` + a `Column("timestamp") > <datetime>` filter, then re-run.

- [ ] **Step 4: Run the full scanjobs + view suites**

Run: `.venv/bin/pytest tests/scanjobs tests/view -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/inspect_scout/_view/_api_v2_scans.py
git commit -m "feat(view): back scans listing with persistent SQLite index"
```

---

## Task 6: Remove the obsolete DuckDB scan-jobs view

**Files:**
- Remove: `src/inspect_scout/_scanjobs/duckdb.py`, `tests/scanjobs/test_duckdb.py`

**Interfaces:** none produced. This is cleanup once nothing imports `DuckDBScanJobsView` or the old `scan_jobs_view` from `.duckdb`.

- [ ] **Step 1: Prove there are no remaining references**

Run:
```bash
grep -rn "scanjobs.duckdb\|DuckDBScanJobsView" src tests
```
Expected: no matches (the `__init__.py` and `_api_v2_scans.py` were updated in Tasks 4–5). If anything remains, fix it before deleting.

- [ ] **Step 2: Delete the files**

```bash
git rm src/inspect_scout/_scanjobs/duckdb.py tests/scanjobs/test_duckdb.py
```

- [ ] **Step 3: Verify imports + full implicated suite**

Run:
```bash
.venv/bin/python -c "import inspect_scout._scanjobs as s; print(s.scan_jobs_view)"
.venv/bin/pytest tests/scanjobs tests/view -q
```
Expected: import prints the function; tests PASS.

- [ ] **Step 4: Full check + commit**

```bash
.venv/bin/ruff format src tests
.venv/bin/ruff check --fix src tests
.venv/bin/mypy src tests
git add -A
git commit -m "refactor(scanjobs): remove obsolete in-memory DuckDB scan-jobs view"
```

---

## Notes & Known Risks

- **Timestamp as ISO text** (Task 5 Step 3): ISO8601 sorts correctly lexically, but keyset cursors bind `datetime` params. The pagination suite is the gate; the fix is a `sqlite3.register_adapter(datetime, ...)` in the store. A direct regression test lives in `test_store.py`.
- **Active scans:** handled inside `refresh_index` — any scan_id currently in `active_scans_store` is force-re-read each connect so its `status="active"` / `active_completion_pct` are correct in the file, keeping all filtering/ordering in SQL (no query-time overlay). Few scans are ever active, so the cost is negligible.
- **Remote-listing cost:** the recursive `fs.ls(...)` to detect new scans is O(total scans) in *list* operations (not status reads) and is inherent to lazy-on-read. Acceptable at expected scan counts; revisit (write-time/hybrid index) only if it bites.
- **Concurrency:** WAL + `busy_timeout=5000` covers view-server + CLI on one machine. The local cache is per-machine by design (see issue #474); cross-machine sharing is explicitly out of scope.
- **Schema changes:** any change to `ScanRow` columns requires bumping `SCANS_INDEX_VERSION` in `cache_path.py` (drop-and-rebuild; cheap given incremental refill).
