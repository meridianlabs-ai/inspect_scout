# Streaming Transcript Reads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound scan/search memory to O(in-flight segments × context window) for messages-only content, independent of transcript size, via a spool-and-replay `TranscriptHandle` streaming read API.

**Architecture:** A new `TranscriptHandle` async-CM protocol with multi-shot `messages()`/`events()` iterators and memoized `load()`, implemented for eval logs via single-pass spool-and-replay (filtered items to JSONL spool, attachments/pools to an offset-indexed spool, replay resolves per item). The scan pipeline switches at `_parse_function` (size threshold + scanner capability); `llm_scanner` gains a streaming segmenter with bounded concurrency; `ResultReport.input` becomes info-only for streamed scans.

**Tech Stack:** Python 3.10+, ijson (yajl2_c backend), pydantic v2 `TypeAdapter`, anyio, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-07-01-streaming-transcript-reads-design.md`

## Global Constraints

- Use the venv directly: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/mypy`. Never `uv run` or `uv sync`.
- Strict typing: modern syntax (`X | None`, `dict[str, Any]`), all functions annotated including tests. Run `.venv/bin/mypy src tests` for touched files before each commit.
- Streaming threshold: `STREAMING_THRESHOLD_BYTES = 64 * 1024 * 1024` (64 MB module constant). Below: existing in-memory path unchanged (including early-exit). Above: spool-and-replay.
- Handles never cross process boundaries: `__reduce__` raises `TypeError`.
- Spool files live under the task files cache dir (`init_task_files_cache()`); cleanup must survive cancellation (`finally`/CM-based, not GC finalization).
- Non-goals (do NOT implement): timeline/events streaming, parquet cell-splitting, hierarchical LLM reduction, exploded parquet schema.
- Run only implicated tests during development; full `make check` + full affected-test-suite run at the end of each task group / PR boundary.
- Never commit `docs/plans/` or `docs/superpowers/` documents.

## File Structure

```
src/inspect_scout/_transcript/
  handle.py                 (NEW: TranscriptHandle protocol + MaterializedTranscriptHandle)
  json/
    spool.py                (NEW: SpoolWriter/SpoolReader — offset-indexed spool + JSONL item spool)
    stream_parse.py         (NEW: single-pass spool-building parse + replay iterators)
    load_filtered.py        (MODIFY: extract shared coroutine wiring for reuse)
  eval_log.py               (MODIFY: EvalLogTranscriptsView.open(); read() delegates)
  transcripts.py            (MODIFY: TranscriptsReader.open() default impl)
  database/parquet/transcripts.py (MODIFY: ParquetTranscriptsDB.open())
  messages.py               (MODIFY: segment_messages_stream())
src/inspect_scout/
  _scanner/types.py         (MODIFY: ScannerInput + handle input names)
  _scanner/util.py          (MODIFY: get_input_type_and_ids handles TranscriptHandle)
  _scanner/result.py        (MODIFY: _serialize_input info-only branch)
  _scanner/scanner.py       (MODIFY: SCANNER_ACCEPTS_HANDLE_ATTR)
  _concurrency/common.py    (MODIFY: ScannerJob.union_transcript type widened)
  _scan.py                  (MODIFY: _parse_function switch, _scan_one error containment)
  _llm_scanner/_llm_scanner.py (MODIFY: accept handle, streaming segmentation, bounded window)
  _view/_api_v2_search.py   (MODIFY: use open() for LLM search)
tests/transcript/
  test_spool.py             (NEW)
  test_stream_parse.py      (NEW)
  test_handle.py            (NEW)
  test_handle_equivalence.py (NEW)
tests/scanner/
  test_streaming_seam.py    (NEW)
tests/llm_scanner/
  test_streaming_segments.py (NEW)
```

PR grouping: Tasks 1–5 (handle + eval-log streaming read), Tasks 6–8 (seam + result plumbing), Tasks 9–11 (llm_scanner + endpoint), Task 12 (parquet).

---

### Task 1: Spool primitives (`spool.py`)

**Files:**
- Create: `src/inspect_scout/_transcript/json/spool.py`
- Test: `tests/transcript/test_spool.py`

