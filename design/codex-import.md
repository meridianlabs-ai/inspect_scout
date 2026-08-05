# Codex CLI importer — research and design

Research notes and a design proposal for a `codex` transcript source, based on
(1) a deep-dive into the existing Claude Code importer, (2) the OpenAI Codex CLI
rollout format (from the `openai/codex` source, HEAD ≈ v0.146.1/0.147-alpha,
Aug 2026), and (3) inspect_swe's current Claude Code and Codex support.

## 1. How the Claude Code importer works today

### 1.1 Two-repo split

The importer is split across inspect_scout and inspect_swe (`inspect-swe>=0.2.56`
is a dependency). Scout owns discovery and transcript shaping; inspect_swe owns
the JSONL→event conversion library, shared with the live Claude-Code-as-agent path:

| Layer | Location |
|---|---|
| Source entry point + slug merging + transcript assembly | `inspect_scout/sources/_claude_code/transcripts.py` |
| File discovery, path decode, bounded peeking | `inspect_scout/sources/_claude_code/client.py` |
| Scout-specific subagent file loader (`AgentEventLoader`) | `inspect_scout/sources/_claude_code/events.py` |
| Pydantic JSONL models + `consolidate_assistant_events` | `inspect_swe/_claude_code/_events/models.py` |
| Event detection/filtering | `inspect_swe/_claude_code/_events/detection.py` |
| uuid/parentUuid tree + `/clear` splitting | `inspect_swe/_claude_code/_events/tree.py` |
| Message/metadata/usage extraction | `inspect_swe/_claude_code/_events/extraction.py` |
| Core conversion (`_EventProcessor`, `process_parsed_events`) | `inspect_swe/_claude_code/_events/events.py` |

History (see `design/claude-code-events.md`): the conversion modules originally
lived in scout, were copied to inspect_swe for the live agent, then scout deleted
its copies and re-imported. `transcripts.py`/`client.py` deliberately stayed in
scout. The one real extension seam is the `AgentEventLoader` Protocol
(`inspect_swe events.py:76-92`) — the converter is agnostic about where subagent
events come from (files for scout, stream buffers for the live path).

### 1.2 The source contract

There is no base class or registry. A source is an async generator exported from
`inspect_scout.sources.__all__` with the conventional signature:

```python
async def claude_code(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator[Transcript]: ...
```

`limit`/`from_time`/`to_time` are "promoted" CLI params (`--limit/--from/--to`);
everything else goes through `-P name=value`. The CLI discovers sources by
introspecting `__all__` (`_cli/import_command.py:28-41`). Consumers do
`db.insert(claude_code(...))` — streaming, idempotent by `transcript_id`.

### 1.3 Pipeline per file

```
discover (glob, mtime filter, newest-first) → peek slug (≤10 lines) → group by slug
→ backfill time-filtered slug partners → per file:
    read JSONL → parse_events (allowlist user/assistant/system, extra="ignore")
    → consolidate_assistant_events → build_event_tree (uuid/parentUuid)
    → flatten chronologically → split_on_clear → per segment:
        filter chrome → _EventProcessor → scout events
        → timeline_build → span_messages(root, compaction="all")
        → stable_message_ids → Transcript
```

Key mechanics worth carrying forward:

- **Accumulated-messages model**: `_EventProcessor` keeps a running message list;
  each assistant event's `ModelEvent.input` is that reconstruction of what the
  model saw. Compaction clears it.
