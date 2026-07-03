# Bounded-Memory Transcript Reads (Streaming) — Design

**Date:** 2026-07-01
**Status:** Draft for review

## Problem

Scanning or LLM-searching a very large transcript (multi-GB sample JSON inside an
eval log zip) OOMs. The dominant consumer, `llm_scanner`, fundamentally needs only
one context-window worth of rendered message text at a time: it segments the
transcript (`transcript_messages` → `segment_messages`), sends each segment to an
LLM, and reduces the per-segment results. Nothing in that consumption pattern
requires random access to the whole transcript.

Today the pipeline materializes everything anyway:

1. **Read amplification.** `TranscriptsView.read()`
   (`src/inspect_scout/_transcript/eval_log.py`, parquet equivalent in
   `src/inspect_scout/_transcript/database/parquet/transcripts.py`) materializes
   the full filtered transcript with ~3× copy amplification in
   `src/inspect_scout/_transcript/json/load_filtered.py`: raw dicts in
   `ParseState` + a rebuilt tree from `_resolve_attachments` (it reconstructs
   every dict/list) + validated Pydantic objects from `Transcript.model_validate`,
   all alive at peak. Parsed Python objects run ~5–10× the JSON byte size.
2. **Segment materialization.** `llm_scanner` collects
   `segments = [seg async for seg in transcript_messages(...)]` then `tg_collect`s
   *all* segments concurrently (`_llm_scanner.py:306-321`) — O(transcript) even
   after the read.
3. **Record-time re-materialization.** `ResultReport(input=loader_result)`
   embeds the full `Transcript` (`_scan.py:1014`); `_serialize_input` writes the
   whole transcript JSON into the results DB (`_scanner/result.py:213-231`), and
   in multi-process mode the report is pickled over the upstream queue.

A structural constraint shapes any fix: in the sample JSON, field order is
`messages`, …, `events`, `attachments`, `events_data` — the attachments dict and
dedup pools needed to resolve `attachment://<id>` refs and pool ranges arrive
*after* the content that references them, so strict single-pass
stream-and-emit is impossible.

## Goal

Peak memory for llm_scanner-style scans and the FastAPI LLM-search endpoint is
**O(N-in-flight × context window)**, independent of transcript size, for
messages-only content requests. Existing `Scanner[Transcript]` scanners keep
working unchanged, with no behavior or performance regression for
typical-size transcripts.

### Explicit non-goals (this phase)

- **Events/timeline scans stay materialized.** `timeline_build` and stored-timeline
  UUID resolution need the full event list. Best achievable there is O(largest
  compaction region) — noted as a phase-2 opportunity (see Deferred).
- **Parquet cell floor.** DuckDB returns a content cell as one Python string;
  the parquet backend keeps a hard floor of ~1× the stored JSON text per
  requested column. Streaming removes only the ~3× Pydantic amplification there.
  The true fix (exploded schema) is deferred.
- **LLM reducer overflow.** `ResultReducer.llm` concatenates all segment results
  into one synthesis prompt (`_llm_scanner/_reducer.py:264-275`); a 3 GB
  transcript ≈ thousands of segments overflows the reducer model's context.
  Follow-up work (hierarchical reduction or a cap); not blocking because
  per-Result memory is small.
- **Mixed scan jobs.** `_scan.py` reads the union content of all scanners on a
  transcript; one events-hungry or stream-incapable scanner in the job forces
  the materialized path for that transcript (correct, just not improved).

## Design

### 1. `TranscriptHandle`: multi-shot streaming read API

New protocol (in `_transcript/types.py` or a sibling module):

```python
class TranscriptHandle(Protocol):
    """Async context manager providing streaming access to transcript content."""

    info: TranscriptInfo

    def messages(self) -> AsyncIterator[ChatMessage]: ...
    def events(self) -> AsyncIterator[Event]: ...
    async def load(self) -> Transcript:  # memoized full materialization
        ...
```