**Interfaces:**
- Produces:
  - `class BlobSpool:` — append-only temp file + in-memory offset index.
    - `__init__(self, dir: Path)` — creates temp file in `dir`, opens for write, **unlinks immediately on POSIX** (keeps fd).
    - `put(self, key: tuple[str, int] | str, value: str) -> None` — appends UTF-8 bytes, records `(offset, length)`.
    - `get(self, key: tuple[str, int] | str) -> str | None` — seeks + reads; None when absent.
    - `pool_len(self, pool_name: str) -> int` — number of `(pool_name, i)` entries.
    - `close(self) -> None` — idempotent; closes fd (file already unlinked).
  - `class ItemSpool:` — JSONL spool for filtered message/event dicts.
    - `__init__(self, dir: Path)` — same unlink-after-open pattern.
    - `append(self, item: dict[str, Any]) -> None` — one compact-JSON line.
    - `__len__(self) -> int`
    - `items(self) -> Iterator[dict[str, Any]]` — re-iterable: each call seeks to 0 and yields `json.loads` per line. Uses its own file offset tracking so concurrent iterations are safe (each `items()` call opens its own `os.dup`'d reader or tracks its own offset — implement via `open(fd_path)`-free approach: store offsets per iterator using `os.pread`).
    - `close(self) -> None` — idempotent.

Keys: attachments use plain `str` id; pool items use `(pool_name, index)` (positional — pool refs are half-open ranges, `json/pool.py:15-24`).

Use `os.pread(self._fd, length, offset)` for reads in both classes so multiple iterators/readers never interfere via shared file position. Writes go through a single buffered writer; `put`/`append` flush is not needed per-call — flush before first read (track a `_dirty` flag).

- [ ] **Step 1: Write failing tests**

```python
"""Tests for spool primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspect_scout._transcript.json.spool import BlobSpool, ItemSpool


def test_blob_spool_roundtrip(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    try:
        spool.put("att1", "hello world")
        spool.put(("message_pool", 0), json.dumps({"role": "user"}))
        spool.put(("message_pool", 1), json.dumps({"role": "assistant"}))
        assert spool.get("att1") == "hello world"
        assert json.loads(spool.get(("message_pool", 1)) or "") == {
            "role": "assistant"
        }
        assert spool.get("missing") is None
        assert spool.pool_len("message_pool") == 2
        assert spool.pool_len("call_pool") == 0
    finally:
        spool.close()


def test_blob_spool_unicode(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    try:
        spool.put("u", "héllo — ünïcode 你好")
        assert spool.get("u") == "héllo — ünïcode 你好"
    finally:
        spool.close()


def test_blob_spool_no_file_left_behind(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    spool.put("k", "v")
    spool.close()
    assert list(tmp_path.iterdir()) == []  # unlinked on creation (POSIX)


def test_item_spool_reiterable(tmp_path: Path) -> None:
    spool = ItemSpool(tmp_path)
    try:
        items: list[dict[str, Any]] = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        for item in items:
            spool.append(item)
        assert len(spool) == 2
        assert list(spool.items()) == items
        assert list(spool.items()) == items  # second iteration identical
    finally:
        spool.close()


def test_item_spool_interleaved_iterations(tmp_path: Path) -> None:
    spool = ItemSpool(tmp_path)
    try:
        for i in range(3):
            spool.append({"n": i})
        it1 = spool.items()
        it2 = spool.items()
        assert next(it1) == {"n": 0}
        assert next(it2) == {"n": 0}
        assert next(it1) == {"n": 1}
        assert list(it2) == [{"n": 1}, {"n": 2}]
    finally:
        spool.close()


def test_close_idempotent(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    spool.close()
    spool.close()
    ispool = ItemSpool(tmp_path)
    ispool.close()
    ispool.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/transcript/test_spool.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'inspect_scout._transcript.json.spool'`

- [ ] **Step 3: Implement `spool.py`**

```python
"""Disk spools for streaming transcript parses.

Spool files are created inside the task files cache dir and unlinked
immediately after open (POSIX), so crash leaks are impossible; the data
lives until the fd is closed. Reads use os.pread so concurrent iterators
never interfere via shared file position.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator

SpoolKey = tuple[str, int] | str


class BlobSpool:
    """Append-only spool with an in-memory offset index.

    Keys are attachment ids (str) or positional pool entries
    ((pool_name, index)) -- pool refs are half-open ranges so pool
    items must be positionally addressable.
    """

    def __init__(self, dir: Path) -> None:
        fd, path = tempfile.mkstemp(dir=dir, prefix="scout-spool-", suffix=".blob")
        os.unlink(path)
        self._fd: int | None = fd
        self._index: dict[SpoolKey, tuple[int, int]] = {}
        self._pool_counts: dict[str, int] = {}
        self._write_offset = 0

    def put(self, key: SpoolKey, value: str) -> None:
        assert self._fd is not None
        data = value.encode("utf-8")
        os.pwrite(self._fd, data, self._write_offset)
        self._index[key] = (self._write_offset, len(data))
        self._write_offset += len(data)
        if isinstance(key, tuple):
            pool_name, _ = key
            self._pool_counts[pool_name] = self._pool_counts.get(pool_name, 0) + 1

    def get(self, key: SpoolKey) -> str | None:
        assert self._fd is not None
        entry = self._index.get(key)
        if entry is None:
            return None
        offset, length = entry
        return os.pread(self._fd, length, offset).decode("utf-8")

    def pool_len(self, pool_name: str) -> int:
        return self._pool_counts.get(pool_name, 0)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


class ItemSpool:
    """JSONL spool of dicts supporting multiple concurrent iterations."""

    def __init__(self, dir: Path) -> None:
        fd, path = tempfile.mkstemp(dir=dir, prefix="scout-spool-", suffix=".jsonl")
        os.unlink(path)
        self._fd: int | None = fd
        self._write_offset = 0
        self._count = 0

    def append(self, item: dict[str, Any]) -> None:
        assert self._fd is not None
        line = json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")
        os.pwrite(self._fd, data, self._write_offset)
        self._write_offset += len(data)
        self._count += 1

    def __len__(self) -> int:
        return self._count

    def items(self) -> Iterator[dict[str, Any]]:
        assert self._fd is not None
        fd = self._fd
        end = self._write_offset
        offset = 0
        buffer = b""
        chunk_size = 256 * 1024
        while offset < end or b"\n" in buffer:
            newline = buffer.find(b"\n")
            if newline == -1:
                read_len = min(chunk_size, end - offset)
                if read_len <= 0:
                    break
                buffer += os.pread(fd, read_len, offset)
                offset += read_len
                continue
            line, buffer = buffer[:newline], buffer[newline + 1 :]
            yield json.loads(line)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/transcript/test_spool.py -v`
Expected: 6 PASS

- [ ] **Step 5: Typecheck and commit**

Run: `.venv/bin/mypy src/inspect_scout/_transcript/json/spool.py tests/transcript/test_spool.py`
Expected: no errors

```bash
git add src/inspect_scout/_transcript/json/spool.py tests/transcript/test_spool.py
git commit -m "feat: disk spool primitives for streaming transcript reads"
```

---

### Task 2: Single-pass spool-building parse (`stream_parse.py` — parse half)

**Files:**
- Create: `src/inspect_scout/_transcript/json/stream_parse.py`
- Test: `tests/transcript/test_stream_parse.py`

**Interfaces:**
- Consumes: `BlobSpool`, `ItemSpool` (Task 1); filter coroutines from `json/reducer.py` (`message_item_coroutine`, `event_item_coroutine`, `attachments_coroutine` NOT reused for attachments — see below); prefix constants from `reducer.py`; section-classification approach from `load_filtered.py::_parse_and_filter`.
- Produces:
  - `@dataclass class StreamParseResult:` fields: `messages: ItemSpool`, `events: ItemSpool`, `blobs: BlobSpool` (attachments + pools), `metadata: dict[str, Any]`, `target: str | list[str] | None`, `scores: dict[str, Any]`, `timelines: list[dict[str, Any]]`, `close() -> None` (closes all three spools, idempotent).
  - `async def stream_parse_to_spool(sample_bytes: IO[bytes] | AsyncIterable[bytes], messages_filter: MessageFilter, events_filter: EventFilter, spool_dir: Path) -> StreamParseResult`

Behavior:
- One ijson pass (`ijson.parse_async`, `use_float=True`), reusing the section-classification structure from `_parse_and_filter` (`load_filtered.py:326-454`).
- Filtered messages/events: reuse `_item_coroutine` semantics but the sink appends each **completed** item dict to the `ItemSpool` instead of a list. Implement by passing a list-like adapter whose `append` writes to the spool (`_item_coroutine(target_list, ...)` takes any object with `append`; verify and if it also reads the list, wrap minimally).
- **ALL attachments spooled** (no `attachment_refs` filtering — refs inside pool items arrive after attachments; this also fixes the live pool-attachment bug). New coroutine `_spool_attachments_coroutine(blobs)` modeled on `attachments_coroutine` (`reducer.py:186-202`) minus the ref check.
- Pool items (all four prefixes: `message_pool.item`, `call_pool.item`, `events_data.messages.item`, `events_data.calls.item`): spooled to `blobs` with keys `("message_pool", i)` / `("call_pool", i)` via a counting sink adapter over `_unfiltered_item_coroutine`.
- `metadata`/`target`/`scores`/`timelines`: reuse the existing coroutines unchanged (small data, kept in memory).
- No early-exit (attachments/pools must always be read). NaN/Inf (`ijson.JSONError`): let it propagate — the caller (Task 4) handles fallback.
- On any exception, close all spools before re-raising (`try/except BaseException: result.close(); raise`).

- [ ] **Step 1: Write failing tests**

```python
"""Tests for single-pass spool-building stream parse."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool


def _stream(data: dict[str, Any]) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


SAMPLE: dict[str, Any] = {
    "id": "s1",
    "metadata": {"k": "v"},
    "target": "the-target",
    "messages": [
        {"id": "m1", "role": "user", "content": "hello"},
        {"id": "m2", "role": "assistant", "content": "attachment://" + "a" * 32},
    ],
    "scores": {"scorer": {"value": 1}},
    "events": [
        {"event": "model", "timestamp": 1.0, "input_refs": [[0, 2]]},
        {"event": "info", "timestamp": 2.0, "data": "x"},
    ],
    "attachments": {"a" * 32: "resolved-text"},
    "events_data": {
        "messages": [
            {"role": "user", "content": "pooled-1"},
            {"role": "assistant", "content": "attachment://" + "b" * 32},
        ],
        "calls": [],
    },
}


@pytest.mark.asyncio
async def test_parse_spools_filtered_items(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), "all", ["model"], tmp_path)
    try:
        messages = list(result.messages.items())
        assert [m["id"] for m in messages] == ["m1", "m2"]
        events = list(result.events.items())
        assert len(events) == 1 and events[0]["event"] == "model"
        assert result.metadata == {"k": "v"}
        assert result.target == "the-target"
        assert result.scores == {"scorer": {"value": 1}}
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_spools_all_attachments_and_pools(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), None, None, tmp_path)
    try:
        # attachments spooled even when no kept item references them
        assert result.blobs.get("a" * 32) == "resolved-text"
        # pool items positionally addressable
        assert result.blobs.pool_len("message_pool") == 2
        pooled = json.loads(result.blobs.get(("message_pool", 1)) or "")
        assert pooled["content"] == "attachment://" + "b" * 32
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_message_filter(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), ["user"], None, tmp_path)
    try:
        messages = list(result.messages.items())
        assert [m["role"] for m in messages] == ["user"]
        assert len(result.events) == 0
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_nan_raises(tmp_path: Path) -> None:
    import ijson

    bad = io.BytesIO(b'{"id": "s", "messages": [], "x": NaN}')
    with pytest.raises(ijson.JSONError):
        await stream_parse_to_spool(bad, "all", "all", tmp_path)
    assert list(tmp_path.iterdir()) == []  # spools closed/unlinked on error
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/transcript/test_stream_parse.py -v`
Expected: FAIL with `ModuleNotFoundError` (stream_parse does not exist)

- [ ] **Step 3: Implement the parse half of `stream_parse.py`**

Structure (follow `_parse_and_filter` closely for section classification — copy the inlined prefix-classification block verbatim; it is performance-critical and documented as such):

```python
"""Single-pass spool-building parse and replay for large transcripts.

Parses the sample JSON once, spooling filtered messages/events (unresolved)
to JSONL and ALL attachments + pool items to an offset-indexed blob spool.
Replay (see replay_* functions) resolves attachment:// refs and pool ranges
per item, validates via TypeAdapter, and yields -- O(one item) memory.

Spooling all attachments is required (refs inside events_data pool items
arrive after the attachments section) and fixes the pool-attachment
resolution bug in the in-memory path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, AsyncIterable

import ijson  # type: ignore
from inspect_ai._util.async_bytes_reader import adapt_to_reader

from ..types import EventFilter, MessageFilter
from .reducer import (
    # ... same prefix constants as load_filtered.py imports ...
    ListProcessingConfig,
    ParseState,
    message_item_coroutine,
    event_item_coroutine,
    metadata_coroutine,
    scores_coroutine,
    target_coroutine,
    timeline_item_coroutine,
)
from .spool import BlobSpool, ItemSpool


class _SpoolSink(list):  # type: ignore[type-arg]
    """List stand-in whose append writes to an ItemSpool."""

    def __init__(self, spool: ItemSpool) -> None:
        super().__init__()
        self._spool = spool

    def append(self, item: Any) -> None:
        self._spool.append(item)


class _PoolSink(list):  # type: ignore[type-arg]
    """List stand-in whose append writes positional pool entries to a BlobSpool."""

    def __init__(self, blobs: BlobSpool, pool_name: str) -> None:
        super().__init__()
        self._blobs = blobs
        self._pool_name = pool_name
        self._i = 0

    def append(self, item: Any) -> None:
        self._blobs.put(
            (self._pool_name, self._i),
            json.dumps(item, ensure_ascii=False, separators=(",", ":")),
        )
        self._i += 1


@dataclass
class StreamParseResult:
    messages: ItemSpool
    events: ItemSpool
    blobs: BlobSpool
    metadata: dict[str, Any] = field(default_factory=dict)
    target: str | list[str] | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    timelines: list[dict[str, Any]] = field(default_factory=list)

    def close(self) -> None:
        self.messages.close()
        self.events.close()
        self.blobs.close()
```

The `stream_parse_to_spool` body mirrors `_parse_and_filter` (`load_filtered.py:260-454`) with these substitutions:

- `state = ParseState()` still used for metadata/target/scores/timelines coroutines, but messages/events coroutines are constructed with `_SpoolSink` targets: build `ListProcessingConfig` as today, then call the underlying `_item_coroutine(_SpoolSink(messages_spool), set(), config)` (import `_item_coroutine` and `_unfiltered_item_coroutine` directly from `reducer` — they accept any `.append`-able; the `attachment_refs` set arg is passed a throwaway `set()` since refs are not needed).
- Attachments section: inline coroutine that on each `(prefix, "string", value)` under `attachments.` extracts the id (same prefix-splitting as `attachments_coroutine`, `reducer.py:186-202`) and does `blobs.put(attachment_id, value)` — **no ref check**.
- Pool sections: `_unfiltered_item_coroutine(_PoolSink(blobs, "message_pool"), MESSAGE_POOL_ITEM_PREFIX)` etc. for all four prefixes. Pools are spooled **unconditionally** (not only when events requested — replay of messages doesn't need them, but the cost is negligible and it keeps one code path).
- No early-exit branch.
- Wrap the whole body:

```python
    messages_spool = ItemSpool(spool_dir)
    events_spool = ItemSpool(spool_dir)
    blobs = BlobSpool(spool_dir)
    result = StreamParseResult(messages_spool, events_spool, blobs)
    try:
        async with adapt_to_reader(sample_bytes) as reader:
            async for prefix, event, value in ijson.parse_async(reader, use_float=True):
                ...  # section classification + dispatch
        result.metadata = state.metadata
        result.target = state.target
        result.scores = state.scores
        result.timelines = state.timelines
        return result
    except BaseException:
        result.close()
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/transcript/test_stream_parse.py -v`
Expected: 4 PASS

- [ ] **Step 5: Run existing load_filtered tests (no regression), typecheck, commit**

Run: `.venv/bin/pytest tests/scanner/test_load_filtered.py -v && .venv/bin/mypy src/inspect_scout/_transcript/json/`
Expected: all PASS, no type errors

```bash
git add src/inspect_scout/_transcript/json/stream_parse.py tests/transcript/test_stream_parse.py
git commit -m "feat: single-pass spool-building stream parse"
```

---

### Task 3: Replay iterators (`stream_parse.py` — replay half)

**Files:**
- Modify: `src/inspect_scout/_transcript/json/stream_parse.py`
- Test: `tests/transcript/test_stream_parse.py` (extend)

**Interfaces:**
- Consumes: `StreamParseResult` (Task 2); `ATTACHMENT_PATTERN` regex from `load_filtered.py:49`; pool-ref expansion semantics from `json/pool.py::_resolve_events_pools`.
- Produces (added to `stream_parse.py`):
  - `def replay_messages(result: StreamParseResult) -> Iterator[ChatMessage]`
  - `def replay_events(result: StreamParseResult) -> Iterator[Event]`
  - `def resolve_item_dict(item: dict[str, Any], blobs: BlobSpool) -> dict[str, Any]` — resolves `attachment://` refs (string-level, recursive over dict/list, same as `_resolve_dict_attachments` in `load_filtered.py:571-579` but looking up in `blobs`) mutating in place; for event dicts additionally expands `input_refs`/`call_refs` positional ranges from `blobs` pools (same semantics as `_resolve_events_pools`, `json/pool.py:27-47`, but fetching `("message_pool", i)` / `("call_pool", i)` entries and **then** resolving attachment refs inside the fetched pool items too — this is the bug fix).

Validation: module-level `_CHAT_MESSAGE_ADAPTER = TypeAdapter(ChatMessage)` and `_EVENT_ADAPTER = TypeAdapter(Event)` (both are pydantic discriminated unions — `ChatMessage` from `inspect_ai.model._chat_message`, `Event` from `inspect_ai.event._event`). `replay_*` yields `adapter.validate_python(resolved_dict)` per item.

Note these are sync generators (all I/O is local pread) — the async surface comes in Task 4's handle.

- [ ] **Step 1: Write failing tests (append to test_stream_parse.py)**

```python
@pytest.mark.asyncio
async def test_replay_messages_resolves_attachments(tmp_path: Path) -> None:
    from inspect_scout._transcript.json.stream_parse import replay_messages

    result = await stream_parse_to_spool(_stream(SAMPLE), "all", None, tmp_path)
    try:
        messages = list(replay_messages(result))
        assert messages[1].content == "resolved-text"  # attachment resolved
        assert messages[0].role == "user"
        # multi-shot: second replay identical
        again = list(replay_messages(result))
        assert [m.id for m in again] == [m.id for m in messages]
    finally:
        result.close()


@pytest.mark.asyncio
async def test_replay_events_expands_pools_and_pool_attachments(
    tmp_path: Path,
) -> None:
    from inspect_scout._transcript.json.stream_parse import replay_events

    result = await stream_parse_to_spool(_stream(SAMPLE), None, "all", tmp_path)
    try:
        events = list(replay_events(result))
        model_events = [e for e in events if e.event == "model"]
        assert len(model_events) == 1
        inputs = model_events[0].input
        assert len(inputs) == 2  # input_refs [[0, 2]] expanded from pool
        # THE BUG FIX: attachment ref inside a pool item is resolved.
        # (Requires "b"*32 in SAMPLE attachments — extend SAMPLE first.)
        assert inputs[1].content == "pool-attachment-resolved"
    finally:
        result.close()
```

Also extend `SAMPLE["attachments"]` with `"b" * 32: "pool-attachment-resolved"` so the pool-attachment fix is assertable, and give the model event minimal required fields for `Event` validation (check `ModelEvent` required fields — at minimum `event`, `timestamp`, `model`, `input`, `output`; copy a passing minimal model-event dict from `tests/scanner/test_load_filtered.py::test_pool_resolution` which already constructs one).

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/transcript/test_stream_parse.py -v -k replay`
Expected: FAIL with ImportError (replay_messages not defined)

- [ ] **Step 3: Implement replay half**

```python
import re
from typing import Iterator

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from pydantic import TypeAdapter

_ATTACHMENT_PATTERN = re.compile(r"attachment://([a-f0-9]{32})")
_CHAT_MESSAGE_ADAPTER: TypeAdapter[ChatMessage] = TypeAdapter(ChatMessage)
_EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)


def _resolve_strings(obj: Any, blobs: BlobSpool) -> Any:
    if isinstance(obj, str):
        if "attachment://" not in obj:
            return obj
        return _ATTACHMENT_PATTERN.sub(
            lambda m: blobs.get(m.group(1)) or m.group(0), obj
        )
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _resolve_strings(v, blobs)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _resolve_strings(v, blobs)
        return obj
    return obj


def _expand_pool_range(
    refs: list[list[int]], pool_name: str, blobs: BlobSpool
) -> list[Any]:
    result: list[Any] = []
    for start, end_exclusive in refs:
        for i in range(start, end_exclusive):
            raw = blobs.get((pool_name, i))
            if raw is not None:
                result.append(_resolve_strings(json.loads(raw), blobs))
    return result


def resolve_item_dict(item: dict[str, Any], blobs: BlobSpool) -> dict[str, Any]:
    input_refs = item.get("input_refs")
    if input_refs and blobs.pool_len("message_pool"):
        item["input"] = _expand_pool_range(input_refs, "message_pool", blobs)
        item.pop("input_refs", None)
    call = item.get("call")
    if call and call.get("call_refs") is not None and blobs.pool_len("call_pool"):
        key = call.get("call_key", "messages")
        call.setdefault("request", {})[key] = _expand_pool_range(
            call["call_refs"], "call_pool", blobs
        )
        call.pop("call_refs", None)
        call.pop("call_key", None)
    return _resolve_strings(item, blobs)


def replay_messages(result: StreamParseResult) -> Iterator[ChatMessage]:
    for item in result.messages.items():
        yield _CHAT_MESSAGE_ADAPTER.validate_python(resolve_item_dict(item, result.blobs))


def replay_events(result: StreamParseResult) -> Iterator[Event]:
    for item in result.events.items():
        yield _EVENT_ADAPTER.validate_python(resolve_item_dict(item, result.blobs))
```

Note: `_PoolSink` in Task 2 must spool the four prefixes into the two logical pools — `events_data.messages`/`message_pool` → `"message_pool"`, `events_data.calls`/`call_pool` → `"call_pool"` (both on-disk shapes carry the same data; a file has one or the other, so shared counters are safe).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/transcript/test_stream_parse.py -v`
Expected: all PASS

- [ ] **Step 5: Typecheck and commit**

Run: `.venv/bin/mypy src/inspect_scout/_transcript/json/stream_parse.py`

```bash
git add src/inspect_scout/_transcript/json/stream_parse.py tests/transcript/test_stream_parse.py
git commit -m "feat: replay iterators with attachment and pool resolution (fixes pool-attachment refs)"
```

---

### Task 4: `TranscriptHandle` protocol + implementations (`handle.py`)

**Files:**
- Create: `src/inspect_scout/_transcript/handle.py`
- Test: `tests/transcript/test_handle.py`

**Interfaces:**
- Consumes: `stream_parse_to_spool`, `replay_messages`, `replay_events`, `StreamParseResult` (Tasks 2–3); `Transcript`, `TranscriptInfo`, `TranscriptContent` from `_transcript/types.py`; `load_filtered_transcript` from `json/load_filtered.py`.
- Produces:

```python
STREAMING_THRESHOLD_BYTES: int = 64 * 1024 * 1024

class TranscriptHandle(Protocol):
    """Streaming access to transcript content. Async context manager."""
    @property
    def info(self) -> TranscriptInfo: ...
    def messages(self) -> AsyncIterator[ChatMessage]: ...   # multi-shot
    def events(self) -> AsyncIterator[Event]: ...           # multi-shot
    async def load(self) -> Transcript: ...                 # memoized
    async def __aenter__(self) -> "TranscriptHandle": ...
    async def __aexit__(self, *exc: object) -> None: ...
    async def aclose(self) -> None: ...

class MaterializedTranscriptHandle:
    """Handle over an already/eagerly loaded Transcript (small-file path)."""
    def __init__(self, load_fn: Callable[[], Awaitable[Transcript]], info: TranscriptInfo) -> None: ...
    # messages()/events() iterate (await load()).messages/.events

class SpooledTranscriptHandle:
    """Handle backed by a StreamParseResult spool (large-file path)."""
    def __init__(
        self,
        info: TranscriptInfo,
        parse: Callable[[], Awaitable[StreamParseResult]],  # deferred: runs on first use
        load_fallback: Callable[[], Awaitable[Transcript]],  # json5/NaN materializing fallback
    ) -> None: ...
```

Behavior details:
- **Lazy-opening:** `SpooledTranscriptHandle` runs `parse()` on first `messages()`/`events()`/`load()` call, not at construction (prefetched ScannerJobs must not pin resources). Memoize the `StreamParseResult`.
- `messages()`/`events()` wrap the sync replay generators as async iterators, checkpointing every 64 items via `await anyio.lowlevel.checkpoint()` so long replays don't starve the event loop.
- `load()` on `SpooledTranscriptHandle`: build a `Transcript` by collecting the replay iterators + the metadata/target/scores side-channel (merge semantics identical to `_merge_unthinned`, `load_filtered.py:217-226`); memoize. If `parse()` raised `ijson.JSONError` (NaN/Inf), call `load_fallback()` and serve `messages()`/`events()` from the loaded transcript thereafter.
- **Pickling refused:** both classes implement `def __reduce__(self) -> NoReturn: raise TypeError("TranscriptHandle cannot be pickled (must not cross process boundaries)")`.
- `aclose()`/`__aexit__`: close the memoized `StreamParseResult` if any; idempotent. `MaterializedTranscriptHandle.aclose()` is a no-op.
- Timelines: `load()` attaches raw timeline dicts only when the transcript came via `load_fallback` or the materialized path — the streaming path is messages/events only (spec non-goal); `StreamParseResult.timelines` is passed through to `load()`'s Transcript via `timeline_load` **only when events were fully loaded** — mirror the existing guard in `eval_log.py:504-528`. Keep it simple: `SpooledTranscriptHandle.load()` sets `timelines=[]` (streaming handles are only selected for messages-only content — enforced at the seam, Task 7).

- [ ] **Step 1: Write failing tests**

```python
"""Tests for TranscriptHandle implementations."""

from __future__ import annotations

import io
import json
import pickle
from pathlib import Path
from typing import Any

import pytest

from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
)
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool
from inspect_scout._transcript.types import Transcript, TranscriptInfo

INFO = TranscriptInfo(transcript_id="t1", source_type="eval_log", source_id="e1")

SAMPLE: dict[str, Any] = {
    "id": "t1",
    "messages": [
        {"id": "m1", "role": "user", "content": "hello"},
        {"id": "m2", "role": "assistant", "content": "world"},
    ],
    "events": [],
    "attachments": {},
}


def _spooled_handle(tmp_path: Path) -> SpooledTranscriptHandle:
    async def parse() -> Any:
        return await stream_parse_to_spool(
            io.BytesIO(json.dumps(SAMPLE).encode()), "all", None, tmp_path
        )

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    return SpooledTranscriptHandle(INFO, parse, fallback)


@pytest.mark.asyncio
async def test_spooled_handle_multi_shot(tmp_path: Path) -> None:
    async with _spooled_handle(tmp_path) as handle:
        first = [m async for m in handle.messages()]
        second = [m async for m in handle.messages()]
        assert [m.id for m in first] == ["m1", "m2"]
        assert [m.id for m in second] == ["m1", "m2"]


@pytest.mark.asyncio
async def test_spooled_handle_load_memoized(tmp_path: Path) -> None:
    async with _spooled_handle(tmp_path) as handle:
        t1 = await handle.load()
        t2 = await handle.load()
        assert t1 is t2
        assert len(t1.messages) == 2
        assert t1.transcript_id == "t1"


@pytest.mark.asyncio
async def test_handle_refuses_pickle(tmp_path: Path) -> None:
    handle = _spooled_handle(tmp_path)
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(handle)
    await handle.aclose()


@pytest.mark.asyncio
async def test_spooled_handle_lazy_and_cleanup(tmp_path: Path) -> None:
    handle = _spooled_handle(tmp_path)
    # not yet parsed: aclose before use is safe
    await handle.aclose()
    await handle.aclose()  # idempotent


@pytest.mark.asyncio
async def test_materialized_handle(tmp_path: Path) -> None:
    transcript = Transcript(
        transcript_id="t1", messages=[], events=[], metadata={}
    )
    calls = 0

    async def load_fn() -> Transcript:
        nonlocal calls
        calls += 1
        return transcript

    async with MaterializedTranscriptHandle(load_fn, INFO) as handle:
        assert (await handle.load()) is transcript
        assert [m async for m in handle.messages()] == []
        assert calls == 1  # memoized
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/transcript/test_handle.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement `handle.py`** (full implementation per the interface block above; async wrappers over replay generators with periodic `anyio.lowlevel.checkpoint()`; `_merge_unthinned`-equivalent metadata merge in `load()`)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/transcript/test_handle.py -v`
Expected: 6 PASS

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/_transcript/handle.py
git add src/inspect_scout/_transcript/handle.py tests/transcript/test_handle.py
git commit -m "feat: TranscriptHandle protocol with spooled and materialized implementations"
```

---

### Task 5: `EvalLogTranscriptsView.open()` + reader plumbing + equivalence tests

**Files:**
- Modify: `src/inspect_scout/_transcript/eval_log.py` (add `open()` to `EvalLogTranscriptsView`; add `open()` to `EvalLogTranscriptsReader`)
- Modify: `src/inspect_scout/_transcript/transcripts.py` (add `TranscriptsReader.open()` with default impl)
- Modify: `src/inspect_scout/_transcript/database/database.py` (add `TranscriptsView.open()` default impl)
- Test: `tests/transcript/test_handle_equivalence.py`

**Interfaces:**
- Produces:
  - `TranscriptsReader.open(self, transcript: TranscriptInfo, content: TranscriptContent) -> AsyncContextManager[TranscriptHandle]` — non-abstract default: returns `MaterializedTranscriptHandle(lambda: self.read(transcript, content), transcript)` wrapped in a trivial async CM. Backends override for real streaming.
  - Same-shaped `open()` on `TranscriptsView` (default `MaterializedTranscriptHandle` over `self.read`).
  - `EvalLogTranscriptsView.open()`: decides by `entry.uncompressed_size` (already fetched via `_get_zip_reader_and_entry`) vs `STREAMING_THRESHOLD_BYTES` **and** whether `content.timeline is None`:
    - small or timeline-requested → `MaterializedTranscriptHandle` over the existing `read()` (early-exit fast path preserved untouched).
    - large messages/events-only → `SpooledTranscriptHandle` whose `parse` callable opens the zip member (`zip_reader.open_member(entry)`) and runs `stream_parse_to_spool(stream, content.messages, content.events, spool_dir)` with `spool_dir = self._files_cache.cache_dir` (fall back to `tempfile.gettempdir()` when no cache); whose `load_fallback` runs the existing `read()` (json5/NaN path).
    - When the source is remote and not locally cached (cache full/missing), first spool the member's compressed bytes to a local temp file, then parse from it — never stream S3 twice. (Reuse `resolve_remote_uri_to_local`; if it returns the remote URI unchanged, download the member via the zip reader ONCE into a local spool file inside `open()`'s parse callable.)
- `EvalLogTranscriptsReader.open()` delegates to `self._db.open(...)`.

- [ ] **Step 1: Write failing equivalence tests**

```python
"""Equivalence: streamed handle vs materialized read() on real eval logs."""

from __future__ import annotations

from pathlib import Path

import pytest

from inspect_scout._transcript import handle as handle_mod
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.types import TranscriptContent

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOG = str(
    LOGS_DIR / "2025-09-23T08-09-58-04-00_theory-of-mind_bbB4eRCx2rFJLyPH42Cj9r.eval"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        TranscriptContent(messages="all", events=None),
        TranscriptContent(messages=["assistant"], events=None),
        TranscriptContent(messages="all", events="all"),
        TranscriptContent(messages=None, events=["model"]),
    ],
)
async def test_streamed_equals_materialized(
    content: TranscriptContent, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the spooled path regardless of file size
    monkeypatch.setattr(handle_mod, "STREAMING_THRESHOLD_BYTES", 0)
    view = EvalLogTranscriptsView(LOG)
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        assert infos
        info = infos[0]
        materialized = await view.read(info, content)
        async with await view.open(info, content) as h:
            streamed_messages = [m async for m in h.messages()]
            streamed_events = [e async for e in h.events()]
            loaded = await h.load()
        assert [m.model_dump() for m in streamed_messages] == [
            m.model_dump() for m in materialized.messages
        ]
        assert [e.model_dump() for e in streamed_events] == [
            e.model_dump() for e in materialized.events
        ]
        assert loaded.metadata == materialized.metadata
    finally:
        await view.disconnect()


@pytest.mark.asyncio
async def test_small_file_uses_materialized_handle() -> None:
    # default threshold (64MB) >> fixture size -> MaterializedTranscriptHandle
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle

    view = EvalLogTranscriptsView(LOG)
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        cm = await view.open(
            infos[0], TranscriptContent(messages="all", events=None)
        )
        async with cm as h:
            assert isinstance(h, MaterializedTranscriptHandle)
    finally:
        await view.disconnect()
```

Note: run the parametrized test against **all three** fixture logs in `tests/recorder/logs/` (extend the parametrize or loop) — they exercise attachments and pool-condensed events. Check whether any fixture has `events_data`; if none does, add one case using the pool-shaped inline JSON from `tests/scanner/test_load_filtered.py::test_pool_resolution_events_data_schema` written to a temp `.eval` via `inspect_ai.log.write_eval_log` — if that proves awkward, cover pools only at the `stream_parse` level (already done in Task 3) and note it.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/transcript/test_handle_equivalence.py -v`
Expected: FAIL with AttributeError (`open` not defined)

- [ ] **Step 3: Implement `open()` on the three classes** per the interface block. Key detail for `EvalLogTranscriptsView.open()`: it must not hold the zip stream open across the CM boundary — the `parse` callable owns opening and closing the member stream (open inside, `async with await zip_reader.open_member(entry)` around `stream_parse_to_spool`).

- [ ] **Step 4: Run equivalence + existing eval_log tests**

Run: `.venv/bin/pytest tests/transcript/test_handle_equivalence.py tests/transcript/test_eval_log_caching.py tests/transcript/test_eval_log_read_messages_events.py tests/scanner/test_load_filtered.py -v`
Expected: all PASS

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/_transcript/
git add -A src/inspect_scout/_transcript tests/transcript/test_handle_equivalence.py
git commit -m "feat: TranscriptsReader.open() streaming read API for eval logs"
```

---

### Task 6: `ScannerInput`/result plumbing for handles

**Files:**
- Modify: `src/inspect_scout/_scanner/types.py`
- Modify: `src/inspect_scout/_scanner/util.py`
- Modify: `src/inspect_scout/_scanner/result.py`
- Test: `tests/scanner/test_streaming_seam.py` (new, first tests)

**Interfaces:**
- Consumes: `TranscriptHandle` (Task 4).
- Produces:
  - `ScannerInputNames` gains `"transcript_handle"`.
  - `ScannerInput` union gains `TranscriptHandle` (import under `TYPE_CHECKING` + runtime via the concrete protocol check; since `TranscriptHandle` is a Protocol, `get_input_type_and_ids` dispatches with `isinstance(loader_result, (MaterializedTranscriptHandle, SpooledTranscriptHandle))` — or make `TranscriptHandle` `@runtime_checkable`; choose `@runtime_checkable` on the protocol, checked FIRST in the isinstance chain since handles are not Transcripts).
  - `get_input_type_and_ids(handle)` → `("transcript_handle", [handle.info.transcript_id])`.
  - `_serialize_input` for `input_type == "transcript_handle"`: returns `(to_json_str_compact(input.info), None)` — **info only, never content**. Requires `ResultReport.input` to accept the handle transiently; since `ResultReport` is pydantic and handles refuse pickling/serialization, store `handle.info` (a `TranscriptInfo`) as the report's `input` instead: in `_scan_one` (Task 7) construct `ResultReport(input=handle.info, ...)` — so `ScannerInput` gains `TranscriptInfo`, NOT the handle itself, and `_serialize_input` gets a `TranscriptInfo` branch. `get_input_type_and_ids` maps `TranscriptInfo` → `("transcript_handle", [info.transcript_id])`. This keeps `ResultReport` pickleable with zero content.

- [ ] **Step 1: Write failing tests**

```python
"""Tests for the streaming scanner seam: input plumbing."""

from __future__ import annotations

from inspect_scout._scanner.result import _serialize_input
from inspect_scout._scanner.util import get_input_type_and_ids
from inspect_scout._transcript.types import TranscriptInfo


def test_input_type_for_transcript_info() -> None:
    info = TranscriptInfo(transcript_id="t1")
    assert get_input_type_and_ids(info) == ("transcript_handle", ["t1"])


def test_serialize_input_info_only() -> None:
    info = TranscriptInfo(transcript_id="t1", source_id="e1")
    input_json, input_data = _serialize_input(
        info, "transcript_handle", pool_dedup=True
    )
    assert input_data is None
    assert '"transcript_id":"t1"' in input_json.replace(" ", "")
    assert "messages" not in input_json  # no content fields serialized
```

Note: `TranscriptInfo` has no `messages`/`events` fields, so the last assert guards against accidental future widening.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/scanner/test_streaming_seam.py -v`
Expected: FAIL (`"transcript_handle"` not a valid input name / returns None)

- [ ] **Step 3: Implement**

In `types.py`: add `TranscriptInfo` to `ScannerInput` union; add `"transcript_handle"` to `ScannerInputNames`.

In `util.py`, at the TOP of the isinstance chain (before `Transcript`, since `Transcript` subclasses `TranscriptInfo` — order matters in reverse: check `Transcript` first, then `TranscriptInfo`):

```python
    if isinstance(loader_result, Transcript):
        return ("transcript", [loader_result.transcript_id])
    elif isinstance(loader_result, TranscriptInfo):
        return ("transcript_handle", [loader_result.transcript_id])
```

In `result.py` `_serialize_input`: `"transcript_handle"` falls into the existing `not in ("transcript", "events")` branch (plain `to_json_str_compact`) — verify that's already correct and add the input_type to no special-casing; just extend the docstring.

- [ ] **Step 4: Run tests + existing scanner tests**

Run: `.venv/bin/pytest tests/scanner/ -v -x`
Expected: all PASS

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/_scanner/
git add src/inspect_scout/_scanner tests/scanner/test_streaming_seam.py
git commit -m "feat: transcript_handle scanner input type (info-only result serialization)"
```

---

### Task 7: Scan-pipeline seam — `ScannerJob` handle + `_parse_function` switch + error containment

**Files:**
- Modify: `src/inspect_scout/_concurrency/common.py` (`ScannerJob`)
- Modify: `src/inspect_scout/_scan.py` (`_parse_function` at :582, `_scan_one` at :926)
- Modify: `src/inspect_scout/_scanner/scanner.py` (add `SCANNER_ACCEPTS_HANDLE_ATTR = "___scanner_accepts_handle___"` next to `SCANNER_CONTENT_ATTR` at :65)
- Test: `tests/scanner/test_streaming_seam.py` (extend)

**Interfaces:**
- Consumes: `TranscriptHandle`, `MaterializedTranscriptHandle` (Task 4), `TranscriptsReader.open()` (Task 5), input plumbing (Task 6).
- Produces:
  - `ScannerJob.union_transcript: Transcript | TranscriptHandle` (rename NOT needed; widen the type; update docstring).
  - `_parse_function` behavior:
    - Compute `streaming_eligible = all scanners in job have SCANNER_ACCEPTS_HANDLE_ATTR set on their scan fn AND union_content.timeline is None AND union_content.events is None`. (Events excluded in phase 1: streaming is messages-only per spec.)
    - If eligible: `handle_cm = await reader.open(job.transcript_info, union_content)`; enter it; put the handle in `ScannerJob`. The backend's threshold decides spooled-vs-materialized internally — `_parse_function` doesn't check size itself.
    - Else: current `reader.read(...)` path unchanged.
    - Handle lifetime: the handle must be closed after the LAST scanner job for the transcript completes. Followers share the lead's handle. Close in `record_results` wrapper or attach `aclose` to the lead job completion — implement by having `_scan_one` close the handle when the job has no followers remaining: simplest correct approach: the lead's `followers` tuple is scanned after lead completes; close the handle after all follower jobs complete. Since strategies control scheduling, attach the CM exit to a completion counter: add `handle_close: Callable[[], Awaitable[None]] | None = None` field to `ScannerJob`; the strategy already calls `record_results` once per ScannerJob — wrap: parse_function counts jobs (1 lead + N followers), and each `_scan_one` completion decrements via closure; on zero, `await handle.aclose()`. Keep the counter in the closure created inside `_parse_function` (single-process worker context — no cross-process concerns; handles never cross processes).
  - `_scan_one` behavior:
    - `job.union_transcript` may be a handle. If the scanner accepts handles (has the attr), pass the handle directly to the scanner, bypassing the loader: `loader_iterations = _single(handle)`. Else (only reachable when handle is materialized-capable): `transcript = await handle.load()` then existing loader path.
    - `transcript_id` for `Error` construction: use `job.union_transcript.transcript_id` if `Transcript` else `job.union_transcript.info.transcript_id` — add a small helper `_job_transcript_id(job)`.
    - **Error containment:** wrap the `async for loader_result in loader(...)` iteration itself (and handle iteration) in try/except: stream-raised exceptions (corrupt JSON surfacing lazily) become an `Error` report attributed as a parse error, matching `_reports_for_parse_error` semantics, and `_scan_one` returns normally. `PrerequisiteError` still re-raises. Implement by restructuring: get the iterator, loop with explicit `try: loader_result = await anext(it)` / `except StopAsyncIteration: break` / `except PrerequisiteError: raise` / `except Exception as ex: results.append(<error report>); break`.
    - `ResultReport.input` for handle scans = `handle.info` (Task 6).

- [ ] **Step 1: Write failing tests (extend test_streaming_seam.py)**

```python
import pytest

from inspect_scout import scanner
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import SCANNER_ACCEPTS_HANDLE_ATTR


@pytest.mark.asyncio
async def test_scan_one_with_handle_scanner(tmp_path: Path) -> None:
    """A handle-accepting scanner receives the handle and results record info-only."""
    from inspect_scout._concurrency.common import ScannerJob
    from inspect_scout._scan import _scan_one
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.types import Transcript, TranscriptInfo

    info = TranscriptInfo(transcript_id="t1")
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    async def load_fn() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load_fn, info)

    @scanner(messages="all")
    def handle_scanner():  # type: ignore[no-untyped-def]
        async def scan(transcript: Transcript) -> Result:
            return Result(value="ok")

        setattr(scan, SCANNER_ACCEPTS_HANDLE_ATTR, True)
        return scan

    s = handle_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="hs")
    reports = await _scan_one(job, validation=None, fail_on_error=True)
    assert len(reports) == 1
    assert reports[0].input_type == "transcript_handle"
    assert reports[0].input == info  # info only, no content


