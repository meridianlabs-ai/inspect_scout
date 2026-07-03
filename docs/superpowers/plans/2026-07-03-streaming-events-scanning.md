# Streaming Events Scanning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** llm_scanner scans events-content on huge agentic transcripts with bounded memory (O(structure + selected context windows)) instead of full materialization.

**Architecture:** Two-pass "stub skeleton" over the multi-shot `TranscriptHandle`: pass 1 streams `handle.events()` keeping only stub events (structure + classification signals; ModelEvent bulk stripped, prompts interned), runs the *unchanged* `timeline_build` → `_walk_spans` pipeline on the stubs, and computes the set of ModelEvent UUIDs whose full content is actually needed; pass 2 re-streams collecting only those events and substitutes them into the stub tree; the existing `timeline_messages` → segmentation → bounded scanning back half then runs verbatim.

**Tech Stack:** Python 3.10+, pydantic v2 (`model_copy`), inspect_ai event models, anyio, pytest.

**Spec:** `docs/superpowers/specs/2026-07-03-streaming-events-scanning-design.md`
**Branch:** work directly on `feature/streaming-transcript-reads` (this extends PR #491 — no new branch).

## Global Constraints

- Use the venv directly with `PYTHONPATH=$PWD/src` prefix: `PYTHONPATH=$PWD/src .venv/bin/pytest ...`, `PYTHONPATH=$PWD/src .venv/bin/mypy ...`. Never `uv run`/`uv sync`.
- Strict typing, all functions annotated including tests. mypy + ruff check + ruff format clean before every commit.
- The batch pipeline (`timeline_build`, `_walk_spans`, `timeline_messages`, `span_messages`) must NOT be modified — fidelity comes from running it unchanged on stubs. (inspect_ai is a separate repo; never edit it.)
- Selection rule (from spec + code reading): needed full ModelEvents = last ModelEvent per kept compaction region (per scannable span) **plus** the first ModelEvent after each kept `trim`-type CompactionEvent (its `.input` is read by `_trim_prefix`, `messages.py:628-633`).
- uuid-less ModelEvent rule: if any *needed* ModelEvent lacks a `uuid`, raise `_StubSkeletonUnsupported` and fall back to the materialized path (`handle.load()`) for that transcript. Never silently mis-select.
- Timelines (`timeline=` content / stored timelines) stay materialized — out of scope.
- Known pre-existing failures in tests/observe and tests/sources/{langsmith,logfire,phoenix,weave}_source (stale openai in venv) — ignore.
- Never commit `docs/plans/` or `docs/superpowers/` documents.

## File Structure

```
src/inspect_scout/_transcript/timeline_stream.py   (NEW: stub reducer, selection, two-pass orchestration)
src/inspect_scout/_llm_scanner/_llm_scanner.py     (MODIFY: route handle+events through stream path)
src/inspect_scout/_scan.py                         (MODIFY: _streaming_eligible allows events)
tests/transcript/fixtures_agentic.py               (NEW: synthetic multi-agent event-list builder)
tests/transcript/test_timeline_stream.py           (NEW: stub/selection/fidelity tests)
tests/transcript/test_streaming_memory.py          (MODIFY: events-heavy regression)
tests/scan/test_streaming_seam.py                  (MODIFY: eligibility)
tests/llm_scanner/test_streaming.py                (MODIFY: events-config attr + e2e equivalence)
```

Commits go directly on `feature/streaming-transcript-reads`; push at the end.

---

### Task 1: Synthetic multi-agent event fixture

**Files:**
- Create: `tests/transcript/fixtures_agentic.py`
- Test: `tests/transcript/test_timeline_stream.py` (first tests)

**Interfaces:**
- Produces: `def agentic_events(*, big_payload: str = "x" * 200) -> list[Event]` — a deterministic event list exercising every classification path the spec names, and `def agentic_transcript(events: list[Event] | None = None) -> Transcript` wrapping them (`Transcript.model_construct(transcript_id="agentic-1", messages=[], events=..., timelines=[], metadata={})`).

The event list must contain (build with real inspect_ai constructors — study how `tests/transcript/test_messages.py` and `tests/transcript/test_timeline_repr.py` construct `ModelEvent`/`SpanBeginEvent`/`SpanEndEvent`/`ToolEvent`/`CompactionEvent`; reuse their helper style):
1. Top-level `solvers` span containing a `type="agent"` span "main" with: 3 ModelEvents (system prompt "MAIN", tool_calls on the middle one), interleaved ToolEvents whose `result`/`arguments` contain `big_payload`.
2. A nested `type="agent"` span "sub" inside main: 2 ModelEvents with system prompt "SUB" and a ToolEvent between them (single tool-calling turn shape → utility candidate: give it a DIFFERENT prompt from parent and make it NOT tool_invoked so `_classify_utility_agents` marks it utility) AND a second nested agent span "sub2" with 3 ModelEvents, same prompt as parent, multi-turn (NOT utility — must be scanned).
3. A `type="solver"` primitive span (e.g. "generate") with one ModelEvent — gets unrolled into parent.
4. A `type="tool"` span containing a ModelEvent (tool-spawned agent → agent span per `_is_agent_span`).
5. One foreign-prompt helper ModelEvent directly in main (different system prompt, no tool_calls → `_wrap_utility_events` wraps it).
6. Two `CompactionEvent`s in main: one `type="summary"`, one `type="trim"`, with ModelEvents before/after each (so regions exist and the trim-first-event rule is exercised).
7. Every ModelEvent has a distinct `uuid` and distinct final assistant output text (so segment equivalence can detect selection mistakes).

- [ ] **Step 1: Write a smoke test that the fixture classifies as intended**

```python
"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from inspect_ai.event import timeline_build

from tests.transcript.fixtures_agentic import agentic_events


def test_agentic_fixture_classification() -> None:
    """The fixture must exercise the classification paths the spec names."""
    from inspect_scout._transcript.timeline import _walk_spans

    tree = timeline_build(agentic_events())
    spans = list(_walk_spans(tree.root, depth=None))
    names = [s.name for s in spans]
    # main agent, sub2 (non-utility nested agent), and the tool-spawned agent
    # are scannable; "sub" (utility) and the wrapped helper are NOT.
    assert "main" in names
    assert "sub2" in names
    assert "sub" not in names
    utility_spans = _collect_utility(tree.root)
    assert len(utility_spans) >= 2  # "sub" + wrapped foreign-prompt helper
```

(Include a small local `_collect_utility` walker in the test file.)

- [ ] **Step 2: Run to verify it fails** — `PYTHONPATH=$PWD/src .venv/bin/pytest tests/transcript/test_timeline_stream.py -v` → FAIL (fixtures module missing)

- [ ] **Step 3: Implement `fixtures_agentic.py`** — iterate until the smoke test's classification assertions hold (this pins the fixture's semantics; expect a few rounds tuning prompts/spans against `timeline_build`'s rules).

- [ ] **Step 4: Run to verify pass** — same command → PASS

- [ ] **Step 5: Typecheck + commit**

```bash
PYTHONPATH=$PWD/src .venv/bin/mypy tests/transcript/fixtures_agentic.py tests/transcript/test_timeline_stream.py
git add tests/transcript/fixtures_agentic.py tests/transcript/test_timeline_stream.py
git commit -m "test: synthetic multi-agent event fixture for streaming events scanning"
```

---

### Task 2: Event stubbing (pass-1 reducer primitives)

**Files:**
- Create: `src/inspect_scout/_transcript/timeline_stream.py`
- Test: `tests/transcript/test_timeline_stream.py` (extend)

**Interfaces:**
- Produces:
  - `class _PromptInterner:` — `def intern(self, s: str) -> str` returning a canonical instance (dict-backed).
  - `def stub_event(event: Event, interner: _PromptInterner) -> Event` — returns the event unchanged for small types; for `ModelEvent` and `ToolEvent` returns a stripped `model_copy`.
  - `class _StubSkeletonUnsupported(Exception)` — raised when the skeleton cannot faithfully represent the transcript (used later for uuid-less fallback).

Stubbing rules (spec):
- `ModelEvent` → `event.model_copy(update={...})` keeping `uuid`, `span_id`, timestamps and: `input` reduced to only its `ChatMessageSystem` entries with `content` interned (string content; for list content intern the joined text via a rebuilt ChatMessageSystem — check `_get_system_prompt_for_event` in inspect_ai `_timeline.py:1124-1140`: it reads `msg.content` str or parts' `.text`, so preserving the system message as-is but interned-where-string is sufficient); `output` reduced so `_has_tool_calls` (`_timeline.py:1143-1149`: `output.choices[0].message.tool_calls`) is preserved — keep `choices[0].message.tool_calls` and empty the message `content`; drop other choices; `tools=[]`, `call=None`, `config` left (small), `error`/`traceback` kept (small strings).
- `ToolEvent` → `model_copy(update={"arguments": {}, "result": "", "events": [], "view": None})` — everything else kept (`agent`, `agent_span_id`, `function`, `id`, ... are what `_is_agent_span`/`_extract_agent_results` read).
- `CompactionEvent`, `SpanBeginEvent`, `SpanEndEvent`, `BranchEvent`, `AnchorEvent` → unchanged.
- Everything else → unchanged (they are positional only; if a later memory test shows a bulk carrier, strip it then — keep-by-default per spec).

- [ ] **Step 1: Write failing tests**

```python
def test_stub_model_event_preserves_classification_signals() -> None:
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    events = agentic_events(big_payload="y" * 100_000)
    interner = _PromptInterner()
    for ev in events:
        stub = stub_event(ev, interner)
        assert stub.uuid == ev.uuid and stub.span_id == ev.span_id
        if isinstance(ev, ModelEvent):
            assert _get_system_prompt_for_event(stub) == _get_system_prompt_for_event(ev)
            assert _has_tool_calls(stub) == _has_tool_calls(ev)
            assert "y" * 1000 not in stub.model_dump_json()
        if isinstance(ev, ToolEvent):
            assert stub.agent == ev.agent and stub.function == ev.function
            assert "y" * 1000 not in stub.model_dump_json()


def test_prompt_interning_shares_instances() -> None:
    from inspect_scout._transcript.timeline_stream import _PromptInterner

    interner = _PromptInterner()
    a = interner.intern("p" * 10_000)
    b = interner.intern("p" * 10_000)
    assert a is b
```

(import `_get_system_prompt_for_event`/`_has_tool_calls` from `inspect_ai.event._timeline` — private but stable enough for tests; if import fails, replicate their 6-line logic locally in the test.)

- [ ] **Step 2: Verify fail** → ImportError
- [ ] **Step 3: Implement** the module (docstring explains the two-pass skeleton design and links the spec)
- [ ] **Step 4: Verify pass**
- [ ] **Step 5: Typecheck + commit** — `git commit -m "feat: event stubbing primitives for streaming events skeleton"`

---

### Task 3: Needed-event selection

**Files:**
- Modify: `src/inspect_scout/_transcript/timeline_stream.py`
- Test: `tests/transcript/test_timeline_stream.py` (extend)

**Interfaces:**
- Consumes: `TimelineSpan` tree from `timeline_build(stubs)`; `_walk_spans` from `_transcript/timeline.py`.
- Produces: `def needed_model_event_uuids(root: TimelineSpan, *, compaction: Literal["all", "last"] | int, depth: int | None) -> set[str]` — walks scannable spans exactly like `timeline_messages` (`_walk_spans(root, depth=depth)`), and per span mirrors `span_messages`' kept-region logic (`messages.py:566-655`): normalize compaction to n; slice regions; select last ModelEvent per kept region PLUS first ModelEvent after each kept `trim`-type CompactionEvent. Raises `_StubSkeletonUnsupported` if a selected ModelEvent has `uuid is None`.

The property to pin: **selection is exactly the set of ModelEvents whose content `span_messages` touches.** Test this by construction rather than reimplementation-vs-reimplementation:

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.parametrize("compaction", ["all", "last", 2])
def test_selection_covers_span_messages_reads(compaction) -> None:
    """Every ModelEvent whose data span_messages uses is selected."""
    from inspect_scout._transcript.timeline_stream import needed_model_event_uuids

    events = agentic_events()
    tree = timeline_build(events)
    needed = needed_model_event_uuids(tree.root, compaction=compaction, depth=None)

    # Blank out every non-selected ModelEvent's content; span_messages output
    # over scannable spans must be unchanged.
    blanked = [
        _blank_model_event(e)
        if isinstance(e, ModelEvent) and e.uuid not in needed
        else e
        for e in events
    ]
    blanked_tree = timeline_build(blanked)
    for span, blanked_span in zip(
        _walk_spans(tree.root, depth=None),
        _walk_spans(blanked_tree.root, depth=None),
        strict=True,
    ):
        assert _dump(span_messages(span, compaction=compaction)) == _dump(
            span_messages(blanked_span, compaction=compaction)
        )


def test_selection_uuidless_raises() -> None:
    from inspect_scout._transcript.timeline_stream import (
        _StubSkeletonUnsupported,
        needed_model_event_uuids,
    )
    events = agentic_events()
    # strip a uuid from a needed event (the last ModelEvent)
    events = [e.model_copy(update={"uuid": None}) if e is _last_model_event(events) else e for e in events]
    tree = timeline_build(events)
    with pytest.raises(_StubSkeletonUnsupported):
        needed_model_event_uuids(tree.root, compaction="last", depth=None)
```

(Local helpers `_blank_model_event` — content emptied, tool_calls/system preserved so classification is identical; `_dump` — `[m.model_dump() for m in msgs]`; `_last_model_event`.)

- [ ] **Step 2: Verify fail** → ImportError
- [ ] **Step 3: Implement** `needed_model_event_uuids`
- [ ] **Step 4: Verify pass** (all compaction parametrizations)
- [ ] **Step 5: Typecheck + commit** — `git commit -m "feat: needed-event selection for streaming events skeleton"`

---

### Task 4: Two-pass orchestration + end-to-end fidelity

**Files:**
- Modify: `src/inspect_scout/_transcript/timeline_stream.py`
- Test: `tests/transcript/test_timeline_stream.py` (extend)

**Interfaces:**
- Consumes: `TranscriptHandle` (multi-shot `events()`), `stub_event`, `needed_model_event_uuids`, `timeline_messages` from `_transcript/timeline.py`, `MessagesAsStr`.
- Produces:

```python
async def stream_timeline_messages(
    handle: TranscriptHandle,
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    prompt_reserve: int | float = 0.2,
) -> AsyncIterator[TimelineMessages]:
```

Behavior: pass 1 — `async for ev in handle.events(): stubs.append(stub_event(ev, interner))`; `tree = timeline_build(stubs)`; `needed = needed_model_event_uuids(tree.root, compaction=compaction, depth=depth)` (may raise `_StubSkeletonUnsupported` — propagate; caller falls back). Pass 2 — `async for ev in handle.events():` collect full ModelEvents with `ev.uuid in needed` into `full_by_uuid`. Substitute: walk the tree's `TimelineEvent` nodes; where `isinstance(node.event, ModelEvent) and node.event.uuid in full_by_uuid`, set `node.event = full_by_uuid[uuid]` (in-place mutation of the stub tree). Then `async for seg in timeline_messages(tree, messages_as_str=..., model=..., context_window=..., compaction=compaction, depth=depth, prompt_reserve=prompt_reserve): yield seg`.

- [ ] **Step 1: Write the failing fidelity test (the load-bearing test of the whole feature)**

```python
@pytest.mark.parametrize("compaction", ["all", "last", 2])
@pytest.mark.parametrize("depth", [None, 1])
async def test_stream_equals_materialized_segments(compaction, depth) -> None:
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.timeline import timeline_messages
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages

    transcript = agentic_transcript()

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load, _info(transcript))

    def numbering():  # fresh numbering scope per path
        from inspect_scout._scanner.extract import message_numbering
        return message_numbering()[0]

    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle, messages_as_str=numbering(),
            model="mockllm/model", compaction=compaction, depth=depth,
        )
    ]
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            timeline_build(transcript.events).root, messages_as_str=numbering(),
            model="mockllm/model", compaction=compaction, depth=depth,
        )
    ]
    assert streamed == materialized
