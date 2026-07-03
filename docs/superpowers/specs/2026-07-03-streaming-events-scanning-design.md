# Streaming Events Scanning for llm_scanner — Design

**Date:** 2026-07-03
**Status:** Draft for review
**Builds on:** PR #491 (TranscriptHandle / bounded-memory streaming reads)

## Problem

PR #491 bounds memory for messages-only llm_scanner scans. Events-content
scans still materialize the full transcript: `_streaming_eligible`
(`_scan.py`) requires `events is None`, and llm_scanner's events path
(`transcript_messages` → `timeline_build(transcript.events)` →
`timeline_messages`) builds a span tree from the complete event list. Huge
agentic transcripts are events-dominated, so this is where they still OOM.

Target consumer: **llm_scanner over huge agentic transcripts with unknown
span structure** (may be multi-agent). Timelines (stored-timeline scans /
`timeline=` content) remain out of scope — they stay materialized.

## Key insight and key hazard

**Insight:** after tree building and classification, the only events whose
*content* reaches a scanned segment are the last `ModelEvent` per kept
compaction region per scannable span (`span_messages`), plus
`CompactionEvent`s as region markers. A `ModelEvent`'s input is ≤ one
context window by construction. Everything else in a multi-GB agentic
transcript — tool outputs, sandbox events, intermediate model calls — is
used structurally or not at all.

**Hazard (why a naive one-pass reducer is wrong):** `timeline_build`'s
classification reads more than structure:

- `_is_single_turn` **counts** a span's direct ModelEvents/ToolEvents; a
  span holding only its region-last ModelEvent would misclassify multi-turn
  agents as single-turn → `utility=True` → **silently excluded from
  scanning**.
- `_wrap_utility_events` reads **every** ModelEvent's system prompt
  (`event.input` → `ChatMessageSystem`) and `_has_tool_calls(event)`
  (`output.choices[0].message.tool_calls`) to wrap foreign-prompt helper
  calls as utility spans. This can change *which* ModelEvent is the
  scanned "last" one.
- `_is_agent_span` classifies `type="tool"` spans by whether they contain
  ModelEvents; `ToolEvent.agent` / `tool_invoked` matter;
  `_extract_agent_results` reads sibling ToolEvents and next-ModelEvent
  inputs (bridge flow).

Any skeleton must preserve these signals exactly, or scanning silently
diverges from the materialized path on precisely the transcripts we care
about.

## Design: two-pass stub skeleton over the multi-shot handle

The handle's multi-shot contract (each `events()` call re-streams from the
local spool) makes a two-pass design cheap: pass 2 is a local re-read, not
a second S3 fetch.

### Pass 1 — stub skeleton + selection

Stream `handle.events()` once, building a **stub event list**:

- `span_begin`/`span_end`, `CompactionEvent`, `BranchEvent`/`AnchorEvent`:
  retained as-is (small; verify `CompactionEvent` payload size — it may
  carry summary messages, which are ≤ window by construction and needed
  for `compaction="all"` grafting anyway → retain fully).
- `ToolEvent`: retained with heavy payload fields stripped. Strip-set
  (the bulk): `arguments`, `result`, `events`, and any embedded content
  blocks. Keep everything else (`id`, `span_id`, `agent`, `agent_span_id`,
  `function`, timestamps, ...). The implementation derives the keep-set by
  copying the model and emptying the named bulk fields — so new fields are
  kept by default — and the stub-fidelity tests pin the classification
  behavior (`_is_agent_span`, `_extract_agent_results` read `agent`/
  `agent_span_id`/`function`; verified against inspect_ai source during
  implementation).
- `ModelEvent`: retained as a **stub**: `uuid`, `span_id`, timestamps,
  `input` reduced to only its `ChatMessageSystem` entries (with prompt
  strings **interned** via a dict so repeated identical prompts are stored
  once), `output` reduced to preserve `_has_tool_calls` (first choice's
  message with `tool_calls` kept, bulk content emptied). Everything else
  (the conversation payload — the bulk) dropped.
- All other event types: retained as-is unless found to carry bulk
  content (audit `info`/`store`/`sandbox` events; strip if needed —
  they are not scanned, only positional).

Then, on the stub list, run the **real, unchanged** pipeline front half:
`timeline_build(stubs)` → `_walk_spans(root, depth=depth)`. From the
resulting scannable spans compute the **needed-UUID set**: for each
scannable span, split its direct events by `CompactionEvent` into regions,
apply the `compaction` parameter's kept-region rule (mirroring
`span_messages`' selection: `"last"`→1, int→last N, `"all"`→all), and take
the last ModelEvent UUID per kept region. This selection helper is a
small pure function, unit-tested against `span_messages`' own selection
on the same inputs.

### Pass 2 — targeted retention + substitution