@pytest.mark.asyncio
async def test_scan_one_stream_error_contained(tmp_path: Path) -> None:
    """Errors raised during handle iteration produce an Error report, not a crash."""
    from inspect_scout._concurrency.common import ScannerJob
    from inspect_scout._scan import _scan_one
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.types import Transcript, TranscriptInfo

    info = TranscriptInfo(transcript_id="t1")

    async def failing_load() -> Transcript:
        raise ValueError("corrupt sample JSON")

    handle = MaterializedTranscriptHandle(failing_load, info)

    @scanner(messages="all")
    def plain_scanner():  # type: ignore[no-untyped-def]
        async def scan(transcript: Transcript) -> Result:
            return Result(value="ok")

        return scan

    s = plain_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="ps")
    reports = await _scan_one(job, validation=None, fail_on_error=False)
    assert len(reports) == 1
    assert reports[0].error is not None
    assert "corrupt sample JSON" in reports[0].error.error
```

(Exact `scanner`/`Result` import paths and `Result` constructor: check `src/inspect_scout/__init__.py` exports and `_scanner/result.py::Result` fields; adjust `Result(value="ok")` if `value` is not the right kwarg — mirror an existing test in `tests/scanner/test_loaders.py`.)

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/scanner/test_streaming_seam.py -v`
Expected: new tests FAIL (ScannerJob type error / _scan_one crashes)