```

Also run the same fidelity assertion over the real `.eval` fixtures in `tests/recorder/logs/` (events="all" content, spooled handles via threshold-0 monkeypatch on `inspect_scout._util.constants.SPOOL_THRESHOLD_BYTES`) — parametrize over the 4 logs, compaction="all", depth=None only (they may have trivial span structure; the agentic fixture carries the structural burden).

- [ ] **Step 2: Verify fail** → ImportError
- [ ] **Step 3: Implement `stream_timeline_messages`**
- [ ] **Step 4: Verify pass** (all parametrizations + eval-log fixtures)
- [ ] **Step 5: Typecheck + commit** — `git commit -m "feat: two-pass streaming timeline messages over TranscriptHandle"`

---

### Task 5: Seam + llm_scanner wiring

**Files:**
- Modify: `src/inspect_scout/_scan.py` (`_streaming_eligible`)
- Modify: `src/inspect_scout/_llm_scanner/_llm_scanner.py`
- Test: `tests/scan/test_streaming_seam.py`, `tests/llm_scanner/test_streaming.py` (extend both)

**Interfaces:**
- Consumes: `stream_timeline_messages`, `_StubSkeletonUnsupported` (Task 4); existing `scanner_supports_streaming`, `_streaming_eligible`, `_scan_segments_bounded`.
- Produces: behavior changes only —
  1. `_streaming_eligible`: drop the `events is None` requirement; keep `timeline is None` and the filters-equal-union rule (now also comparing events filters order-insensitively, same helper as messages).
  2. `llm_scanner`: the capability attr condition drops its events exclusion (static configs with events content now set `supports_streaming`; `timeline is not None` still excludes). On the handle path: if the effective content includes events, consume `stream_timeline_messages(handle, ...)` through the existing bounded window (`TimelineMessages` carries span ids — reuse the existing span-id pairing/sort). Wrap in `try/except _StubSkeletonUnsupported:` → fall back to `transcript = await handle.load()` + existing materialized path.
  3. Messages-only handle path unchanged.

- [ ] **Step 1: Write failing tests**

```python
# tests/scan/test_streaming_seam.py
def test_streaming_eligible_events_content() -> None:
    # two scanners, both events=["model","compaction","span_begin","span_end"],
    # union equal -> eligible; one scanner events=["model"] narrower -> not.


