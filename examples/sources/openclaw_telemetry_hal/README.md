# OpenClaw telemetry-hal plugin import

An **example** transcript source that imports JSONL telemetry produced by the
third-party
[`openclaw-telemetry-hal`](https://github.com/sage-princeton/openclaw-telemetry-hal)
plugin. Its entry point is `openclaw_telemetry_hal()` and it stamps a
`source_type` of `"openclaw_telemetry_hal"` onto the transcripts it yields.

This is not a built-in Scout source: it is a one-off written to import data from
evals such as CRUX1 that happened to be captured with this telemetry plugin. It
lives here as a worked example of writing a custom source you can copy into your
own project and adapt. The code here depends only on the public `inspect_scout`
/ `inspect_ai` APIs, so it works unchanged outside the Scout repo.

## Usage

`openclaw_telemetry_hal()` is an async generator of `Transcript` objects, so it
plugs straight into `transcripts_db().insert()`:

```python
from inspect_scout import transcripts_db

from openclaw_telemetry_hal import openclaw_telemetry_hal

async with transcripts_db("transcripts") as db:
    await db.insert(openclaw_telemetry_hal("~/.openclaw/logs/telemetry.jsonl"))
```

`populate_db.py` in this directory is a runnable version of the snippet above.
Run it with no argument to read the plugin's default output
(`~/.openclaw/logs/telemetry.jsonl`), or pass a telemetry directory or a
specific `.jsonl` file to import instead:

```bash
cd examples/sources

# default: ~/.openclaw/logs/telemetry.jsonl
python -m openclaw_telemetry_hal.populate_db

# or point at a specific telemetry file / directory
python -m openclaw_telemetry_hal.populate_db /path/to/telemetry.jsonl
```

> [!WARNING]
> Importing a large capture such as CRUX1 can take around 10 minutes.

The test suite (`tests/`) is not part of Scout's CI test run (it lives outside
`tests/`); run it directly with `pytest
examples/sources/openclaw_telemetry_hal/tests` if you adapt the code.

## Design notes

Motivation: data from evals such as CRUX1 were captured using this telemetry plugin.

## Schemas supported

The CRUX1 dataset was generated using
https://github.com/sage-princeton/openclaw-telemetry-hal. This tool is a fork of
https://github.com/knostic/openclaw-telemetry.

Native OpenClaw session files (the bundles written under `~/.openclaw/`) are an
entirely different schema. This example only handles the `openclaw-telemetry-hal`
schema.

Within that schema, the importer is strict about session classification: a
`sessionKey` kind outside `main`/`telegram`/`dashboard`/`subagent` on a consumed
(`agent.*`/`tool.*`) event — e.g. a chat surface we have not seen — fails the
import with an error naming the kind, rather than silently dropping that
session's activity. Native session support is a future, separate source — see "Native
session files vs the telemetry-hal plugin" below for what that richer schema
offers.

## Native session files vs the telemetry-hal plugin

Notes from comparing a single run captured both ways. "Native" below assumes
access to the **whole** session bundle, not just one `.jsonl`.

### The native bundle (per run)

For each session (orchestrator + each sub-agent) OpenClaw writes, keyed/named by `sessionId`:

- **`<sessionId>.jsonl`** — the conversation: a tree of `session` / `model_change` /
  `thinking_level_change` / `custom` / `message` / `leaf` records. `message`s carry full content, per-message `usage`,
  `responseId`, and rich `toolResult.details`. - **`<sessionId>.trajectory.jsonl`** — a runtime event trace
  (`session.started`, `context.compiled`, `prompt.submitted`, `model.completed`, `trace.artifacts`, `session.ended`).
  Every record's envelope carries `sessionId` + `sessionKey` + `runId`.
- **`<sessionId>.trajectory-path.json`** — pointer stamping the trajectory's `sessionId`.
- **`sessions.json`** — a registry keyed by runtime `sessionKey`, one entry per session.

### Joining sessions (topology)

The `.jsonl` itself has **no** `sessionKey` and **no** parent pointer (its `parentId`
is an intra-file tree link only). The reliable joins, strongest first:

1. **`sessions.json` (authoritative).** Each entry gives `sessionId` (→ file),
   `sessionFile`, `spawnedBy` (parent's runtime `sessionKey` — the true agent tree),
   `parentSessionKey` (conversation-continuity lineage across turns), plus `label`
   (e.g. `usd-gbp`), `spawnDepth`, `subagentRole`. Child→parent file = two structured
   lookups, no heuristics. Caveat: it is a **global, mutable index** — may contain other
   runs / stale entries / redacted ids, so intersect with files actually on disk.
2. **Trajectory envelopes (fallback for identity).** Each binds `sessionId ↔ sessionKey ↔ runId`
   structurally; parent only via `announce:v1:…:<childKey>:…` run ids (present only for
   children that announced) — partial.
3. **Content joins (last resort).** Orchestrator `sessions_history` / completion-event
   prose echo child `sessionId`/`sessionKey`; align on the globally-unique `responseId`.

Cross-check: filename == `.jsonl` `session.id` == trajectory envelope `sessionId` ==
registry `sessionId` (all agreed in our sample) — use it to validate, not just trust.

### What native files have that telemetry-hal does NOT

The telemetry transcript is ~a reformatted subset; the native bundle is strictly richer:

- **Per-session token/cost rollups** — `estimatedCostUsd` plus `inputTokens`, `cacheRead`,
  `totalTokens`, … *(sessions.json)*. Telem carries only per-call `usage`; its per-call
  `cost` is populated in some captures (e.g. CRUX1, ~86% of turns non-zero) and all-zero in
  others, and we drop it either way since Inspect `ModelUsage` has no cost field.
- **Prompt/context provenance**: system-prompt char count + **sha256 hash**, injected
  workspace files, tool/skill inventory with hashes (`systemPromptReport`); the actual
  **compiled prompt** / `finalPromptText` and `contextBudgetStatus`. *(sessions.json + trajectory)*
- **Authoritative topology**: `spawnedBy`, `parentSessionKey`, `label`, `spawnDepth`,
  `subagentRole`; `runId` boundaries. *(sessions.json + trajectory)*
- **Conversation structure**: `parentId` tree + `leaf` branching, `model_change` /
  `thinking_level_change` config events, `idempotencyKey`. *(jsonl)*
- **Run metadata**: `status`, `abortedLastRun`, timeout flags, `runtimeMs`, channel/origin.
- **Timing**: two timestamps per `message` — record-level ISO (append time) +
  `message.timestamp` epoch-ms (logical time) — for ordering + ms wall-clock on every
  message *(jsonl)*; per-turn wall-clock = `ts(model.completed) − ts(prompt.submitted)`
  *(trajectory)*; per-session wall-clock via `sessionStartedAt` / `startedAt` / `endedAt` /
  `runtimeMs` *(sessions.json)*. The one timing gap is per-tool latency — see below.

### What telemetry-hal has that native files do NOT

Essentially one thing: **uniform per-tool-call latency + success/error** via
`tool.start`/`tool.end` (`durationMs`, `success`) for *every* tool. Natively, exact tool
timing exists only for some tools (`exec` → `durationMs`, `web_fetch` → `tookMs`); for the
rest (`sessions_*`, `web_search`, `subagents`) it must be **approximated** from record-level
timestamps (`recordTS(toolResult) − recordTS(assistant toolCall)` — validated to within
~10–30% of the plugin's numbers). Otherwise telem is the thinner, streaming-oriented view.

Caveat on what the importer *surfaces*: this per-tool timing is available in the
format but is **only reconstructed for schema-B sub-agent calls** (where the
`tool.*` stream is the sole record). Orchestrator and schema-A tool calls are
built from the `messages[]` content channel and carry no timing — see "Per-tool
timing is not surfaced for the orchestrator" under Known limitations.

## OpenClaw telemetry: `telemetry-hal` vs `knostic` JSONL output

https://github.com/sage-princeton/openclaw-telemetry-hal
https://github.com/knostic/openclaw-telemetry

`telemetry-hal` is a fork of `knostic`'s plugin: the file layout is identical
(`redact.ts`, `ratelimit.ts`, `rotate.ts`, `integrity.ts`, `syslog.ts` are byte-identical)
and the event envelope (`ts`, `seq`, `sessionKey?`, `agentId?`) and config are the same.
They diverge on **whether message/prompt content is written to the JSONL**.

- **knostic** (`knostic/openclaw-telemetry`) — metadata-only: lengths, never the text.
- **telemetry-hal** (`sage-princeton/openclaw-telemetry-hal`) — full content: message bodies,
  prompts, whole message arrays, plus extra fields and an extra event type.

The importer requires the **telemetry-hal** fork: a knostic file has no message/prompt
content and would import as empty-bodied transcripts.

### Schema differences by event

| Event                                   | knostic fields                         | telemetry-hal fields                                                                              |
|-----------------------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------|
| `message.in`                            | `channel`, `from`, **`contentLength`** | `channel`, `from`, **`content`** (full text), `contentLength?`, **`timestamp?`**, **`metadata?`** |
| `message.sending`                       | *(does not exist)*                     | `channel`, `to`, **`content`** — extra event type                                                 |
| `message.out`                           | `channel`, `to`, `success`, `error?`   | same **+ `content`** (full text)                                                                  |
| `agent.start`                           | **`promptLength`**                     | **`prompt`** (full text), `promptLength?`, **`messages?`** (full array)                           |
| `agent.end`                             | `success`, `durationMs?`, `error?`     | same **+ `messages?`** (full array)                                                               |
| `tool.start` / `tool.end` / `llm.usage` | —                                      | identical in both                                                                                 |

### Data-handling differences

| Concern                                       | knostic                                                            | telemetry-hal                                                                                                                                                     |
|-----------------------------------------------|--------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Conversation content in logs                  | never written                                                      | written in full                                                                                                                                                   |
| Redaction (`redact.enabled`, default `false`) | identical regex secret-scrub; never strips bodies                  | same — does **not** protect content                                                                                                                               |
| Write path                                    | single service pipeline (rate limit → redact → sign → file/syslog) | **also** an always-on raw `appendFileSync` (in the same `emit()`) to `OPENCLAW_TELEMETRY_FILE` (default `~/.openclaw/logs/telemetry.jsonl`), writing the pre-service payload — **bypassing redaction, rate limit, integrity, rotation, and the `seq`/`ts` stamping the service adds** (so a raw-dump file carries `sessionKey`/`agentId` from OpenClaw but no `seq`/`ts`) |
| Serializer                                    | plain `JSON.stringify`, drops on write failure                     | handles bigint/circular refs, retries on failure                                                                                                                  |

### Bottom line

Treat them as different data products despite the shared name:

- **knostic** — privacy-preserving, metadata-only (lengths, timing, tokens/cost, tool names + params).
- **telemetry-hal** — full-fidelity capture including raw conversation content and prompts, with a
  redaction-bypassing raw dump file.

## Sub-agent encodings: schema A vs schema B

OpenClaw records a sub-agent's activity in one of two ways, and the importer
handles both (the `SubagentSpan` carries `turns` for A and `tool_calls` for B):

- **Schema A** — the sub-agent's own assistant turns appear inside its
  `agent.*` `messages[]`, with `timestamp` + `usage`. The richer form; OpenClaw
  emits it only when it populates a sub-agent's `messages[]`.
- **Schema B** — activity appears only as `tool.start`/`tool.end` events (no
  turns, no usage, no timestamps). Near-universal, since the tool hooks fire for
  every call.

A session may carry A, B, or both (**hybrid**); schema A is authoritative when
present, so hybrid sessions reconstruct from A and ignore the duplicate `tool.*`
events.

Wherever sub-agent activity lands, as per the other importers (e.g. Claude
Code) the transcript's `messages` column contains only the orchestrator's
thread: sub-agent turns are recorded in `events`, nested under agent spans and
labelled by `span_id`, so code that reads only `messages` will not see them.

## Keyless turn dedup and sanitized toolCall ids

Assistant turns recur across the cumulative `agent.*` snapshots and are deduped
by `responseId`. Service-sink captures (e.g. CRUX1) carry **no** `responseId`,
so the fallback key is `(timestamp, content)` — and that content is serialized
with toolCall ids **masked** (`_keyless_content_json` in `parse.py`).

The masking exists because OpenClaw's history sanitizer rewrites tool-call ids
between a turn's first snapshot and all later ones. Observed in `CRUX1_full`: a
turn is appended live with the provider id (`toolu_01…`) exactly once, and every
subsequent snapshot re-serializes it with the underscore stripped (`toolu01…`) —
on both the `toolCall` block and its `toolResult` — with `timestamp`, arguments,
and `usage` identical down to the cost floats. Keying on the raw content kept
both spellings of the same turn: 909 of `CRUX1_full`'s orchestrator turns (~10%,
9,423 → 8,514) were such twins, inflating the headline token total by 75.3M
(~16%, 476.2M → 400.9M), duplicating their model/tool events, and re-anchoring
71 sub-agent spans at the twin instead of the original spawn call.

The first-seen (provider-id) spelling of a turn is the one kept. That is safe
for result linking: `result_by_callid` retains **both** spellings of each
`toolResult`, so the kept turn's `toolCall` ids always resolve. Sub-agent
schema-A turns dedup through the same masked key; user turns and `toolResult`s
are unaffected (ids never appear in their dedup keys).

## Transcript identity

telemetry-hal events carry **no runId** (the envelope is only `ts`/`seq`/
`sessionKey`/`agentId`). The only identity in a `.jsonl` is the orchestrator's
sessionKey trailing segment, and it means different things per surface: a
per-run session id for `main`/`dashboard`, but a **chat id shared across runs**
for `telegram`. So it cannot be the transcript id on its own — two runs in the
same Telegram chat would collide.

The importer therefore keeps that value as `source_id` (the semantic
session/chat identity) and derives `transcript_id` as `"<session_id>-<earliest
event ts>"`. The timestamp is intrinsic to the run (stable across re-imports,
unlike the file name, which changes on copy/rotation) and disambiguates runs
that share a chat id. When no session id is present (kind-only or scrubbed key)
it falls back to the session id alone, then the file stem.

## Known limitations

### TODO: Split multi-session telemetry files into separate transcripts

The current importer treats **one telemetry JSONL file as one Scout
transcript**. That is not the same boundary as an OpenClaw run: the
`openclaw-telemetry-hal` plugin's documented default output is a single
append-only file at `~/.openclaw/logs/telemetry.jsonl` (with no reliable
per-run file rotation), so multiple orchestrator sessions can normally be
present in one file.

Today `parse_telemetry()` pools orchestrator turns across all
non-`subagent` sessions before `transcripts.py` creates the `Transcript`. If a
file contains, for example, `session-AAA` followed by `session-BBB`, the
importer produces one transcript, attributes it to the first session identity it
sees, and interleaves both conversations in that transcript. No separate
transcript is emitted for `session-BBB`.

Future work should split the consolidated telemetry by orchestrator session/run
boundary before transcript construction. Until then, users should provide
files that contain a single orchestrator run if they need transcript-level
identity and conversation boundaries to be exact.

### Tool success/error is exact; precise per-tool latency is not

Each `toolResult` (in the `agent.* messages[]`) carries `isError` and a
`timestamp`, keyed by `toolCallId`. The importer surfaces both: `isError` →
`ToolEvent.failed`/`error`, and the result timestamp → `ToolEvent.completed`
(so the call→result span is real, not the parent turn's time reused). This is an
**exact, id-keyed** join — no heuristics.

Precise per-tool *latency* (`durationMs`) lives only on `tool.end`, which — in
both vintages — carries **no `toolCallId`**, only `toolName`. Attaching it to a
specific orchestrator tool call would require a heuristic name/order positional
match. We deliberately **do not** do this for the orchestrator: the exact
success + result-completion time already give a faithful timing view, and a
best-effort latency number isn't worth the misattribution risk. (Schema-B
sub-agent spans are the one place `tool.*` is consumed, because there it is the
*only* record of the call; its `durationMs`/`success` go in the event metadata.)

### Reasoning tokens

Reasoning tokens are **not** reported separately: OpenClaw bills reasoning inside
`output`, so `ModelUsage.reasoning_tokens` is left 0 even though those
tokens are still counted in the headline totals via `output`.

### Sub-agent responses are not surfaced

A sub-agent's *final report* is delivered as a `message.out` (and paired
`message.sending`) event on the orchestrator's outbound channel — it is **not**
recorded under the sub-agent's `sessionKey`. These events carry no `sessionKey`,
`runId`, or `agentId`, and the spawn's tool result is only an `accepted`
acknowledgement, so a report **cannot be deterministically attributed to the
sub-agent that produced it**. File order misleads (reports arrive in completion
order, not spawn order; e.g. the *Eastern* report can immediately follow the
*weather-west* sub-agent's activity), and the only thing tying a report to a
sub-agent is the report text echoing the spawn `label` — a content heuristic
that does not generalize. We therefore **do not** consume `message.*` events or
nest reports inside sub-agent spans.

### Schema-B sub-agents have no internal transcript

Under schema B, a sub-agent's `agent.start` carries only the
spawn `prompt` with an empty `messages[]`; its activity is visible solely as
`tool.start`/`tool.end` events, which record **no result body, no usage, and no
timestamps** (only `durationMs` on `tool.end`). Consequently a schema-B
sub-agent span shows its reconstructed tool calls but no model turns, token
totals, or wall-clock duration (it renders as `0 · 0s`). This is a property of
the source telemetry, not the importer. Schema-A sub-agents (which carry their
own assistant turns in `messages[]`) are reconstructed in full.

### Sub-agent compactions are not surfaced

`compactionSummary` records are reconstructed as `CompactionEvent`s only for
the orchestrator. A compaction inside a *sub-agent's* snapshot (its own thread
compacting) has never been observed — all 467 compactions in `CRUX1_full` are
under `main` — so rather than misplace it in the root timeline or
speculatively interleave it into the agent span, the importer drops it with a
warning (once per session).

