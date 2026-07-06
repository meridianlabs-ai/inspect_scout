# OpenClaw native session import

Design for `src/inspect_scout/sources/_openclaw/_sessions/` — the source that
imports **native OpenClaw session files** (the bundles OpenClaw writes under
`~/.openclaw/agents/<agent>/sessions/`). The public entry point is `openclaw()`
and its persisted `source_type` is `"openclaw"`.

This is the second OpenClaw importer. The first, `openclaw_telemetry_hal`
(see [openclaw-telemetry-hal.md](openclaw-telemetry-hal.md)), consumes JSONL
telemetry produced by the `openclaw-telemetry-hal` plugin and exists because
datasets such as CRUX1 were captured that way. The native session bundle is the
canonical, strictly richer format — hence it gets the plain `openclaw` name.
Both importers set `agent="openclaw"` (the agent that produced the run) and can
coexist in one transcript database, distinguished by `source_type`.

Sample data: `.dev/data/fx-demo/sessions/` — one orchestrator (dashboard
surface) that spawns three FX-rate sub-agents, plus `sessions.json` and
trajectory files. All schema observations below come from that capture
(session schema `version: 3`).

## The native bundle

For each session (orchestrator and each sub-agent) OpenClaw writes, named by
`sessionId`:

- **`<sessionId>.jsonl`** — the conversation: a `parentId`-linked tree of
  records with full message content, per-turn `usage`, `responseId`, and rich
  `toolResult.details`.
- **`<sessionId>.trajectory.jsonl`** — a runtime event trace
  (`session.started`, `context.compiled`, `prompt.submitted`,
  `model.completed`, `trace.artifacts`, `session.ended`); every record's
  envelope binds `sessionId` + `sessionKey` + `runId`.
- **`<sessionId>.trajectory-path.json`** — pointer stamping the trajectory's
  `sessionId`.

and one shared **`sessions.json`** — a registry keyed by runtime `sessionKey`
(`agent:<agentName>:<kind>[:...]:<uuid>`), one entry per session, carrying the
authoritative topology (`spawnedBy`, `parentSessionKey`, `label`, `spawnDepth`,
`subagentRole`), run metadata (`status`, timings, `runtimeMs`, channel/origin),
token/cost rollups, and a `systemPromptReport` (see "System prompts" below).

Caveat: `sessions.json` is a **global, mutable index**. It may reference
sessions from other runs or files that no longer exist, so everything read from
it is intersected with the files actually on disk.

## Scope and discovery

Entry point (mirrors the Claude Code importer so the CLI's promoted
`--limit`/`--from`/`--to` options work):

```python
async def openclaw(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator[Transcript]
```

`path` accepts:

- `None` — scan the default `~/.openclaw/agents/*/sessions/`
- a sessions directory (contains session `*.jsonl`), e.g. a copied bundle
- a parent directory (`~/.openclaw`, `~/.openclaw/agents`) — scan
  `agents/*/sessions/` (or `*/sessions/`) beneath it
- a single session `.jsonl` file

`*.trajectory.jsonl` and `*.trajectory-path.json` are excluded from discovery,
and trajectories are not consumed at all in v1 (see "Known limitations").
`from_time`/`to_time` filter on file mtime; files are processed newest-first so
`limit` avoids touching old files.

## Transcript boundaries and classification

**One transcript per orchestrator session file.** `sessions.json` classifies
files: entries with `spawnedBy` set are sub-agents, consumed only as nested
agent spans inside their parent's transcript and never yielded standalone.

`parentSessionKey` chains successive orchestrator sessions (conversation
continuity across turns — the sample registry shows five chained dashboard
sessions). v1 does **not** merge chains; the lineage is recorded in transcript
metadata so a future version (or a scanner) can reassemble it, the way the
Claude Code importer merges slug groups.

When `sessions.json` is absent (e.g. a partial copy), the importer warns once
and imports every discovered file as a standalone transcript — no
classification, no sub-agent spans. Predictable degradation; no content
heuristics.

## Identity

`transcript_id = source_id = sessionId` — the `session` header record's `id`,
cross-checked against the filename. Native files fix the telemetry-hal identity
problem outright: the id is per-run, globally unique, and stable across
re-imports, so no timestamp suffix is needed. `source_uri` is the session file
path.

## Record mapping