- [ ] **Step 3: Implement** per the Produces block. Order: `scanner.py` attr constant → `common.py` type widening → `_scan.py` `_scan_one` restructure → `_scan.py` `_parse_function` switch + handle-close counter.

- [ ] **Step 4: Run the full scanner + scan test suites**

Run: `.venv/bin/pytest tests/scanner tests/scan -v 2>/dev/null || .venv/bin/pytest tests/scanner -v`
Expected: all PASS (check whether a `tests/scan/` dir exists; also run `.venv/bin/pytest tests/ -k "scan" -x` for scan-pipeline integration tests)

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/
git add -A src/inspect_scout tests/scanner/test_streaming_seam.py
git commit -m "feat: streaming handle seam in scan pipeline with error containment"
```

---

### Task 8: Streaming segmenter (`segment_messages_stream`)

**Files:**
- Modify: `src/inspect_scout/_transcript/messages.py`
- Test: `tests/transcript/test_messages.py` (extend)

**Interfaces:**
- Consumes: `MessagesSegment` dataclass (`messages.py:78-89`), `_effective_segment_budget`, `_COUNT_*` constants.
- Produces:

```python
async def segment_messages_stream(
    source: AsyncIterator[ChatMessage],
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    prompt_reserve: int | float = 0.2,
) -> AsyncIterator[MessagesSegment]:
```

Behavior: incremental version of `segment_messages`' three passes — consume messages one at a time; render each (`messages_as_str([msg])`, sequential — numbering ordering matters); accumulate rendered chunks up to `chunk_char_target` (same formula, `messages.py:174-179`); when a chunk closes, count its tokens (`model.count_tokens`, serialized — no cross-segment batching; acceptable per spec analysis); when accumulated tokens would exceed `effective_budget`, yield a `MessagesSegment` and release its chunks. Yield the final partial segment. Empty renders skipped as today (`messages.py:166`). Segment counter increments across yields.

- [ ] **Step 1: Write failing tests (append to tests/transcript/test_messages.py — follow the file's existing fixtures for mock models; check how existing `segment_messages` tests stub `count_tokens`, reuse that pattern)**

```python
@pytest.mark.asyncio
async def test_segment_messages_stream_equivalence() -> None:
    """Streamed segmentation produces the same segments as batch for same input."""
    # Use the same mock model + messages fixture as the existing
    # segment_messages tests in this file. Build ~20 messages, budget such
    # that batch mode yields >= 3 segments; assert streamed yields segments
    # with identical messages_str concatenation and identical message ids
    # per segment boundary tolerance: identical unless chunk-packing differs;
    # assert the CONCATENATION of all segments' messages equals the input
    # order and every segment's token count <= budget (the hard contract),
    # not byte-identical boundaries.