- **Monotonic timestamps**: parsed timestamps forced strictly increasing (+1ms),
  unparseable → epoch sentinel (so broken timestamps don't stretch timelines to now).
- **Span shapes**: regular tool → `SpanBegin(type="tool") → ToolEvent → SpanEnd`;
  Task/Agent tool → `SpanBegin(type="agent") → ToolEvent → nested subagent events
  (re-parented) → SpanEnd`.
- **Messages are derived, not assembled**: `span_messages(timeline.root,
  compaction="all")` grafts pre-compaction segments and excludes subagent spans.
- **Dedup**: deterministic `transcript_id` (session uuid + optional `-N` segment
  suffix) + DB-level dedup; `agent-*.jsonl` excluded from discovery so subagents
  can never import twice (loaded only on demand via their parent's Task call).
- **Lenient parsing everywhere**: warn-and-skip bad lines, silently drop unknown
  event types, `extra="ignore"` on all models, no version gating.

### 1.4 The five tricky cases

1. **Fragmented assistant turns** — one API response written as several JSONL
   lines sharing `message.id` (thinking / text / each tool_use separately; only
   the last carries final usage). `consolidate_assistant_events`
   (`models.py:277-346`) merges *consecutive* same-id fragments, taking
   model/id/stop_reason/usage from the last; id-less lines pass through.
2. **Plan/exec slug pairs** — plan mode and execution are two files with
   different `sessionId`s sharing a `slug`. Files are grouped by peeked slug;
   `_backfill_slug_groups` re-adds partners a time/session filter would hide;
   `_merge_transcripts` orders by first-event timestamp, inserts an
   `InfoEvent(source="claude-code")` "Context reset" boundary between sessions
   (timestamped from the *next* session to dodge clock skew), and records
   order-deduped `metadata["session_ids"]`.
3. **`/clear` splitting** — detected via `<command-name>/clear</command-name>`;
   split happens *before* chrome filtering (filtering removes the marker). Multi-
   segment files get `<session>-0`, `<session>-1` ids; single-segment files keep
   the clean id (re-import stability).
4. **Task subagent sidechains** — file path: agentId dug out of the tool result
   by JSON parse → embedded-JSON regex → `agentId: <hex>` plaintext regex →
   `agent_id: <team-id>` regex; file found at
   `<session-dir>/<stem>/subagents/agent-<id>.jsonl` (2.1.x) or legacy flat
   layout; team agents (human-readable ids, hashed filenames) matched by
   comparing the spawn prompt's first 200 chars against each candidate file's
   first user message. Loaded events are recursively converted (max_depth=5) and
   re-parented under the agent span. Streaming path instead buffers
   `isSidechain` events by `sessionId` and FIFO-matches to Task tool ids.
5. **Compaction** — `system/compact_boundary` → `CompactionEvent(type="summary",
   tokens_before=preTokens, metadata={trigger, content})` +
   `accumulated_messages.clear()`. `span_messages(compaction="all")` grafts the
   pre-compaction conversation back into `Transcript.messages` while the
   boundary stays in the event timeline.

## 2. The Codex rollout format

All under `$CODEX_HOME` (default `~/.codex`; env var overrides):

```
sessions/YYYY/MM/DD/rollout-YYYY-MM-DDThh-mm-ss-<thread-uuid>.jsonl      # canonical transcript
sessions/.../rollout-*.jsonl.zst      # idle files zstd-compressed since ~v0.140
archived_sessions/                    # same format, moved on archive
history.jsonl                         # cross-session prompt history (not transcripts)
session_index.jsonl                   # thread-name index
state_5.sqlite etc.                   # derived caches (rollouts remain canonical)
```

### 2.1 Envelope and item types (v0.33+)

Every line: `{"timestamp": "<rfc3339>", "ordinal"?: <u64>, "type": "<variant>",
"payload": {...}}`. `RolloutItem` variants:

- **`session_meta`** (first line; forks may copy a second one — first wins):
  `session_id`/`id` (thread id), `forked_from_id?`, `parent_thread_id?`,
  `timestamp`, `cwd`, `originator`, `cli_version`, `source`
  (`cli`/`vscode`/`exec`/`mcp`/`{custom}`/`{subagent: review|compact|{thread_spawn}}`),
  `base_instructions?`, `history_mode` (`legacy`|`paginated`), `history_base?`
  (parent-prefix-by-reference), `git: {commit_hash, branch, repository_url}`, …
- **`response_item`** — the model-visible conversation (Responses-API items):
  `message` (role user/assistant/developer; content input_text/output_text/
  input_image/…; assistant `phase`: commentary|final_answer), `reasoning`
  (`summary[]` + usually `encrypted_content`, plaintext `content` only for some
  providers), `function_call` (`name`, `arguments` JSON-string, `call_id`),
  `function_call_output` (`call_id`, `output`: **string OR content array**),
  `local_shell_call`, `custom_tool_call(_output)` (e.g. `apply_patch`),
  `web_search_call`, `compaction`/`context_compaction` (encrypted, remote),
  `agent_message` (inter-agent), `tool_search_call(_output)`.
- **`compacted`** (local compaction): `{message: <summary>, replacement_history:
  [ResponseItem…], window_id chain…}` — `replacement_history` is the exact
  post-compaction context.
- **`turn_context`** — per real user turn: `cwd`, `approval_policy`,
  `sandbox_policy`, `model`, `effort`, … (model can change mid-session).
- **`event_msg`** — persisted subset only (`rollout/src/policy.rs`):
  always: `token_count` (cumulative + last-turn usage + rate limits),
  `turn_started`, `turn_complete` (incl. `error`), `turn_aborted`
  (`interrupted|replaced|review_ended|budget_limited`), `thread_rolled_back`, …;
  legacy-mode only: `user_message`, `agent_message`, `agent_reasoning`,
  `entered/exited_review_mode`, `patch_apply_end`, `mcp_tool_call_end`,
  `context_compacted`, `sub_agent_activity`;
  paginated-mode only: `item_completed` with `TurnItem`s
  (CommandExecution with `aggregated_output`, McpToolCall, FileChange, Plan, …).
  Errors, deltas, exec begin/end, approvals are **not** persisted.
- **`world_state`**, **`inter_agent_communication`** (2026 additions).

### 2.2 Behaviors an importer must handle

- **Resume appends to the same file** (no new meta line; wall-clock gaps normal).
  One file = one thread across CLI invocations.
- **Fork creates a new file** with `forked_from_id`; `Copied` persistence copies
  the truncated parent history (including the parent's `session_meta`) into the
  new file; `Referenced` (paginated) stores only new records and points at the
  parent via `history_base` ordinals/byte offsets.
- **`thread_rolled_back`** marks in-place history truncation (undo) — earlier
  items remain physically in the file.
- **Turn boundaries**: a model response is several consecutive `response_item`
  lines (reasoning, message(s), function_call(s)) with no shared id;
  `turn_started`/`turn_complete` and `function_call_output`/user items delimit.
- **Duplicate representation**: real user turns appear both as a `response_item`
  message and a `user_message` event (legacy mode); assistant text likewise.
  Codex's own `rollout_reconstruction.rs` dedupes by pairing — we must too.
- **Pseudo-user messages**: `<user_instructions>`, `<environment_context>`,
  `<skills_instructions>`, `<collaboration_mode>`, … arrive as role=user items;
  newer builds wrap genuine user text after a `## My request for Codex:` marker.
- **Exec output**: `function_call_output.output` is the truncated,
  model-formatted text (`Exit code: … / Wall time: … / Output: …`); pre-≈0.4x
  files instead contain a JSON string `{"output", "metadata": {exit_code,
  duration_seconds}}`. Full output only exists in paginated `CommandExecution`
  items. Tool names: `shell`, `shell_command`, `exec_command`/`write_stdin`,
  plus `local_shell_call` items.
- **Subagents**: review mode and multi-agent `thread_spawn` create **separate
  child rollout files** with `source: {subagent: …}` and `parent_thread_id`;
  the parent's `spawn_agent` tool result carries the child thread id (inspect_swe
  `_codex_cli/_events/detection.py` already parses these payloads).
- **Compaction**: local → `compacted` item with plaintext summary +
  `replacement_history`; remote → encrypted `compaction`/`context_compaction`
  response items; auto-compaction near the context limit and manual `/compact`
  share machinery. `token_count` events bracket it.
- **Interruption**: `turn_aborted`; may leave a dangling `function_call` with no
  output (codex synthesizes "aborted" outputs in memory only).
- **Compression**: idle rollouts become `.jsonl.zst`.
- **Versioning**: no format-version field. Pre-v0.33 files have no envelope
  (bare `SessionMeta` line then raw ResponseItems). Field-level drift handled by
  sniffing (`session_id` backfilled from `id`, `instructions` →
  `base_instructions`, ghost_snapshot lines stripped by modern readers, numeric
  → uuid `window_id` migration, …).

## 3. Trick-by-trick mapping

| Claude Code trick | Codex analogue | Assessment |
|---|---|---|
| Fragmented assistant lines merged by `message.id` | Group **consecutive assistant-side `response_item`s** (reasoning → message → function_calls) into one `ModelEvent`; boundary = user/tool-output item or `turn_*` event. No shared id to lean on. | Same shape, different key: positional grouping instead of id grouping. |
| Slug pair merge + backfill | **Fork/`history_base` linkage.** Resume needs nothing (same file). Copied forks: self-contained file, import standalone, record `forked_from_id` in metadata (accept content overlap with the parent, as codex itself does). Referenced forks/subagents (paginated): file is *incomplete* without the parent prefix → resolve parent by thread id, backfill even if time-filtered — the direct analogue of `_backfill_slug_groups`. | Backfill machinery ports; grouping key is an explicit id, not a slug — simpler and unambiguous. |
| `/clear` split, `-N` suffixes | **Not needed** — `/new` starts a new file. Instead: **`thread_rolled_back` replay** — drop rolled-back items when reconstructing (or record an InfoEvent and keep both? see open questions). | New problem replaces old one. |
| Sidechain buffering + FIFO + agentId regex archaeology | **Explicit ids everywhere**: child rollout has `parent_thread_id`; parent's `spawn_agent` result carries the child thread id; child file is found by globbing for `rollout-*-<thread-id>.jsonl`. Reuse inspect_swe `_codex_cli/_events/detection.py` payload parsers. Exclude `source: subagent` files from top-level discovery (= the `agent-*.jsonl` exclusion, our intrinsic dedup). | Strictly easier than Claude Code. Re-parenting under agent spans via the existing `AgentEventLoader`-style seam. |
| `compact_boundary` → CompactionEvent + graft | `compacted` item → `CompactionEvent(type="summary")`; `tokens_before` from the last preceding `token_count`; then set `accumulated_messages` to the converted `replacement_history` (codex tells us the exact post-compaction context — better than Claude Code's clear-and-rebuild). Remote/encrypted compaction → CompactionEvent with metadata noting opacity. `span_messages(compaction="all")` grafting works unchanged. | Same scout-side machinery; richer source data. |

Novel codex-only hazards (no Claude Code precedent):

1. **Dual/triple representation** of the same content (`response_item` vs legacy
   `event_msg` vs paginated `item_completed`). Rule: `response_item`s are the
   source of truth for messages/tools; persisted events supply *supplements only*
   (usage, aborts, turn errors, MCP structured results, full command output).
2. **Two history modes** (`legacy` default, `paginated`), with different
   persisted-event sets and `ordinal`s. Phase 1 can target legacy + the
   mode-independent items and treat `history_base` resolution as the one
   paginated feature we must support (subagent/fork completeness depends on it).
3. **Pseudo-user messages** — must classify XML-tagged role=user items as
   context, not user speech (they're also the best source for `metadata.cwd`
   etc. on old files lacking rich meta). Strip `## My request for Codex:`
   wrappers.
4. **`function_call_output` polymorphism** (string | content array | old
   JSON-encoded string) and image content in MCP outputs.
5. **Encrypted reasoning** — `ContentReasoning` with summary text as the
   reasoning body and `redacted=True` semantics for encrypted-only items.
6. **Dangling `function_call` on interrupt** — flush-pending with
   `turn_aborted` context (Claude Code's `flush_pending` pattern ports).
7. **`.zst` files** — needs `zstandard` (scout already has heavyweight deps;
   small cost). Skip-with-warning fallback if we'd rather not add it.
8. **Pre-envelope legacy files (≤v0.32)** — propose: detect and skip with a
   warning in phase 1 (sniff: first line has `type: session_meta` → supported;
   bare `{"id": …, "timestamp": …}` → legacy, skipped).
9. **Non-conversation rollouts** — `source: {subagent: compact}`,
   `{internal: memory_consolidation}` etc. must be excluded from discovery.
10. **Model/config drift mid-session** — `turn_context` per turn; ModelEvent
    model should come from the latest preceding `turn_context`, not session meta.

## 4. Proposed architecture

Follow the established two-repo split from day one (the Claude Code importer
took the scout-first path and then had to migrate — see
`design/claude-code-events.md` Part 2):

**inspect_swe** (`src/inspect_swe/_codex_cli/_events/` — new modules beside the
existing bridge-only `consumer.py`/`detection.py`/`toolview.py`):

- `models.py` — Pydantic models for `RolloutLine`, `RolloutItem` payloads,
  `ResponseItem` variants, persisted `EventMsg`s; `extra="ignore"`, unknown
  `type`s dropped (same forward-compat posture as Claude Code).
- `rollout.py` (or extend `detection.py`) — sniffing, pseudo-message
  classification, turn grouping, rollback replay, dedup of event/response pairs.
- `extraction.py` — content conversion (ContentText/Reasoning/Image, ToolCall),
  usage from `token_count`, metadata from session_meta/turn_context/
  environment_context.
- `events.py` — `_RolloutProcessor` mirroring `_EventProcessor`: accumulated
  messages, monotonic timestamps, pending-call map keyed on `call_id`,
  tool/agent span emission, CompactionEvent, plus an `AgentEventLoader`-style
  Protocol for child-rollout loading. Reuse `toolview.py` for exec/apply_patch/
  spawn_agent/web_search views.

**inspect_scout** (`src/inspect_scout/sources/_codex/`):

- `client.py` — discovery under `$CODEX_HOME/sessions` (+ optional
  `archived_sessions`), date-partition walk, mtime filter, newest-first,
  `.zst` handling, bounded peek of the `session_meta` line (line 1 — cheaper
  than Claude Code's 10-line peek), child/internal-rollout exclusion,
  `find_child_rollout(thread_id)`.
- `events.py` — the child-rollout loader injected into the inspect_swe
  converter (recursion + re-parenting, max depth).
- `transcripts.py` — `async def codex(path, session_id, from_time, to_time,
  limit)`; fork/`history_base` backfill; transcript assembly identical in shape
  to Claude Code's (`timeline_build` → `span_messages(compaction="all")` →
  `stable_message_ids`).
- Registration in `sources/__init__.py`; docs stanzas in
  `docs/reference/sources.qmd` and `docs/db_importing.qmd`.

Transcript field mapping:

| Field | Value |
|---|---|
| `transcript_id` / `source_id` | thread id (rollout uuid) |
| `source_type` | `"codex_cli"` |
| `source_uri` | `file://<rollout path>#<thread id>` |
| `agent` | `"codex-cli"` |
| `date` | session_meta `timestamp` (fall back to first line timestamp) |
| `task_set` | session_meta `cwd` |
| `task_id` | thread name from `session_index.jsonl` if present, else thread id |
| `model` | first `turn_context.model` (metadata records changes) |
| `total_tokens` | sum of per-ModelEvent usage (from `token_count.last`), cross-checked against final cumulative |
| `metadata` | `cwd`, `git` (branch/commit/url), `cli_version`, `originator`, `source`, `forked_from_id`, `history_mode`, `model_provider` |

**inspect_swe follow-on (separate PR)** — sandboxed eval runs currently discard
session files; to make them importable: widen the dead `_last_rollout()` helper
(`_codex_cli/codex_cli.py:498-510`) to enumerate all rollouts under
`$CODEX_HOME/sessions` (attempts + subagents produce several), read them back
from the sandbox, and attach to the eval log (pattern: `ClaudeCodeDebug`
StoreModel). Same gap exists for Claude Code (`~/.claude/projects/<encoded>/
<session-id>.jsonl` is host-predictable since the session id is allocated
host-side). Then a scout source can import from eval logs, not just local
machines.

## 5. Testing and verification

Mirror the Claude Code suite (`tests/sources/claude_code_source/`, 5 files /
~3.2k lines / 12 hand-authored fixtures of 2–6 lines each):

**Unit fixtures** (hand-written, one per behavior, exact-arithmetic assertions —
token counts and ids chosen so tests assert `== 300`, not `> 0`):

- simple conversation (meta + turn_context + user + reasoning + assistant +
  token_count + turn_complete)
- shell `function_call`/`function_call_output` pair; old-format JSON output
  string; output-as-content-array (MCP with image)
- multi-item assistant turn (reasoning + commentary message + 2 function_calls)
  → single consolidated ModelEvent
- pseudo-user messages (`environment_context`, `user_instructions`,
  `## My request for Codex:` wrapper) → filtered/classified, not user speech
- duplicate `user_message`/`agent_message` events → deduped against
  response_items
- local compaction (`compacted` with `replacement_history`) → CompactionEvent +
  post-compaction `ModelEvent.input` equals replacement history; remote
  encrypted compaction
- interrupted turn (`turn_aborted`, dangling function_call) → flushed pending
  tool
- review-mode pair (parent + child rollout with
  `source: {subagent: "review"}`) → nested agent span; thread_spawn multi-agent
  pair
- copied fork (second `session_meta` mid-file, `forked_from_id`) — first meta
  wins; referenced fork (`history_base`) → parent backfill incl. the
  `os.utime`-backdated time-filter defeat test (port of
  `test_slug_backfill_with_time_filter`)
- `thread_rolled_back` replay
- `.zst` fixture; pre-envelope legacy file → skipped with warning; unknown
  item/event types → ignored
- discovery: date-partition walk, `session_id` filter, mtime window, child
  rollout exclusion, `limit` early-exit

**Verification against reality** (the format is reverse-engineered from Rust
source, so fixtures alone prove self-consistency, not fidelity):

1. **Real-session corpus**: run codex CLI on scripted toy tasks (a plain task,
   a tool-heavy task, a `/compact`, an interrupt, a review, a resume, a fork)
   across a small version matrix (current stable + the oldest version we claim);
   snapshot the produced rollouts as integration fixtures (scrub paths/keys).
2. **Property checks over any corpus** (importer smoke harness): every file
   yields a transcript or a logged skip reason; no user `response_item` lost;
   every `function_call` paired or flushed; per-event usage sums ≈ final
   cumulative `token_count`; timestamps monotonic; re-import → identical
   `transcript_id`s and DB dedup.
3. **Differential check vs the bridge** (once inspect_swe captures rollouts):
   the same eval run produces both a bridge-built transcript and an imported
   one — message texts, tool sequence, and token totals should agree. This is
   the strongest end-to-end verification available and also validates the
   inspect_swe capture work.
4. **Cross-check against codex's own reader**: `codex resume`/`codex exec
   resume --last` on our fixture files must not error (guards against fixtures
   drifting from the real schema).

## 6. Open questions

1. **Where to develop first** — inspect_swe from the start (recommended; the
   migration cost was already paid once for Claude Code, and the
   `AgentEventLoader` seam exists) vs scout-local then upstream. Cross-repo
   iteration means scout PRs pin a new `inspect-swe` release.
2. **Copied-fork overlap** — import parent and fork both (duplicated prefix
   content across two transcripts) or attempt prefix-dedup? Proposal: import
   both, record `forked_from_id`; dedup is analysis-time concern.
3. **Rollback semantics** — replay `thread_rolled_back` (drop truncated items,
   matching what the model saw) vs keep items + boundary InfoEvent (matching
   the compaction philosophy of "boundary stays in the timeline"). Proposal:
   replay for `accumulated_messages`/ModelEvent.input, keep an InfoEvent in the
   event stream.
4. **Paginated mode scope** — full support in phase 1, or legacy +
   `history_base` resolution only?
5. **`archived_sessions/`** — include in default discovery or behind a param?
6. **`exec`/`mcp`-sourced rollouts** — codex's own pickers hide them; we likely
   *want* them (headless runs are exactly what scout analyzes). Include, record
   `source` in metadata.
7. **zstandard dependency** — add, or skip `.zst` with a warning?