Records are processed **in file order** (append order, hence chronological).
The `parentId` tree is used for validation, not traversal: in observed data the
message chain is linear, with `leaf` records appearing only as bookkeeping
side-children. If a true divergent branch is encountered (two `message` records
sharing a parent), the import fails with an error naming the session — better
to learn what branching looks like in real data than to guess a linearization.

| Record | Handling |
|---|---|
| `session` | Header: identity, `cwd`, schema `version` → metadata |
| `message` role `user` | `ChatMessageUser` in the thread. Includes runtime-injected internal-context messages (e.g. sub-agent announce results) — they are real model input |
| `message` role `assistant` | `ModelEvent` (input = running thread so far; per-turn `usage`, `model`, `stopReason`, `responseId`) + `ChatMessageAssistant`; then one `ToolEvent` per `toolCall` block |
| `message` role `toolResult` | Completes the matching `ToolEvent` by `toolCallId`: result content, real completion timestamp (true call→result spans), `isError` → `ToolEvent.failed`/`ToolCallError` (as in telemetry-hal), and `details` (e.g. `exec` `durationMs`, `exitCode`) into `ToolEvent.metadata` + `ChatMessageTool` |
| `custom_message` (e.g. `openclaw.sessions_yield`) | `ChatMessageUser` — injected into the next run's context, so the model saw it |
| `model_change` / `thinking_level_change` | Not events in v1; `model_change` seeds the initial model name |
| `custom` (`model-snapshot`, `openclaw:bootstrap-context:*`) | Ignored for content (run-boundary bookkeeping) |
| `leaf` | Ignored (branch bookkeeping) |
| anything else | **Fail the import**, naming the record type |

Unknown `message` roles and unknown assistant content block types also fail
loudly — the same strictness precedent as telemetry-hal's session-kind check.
Torn/unparseable JSONL lines (crash mid-append) are skipped with a warning,
matching the Claude Code importer. Empty files, or files whose records produce
no messages, yield no transcript.

What this fixes relative to telemetry-hal: each turn appears exactly once (the
cumulative-snapshot dedup and sanitized-toolCall-id machinery disappears
entirely), timestamps are per-message, `usage`/`responseId` are per-turn, tool
results carry real completion times and details, and sub-agent joins are exact.

## Sub-agent spans

