# Plan: Bridge ModelEvent Replacement via JSONL Streaming

## Context

When running Claude Code as an agent inside inspect_swe, two parallel streams of ModelEvents exist:

1. **JSONL-derived** (from Claude Code's stdout) — thin ModelEvents but with full agent hierarchy context (spans, tool events, subagent nesting via Task tools)
2. **Bridge-derived** (from inspect_ai's `model.generate()`) — rich ModelEvents with full `ModelCall` data, proper tool definitions, and config, but no agent parenting context

The goal is to **replace** JSONL-derived ModelEvents with their bridge counterparts while preserving the structural context (spans, tool events, agent hierarchy) that only the JSONL stream provides. This gives us the best of both worlds: rich model call data with correct agent parenting.

## Approach

### Part 1: Preserve message ID in inspect_ai (the join key)

When the Anthropic provider creates a `ChatMessageAssistant`, it auto-generates a `shortuuid` as the message `id`. This same ID flows back to Claude Code (via the bridge's `Message.id` response field) and appears in Claude Code's JSONL as `AssistantMessage.id`. This is our natural join key — but currently neither side preserves it for matching.

**File:** `../inspect_ai/src/inspect_ai/model/_providers/anthropic.py`
- In `model_output_from_message()` (line ~1885), the `ChatMessageAssistant` is created without preserving the Anthropic API response `message.id`
- We do NOT need the API message ID — the bridge's own auto-generated `ChatMessageAssistant.id` is already the join key
- However, we should verify this ID reliably flows through. The key chain is:
  1. `ChatMessageAssistant(...)` at line 1885 → `model_post_init` assigns `self.id = uuid()` (shortuuid)
  2. Bridge's `anthropic_api_impl.py` line 146: `Message.model_construct(id=output.message.id or uuid(), ...)`
  3. Claude Code receives this `Message.id` and writes it to JSONL as `AssistantMessage.id`

**No change needed in anthropic.py** — the ID already flows correctly. What we need is to preserve it when creating the JSONL-derived ModelEvent.

**File:** `events.py` (currently in inspect_scout, will move to inspect_swe)
- In `to_model_event()` (line ~100), set `id=event.message.id` on the `ChatMessageAssistant`:
  ```python
  output_message = ChatMessageAssistant(
      id=event.message.id,  # preserve for bridge correlation
      content=output_content,
      tool_calls=tool_calls if tool_calls else None,
  )
  ```

### Part 2: Move `claude_code_events()` pipeline to inspect_swe

The dependency analysis confirms zero dependencies on inspect_scout — everything is either internal to `_claude_code/` or from `inspect_ai` public APIs.

**Files to copy from `inspect_scout/src/inspect_scout/sources/_claude_code/` to `inspect_swe/src/inspect_swe/_claude_code/`:**

| Source file | Purpose | Notes |
|---|---|---|
| `models.py` | Pydantic models for JSONL format | Full copy |
| `detection.py` | Event type detection & filtering | Full copy |
| `extraction.py` | Message/content extraction | Full copy |
| `tree.py` | Event tree reconstruction | Full copy |
| `util.py` | Timestamp parsing | Full copy |
| `toolview.py` | Tool markdown view | Full copy |
| `events.py` | Core conversion (`claude_code_events`, `_EventProcessor`, `to_model_event`, etc.) | Copy only the conversion functions, NOT `transcripts.py`-level orchestration |

**NOT moved:** `transcripts.py`, `client.py` (file discovery) — these stay in inspect_scout. `transcripts.py` will later import from inspect_swe instead.

**Note:** `client.py` has agent file loading for nested subagents (`_load_agent_events`). In the bridge streaming scenario, subagent events arrive inline via `isSidechain`/`sessionId` — we don't need file-based loading. We should make agent file loading optional/pluggable so inspect_swe can work without it.

### Part 3: Streaming exec + JSONL parsing in claude_code agent

**File:** `inspect_swe/src/inspect_swe/_claude_code/claude_code.py`

Currently `exec_remote()` runs with `stream=False` and stdout is captured as a string after completion (line 252-262). Change to streaming exec so we can process JSONL incrementally.

```python
# Instead of:
result = await sbox.exec_remote(cmd=..., stream=False)
debug_output.append(result.stdout)

# Do:
async with sbox.exec_remote(cmd=..., stream=True) as process:
    async for event in merged_event_stream(process.stdout, bridge_events):
        # event is a fully enriched Event (ModelEvent from bridge, everything else from JSONL)
        transcript()._event(event)
```

Key considerations:
- Need to check `exec_remote` streaming API — what does `stream=True` return? An async iterable of stdout lines?
- JSONL lines from stdout need to be parsed to `dict` and fed into `claude_code_events()`
- The retry/attempts loop (lines 238-301) needs to work with streaming

### Part 4: Bridge ModelEvent collection and replacement

**Collection mechanism:** Use `transcript()._subscribe()` to intercept ModelEvents as they're created by `model.generate()`. The callback fires twice per model call:
1. First with `pending=True` (event created, no output yet)
2. Second with `pending=None` (completed, has `output` and `call`)

We only care about completed events. Build a dict keyed by `output.message.id` (the `ChatMessageAssistant.id`):

```python
bridge_model_events: dict[str, ModelEvent] = {}

def on_event(event: Event) -> None:
    if isinstance(event, ModelEvent) and event.pending is None:
        msg_id = event.output.choices[0].message.id if event.output.choices else None
        if msg_id:
            bridge_model_events[msg_id] = event
```

**Important:** The bridge ModelEvents will arrive on the transcript BEFORE the JSONL event with the same message ID (because the bridge processes the API response, returns it to Claude Code, then Claude Code writes it to JSONL). So by the time we see the JSONL assistant event, the bridge ModelEvent should already be in our dict.

**Replacement logic in `claude_code_events()` wrapper:**

```python
async for event in claude_code_events(jsonl_stream):
    if isinstance(event, ModelEvent):
        msg_id = event.output.choices[0].message.id if event.output.choices else None
        if msg_id and msg_id in bridge_model_events:
            # Replace with bridge ModelEvent (richer data)
            bridge_event = bridge_model_events.pop(msg_id)
            # Copy structural context from JSONL event to bridge event
            bridge_event.span_id = event.span_id
            bridge_event.timestamp = event.timestamp
            yield bridge_event
            continue
    yield event
```

### Part 5: Wire it together

The overall flow in `claude_code.py`:

1. Set up bridge as before (`sandbox_agent_bridge`)
2. Subscribe to transcript to collect bridge ModelEvents
3. Start Claude Code with streaming exec
4. Feed stdout lines through JSONL parser → `claude_code_events()`
5. For each yielded event:
   - If ModelEvent: look up bridge counterpart by message ID, replace if found
   - Otherwise: yield as-is (SpanBeginEvent, SpanEndEvent, ToolEvent, etc.)
6. All events go into the transcript, giving us rich model data with correct agent hierarchy

### Part 6: Update inspect_scout to import from inspect_swe

After the move, `inspect_scout.sources._claude_code.transcripts` should import `claude_code_events` and `process_parsed_events` from `inspect_swe._claude_code.events` instead of the local copy. The local event conversion files can then be removed.

## Key Files

| File | Repo | Action |
|---|---|---|
| `src/inspect_swe/_claude_code/claude_code.py` | inspect_swe | Modify: streaming exec, JSONL parsing, event replacement |
| `src/inspect_swe/_claude_code/events.py` | inspect_swe | New: copied from inspect_scout with modifications |
| `src/inspect_swe/_claude_code/models.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/detection.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/extraction.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/tree.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/util.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/toolview.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_scout/sources/_claude_code/events.py` | inspect_scout | Later: re-import from inspect_swe |
| `src/inspect_scout/sources/_claude_code/transcripts.py` | inspect_scout | Later: update imports |

## Open Questions

1. **`exec_remote` streaming API** — Need to verify what `stream=True` returns. Is it an async context manager yielding stdout lines? Or something else? Also need to handle the fact that stdout chunks could be jagged (i.e. not all split on newlines).
2. **Nested subagent handling** — In streaming mode, subagent events arrive inline via `isSidechain`. But the current code also supports loading subagent files from disk (`client.py`). In the sandbox bridge scenario, do subagents exist as separate Claude Code processes with their own JSONL, or are they inline? This affects whether we need `client.py`.
3. **Event ordering guarantee** — We assume bridge ModelEvents are collected before their JSONL counterparts arrive. If there's a race condition (JSONL arrives first), we'd need a buffering strategy. Worth verifying timing.

## Verification

1. **Unit tests:** Test the message ID preservation in `to_model_event()` — verify `event.message.id` flows through to `ModelEvent.output.message.id`
2. **Integration test:** Run a simple Claude Code eval through inspect_swe, capture the event stream, verify:
   - ModelEvents have `call` data (from bridge)
   - Span hierarchy is correct (from JSONL)
   - Agent nesting is preserved for Task tool calls
3. **Existing tests:** Run `pytest tests/` in inspect_scout to ensure `transcripts.py` changes don't break existing functionality
4. **inspect_swe tests:** Run `pytest` in inspect_swe after the changes


## Working Guidelines

1. **One phase at a time.** Implement, test, and verify each part before moving to the next.
2. **Plan each part.**. Each part should have its own sub-plan discussed and approved before coding. 
2. **Review before commit.** After tests pass, pause and review the code together before committing. Do not auto-commit.
3. **Full tests at each step.** Every phase produces implementation  and tests. 

