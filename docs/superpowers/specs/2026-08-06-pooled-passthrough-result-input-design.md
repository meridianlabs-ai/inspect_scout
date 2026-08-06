# Pooled-Passthrough Result Input — Design Spec

**Date:** 2026-08-06
**Status:** Draft — design agreed, not yet implemented
**Related:** PR #491 (bounded-memory streaming transcript reads)

## Problem

`ResultReport.input` must hold the full transcript so scan results stay
self-contained (readable without the original eval logs). Today that value is
produced by a lossy round trip:

1. The spool holds transcript items **unresolved** — pool index refs and
   `attachment://` refs intact — with pool entries and attachments in the
   `BlobSpool`.
2. Replay (`replay_messages` / `replay_events`) **expands** both, producing
   typed objects with fully inlined content.
3. `_serialize_input` then calls `condense_events(...)`, which **re-derives**
   an equivalent pooling from scratch.

Step 3 forces materialization: `condense_events` is a whole-collection
operation (two passes building shared pools over every event), so the entire
event list must exist as typed Pydantic objects at once. That is the only
reason `_transcript_for_record()` currently calls `handle.load()`.

The waste is that **the compact form the recorder wants already exists in the
spool.** The eval-log sample carries `events_data.messages` /
`events_data.calls` (legacy: `message_pool` / `call_pool`), which is the same
`EventsData` shape `condense_events` produces and `expand_events` consumes.

Step 2 is separately harmful: resolving attachments *inlines every duplicate*.
Attachments exist to dedupe repeated content by hash, so a resolved transcript
is materially larger than the source it came from — and that inflated form is
what gets written to every result row.

## Goals

- Record the transcript without building the Pydantic object graph or
  re-condensing.
- Preserve self-containment: everything needed to reconstruct the transcript
  travels with the results.
- No change to the results **schema** (no new column) and no change to the
  Python read path.
- Shrink recorded output by keeping content deduped rather than inlined.

## Non-Goals

- Removing the O(transcript) floor entirely. See "Memory reality" — a parquet
  cell is an atomic value, so `input` must exist as one contiguous string at
  write time. Eliminating that requires storing transcripts outside the cell
  (see Follow-ups).
- Changing the `MaterializedTranscriptHandle` path. It already holds a
  `Transcript`; it keeps the existing `condense_events` path.
- Changing what non-handle scanners (message/event/timeline inputs) record.

## Design

### Where it plugs in

`_scan.py::_transcript_for_record(handle)` is the single call site introduced
when info-only recording was reverted. For a `SpooledTranscriptHandle` it is
replaced by a path that produces the two serialized column values directly,
bypassing `Transcript` construction and `_serialize_input`'s condense step:

```
(input_json, input_data_json) = pooled_passthrough(handle)
```

`MaterializedTranscriptHandle` and plain `Transcript` inputs are unaffected and
continue through `_serialize_input`.

This means `ResultReport` needs a way to carry pre-serialized column values
rather than a live `ScannerInput`. See "Open questions".

### Two-pass pruning

Pool references are **positional range-encoded** indices into a shared pool
(`condense_model_event_inputs` assigns each unique message a position and
rewrites `ModelEvent.input` as a range). Dropping unreferenced pool entries
therefore shifts every later index, so pruning requires reindexing.

Attachments are keyed by content hash, so pruning them is a simple set
membership test — no remap.

The `TranscriptHandle` contract is explicitly multi-shot, and the spool is
local disk (the events-streaming skeleton already re-reads it), so two passes
are cheap and idiomatic:

**Pass 1 — collect.** Iterate `ItemSpool` items (messages and events) without
resolving. For each item record:
- pool indices referenced by the item's range refs, per pool
  (`message_pool`, `call_pool`)
- attachment ids matched by `ATTACHMENT_REF_PATTERN`

Then build, per pool, an ascending-order compaction map
`old_index -> new_index` over the referenced indices only. Ascending order
keeps pool ordering stable and makes the map a simple enumeration.