# tests/llm_scanner/test_streaming.py
def test_events_config_sets_streaming_attr() -> None:
    scan_fn = llm_scanner(question="q?", answer="boolean",
                          content=TranscriptContent(events="all"))
    assert scanner_supports_streaming_attr(scan_fn)  # adapt to real helper


async def test_handle_events_scan_equals_transcript_scan() -> None:
    # agentic_transcript() via MaterializedTranscriptHandle with events content;
    # mockllm model; assert Result equals the Transcript-input scan.


async def test_stub_unsupported_falls_back(monkeypatch) -> None:
    # monkeypatch timeline_stream.needed_model_event_uuids to raise
    # _StubSkeletonUnsupported; scan must still succeed (materialized fallback)
    # and produce the same Result.
```

(Write these against the file's existing conventions — mockllm construction, `_handle_for`, `_scan` helpers already exist in tests/llm_scanner/test_streaming.py from #491; reuse them.)

- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement** (order: `_scan.py` eligibility → llm_scanner attr condition → llm_scanner handle-events routing + fallback)
- [ ] **Step 4: Verify pass**, then run the neighbouring suites: `PYTHONPATH=$PWD/src .venv/bin/pytest tests/scan tests/llm_scanner tests/scanner -q` → all pass
- [ ] **Step 5: Typecheck + commit** — `git commit -m "feat: streaming events scanning through the scan seam and llm_scanner"`

---

### Task 6: Memory regression + e2e

**Files:**
- Modify: `tests/transcript/test_streaming_memory.py`
- Modify: `tests/scan/` e2e streaming test file (find the Task-C e2e test from #491; extend alongside it)

**Interfaces:** consumes everything above.

- [ ] **Step 1: Write the events-heavy memory test**

```python
@pytest.mark.slow
async def test_streamed_events_scan_bounded(tmp_path) -> None:
    """Agentic events-heavy sample: two-pass skeleton stays far below
    materialization. Bulk lives in ToolEvent results + non-selected
    ModelEvent conversations (~40 MB); selected content is small."""
    # Build a large agentic sample: reuse fixtures_agentic with
    # big_payload="x" * 500_000 and enough repeated turns to exceed 35 MB
    # serialized. Write it through stream_parse (as in the existing
    # messages-heavy test) or construct a SpooledTranscriptHandle over the
    # serialized sample JSON. Measure ONLY pass1+pass2+segmentation with
    # tracemalloc (same windowing rationale as the existing test: ijson
    # ObjectBuilder gc-cycle garbage documented there).
    # Assert peak < 12 MB where materializing the events costs > 40 MB.
    # Also assert pass-1 stub retention effectiveness: peak scales with
    # stub size, not payload size (double the payload, peak within 20%).
