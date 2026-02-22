# Documentation Plan: New Features on `feature/transcript-nodes`

## New Features Summary

### 1. Timeline System (major new feature)

- **`build_timeline(events)`** — Converts flat event list into hierarchical `Timeline` with spans, branches, agents
- **`Timeline`** / **`TimelineSpan`** / **`TimelineEvent`** / **`TimelineBranch`** — The node types; spans have `name`, `span_type`, `content`, `branches`, `outline`, token counts
- **`filter_timeline(timeline, predicate)`** — Prune a timeline by span predicate
- **`timeline.render()`** — ASCII swimlane diagram of the timeline
- **Docs:** Only stub listings in `reference/transcript.qmd`. No narrative docs for `build_timeline`, `filter_timeline`, or `TimelineSpan` fields.

### 2. Message Extraction Pipeline (major new feature)

- **`transcript_messages(transcript, ...)`** — Unified entry point; auto-selects strategy (timelines → events → messages)
- **`segment_messages(source, ...)`** — Lower-level: segments messages to fit context windows
- **`span_messages(source, ...)`** — Extract messages from a span/event list with compaction handling (use `split_compactions=True` to preserve compaction region structure)
- **`timeline_messages(timeline, ...)`** — Walk span tree yielding `TimelineMessages` per non-utility span
- **`MessagesSegment`** / **`TimelineMessages`** — Return types
- **Docs:** `transcript_messages` and `timeline_messages` well documented in `scanners.qmd` toolkit section. `segment_messages`, `span_messages` are stub-only or one-liners.

### 3. Claude Code Source (entirely new)

- **`claude_code(path, session_id, from_time, to_time, limit)`** — Reads Claude Code sessions from `~/.claude/projects/`, converts to `Transcript` objects
- Handles `/clear` splitting, plan-mode slug merging, time filtering
- **Docs:** Well documented in `db_importing.qmd`.

### 4. `scout import` CLI Command (entirely new)

- **`scout import <source> [options]`** — CLI for importing from any source (claude_code, phoenix, langsmith, logfire)
- Flags: `--limit`, `--from`, `--to`, `-P key=value`, `--dry-run`, `--overwrite`, `--sources`
- **Docs:** Not documented. CLI reference stubs are all empty.

### 5. LLM Scanner Enhancements

- **`content=TranscriptContent(...)`** — Override transcript content filters (e.g., enable timelines)
- **`context_window=`** — Split long transcripts into segments scanned independently
- **`compaction=`** — How to handle compaction boundaries (`"all"`, `"last"`, or `int`)
- **`depth=`** — Max span tree depth for timeline processing
- **`reducer=`** — Custom reducer for multi-segment results
- **Docs:** Documented in `llm_scanner.qmd` prose sections. No consolidated parameter table.

### 6. ResultReducer (entirely new)

- **`ResultReducer.mean/median/mode/max/min/any/union/last`** — Static reducers for multi-segment aggregation
- **`ResultReducer.llm(model, prompt)`** — LLM-based reducer factory
- **Docs:** Well documented in both `llm_scanner.qmd` and `scanners.qmd`.

### 7. Scanning Toolkit Functions (new public API)

- **`generate_answer(prompt, answer, ...)`** — Standalone LLM generation → `Result`
- **`parse_answer(output, answer, ...)`** — Pure parsing, no LLM call
- **`message_numbering(preprocessor)`** — Creates `[M1]`, `[M2]`... counter pair for cross-segment consistency
- **`scan_segments()`** — Concurrent segment scanning with ordered results
- **`AnswerSpec`** — Type alias for all answer specifications
- **Docs:** All documented in `scanners.qmd` Scanning Toolkit section.

### 8. Scanner/Loader Decorator Changes

- **`@scanner(timeline=True)`** — New parameter to request timeline data
- **`@loader(timeline=True)`** — Same for loaders
- Auto-inference from `Timeline` type annotation
- **Docs:** Covered implicitly in `scanners.qmd` and `llm_scanner.qmd` examples.

### 9. Transcript Model Change

- **`Transcript.timelines: list[Timeline]`** — New field
- **Docs:** Missing from `_transcript_fields.md` field table. Used in code examples but never formally described.

## Documentation Gap Summary

| Gap | Priority |
|-----|----------|
| `build_timeline` / `filter_timeline` narrative docs | High — core new concept |
| `TimelineSpan` type and fields | High — users need to understand the data model |
| `Transcript.timelines` in field table | Medium — quick fix |
| `scout import` CLI command | High — entirely undocumented |
| `llm_scanner()` consolidated parameter table | Medium — params documented in prose but no reference table |
| `segment_messages` / `span_messages` examples | Low — advanced/lower-level APIs |
| CLI reference stubs (all empty) | Pre-existing gap |

## Coverage Notes

The best-documented new features are the Scanning Toolkit (`scanners.qmd`), the Claude Code source (`db_importing.qmd`), and the llm_scanner timeline/context-window features. The biggest gaps are around the Timeline data model itself and the `scout import` CLI.