### Per-tool timing is not surfaced for the orchestrator

`durationMs` + `success` live *only* on `tool.end` events — the same stream that
constitutes schema B. Schema A/B governs where a session's **content** (turns,
arguments, tool *results*, usage) comes from; the `tool.*` stream is a separate,
always-on **timing** channel. The importer builds orchestrator and schema-A
tool events from the content channel (`messages[]` `toolCall`/`toolResult`
blocks) and does **not** consult the timing channel for them, so those
`ToolEvent`s carry no duration (`completed == timestamp`) and no success flag.
Only schema-B sub-agent calls — where the content channel is empty and `tool.*`
is the sole record — surface `durationMs`/`success` (into `ToolEvent.metadata`).
Even there, attribution is best-effort: `tool.end` carries only `toolName`, not
`toolCallId`, so overlapping same-named schema-B calls can still have
duration/success attached to the wrong start.

This is a deliberate omission, not an oversight. Joining the timing channel back
onto orchestrator/schema-A tool calls is **not** reliable: `tool.start`/`tool.end`
carry **no `toolCallId`**, while the
content `toolCall` blocks do. The only possible join is positional (match the
k-th `tool.end` of a given `toolName` to the k-th `toolCall` of that name), and
it is fragile in practice — the two streams can live under **different
sessionKeys** for the same orchestrator (in the demo, content under
`agent:main:main`, timing under `agent:main:telegram:…`), the counts differ
(orphan runtime `sessions_yield` `tool.*` events with no content counterpart),
and repeated identical calls can only be ordered, not keyed. A best-effort
positional join is feasible on a *complete* file but would attach timing to at
most a couple of tools per turn while risking mis-attribution; we judged the
fidelity/complexity trade-off not worth it for v1. If per-tool latency becomes a
real requirement, implement it strictly best-effort (name-ordered match, attach
only on a hit, never fabricate) with fixtures covering clean alignment and
orphan `tool.*` events.