**Pass 2 — emit.** Re-iterate the spool, rewriting each item's pool refs
through the compaction map, and stream the items into the `input` JSON
envelope. Fetch only the referenced pool entries and attachments from
`BlobSpool` (`pool_len()` + `get((pool, i))` for pools, `get(id)` for
attachments).

Attachment refs are **not** resolved in either pass.

### Envelope

`input` mirrors what `SpooledTranscriptHandle.load()` would have produced, so
downstream consumers see the same shape:

- `info.model_dump()` fields, merged with unthinned metadata via the existing
  `_merge_unthinned(info.metadata, result)` (sample metadata, target, scores)
- `messages`: items from the message `ItemSpool`, verbatim (attachment refs
  intact; transcript messages carry no pool refs)
- `events`: items from the event `ItemSpool`, pool refs remapped, attachment
  refs intact
- `timelines`: `[]`, matching today's spooled `load()`

### `input_data` format

Attachments nest inside the existing `input_data` column rather than taking a
new one:

```json
{
  "messages": [ ...pruned message pool... ],
  "calls":    [ ...pruned call pool... ],
  "attachments": { "<hash>": "<content>", ... }
}
```

This is safe on both read paths **without an upstream change**:

- **Python:** `expand_events` deserializes with
  `raw.get("messages", [])` / `raw.get("calls", [])` — unknown keys are
  ignored.
- **Schema:** the `EventsData` component in `openapi.json` already declares
  `"additionalProperties": true`, so the extra key validates.

When the pruned pools and attachments are all empty, emit `input_data` as
`None` so the row matches today's shape for content-free cases and is skipped
by `_expand_events_in_df`'s `isna().all()` guard.

### Read-path compatibility

| Consumer | Pooled events | Attachment refs |
|---|---|---|
| `_expand_events_in_df` (Python) | already calls `expand_events` ✓ | **not handled** — see below |
| `expandInputEvents.ts` (viewer) | already calls `expandEvents` ✓ | **not handled** |
| transcripts endpoint (viewer) | `expandEvents` ✓ | `resolveAttachments` ✓ |

Pool expansion needs no work anywhere. Attachment resolution already exists in
the viewer (`attachmentsHelpers.ts::resolveAttachments`) and is wired to the
**transcripts** endpoint, which serves exactly this compact form today. It is
not wired to the **results** path, because results currently arrive
pre-resolved.

### Required viewer change

In the scan-results path, after `expandInputEvents(...)`, resolve attachments
against `input_data.attachments` using the existing helper — mirroring what
`api-scout-server.ts` already does for transcripts:

```ts
const events = expandEvents(parsed.events, parsed.events_data ?? null);
messages: resolveAttachments(messages, attachments),
events: resolveAttachments(events, attachments),
```

Because `EventsData` is `additionalProperties: true`, `attachments` arrives
untyped in `generated.ts`. To get a typed accessor, declare a Scout-side
response model for the results `input_data` rather than reaching through an
index signature.

**This change is mandatory, not optional.** Without it the viewer renders
`attachment://<hash>` as literal text.

## Memory reality

State the claim accurately; do not repeat the "bounded regardless of size"
framing.

`input` is a single parquet cell, and a cell is an atomic value — PyArrow needs
the complete string to build the array. So peak at record time is **O(size of
the condensed transcript JSON)**, not O(one item). This design does not remove
that floor.

What it does remove:

- the Pydantic object graph (~3× the content) built by `load()`
- attachment inlining, which expands every duplicate — for agentic transcripts
  with repeated system prompts and tool outputs, the resolved form is
  substantially larger than the source
- the `condense_events` re-derivation pass

Net: peak drops from roughly **3× resolved** to **1× condensed**, with the
condensed/resolved ratio itself often large. The honest headline is "bounded
during the scan; recording peaks at roughly the source sample size."