```

Write it concretely following `test_streamed_messages_read_bounded`'s structure in the same file (threshold budget derivation, slow marker, tracemalloc window comment).

- [ ] **Step 2: Extend the e2e scan test**: real `scan()` with one events-content llm_scanner (static question, mockllm) over the agentic fixture written to a temp `.eval` log (use `inspect_ai.log.write_eval_log` — check how existing fixtures were produced; if writing a log is impractical, drive through `ParquetTranscriptsDB.insert` + scan from the DB), `SPOOL_THRESHOLD_BYTES=0`, assert results recorded and `SpooledTranscriptHandle` used (spy pattern from the existing e2e test).

- [ ] **Step 3: Run** — memory test with `--runslow`, e2e, then the full suite: `PYTHONPATH=$PWD/src .venv/bin/pytest tests/ -q --ignore=tests/observe --ignore=tests/sources` → all pass; mypy + ruff clean.

- [ ] **Step 4: Commit + push + update PR**

```bash
git add -A tests
git commit -m "test: events streaming memory regression and e2e scan"
git push metr feature/streaming-transcript-reads
```

Then update the PR #491 description: move "events/timeline scans stay materialized" from non-goals to a qualified claim (events-content llm_scanner scans now stream via the two-pass stub skeleton; timelines remain materialized; memory bound O(structure + selected windows)).

---

## Final verification

- [ ] Full suite green, mypy/ruff clean (commands above)
- [ ] Fidelity parametrizations all green (compaction × depth × fixtures)
- [ ] Memory numbers recorded in the test comments (measured, not guessed)
- [ ] PR #491 description updated