### Large imports balloon `events` storage (fragmented input pointers)

Each orchestrator turn becomes a `ModelEvent` whose `input` is the **whole
conversation up to that turn** (see `events.py`), so a single long thread of *N*
turns carries ~*N²* messages of input across its events. The cost is
concentrated almost entirely in the **orchestrator** thread, which is the one
that grows large: for `CRUX1_full` its 9,423 model turns reference a thread that
grows to ~19,647 messages — **90.8M message slots** in total (≈ *N²*/2). (The
figures in this section were measured before the sanitized-id twin dedup — see
"Keyless turn dedup" above — which removes ~10% of those turns; the shape of
the analysis is unchanged.)
Sub-agent turns are *not* the problem: their threads are short and clean, so
they range-encode to exactly one pair per turn (measured: 1,378 sub-agent events
→ 1,378 ranges, ~0 MiB). The remainder of this note is about the orchestrator.

The parquet writer condenses this with `condense_events`: each input message is
replaced by an integer index into a shared pool (so each unique message is
stored **once**, ~12 MB), and the per-turn index list is range-encoded —
`[0,1,2,…,k]` collapses to a single `[[0, k]]` pair. When inputs are clean
prefixes this turns the *N²* pointer population into ~one range per event
(~130 KB total). The pool keeps the **data** small; range-encoding is what keeps
the **pointers** small.