@pytest.mark.asyncio
async def test_segment_messages_stream_releases_early() -> None:
    """First segment is yielded before the source iterator is exhausted."""
    yielded_before_exhaustion = False

    async def source() -> AsyncIterator[ChatMessage]:
        # yield enough messages for 2+ segments; set a flag consumer can check
        ...

    # consume one segment from segment_messages_stream(source(), ...) then
    # assert the source has NOT been fully consumed (track via counter).
```

Write these concretely against the file's existing test scaffolding (it has mock-model helpers; find `get_model("mockllm/model")` usage or a `count_tokens` stub in `tests/transcript/test_messages.py` and reuse).

- [ ] **Step 2: Run to verify failure** — `.venv/bin/pytest tests/transcript/test_messages.py -v -k stream` → FAIL (name not defined)

- [ ] **Step 3: Implement `segment_messages_stream`** in `messages.py` (place directly after `segment_messages`).

- [ ] **Step 4: Run** — `.venv/bin/pytest tests/transcript/test_messages.py -v` → all PASS

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/_transcript/messages.py
git add src/inspect_scout/_transcript/messages.py tests/transcript/test_messages.py
git commit -m "feat: streaming message segmentation"
```

---

### Task 9: `llm_scanner` — accept handle, streaming segmentation, bounded concurrency