Stream `handle.events()` again, collecting **full** `ModelEvent`s whose
`uuid` is in the needed set (O(#scannable spans × kept regions × context
window) retention). Substitute them into the already-built stub tree
(replace `TimelineEvent.event` by uuid — no rebuild). Then run the
existing back half unchanged: `timeline_messages(tree, ...)` →
`segment_messages` per span → bounded-window scanning (already in place
from #491).

### Equivalence by construction, fidelity by test

The pipeline code (classification, unrolling, utility detection, depth
walk, compaction merge, numbering, reduction grouping) is not
re-implemented — it runs verbatim on the skeleton. The only new logic is
(a) stubbing (what to strip) and (b) needed-UUID selection. Both are where
fidelity can break, so the **load-bearing test** is end-to-end
equivalence: `transcript_messages` segments over the two-pass skeleton ≡
segments over the materialized transcript, across fixtures including a
genuinely multi-agent one (nested agent spans, unrolled solver spans, a
utility agent, foreign-prompt helper calls, compaction events). If no
existing fixture has this structure, synthesize one (write an eval log
with constructed events) as part of the work.

### Seam and wiring changes

1. `_streaming_eligible` (`_scan.py`): allow `events is not None` when
   `timeline is None` (messages may also be present — llm_scanner's
   events path ignores raw messages when events exist, matching current
   `transcript_messages` routing).
2. `llm_scanner`: set `supports_streaming` for events-content static
   configs too; on the handle path, when the content includes events,
   route through the two-pass skeleton (new function, e.g.
   `stream_timeline_messages(handle, ...)` in `_transcript/timeline.py` or
   `messages.py`) instead of `handle.load()`.
3. `TranscriptHandle`: **no protocol change**. The two-pass consumer
   composes over `events()` — the reserved `conversations()` accessor
   stays reserved. The reserved `types=` kwarg is used by pass 1/2 only if
   it maps cleanly (both passes need all event types for structure — so
   passes use `types=None`; the scanner's own events filter still applies
   to what `timeline_build` sees? **No** — match current behavior: the
   union content's events filter governs what the handle was opened with,
   same as the materialized path; do not add extra filtering).
4. Non-streaming paths untouched: materialized transcripts keep the
   existing `timeline_build(transcript.events)` route.

### Memory bound (honest statement)

- Pass 1 retention: O(#events × stub size) with prompts interned —
  typically tens of MB for hundreds of thousands of events; document
  measurement in the regression test.
- Pass 2 retention: O(#scannable spans × kept regions × context window).
  For `compaction="last"`: one ModelEvent per span. For `"all"`: one per
  region — irreducible, since "all" grafts every region into output.
- Not O(context window) flat; it is O(structure + selected windows). For
  events-dominated agentic transcripts this drops nearly all bulk.

### Error handling

Same containment as #491: stream-raised errors during either pass surface
in `_scan_one` and become per-transcript Error reports. A uuid-less
ModelEvent (old logs?) cannot be selected by uuid — audit whether
ModelEvents can lack uuids; if so, fall back to positional selection keyed
by (span_id, region ordinal, index) or fall back to materialized for that
transcript (decide during implementation; must not silently mis-select).

## Non-goals

- Stored timelines / `timeline=` content scans (stay materialized).
- Per-item `Scanner[Event]` streaming (tier 1 — separate, easy follow-up).
- Exploded parquet schema (unchanged phase-2 item; this design's
  selection pass becomes a pushdown query there).
- Changing skeleton behavior for the materialized path.

## Testing

- **End-to-end fidelity** (load-bearing): skeleton-path segments ≡
  materialized-path segments (same spans, same `[M#]` numbering, same
  messages_str), across all fixtures + the synthesized multi-agent
  fixture, for `compaction` ∈ {"all", "last", 2} and `depth` ∈ {None, 1}.
- **Selection unit tests**: needed-UUID selection ≡ `span_messages`'
  effective selection on the same event lists (property-style over
  constructed span/compaction shapes).
- **Stub fidelity unit tests**: classification outcomes
  (`utility` flags, agent spans, single-turn) identical on stubs vs full
  events for constructed cases exercising `_wrap_utility_events`,
  `_is_single_turn`, `_is_agent_span`, `_extract_agent_results`.
- **Memory regression**: synthetic events-heavy agentic sample (large
  tool outputs + many model turns); assert two-pass peak ≪ materialized
  peak with a hard budget; assert pass-1 stub retention stays within its
  own budget (prompt interning effective).
- **E2e**: real `scan()` with an events-content llm_scanner over a large
  fixture, threshold forced to 0, results equal to materialized run.

## Rough size

Stub reducer + selection helper: ~300–400 LOC; two-pass orchestration +
llm_scanner/seam wiring: ~200; multi-agent fixture synthesis: ~150; tests:
~600–800. One PR, on top of #491's branch.