**Measured**, on the largest sample (54,425-byte zip entry, id
`5gZvjiyXhVw7JDzm9uG37N`) in the largest real `.eval` log under `tests/`
(`tests/recorder/logs/2025-09-23T08-09-58-04-00_theory-of-mind_bbB4eRCx2rFJLyPH42Cj9r.eval`,
100 samples, 720KB): `tracemalloc` peak for `handle.load()` +
`_serialize_input(..., pool_dedup=True)` was 510,347 bytes vs. 271,110 bytes
for `pooled_passthrough`, a **1.88×** peak reduction; output size (`len(input_json)
+ len(input_data_json or "")`) was 59,396 bytes vs. 44,558 bytes, a **1.33×**
reduction. This sample has no message/call pool entries — its savings come
entirely from not resolving 5 attachments — so both ratios are well short of
the "3× / condensed-often-large" framing above; that framing describes
transcripts with heavier pooling and attachment reuse than this fixture has.
Treat the qualitative direction (smaller peak, smaller output) as established
and the specific multiplier as sample-dependent.

## Scope

- **Applies to:** `SpooledTranscriptHandle` only — the large-transcript case
  the PR targets.
- **Unchanged:** `MaterializedTranscriptHandle`, plain `Transcript` inputs, and
  all non-transcript scanner inputs.
- **To confirm:** whether the parquet backend's `open()` spools pools the same
  way. If it does not, parquet keeps the existing path and the ~1× cell floor
  already documented for it.

## Edge cases

- **Messages-only scan.** `events` is empty, so no pool refs are collected and
  both pools prune to empty. Emit `input_data` as `None` rather than attaching
  the source's full events pool — this is the case pruning most needs to get
  right.
- **Legacy pool spellings.** `message_pool.item` / `call_pool.item` and
  `events_data.messages.item` / `events_data.calls.item` both normalize to the
  same `BlobSpool` keys during parse, so emission is uniform.
- **Filtered events.** The spool holds all pool entries but only filtered
  events; pruning is what keeps the copy from being a superset.
- **`_ensure_parsed` fallback.** When the spooled parse hits malformed JSON,
  the handle falls back to a materialized `Transcript`. That path has no spool,
  so it must fall through to `_serialize_input`.
- **Attachment refs inside pool entries.** Pool entries may themselves contain
  `attachment://` refs. Pass 1 must scan fetched pool entries as well as event
  items, or those ids will be missing from the pruned attachment set.
- **Failure to read the spool.** Keep the existing
  `_transcript_for_record` behaviour: log and fall back to an info-only
  placeholder so an already-produced result is never lost.

## Testing

- **Round-trip equivalence (the primary test).** For a spooled transcript,
  assert `expand_events(input.events, input_data)` plus attachment resolution
  equals the transcript produced by `handle.load()`. This is the correctness
  contract; everything else is subsidiary.
- **Pruning correctness.** A transcript whose events reference a strict subset
  of pool entries: assert the emitted pool contains only referenced entries and
  that remapped refs still resolve to the same messages.
- **Messages-only scan** emits `input_data is None`.
- **Attachment refs inside pool entries** are collected (regression guard for
  the edge case above).
- **Parity with the materialized path**: same transcript through spooled and
  materialized handles yields equivalent expanded output.
- **Viewer**: unit test that results-path input with `attachments` resolves,
  reusing the existing `attachmentsHelpers` tests as a model.
- Do **not** add tracemalloc budget assertions — the repo has no precedent for
  them and the previous set was removed.

## Resolved decisions

### Carrying pre-serialized columns — `SerializedTranscript` on the field only

Three options were wargamed. **Decision: a dedicated `SerializedTranscript`
value type declared in `_scanner/result.py`, reachable only through a new
`ReportInput = ScannerInput | SerializedTranscript` alias used for the
`ResultReport.input` field.** `ScannerInput` itself is not widened.

Established by tracing, and decisive for all three:

- `to_df_columns()` has exactly one call site (`_recorder/buffer.py:217`) and
  always runs in the **main process**.
- In multi-process mode `ResultReport`s are pickled in the worker
  (`_mp_subprocess.py:191-194`) and unpickled in the parent
  (`multi_process.py:269-270`) *before* serialization.
- In single-process, `_scan_one`'s `finally` closes the handle before
  `record_results` runs.

So serialization must happen inside `_scan_one`, and only plain picklable data
may ride the report.

**Rejected — passing the handle itself to `_serialize_input`.** Both handle
classes raise in `__reduce__`, so the report cannot cross the MP queue.
`multiprocessing.Queue.put()` pickles on a feeder thread, so the failure is a
background traceback with the row **silently dropped** while the scan reports
success. Also broken in single-process, where the handle is already closed.

**Rejected — an optional `input_serialized` field with `input` holding a
placeholder.** Comparable size, but `input` would hold an empty `Transcript`
that nothing enforces. A future second reader of `.input` compiles fine and
silently gets `[]`. Under the chosen design the same code fails to compile:
`Item "SerializedTranscript" of "ReportInput" has no attribute "messages"`.
That converts a silent-wrong-answer class into a type error.

**Rejected — adding `SerializedTranscript` to the `ScannerInput` union.**
Measured: +28 lines of `openapi.json` and a rewritten `generated.ts` union
(requiring a coordinated submodule landing), versus **zero churn** for the
field-only variant — `export_openapi_schema.py:48-53` builds
`ScannerInputResponse` from the alias, and `ResultReport` is not reachable
from any route. Worse, `ScannerInput` is exported public API and bounds
`Loader[T]` and the `@scanner` type parameter, so this would make
`Loader[SerializedTranscript]` legal with no runtime path producing one — a
breaking type to remove later. It also forces a branch into
`get_input_type_and_ids` that is both dead (the handle path hardcodes
`("transcript", [info.transcript_id])`) and unimplementable (the id would
require parsing the opaque JSON).

Verified for the chosen variant: mypy clean across 223 files; no Pydantic
coercion in either direction (the shapes are structurally disjoint);
`to_df_columns()` output byte-identical between the two paths.

### Pruning — always on, using upstream primitives

inspect_ai already provides exactly the needed helpers, operating on **raw
JSON mappings** rather than typed events:

- `collect_pool_ref_positions(events) -> PoolRefPositions` with
  `.message_positions` / `.call_positions`
- `remap_pool_refs(event, message_pos_map, call_pos_map) -> dict`

Both walk `POOL_REF_FIELDS`, the registry of every field carrying
range-encoded refs (`input_refs`, `("call", "call_refs")`). Its docstring
names our two use cases explicitly — "callers that load partial pools" and
"export paths [that] translate refs after pool entries are assigned new
positions in a destination store" — and an upstream test
(`test_pool_ref_registry_covers_all_ref_fields`) fails if a new `*_refs`
field is not registered.

**Do not hand-roll ref walking or remapping.** Doing so would silently drop
entries when upstream adds a ref field; the registry is the single source of
truth.

## Open questions

1. **`pool_dedup=False` under passthrough.** `to_df_columns(pool_dedup=...)`
   threads through to `_serialize_input`, but a pre-serialized value is
   already pooled. The flag is dead today (`RecorderBuffer` defaults it to
   `True`; no production construction site overrides it), so passthrough
   would silently ignore it. Either honour it in `pooled_passthrough` by
   expanding, or fail loudly — do not ignore silently.

## Follow-ups

- **Compressed-bytes transcript storage.** Storing the transcript as
  compressed bytes in the scan bundle, outside the `input` cell, removes the
  atomic-cell constraint entirely and dedupes across scanners (today the same
  transcript is embedded once *per scanner*). This design is compatible with
  that and reduces its urgency; it does not replace it.
- Result rows still embed one transcript copy per scanner. Storing once per
  transcript would shrink the frames that #538 and #541 work around.