**Files:**
- Modify: `src/inspect_scout/_llm_scanner/_llm_scanner.py`
- Test: `tests/llm_scanner/test_streaming_segments.py` (check dir name: `ls tests/` for where llm_scanner tests live — adjust path to the existing convention, e.g. `tests/scanner/test_llm_scanner*.py`)

**Interfaces:**
- Consumes: `TranscriptHandle` (Task 4), `segment_messages_stream` (Task 8), `SCANNER_ACCEPTS_HANDLE_ATTR` (Task 7).
- Produces: `llm_scanner`'s inner `scan` signature becomes `async def scan(transcript: Transcript | TranscriptHandle) -> Result:`.

Behavior:
1. At the top of `scan`: derive `info: TranscriptInfo` (`transcript.info` if handle else `transcript`) and a `full_transcript_needed` flag = any of `question`/`template_variables` is callable, or `preprocessor` requires full content, or `timeline is not None`, or the transcript has timelines/events content (handle path is messages-only by seam construction). If handle AND full_transcript_needed → `transcript = await transcript.load()` and proceed exactly as today.
2. Template rendering context: `_resolve_template_kwargs` accesses only `TranscriptInfo` fields (`date`, `task_set`, ... — verify tail of `_resolve_template_kwargs`, `_llm_scanner.py:350+`) → pass `info` for handle scans. `_template_overhead_tokens` takes the same — pass a content-empty `Transcript.model_construct(**info.model_dump(), messages=[], events=[])` where a `Transcript` type is structurally required.
3. Handle + messages path: replace the `segments = [...]` + `tg_collect` block (`_llm_scanner.py:306-321`) with a bounded window:

```python
        window = anyio.Semaphore(_SEGMENT_CONCURRENCY)  # module const = 4
        results: list[tuple[str | None, Result]] = []

        async def scan_bounded(seg: MessagesSegment) -> None:
            try:
                result = await scan_segment(seg.messages_str)
                results.append((None, result))
            finally:
                window.release()

        async with anyio.create_task_group() as tg:
            async for seg in segment_messages_stream(
                handle.messages(),
                messages_as_str=messages_as_str_fn,
                model=resolved_model,
                context_window=context_window,
                prompt_reserve=template_tokens,
            ):
                await window.acquire()
                tg.start_soon(scan_bounded, seg)
```

    Results ordering: `aggregate_results` receives `(span_id, Result)` pairs; for the messages-only path span_id is always None — verify whether `aggregate_results` is order-sensitive (read `_llm_scanner/_reducer.py::aggregate_results`); if order matters, carry `seg.segment` index and sort before aggregating.
4. Materialized path (Transcript input): keep the existing code but ALSO apply the bounded window (replacing unbounded `tg_collect`) — that half of the memory fix applies to all llm_scanner scans.
5. After constructing `scan`, set the capability attr **only when no full-transcript callables are configured**:

```python
    if not callable(question) and not callable(template_variables) and preprocessor is None and timeline is None:
        setattr(scan, SCANNER_ACCEPTS_HANDLE_ATTR, True)
```

    (preprocessor operates on message lists — check `MessagesPreprocessor` usage in `message_numbering`; if it only ever receives per-segment message lists, it is streaming-safe and should NOT block the attr — verify and adjust.)