When an orchestrator assistant turn calls `sessions_spawn`, the paired
`toolResult` JSON names the `childSessionKey` (same structural extraction as
telemetry-hal's `child_session_key_of`). Resolution is two id-keyed lookups, no
heuristics:

1. `childSessionKey` → `sessions.json` entry → `sessionId`
2. `sessionId` → sibling file `<sessionId>.jsonl`

The registry's `sessionFile` is an absolute path from the capture machine, so
only its basename is trusted, resolved against the local directory.

The child file is parsed with the same parser and emitted exactly as the two
existing importers emit delegated work: a `SpanBeginEvent(type="agent")`
anchored at the spawn call, the spawn `ToolEvent` folded in as the span's first
child (tagged `agent_span_id`), the child's own `ModelEvent`s/`ToolEvent`s with
`span_id` set, and a `SpanEndEvent` at the child's last timestamp. The span
name is the spawn `label` argument; span metadata carries the child's
`session_key`, `session_id`, `task`, and registry enrichment (`status`, token
rollups). Nested spawns recurse, depth-bounded (`max_depth=5`, as in the
Claude Code importer). Sub-agent messages never enter the main thread.

**Announce results.** A sub-agent's final report arrives in the orchestrator's
own file as a runtime-injected *user* message (an internal-context block naming
the child's `session_key`). It is already in the thread and is kept as-is. This
closes telemetry-hal's "sub-agent responses are not surfaced" limitation for
free, with deterministic attribution.

Degraded cases:

- Spawn result unparseable or `status != "accepted"` → plain tool event, no
  span (a failed spawn is not an import error).
- Child in registry but file missing on disk → warn, skip the span, keep the
  spawn tool event.
- Child not in registry → warn, skip the span, keep the spawn tool event.

## System prompts

Investigated because telemetry-hal captures nothing about system prompts. The
native format is better, but only partially:

- The session `.jsonl` has **no system-role records**; the system prompt is
  compiled at runtime and never written to the session file.
- `sessions.json` carries a `systemPromptReport` per session: char counts, a
  **sha256 hash** of the system prompt, project/non-project split, every
  injected workspace file (name, path, per-file char counts, truncation
  flags), the skills/tools inventory, and sandbox mode. Provenance and drift
  detection, but not the text.
- The trajectory's `context.compiled`/`prompt.submitted` events have a
  `data.systemPrompt` field intended to carry the full text, but in our capture
  it is dropped for every run: the prompt is 34,375 chars and the trajectory
  writer's per-field limit is 32,768 (`"reason": "trajectory-field-size-limit"`).

The importer therefore copies the `systemPromptReport` summary into transcript
metadata and documents the text itself as unavailable. Future work: read
`context.compiled.systemPrompt` from trajectories when present and untruncated
(plausible for sub-agents with smaller prompts).

## Transcript fields

- `transcript_id` / `source_id` / `source_uri` — see "Identity"
- `date` — first message timestamp
- `model` — most recent assistant turn's model (seeded by `model_change`)
- `task_id` — `transcript_id` (no slug-like grouping exists in the format)
- `task_set` — `None`
- `agent` — `"openclaw"`
- `total_tokens` — billable per-call spend (input + output + cacheRead +
  cacheWrite) summed over orchestrator and sub-agent assistant turns — the
  convention shared by the other importers. `ModelUsage` mapping mirrors
  telemetry-hal's (`reasoning_tokens` stays 0: OpenClaw bills reasoning inside
  `output`)
- `total_time` — wall clock minus idle time from the built timeline (as in the
  Claude Code importer; native per-message timestamps make this meaningful)
- `messages` — the orchestrator thread built during event construction (as in
  telemetry-hal); stable message ids applied across model events and thread,
  as in both existing importers
- `metadata` — `session_key`, `parent_session_key`, `cwd`, `session_version`,
  `n_subagents`, `subagent_session_ids`, `system_prompt_report`, and registry
  enrichment when present (`status`, `label`, channel/origin)

## Module layout

Mirrors the telemetry-hal subpackage:

```
sources/_openclaw/
  __init__.py          # exports openclaw_telemetry_hal + openclaw
  _telemetry_hal/      # existing plugin importer
  _sessions/
    __init__.py        # exports openclaw, OPENCLAW_SOURCE_TYPE
    client.py          # discovery, registry loading, file reading
    parse.py           # records → typed intermediate (per session file)
    events.py          # intermediate → events + messages (spans, recursion)
    transcripts.py     # openclaw() entry point, Transcript assembly
```

`sources/__init__.py` adds `openclaw` to `__all__`, which auto-registers it
with `scout import`.

## Testing

Tests live in `tests/sources/openclaw_source/sessions/`. Fixtures are a
checked-in copy of the fx-demo bundle (small: one orchestrator, three
sub-agents) plus tiny synthetic files for edge cases. Table-driven where
natural. Coverage:

- discovery modes (default dir, sessions dir, parent dir, single file;
  trajectory exclusion; mtime filters; `limit`)
- registry classification (sub-agent files not yielded standalone)
- orchestrator transcript shape (message roles/order including injected
  context messages, `ModelEvent` inputs, usage, tool completion timestamps,
  `exec` details in metadata)
- sub-agent span nesting, spawn folding, recursion bound
- identity (`transcript_id` = sessionId) and aggregates (tokens, time, model)
- degraded modes (no registry, missing child file, torn last line, failed
  spawn)
- strict failures (unknown record type, unknown role, divergent branch)
- integration: import the fixture bundle end-to-end → exactly one transcript
  with three nested agent spans

The fx-demo capture lacks compaction records, true branches, telegram-surface
sessions, and multi-level spawn trees. Richer captures exist (more complex
OpenClaw sessions are available on request) and should be used to (a) manually
sanity-check the importer during development and (b) mint additional fixtures —
especially for whatever the compaction record looks like, since unknown record
types fail the import by design.

## Known limitations

- **Compaction records unsupported (by design, temporarily).** No compaction
  record appears in the sample, so there is nothing to design against. The
  first compacted session will fail the import with the record type named;
  support gets added when we can see the real shape.
- **System prompt text unavailable** — see "System prompts".
- **`parentSessionKey` chains are not merged** — one transcript per session
  file; lineage in metadata only.
- **Trajectory files are not consumed** — per-run boundaries, per-turn
  wall-clock, compiled tool definitions, and (occasionally) system prompt text
  are all in there; deliberately out of scope for v1.
- **No registry → no topology.** Without `sessions.json`, every file imports
  standalone and sub-agent files surface as their own transcripts (with their
  `[Subagent Context]` prompt visible as the first user message).