- `TranscriptsReader` gains `open(info: TranscriptInfo, content: TranscriptContent)
  -> AsyncContextManager[TranscriptHandle]`. `read()` is reimplemented as
  `open(...)` + `load()`. The size threshold (§2) lives inside the handle
  implementation: below it, `load()` uses today's in-memory single-pass parse
  and `messages()`/`events()` iterate the loaded lists; above it, both are
  backed by the spool. Either way `load()` eliminates the existing ~3× copy
  amplification in `load_filtered.py` (in-place attachment resolution +
  incremental validation).
- **Multi-shot:** `messages()`/`events()` may be called repeatedly; each call
  opens a fresh iteration over the local spool (see §2). This is required by the
  lead/follower ScannerJob mechanism (`_scan.py:594-609`), where several scanners
  consume the same transcript, and by `load()`-after-stream fallbacks.
- **Lifetime:** the handle is an async context manager owning the spool file and
  any open zip/S3 streams, modeled on `_OwnedZipStreamContextManager`
  (`eval_log.py:92-133`) with an `aclose()` for never-entered cleanup. Bare
  async-generator finalization under anyio cancellation is explicitly not relied
  upon. Handles are lazy-opening: prefetched ScannerJobs must not pin open file
  handles (the job deque holds up to `task_count × prefetch_multiple` jobs).
- Handles never cross a process boundary (multiprocess workers create their own
  readers; only `ParseJob`/`ResultReport` cross the queue — verified against
  `design/mp.md`). Enforced with a `__reduce__` that raises.
- Non-item data (merged `sample_metadata`, `target`, `scores` — the
  `_merge_unthinned` fields) is collected during the spool pass and available on
  the handle so `load()` and info-consumers don't lose it.

### 2. Eval-log implementation: single-pass spool-and-replay

For large samples, one streaming ijson pass over the zip member:

- Filtered `messages`/`events` items are written **unresolved** as JSON lines to
  a temp spool file (per-section), reusing the existing filter coroutines in
  `json/reducer.py`.
- `attachments` and `events_data`/pool sections are spooled as they arrive:
  one append-only temp file + an offset index (`dict[key, (offset, len)]`).
  **All** attachments are spooled — refs inside pool items arrive after the
  attachments section, so ref-based filtering (today's `state.attachment_refs`
  optimization) cannot be applied. Pool items are addressed **positionally** as
  `(pool_name, index)` — pool refs are half-open ranges (`pool[start:end]`,
  `json/pool.py:15-24`), not id-keyed.
- Iteration (`messages()`/`events()`) replays the JSONL spool: `json.loads` per
  line, resolve `attachment://` refs and pool ranges via the offset index,
  validate the single item via `TypeAdapter`, yield, drop. O(one item) memory.
- Spool mechanism: plain files + in-memory offset dict by default (write-once /
  read-many; measured SQLite would also suffice at ~2.4 GB/s but adds fd/locking
  for no benefit). Spools live under the task files cache dir
  (`init_task_files_cache()`) so existing cleanup (scan `finally`, server
  `atexit`) covers them; on POSIX, unlink-after-open makes crash leaks
  impossible. An aggregate disk budget with a clear error (not silent ENOSPC)
  covers `max_transcripts`-wide concurrency (default 25, × per-process cache
  dirs in MP mode).
- **Why single-pass, not two-pass:** two ijson passes tokenize the multi-GB
  document twice, and — critically — `LocalFilesCache` has a 5 GB total budget
  and silently falls back to the remote URI when full
  (`local_files_cache.py:31, 63-70`), so for exactly the huge logs this design
  targets, a second pass could mean a second full S3 read. Single-pass
  spool-and-replay decompresses once and is field-order independent (no
  order-violation fallback needed).
- When the zip member isn't locally cached and exceeds the threshold, spool the
  member's **compressed bytes** to local disk first, then parse from there —
  never stream the same S3 bytes twice.

**Size threshold (mandatory):** `entry.uncompressed_size` is available from the
zip central directory before reading (`eval_log.py:477`). Below the threshold
(64 MB, module constant): keep today's single-pass in-memory path *including
its early-exit* (which skips the events/attachments
sections entirely for messages-only reads with no refs — `load_filtered.py:335-343`).
Above it: spool-and-replay. No fast-path regression; no spool churn for the
common case. The json5/NaN fallback (`load_filtered.py:162-164`) remains the
only true fallback; for above-threshold files it operates on the spooled local
copy.