OpenClaw transcripts defeat the range-encoding, so the pointers stay near *N²*
(~225 MB compact / ~700 MB pretty-printed for `CRUX1_full` — enough to trip the
view's streaming size limit). Two things fragment the index runs:

1. **Repeated message content** (≈45% of breaks). The pool keys on content
   (ignoring message id), so a message whose text recurs maps back to its
   *first* index. Agentic OpenClaw runs repeat content heavily — the `NO_REPLY`
   orchestrator turns (~450), re-injected runtime/system prompts, and tool results that
   recur dozens to hundreds of times. Each repeat lands a stale index mid-prefix
   (`…, 512, 12, 513, …`), breaking a contiguous run into two.
2. **Sub-agent interleaving** (≈55% of breaks). Sub-agent spans are emitted
   inline mid-stream, so their messages take pool indices *between* the
   orchestrator's. An orchestrator prefix then references indices with a forward
   gap at every span boundary.

Net effect for `CRUX1_full`: the orchestrator's 9,423 turns produce ~16.75M
range pairs (avg run ~5 messages, ~1,800 ranges per turn) instead of ~9.4k. It
is **all pointers — no message data is re-stored**; the cost is purely that
range compression recovers almost nothing once contiguity is lost.

A `condense_events` that pooled **per thread, positionally** (orchestrator and
each sub-agent in their own first-seen order, no cross-content dedup) would
restore one `[[0, k]]` range per turn. Storing `input` columns compact rather
than pretty-printed (`indent=None`) removes the ~3× pretty-print overhead but
not the underlying *N²* pointer count.

Note this *N²* also exists **transiently in RAM** during import, before the
writer condenses anything: `build_content` sets each `ModelEvent.input` to a
prefix snapshot of the running thread (`list(messages)` in `events.py`). The
snapshots share `ChatMessage` refs — no bodies are copied — but the list
*pointers* total ~*N²* (~720 MB for `CRUX1_full`). The streaming reader
(`read_telemetry_events`) bounds only the *input* side; it does not bound this
peak. Eliminating it would require not materializing `input` (e.g. storing
offsets and reconstructing), an architecture change we did not take for v1.

### Heartbeat turns in CRUX1 are not marked as utility agents

Heartbeats are not marked as utility agents, despite their volume (82% of CRUX1 user messages). Typically, utility
agents are out-of-band helper calls (title generation, cache warmup) whose output never enters the main thread, so
hiding them is lossless. Heartbeat turns are the opposite: they run in the main session's context window, every
subsequent model call conditions on them, and in CRUX1 they carry most of the activity (~92% of output tokens and all
473 sub-agent spawns). Filtering them would hide the main flow, not noise around it. (Separately, Inspect's utility
heuristics key on system-prompt divergence, and telemetry-hal captures no system prompts at all — so nothing in these
imports can be heuristically classified as utility either.)
