# Plan: Bridge ModelEvent Replacement via JSONL Streaming

## Context

When running Claude Code as an agent inside inspect_swe, two parallel streams of ModelEvents exist:

1. **JSONL-derived** (from Claude Code's stdout) — thin ModelEvents but with full agent hierarchy context (spans, tool events, subagent nesting via Task tools)
2. **Bridge-derived** (from inspect_ai's `model.generate()`) — rich ModelEvents with full `ModelCall` data, proper tool definitions, and config, but no agent parenting context

The goal is to **replace** JSONL-derived ModelEvents with their bridge counterparts while preserving the structural context (spans, tool events, agent hierarchy) that only the JSONL stream provides. This gives us the best of both worlds: rich model call data with correct agent parenting.

## Key Design Decisions (Resolved)

### Join Key
The `ChatMessageAssistant.id` (a shortuuid auto-generated in inspect_ai) flows through the entire pipeline:
1. Created in `model_output_from_message()` → `ChatMessageAssistant(...)` → `model_post_init` assigns `self.id = uuid()`
2. Bridge returns it as `Message.id` to Claude Code
3. Claude Code writes it to JSONL as `AssistantMessage.id`

No changes needed in `anthropic.py` — the ID already flows correctly.

### Streaming API
`exec_remote(stream=True)` returns an `ExecRemoteProcess` (async iterable, NOT a context manager). It yields:
- `Stdout(data: str)` — raw chunks (not lines)
- `Stderr(data: str)` — raw chunks
- `Completed(exit_code: int)` — process finished

Since stdout delivers **chunks not lines**, we need a simple line buffer: accumulate chunks, split on `\n`, yield complete lines, keep the remainder.

Cleanup: call `await proc.kill()` explicitly. Cancellation auto-kills.

### Subagent Handling
In the streaming/bridge scenario, subagent events arrive **inline** in the same stdout JSONL stream, distinguished by `isSidechain=True` and `sessionId`. The existing `events.py` has a FIFO queue mechanism that buffers and correlates subagent events to their parent Task tool calls. `client.py` (file-based agent loading) is NOT needed for the streaming case.

### Event Ordering
Bridge ModelEvents always arrive before their JSONL counterparts (bridge processes the API response, returns to Claude Code, then Claude Code writes to JSONL). No buffering strategy needed — the lookup dict will always be populated in time.

### Fields to Copy During Replacement
Only two fields need copying from the JSONL event to the bridge event:
- `span_id` — JSONL has correct agent hierarchy; bridge has generic context
- `timestamp` — preserves when the event occurred in the JSONL timeline

Everything else (output, call, config, tools, model, uuid, etc.) stays from the bridge event.

### Dependency Direction
inspect_scout → inspect_swe is a clean unidirectional dependency. Neither package currently depends on the other. No circular dependency risk. After inspect_swe changes are complete and released, inspect_scout will add inspect_swe as a dependency.

## Approach

### Part 1: Preserve message ID in `to_model_event()` ✓

**Commit:** `6f8be11a` — set assistant message id from underlying jsonl event

Added `id=event.message.id or None` to `ChatMessageAssistant(...)` in `to_model_event()`. The `or None` guard normalizes empty strings so `model_post_init` still auto-generates a uuid. Two tests added: ID preservation and empty-string normalization.

### Part 2: Copy `claude_code_events()` pipeline to inspect_swe

Copy 7 files from `inspect_scout/src/inspect_scout/sources/_claude_code/` to `inspect_swe/src/inspect_swe/_claude_code/`:

| Source file | Purpose |
|---|---|
| `models.py` | Pydantic models for JSONL format |
| `detection.py` | Event type detection & filtering |
| `extraction.py` | Message/content extraction |
| `tree.py` | Event tree reconstruction |
| `util.py` | Timestamp parsing |
| `toolview.py` | Tool markdown rendering |
| `events.py` | Core conversion pipeline |

For `events.py`: copy the conversion functions (`claude_code_events`, `_EventProcessor`, `to_model_event`, etc.) but NOT `transcripts.py`-level orchestration.

**NOT copied:** `transcripts.py`, `client.py` — these stay in inspect_scout.

The streaming path in `events.py` already handles inline subagent events via `isSidechain`/`sessionId` buffering — no `client.py` needed. Make `_load_agent_events()` work without file-based loading (the streaming buffer path is already the preferred code path; just ensure the file-based fallback doesn't error when `project_dir` is `None`).

### Part 3: Streaming exec + JSONL line buffering

**File:** `inspect_swe/src/inspect_swe/_claude_code/claude_code.py`

Change from awaitable exec to streaming exec:

```python
# Before:
result = await sbox.exec_remote(cmd=..., stream=False)
debug_output.append(result.stdout)

# After:
proc = await sbox.exec_remote(cmd=...)  # stream=True is default
try:
    line_buffer = ""
    async for event in proc:
        match event:
            case ExecRemoteEvent.Stdout(data=data):
                line_buffer += data
                while "\n" in line_buffer:
                    line, line_buffer = line_buffer.split("\n", 1)
                    yield line  # complete JSONL line
            case ExecRemoteEvent.Stderr(data=data):
                debug_output.append(data)
            case ExecRemoteEvent.Completed(exit_code=code):
                # handle remaining buffer + exit code
finally:
    await proc.kill()
```

The retry/attempts loop needs to work with this streaming approach — each attempt produces a streaming process.

### Part 4: Bridge ModelEvent collection and replacement

**Collection:** Subscribe to the transcript to intercept completed bridge ModelEvents, indexed by `ChatMessageAssistant.id`:

```python
bridge_model_events: dict[str, ModelEvent] = {}

def on_event(event: Event) -> None:
    if isinstance(event, ModelEvent) and event.pending is None:
        msg_id = event.output.choices[0].message.id if event.output.choices else None
        if msg_id:
            bridge_model_events[msg_id] = event

transcript()._subscribe(on_event)
```

**Replacement:** Wrap the `claude_code_events()` output to substitute bridge events:

```python
async for event in claude_code_events(jsonl_lines):
    if isinstance(event, ModelEvent):
        msg_id = event.output.choices[0].message.id if event.output.choices else None
        if msg_id and msg_id in bridge_model_events:
            bridge_event = bridge_model_events.pop(msg_id)
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
4. Line-buffer stdout chunks into complete JSONL lines
5. Parse JSONL lines → feed into `claude_code_events()`
6. For each yielded event:
   - If ModelEvent: look up bridge counterpart by message ID, replace if found
   - Otherwise: yield as-is (SpanBeginEvent, SpanEndEvent, ToolEvent, etc.)
7. All events go into the transcript — rich model data with correct agent hierarchy

### Part 6: Update inspect_scout to import from inspect_swe

After inspect_swe is released with the new `_claude_code/` modules:

1. Add `inspect_swe` as a dependency in inspect_scout's `pyproject.toml`
2. Update `inspect_scout.sources._claude_code.transcripts` to import `claude_code_events` and related functions from `inspect_swe._claude_code.events`
3. Remove the local copies of the 7 moved files from inspect_scout
4. Run all inspect_scout tests to verify

## Key Files

| File | Repo | Action |
|---|---|---|
| `src/inspect_swe/_claude_code/claude_code.py` | inspect_swe | Modify: streaming exec, line buffering, event replacement |
| `src/inspect_swe/_claude_code/events.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/models.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/detection.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/extraction.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/tree.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/util.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_swe/_claude_code/toolview.py` | inspect_swe | New: copied from inspect_scout |
| `src/inspect_scout/sources/_claude_code/events.py` | inspect_scout | Part 1: add message ID; Part 6: re-import from inspect_swe |
| `src/inspect_scout/sources/_claude_code/transcripts.py` | inspect_scout | Part 6: update imports |
| `pyproject.toml` | inspect_scout | Part 6: add inspect_swe dependency |

## Verification

1. **Part 1:** Unit test — verify `event.message.id` flows through `to_model_event()` to `ModelEvent.output.choices[0].message.id`
2. **Part 2:** Run copied module tests in inspect_swe (adapt from inspect_scout test suite)
3. **Parts 3-5:** Integration test — run a Claude Code eval through inspect_swe, verify:
   - ModelEvents have `call` data (from bridge)
   - Span hierarchy is correct (from JSONL)
   - Agent nesting is preserved for Task tool calls
4. **Part 6:** Run full `pytest` in inspect_scout after import changes

## Working Guidelines

1. **One part at a time.** Implement, test, and verify each part before moving to the next.
2. **Plan each part.** Each part should have its own sub-plan discussed and approved before coding.
3. **Review before commit.** After tests pass, pause and review the code together before committing. Do not auto-commit.
4. **Full tests at each step.** Every phase produces implementation and tests.