**Known bug fixed (with regression test):** attachment refs inside
`events_data` pool items are currently left unresolved — the pool coroutines
(`_unfiltered_item_coroutine`, `reducer.py:139-166`) collect no attachment refs,
and `attachments_coroutine` only keeps refs already seen (`reducer.py:201`),
but pools arrive after attachments. The spool-everything design resolves pool
item refs correctly at replay time.

### 3. Parquet implementation

Same replay machinery over the JSON cell(s) DuckDB returns. No attachments
section exists (resolved at import; `_transcript_to_row`), so only `events_data`
needs the positional pool index; messages can stream directly off the cell
string. Floor: ~1× stored JSON text per requested column (documented; see
non-goals). `_ParquetStreamContextManager` is single-shot today
(`parquet/transcripts.py:119-124`) — multi-shot iteration retains the cell
string or re-queries.

### 4. Scan-pipeline seam: `_parse_function` / `ScannerJob`

The materialize-vs-stream decision lives in `_parse_function` (`_scan.py:582`),
**not** the Loader protocol (loaders receive an already-materialized
`Transcript`; by then it's too late).

- `ScannerJob.union_transcript: Transcript` becomes a union: materialized
  `Transcript` (legacy) or `TranscriptHandle`. Lead and followers share the
  handle; each opens its own iteration (multi-shot).
- Decision rule: stream iff `uncompressed_size > threshold` **and** every
  scanner in the ParseJob is stream-capable **and** the union content is
  messages-only. Otherwise materialize via `handle.load()` (memoized —
  one parse shared across scanners, preserving today's amortization).
- **Error containment (required):** with lazy reads, parse/JSON errors surface
  during scanner iteration instead of in `_parse_function`'s try block. Loader
  iteration in `_scan_one` (`_scan.py:967`) currently sits outside any handler,
  and `_perform_scan` would propagate to the worker task group — a single
  corrupt sample would abort the whole scan. Stream-raised errors are caught at
  the `_scan_one` boundary and converted to per-transcript Error reports with
  parse-error attribution, matching today's `_reports_for_parse_error` behavior.

### 5. Scanner opt-in: capability attr, not a new public content type

No new public `Scanner[...]` content type in this phase (the shape must survive
contact with llm_scanner first). Instead, a per-instance capability marker
(precedent: `SCANNER_CONTENT_ATTR`, `_scanner/scanner.py:372-381`) meaning
"accepts a `TranscriptHandle`". llm_scanner internally accepts
`Transcript | TranscriptHandle`.

- Per-instance matters: an llm_scanner constructed with
  `question=Callable[[Transcript], ...]` or `template_variables=fn` or
  `preprocessor` needing full content must **not** claim the capability — those
  configs force the materialized path (annotation-based dispatch is fixed at
  decoration time and cannot express this). Static-string configs (the vast
  majority, including the search endpoint) stream.
- `validate_scanner_signature` / `get_input_type_and_ids` / `ScannerInput`
  extended to accept the handle type; without the `get_input_type_and_ids`
  extension, results are silently dropped (`_scan.py:972-974`).
- A public `Scanner[TranscriptHandle]` type can be promoted later; the loader
  branch is then a thin adapter.

### 6. `ResultReport.input` for streamed scans

For handle-input scans, `ResultReport.input` is **info + ids only** (transcript
info; message ids per scanned segment), never content. `_serialize_input`
(`result.py:213-231`) gains the corresponding branch. This closes the
record-time re-materialization (full-transcript JSON into the results DB and
across the MP pickle queue). Pre-existing note: materialized `Scanner[Transcript]`
scans still serialize full content into results — unchanged here, flagged as a
follow-up.

### 7. Streaming segmentation, inside llm_scanner

Segmentation **cannot** live below the scanner seam: the token budget requires
the resolved judge model, measured template overhead
(`_template_overhead_tokens` → `_effective_segment_budget`,
`_llm_scanner.py:284-304`), and the scan-scoped `message_numbering` closure.

- New streaming variant of `segment_messages` in `_transcript/messages.py`
  consuming `AsyncIterator[ChatMessage]`: render → chunk → count → yield
  segment → release. O(one segment) memory. Global `[M#]` numbering is a
  counter; `message_numbering`'s id maps grow with messages seen (~100 MB-scale
  for millions of messages — accepted, documented).
- llm_scanner replaces `segments = [...]` + unbounded `tg_collect` with a
  bounded-concurrency window (N segments in flight, default tied to
  `max_connections`), retaining only `(span_id, Result)` pairs for
  `aggregate_results`. This bounds memory even for materialized-path scans.
- Only the messages-only branch of `transcript_messages` (`messages.py:337-344`)
  streams; timelines/events branches require materialization (non-goal). This is
  llm_scanner's default (`@scanner(messages="all")`, events=None) — the
  motivating case.

### 8. FastAPI search endpoint

`_api_v2_search.py` switches `view.read(...)` → `view.open(...)` and passes the
handle to llm_scanner. (Correction to earlier drafts: this endpoint has no
`max_bytes`/413 today — it simply OOMs. The 413 guard on the raw
transcript-stream endpoint in `_api_v2_transcripts.py` serves the browser
viewer and is untouched.) Per-request memory becomes O(N × context window).

## Testing

- **Equivalence:** streamed (`open()` + iterate) vs. materialized (`read()`)
  produce identical messages/events/Transcripts on fixture logs — including
  attachment-heavy, pool-condensed (`events_data`), NaN-containing (json5
  fallback), and both spool/in-memory threshold regimes (force threshold to 0
  to exercise spooling on small fixtures).
- **Pool-attachment regression test:** sample with `attachment://` refs inside
  `events_data` pool items resolves correctly via the spool path (fixes live
  bug; assert current path's failure first).
- **Memory regression:** synthetic large sample (events section dominating);
  `tracemalloc` asserts the streamed scan stays within a fixed budget where
  materialization would exceed it.
- **Error containment:** corrupt/truncated sample JSON in a multi-transcript
  scan yields one Error row, scan completes.
- **Seam tests:** mixed jobs (streaming + legacy scanner → materialized, single
  parse); follower jobs re-iterate the handle; callable-config llm_scanner
  forces materialization; `ResultReport.input` for streamed scans contains no
  content; handles refuse pickling.
- **Lifecycle:** cancellation mid-stream closes spool + zip streams (no fd/tmp
  leaks); prefetched jobs don't hold open handles.
- **Endpoint:** search endpoint integration test on a large fixture.

## Deferred / phase 2 (recorded, not in scope)

- **Exploded parquet schema** (row-per-message/event, pool tables): removes the
  parquet cell floor, makes filtering/segment-planning pushdown-cheap, enables
  streaming import. Schema migration + back-compat reader; the handle protocol
  is the seam it plugs in behind.
- **Streaming compaction path:** `compaction="last"` needs only the final
  ModelEvent per region; with a structural index (or at-rest layout) this makes
  events-derived scans O(context window). Lives on the events path, excluded
  from phase 1.
- **Hierarchical LLM reduction** for many-segment scans.
- **Bounded `ResultReport.input` for materialized transcript scans.**
- Timeline-forces-`events="all"` pruning fix and json5-fallback bounding for
  the materialized path (superseded for the OOM case by this design, still
  worthwhile independently).

## Rough size

Handle protocol + eval-log spool-and-replay implementation: ~700–900 LOC;
parquet `open()`: ~200; seam (`ScannerJob`/`_parse_function`/`_scan_one` error
containment): ~250; `ScannerInput`/result plumbing: ~150; streaming segmenter +
llm_scanner bounded window + capability attr: ~350; endpoint: ~50; tests:
~800–1,000. Landable as 3–4 PRs: (1) handle + eval-log streaming read +
equivalence tests; (2) seam + result plumbing; (3) llm_scanner + segmenter +
endpoint; (4) parquet `open()`.