- [ ] **Step 1: Write failing tests** — using `mockllm/model` (existing llm_scanner test conventions — find them via `grep -rl "llm_scanner" tests/`), cover: (a) handle-input scan over a `MaterializedTranscriptHandle` with a few messages produces a Result equal to the Transcript-input scan of the same content; (b) an llm_scanner with `question=lambda t: ...` does NOT get the capability attr; (c) static-config llm_scanner DOES get the attr; (d) bounded window: with 6 segments and `_SEGMENT_CONCURRENCY=2`, at most 2 `generate` calls in flight (track via mock model counter).

- [ ] **Step 2: Run to verify failure**

- [ ] **Step 3: Implement** per behavior block.

- [ ] **Step 4: Run all llm_scanner tests + scanner suite** — `.venv/bin/pytest tests/ -k "llm_scanner" -v && .venv/bin/pytest tests/scanner -q`

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/_llm_scanner/
git add -A src/inspect_scout/_llm_scanner tests/
git commit -m "feat: llm_scanner streaming segmentation with bounded concurrency"
```

---

### Task 10: Memory regression test

**Files:**
- Create: `tests/transcript/test_streaming_memory.py`

**Interfaces:** Consumes everything above.

- [ ] **Step 1: Write the test** (this test is the deliverable; no TDD split)

```python
"""Memory regression: streamed reads stay bounded on large synthetic samples."""

from __future__ import annotations

import io
import json
import tracemalloc
from pathlib import Path

import pytest

from inspect_scout._transcript.handle import SpooledTranscriptHandle
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool
from inspect_scout._transcript.types import Transcript, TranscriptInfo

# ~50 MB of events, ~100 KB of messages: a scan requesting messages only
# must not pay for the events.
N_EVENTS = 5_000
EVENT_PAYLOAD = "x" * 10_000


def _build_sample() -> bytes:
    sample = {
        "id": "big",
        "messages": [
            {"id": f"m{i}", "role": "user", "content": f"msg {i}"}
            for i in range(100)
        ],
        "events": [
            {"event": "info", "timestamp": float(i), "data": EVENT_PAYLOAD}
            for i in range(N_EVENTS)
        ],
        "attachments": {},
    }
    return json.dumps(sample).encode()


@pytest.mark.asyncio
async def test_streamed_messages_read_bounded(tmp_path: Path) -> None:
    data = _build_sample()
    assert len(data) > 45 * 1024 * 1024

    tracemalloc.start()
    result = await stream_parse_to_spool(io.BytesIO(data), "all", None, tmp_path)
    try:
        from inspect_scout._transcript.json.stream_parse import replay_messages

        count = sum(1 for _ in replay_messages(result))
        assert count == 100
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        result.close()

    # Materializing this sample costs > len(data) (~50 MB) in dicts alone.
    # The streamed path must stay far below: budget 16 MB.
    assert peak < 16 * 1024 * 1024, f"peak {peak / 1024 / 1024:.1f} MB"
```

Mark it `@pytest.mark.slow` if the repo has that convention (check `pyproject.toml` markers); the build takes seconds.

- [ ] **Step 2: Run** — `.venv/bin/pytest tests/transcript/test_streaming_memory.py -v` → PASS (if peak exceeds budget, investigate before loosening: the most likely leak is `ijson` buffering or the sink adapters retaining items)

- [ ] **Step 3: Commit**

```bash
git add tests/transcript/test_streaming_memory.py
git commit -m "test: memory regression for streamed transcript reads"
```

---

### Task 11: FastAPI search endpoint

**Files:**
- Modify: `src/inspect_scout/_view/_api_v2_search.py:234-264`
- Test: extend the existing search endpoint tests (find via `grep -rl "_api_v2_search\|/search" tests/`)

**Interfaces:** Consumes `TranscriptsView.open()` (Task 5), handle-accepting `llm_scanner` (Task 9).

Behavior: for `LlmSearchRequest` (the non-grep branch), replace read-then-scan with:

```python
        async with transcripts_view(transcript_dir) as view:
            condition = Column("transcript_id") == id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(status_code=404, detail="Transcript not found")
            content = TranscriptContent(messages=request.messages, events=request.events)
            if isinstance(request, GrepSearchRequest):
                transcript = await view.read(infos[0], content)
                output = await grep_scanner(...)(transcript)
            else:
                async with await view.open(infos[0], content) as handle:
                    try:
                        output = await llm_scanner(
                            question=request.query,
                            answer="string",
                            template=LLM_SEARCH_TEMPLATE,
                            model=request.model,
                            reducer=ResultReducer.llm(model=request.model),
                        )(handle)
                    except Exception as err:
                        raise HTTPException(status_code=502, detail=str(err)) from err
```

Note the scan must now run **inside** the view/handle context (today it runs after the view exits — the handle needs the view's resources). When `request.events` is set, `view.open()`'s backend threshold logic still applies but llm_scanner will `load()` (events content → full path) — correct, just not memory-improved.

- [ ] **Step 1: Write/extend failing test** — LLM search over a fixture transcript returns the same `SearchResponse.result` shape as before (existing tests should mostly cover this; add one asserting the streamed path is exercised by forcing `STREAMING_THRESHOLD_BYTES=0` via monkeypatch and confirming the search still succeeds).

- [ ] **Step 2: Run to verify failure/behavior**

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run view/search tests** — `.venv/bin/pytest tests/ -k "search or api_v2" -v`

- [ ] **Step 5: Typecheck and commit**

```bash
.venv/bin/mypy src/inspect_scout/_view/
git add src/inspect_scout/_view/_api_v2_search.py tests/
git commit -m "feat: LLM search endpoint uses streaming transcript handle"
```

---

### Task 12: Parquet `open()`

**Files:**
- Modify: `src/inspect_scout/_transcript/database/parquet/transcripts.py`
- Test: `tests/transcript/database/` (extend the parquet read tests — find `test_parquet_db.py` read-path tests)

**Interfaces:** Consumes `SpooledTranscriptHandle`, `stream_parse_to_spool` (Tasks 2–4).

Behavior: `ParquetTranscriptsDB.open()` overrides the default. For messages-only content where the summed requested-column sizes exceed `STREAMING_THRESHOLD_BYTES` (size via the existing `_get_content_size` helper, `transcripts.py:748`): build a `SpooledTranscriptHandle` whose `parse` callable fetches the JSON cells (existing `fetchone` logic) and runs `stream_parse_to_spool` over the synthesized `{"messages": ..., "events": ...}` byte stream (reuse the `stream_content_bytes` chunking generator, `transcripts.py:812-838`). Documented floor: the fetched cell strings are ~1× content in memory during parse (spec non-goal to fix). Below threshold or non-messages-only: `MaterializedTranscriptHandle` over `read()`. No attachments section in parquet; `events_data` pools spool as in Task 2.

- [ ] **Step 1: Write failing test** — parquet DB with a few transcripts: `open()` + `messages()` equals `read().messages` (mirror Task 5's equivalence test but against a temp parquet DB built with `ParquetTranscriptsDB.insert()`; copy DB-construction scaffolding from `tests/transcript/test_parquet_db.py`). Force threshold 0 to exercise the spooled path.

- [ ] **Step 2: Run to verify failure**

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run parquet tests** — `.venv/bin/pytest tests/transcript -k parquet -v`

- [ ] **Step 5: Full check and commit**

```bash
make check && .venv/bin/pytest tests/transcript tests/scanner -q
git add -A src/inspect_scout/_transcript/database tests/
git commit -m "feat: parquet transcripts streaming open()"
```

---

## Final verification (after all tasks)

- [ ] `make check` — clean
- [ ] `.venv/bin/pytest` — full suite green
- [ ] Manual smoke: `scout` LLM search against a large local eval log (if one is available) — memory observed bounded via `psutil`/`top`
- [ ] Review spec non-goals still hold (no timeline streaming, no parquet cell splitting, reducer overflow documented as follow-up)
