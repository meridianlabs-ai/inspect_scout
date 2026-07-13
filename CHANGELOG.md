## Unreleased

- Bugfix: Guard against empty eval logs producing invalid SQL

## [0.4.44](https://github.com/meridianlabs-ai/inspect_scout/compare/0.4.43...v0.4.44) (2026-07-13)


### Bug Fixes

* improve scout import output when no transcripts are imported ([#505](https://github.com/meridianlabs-ai/inspect_scout/issues/505)) ([5d7c144](https://github.com/meridianlabs-ai/inspect_scout/commit/5d7c144b22285a206e5685ea6824c8bd2b174348))
* sync OpenAPI schema for inspect_ai reasoning_mode ([5d7c144](https://github.com/meridianlabs-ai/inspect_scout/commit/5d7c144b22285a206e5685ea6824c8bd2b174348))

## 0.4.43 (05 July 2026)

- Store transcript and scan-result event/input columns as compact JSON (`indent=None`), substantially reducing on-disk Parquet size and the bytes streamed to Scout View (e.g. ~700 MiB → ~200 MiB for a large events column).
- Security: Remove terminal control sequences from scanner names, scan metadata, errors, progress text, and filenames before rendering console output.
- Security: Build DuckDB queries from bound Parquet sources and quoted, schema-validated identifiers so malicious transcript/scan filenames and sort or distinct columns cannot inject SQL.
- Add `timeline` option to `transcript_messages()` and `llm_scanner()` for selecting a named timeline.
- Scout View: Back the scans list with a persistent, per-location SQLite index in the local Scout cache. The index is lazily refreshed from scan metadata, so filtering, sorting, pagination, and distinct-value queries no longer rebuild the full scans table on every request.
- Scout View: Fix event panel nav pills never expanding back from picker mode 
- Scout View: Cap oversized tool/text output to prevent resize layerization stalls
- Scout View: Fix broken commit links for ssh-style GitHub origins
- Scout View: Improve MathJax Sanitization
- Bugfix: Per-key validation metrics for dict/multi-label targets now bucket each key against its own target value. Previously the whole-dict positivity (always positive for a non-empty dict) was applied to every key, so a key whose target was `False`/negative was scored TP/FN instead of TN/FP, inflating per-key precision and specificity.
- Bugfix: Respect `--log-level` CLI arg and `SCOUT_LOG_LEVEL` env var across all `scout` commands.

## 0.4.41 (12 June 2026)

- Chunk token counting in segment_messages so large transcripts don't flood the connection pool.
- Bugfix: Preserve the caller's protocol (e.g. `file://`) in scan locations returned by scan listing (regression in v0.4.36 that broke relative folder display in the VS Code scans panel).

## 0.4.39 (02 June 2026)

- Transcript: Resolve `ModelEvent` input references from the consolidated `events_data` message and call pools.
- Compatibility with Pandas 3.0 and DuckDB 1.5.

## 0.4.38 (25 May 2026)

- Update `inspect-ai` dependency to 0.3.226
- Update `inspect-swe` dependency to 0.2.56
- Bugfix: Correct resolution of relative paths in transcript database index.

## 0.4.37 (22 May 2026)

- Observe: OpenAI Chat Completions and Responses API calls that fail before any usable response now produce a `ModelEvent` instead of being dropped.
- Structured generate: Warn model for orphan tool_use in structured_generate retry loop.
- Enumerate all CSV, YAML, and JSON files when looking for validation sets (don't skip gitignored files).
- LLM Scanner / messages API: Sizing segments now subtracts the rendered scanner template's tokens from the per-segment budget, so long templates no longer push the prompt past `context_window`.
- Bugfix: Serialize metadata flds with pydantic_core.to_json
- Include task_id and task_repeat in validations data files (as optional informational fields)
- Scout View: Refine scanner result header and All Scores dialog
- Scout View: Don't allow malformed metadata to blow up entire scan (#245)
- Scout View: Refine scanner result header and All Scores dialog (#243)
- Scout View: Stop polling scans list (#234)
- Scout View: Redesign MetaDataGrid with section cards and striping (#228)
- Scout View: Prevent horizontal scroll on messages tab (#225)
- Scout View: Scout scan UI fixes and negative filter (#226)
- Scout View: Refine scanner result header and All Scores dialog
- Scout View: Support custom role labels for transcript message rendering.
- Bugfix: Stop doing blocking S3 file I/O on hot paths.
- Bugfix: Resolve nested schema references for `AnswerStructured`.

## 0.4.35 (16 May 2026)

- LLM Scanner: `generate_answer()` and `structured_generate()` accept `context_tools` — additional `ToolInfo` definitions declared in the request but never invoked (`tool_choice` forces the answer tool for structured answers and is `"none"` for textual answers). This lets callers pass a `prompt` containing prior `tool_use` blocks (e.g. when asking a follow-up question about an existing transcript) without the API rejecting the request for referencing undeclared tools.
- Transcript: Add `span_tools()` alongside `span_messages()` to extract the union of `ToolInfo` definitions (deduped by name, last-seen wins) from a `Timeline`/`TimelineSpan`/`list[Event]`. Useful for callers that replay or interrogate a recorded conversation and need to re-declare the tools that were in scope.
- Scan results: Fix `TypeError: int() argument must be ... not 'NAType'` raised by `_expand_resultset_rows` when aligning an all-NA pyarrow column to a non-nullable numpy numeric dtype. Falls back to object dtype when the target dtype cannot hold NA.
- LLM Scanner: On timeline scans, reduce within-span chunks to one Result per span before wrapping in a resultset; custom reducers now fire on chunked spans (#431).
- LLM Scanner: `ResultReducer.llm()` now uses the synthesizer's own reasoning as the reduced `Result.explanation`, instead of a `[Segment N]` concat of the per-chunk explanations. The synthesis prompt also instructs the model to preserve `[M1]`-style message citations so the reduced explanation stays traceable to the merged references.

## 0.4.34 (12 May 2026)

- Refactor scan panel display for use in Inspect task display. 

## 0.4.33 (11 May 2026)

- Scanning: Expose recorder primitives for inspect_ai eval_set scanner integration.
- Observe: Stream-capture wrappers now emit the accumulated partial response when the underlying SDK stream raises mid-iteration (e.g. `overloaded_error`, connection reset, content-filter `error` SSE event). The resulting `ModelEvent` carries the partial output with `error` set; OpenAI mid-stream errors whose `code` indicates moderation (`invalid_prompt`, `content_policy_violation`, `content_filter`, `cyber_policy`) are mapped to `stop_reason="content_filter"`.
- Scout view: Dark mode in scout viewer (#165)
- Scout view: Improve narrow-width viewing (#209)
- Scout view: Outline: align close icon with title and make rootHeader sticky (#197)
- Scout view: fix model retry event ordering (#189)

## 0.4.32 (06 May 2026)

- LLM Scanner: Redefine `depth` semantics for timeline scanning. `depth` now counts levels of *scannable* spans (top-level agents/solvers and their scannable descendants).

## 0.4.29 (05 May 2026)

- Transcripts: Treat directories with `.eval` files as an eval log collection (presence of `.parquet` no longer prevails).
- Dependencies: Sync to semaphore changes in Inspect v0.3.217.
- Bugfix: Exit non-zero when `--fail-on-error` and scan does not complete.
- Bugfix: Always reset text progress indicator when job completes.

## 0.4.28 (29 April 2026)

- LLM Scanner: Send default-template prompts as two content blocks (preamble + transcript / per-scanner tail) with `cache_prompt=True`. On Anthropic, the shared-prefix block is marked for caching so multiple scanners on the same transcript share a cache entry.
- LLM Scanner: `template` parameter accepts a `tuple[str, str]` of `(prefix, suffix)` to opt custom templates into the same two-block cache-aware rendering. Passing a single `str` keeps the legacy single-block behavior unchanged.
- Scanners: Run the first scanner alone for each transcript; release the rest only after it completes. Lets the lead's generate populate the prompt cache so followers hit the warm cache.
- Scanner as Scorer: When `Result.value` is `None` but the result includes an answer, explanation, or metadata, return a `NOANSWER` score that preserves those fields instead of dropping the score entirely.
- `generate_answer()` / `structured_generate()`: add `config: GenerateConfig | None` parameter for per-call overrides (e.g. `cache`), so callers no longer need to mutate or copy the role `Model` to set generation options. `parallel_tool_calls` remains forced to `False` for structured answers.
- Scout View: Improve message collapse behavior.
- Scout View: Fade out bottom of truncated expandable panels to indicate more content below.
- Scout View: Fix timeline error markers incorrectly flagging every model and tool event.
- Scout View: Store task list filter/sort state independently per scope (Tasks vs Folders, individual folders).
- Scout View: Add Tokens and Duration columns to samples list.
- Scout View: Detect additional todo/task tool names (for inspect deepagent).
- Scout View: Default expand transcripts to show branches.
- Scout View: Fix transcript scroll-to-event navigation for short event lists.
- Scout View: Branch-aware citation navigation in transcript view with deep-linking via `?message=<id>`.
- Scout View: Fix double borders on root elements of transcript.
- Scout View: Improve expandable panel height measurement and button visibility.
- Scout View: Display approvals within tool calls; improve formatting of rejections and long approvals.

## 0.4.27 (20 April 2026)

- Scanner as Scorer: Modify format for improved API for view client.
- Scanner as Scorer: Write sentinel value so view client can detect scanner content.
- Scout View: Fix error when attempting to collapse all or expand all events in transcripts.
- Scout View: Improvements to expand / collapse behavior in transcripts.
- Scout View: Don't show empty entries in messages view when a message is retried.
- Bugfix: resolve transcript_score types to string when resuming scans.

## 0.4.26 (15 April 2026)

- Utilities: Export `message_as_str` function.
- Utilities: Add `format` option to `messages_as_str` function ("text", "json", or "list").
- Scout View: Consolidate transcript viewer to shared component. Miscellaneous fixes and improvements.

## 0.4.25 (04 April 2026)

- Scanners: Distinguish thinking, thinking summary, and redacted thinking when rendering messages for scanners.
- Scanners: Surround assistant messages with `prefill=True` in metadata with `<prefill>` tag when rendering messages for scanners.
- Scanners: Match references across all fields in scan result.
- Metrics: Filter out NaN metrics (occurs when all scan results are errors).
- Metrics: Filter out non-numeric keys from scanner values when computing scanner metrics.
- Timelines: Ensure that all events are loaded from reading timelines.
- Timelines: Update to use new timeline branch scheme from inspect-ai.
- Timelines: Add `label_for_id` option to `message_numbering()` function.
- Modules: Rename `async` module to `aio`.
- VS Code Integration: Fix regression displaying Scout View in VS Code.
- Scout View: Show tooltip for array or object values which have been truncated.
- Scout View: Improve citation matching in results view.

## 0.4.23 (25 March 2026)

- Add timeline types to `@scanner` decorator overloads.
- Scout View: Fix white circle over compaction markers.
- Bugfix: Handle excluded input column in event expansion.
- Bugfix: Always truncate error file on resume to prevent stale errors.

## 0.4.22 (20 March 2026)

- Transcripts: Use `events_data` to reduce memory and storage requirements of `events`.
- Summary: Count only positive values in resultset aggregation.
- Summary: Reset summary state on new scan init to prevent accumulation across scans.
- Recorder: Preserve error file on scan resume instead of truncating.

## 0.4.21 (16 March 2026)

- Scanner as scorer: Forward timelines from eval sample to scanner if requested.
- Scout View: Correctly display timelines in results view.
- Scout View: Show dictionary-based metriecs in scanner sidebar.
- Scout View: Bundle `dist/` assets during packaging.

## 0.4.20 (16 March 2026)

- LLM Scanner: Automatic transcript segmentation by context window with configurable compaction handling.
- LLM Scanner: `AnswerMultiLabel(allow_none=True)` lets the model respond with `ANSWER: NONE` when no labels apply.
- Scanner Tools: `generate_answer()` automatically retries with format feedback when the model's response can't be parsed.
- Scanner Tools: `message_numbering()`, `scanner_prompt()`, `generate_answer()`, and `parse_answer()` functions for building custom scanners with fine-grained control.
- Scanner Tools: `ResultReducer` for reducing results from multiple transcript segments into single results, with built-in majority and LLM-based reducers.
- Scanner Tools: `transcript_messages()`, `segment_messages()`, and `span_messages()` functions for extracting and segmenting transcript messages.
- Transcript DB: `claude_code()` source for importing transcripts from Claude Code session logs. Supports filtering by project, session, and time range, session merging, and image extraction.
- CLI: `scout import` command for importing transcripts from registered sources into Scout projects.
- Serialization: Use `pa.large_string` for string types to support larger column/file sizes. 
- Multiprocessing: Improve handling of model instances with multiprocessing serialization.
- Transcripts: unthin `target` and and add `scores` from sample JSON.
- Transcripts: Set row group size to 25 (specify as rows not bytes).
- Transcripts: Address DuckDB 1.5 compatibility issue w/ mixed type CASE expressions.
- Transcripts: Switch over to async ZIP modules (`async_zip`, `zip_common`, `compression`, `compression_transcoding`, `async_bytes_reader`) that have migrated to `inspect_ai`.
- Transcripts: Remove parquet encryption (not used + issues w/ DuckDB 1.5).
- Transcripts: Ensure that all documented schema columns exist when running transcript queries.
- Observe: Prevent transcript index staleness/warning from occurring when running parallel observe contexts.
- Scout View: Properly sort scanner results using the value type.
- Scout View: Enable minification and caching of view static assets.
- Scout View: Fix issue rendering transcript events when showing the validation panel.
- Scout View: Add 'None' option to column chooser to unselect all columns.
- Bugfix: Fix early-exit bug the failed to unthin `sample_metadata`

## 0.4.19 (17 February 2026)

- LLM Scanner: Store model stop_reason result metadata.
- Scout View: Fix incorrect behavior when attempting to view scanner results with result sets.

## 0.4.18 (14 February 2026)

- Bugfix: Fix token counting when a single worker task processes multiple scans sequentially.

## 0.4.17 (13 February 2026)

- Transcript DB: Improve Anthropic and Google tool call capture for `pheonix()` transcript source.

## 0.4.16 (13 February 2026)

- Transcript DB: `phoenix()` transcript source for importing transcripts from Arize Phoenix.

## 0.4.15 (12 February 2026)

- Scout View: Support for displaying cost limits.

## 0.4.14 (12 February 2026)

- Scout View: Improve display of large dictionary scan values.
- Enable customization of the scan buffer directory via `SCOUT_SCANBUFFER_DIR` environment variable.
- Bugfix: Fix answer parsing when LLM echoes "Answer:" in reasoning before the actual answer marker.

## 0.4.13 (11 February 2026)

- Validation: Support for applying validation labels in Scout View.
- Compatibility with latest release of the Inspect VS Code Extension.

## 0.4.12 (09 February 2026)

- Scoring: Apply content filter for scanners when using them as Inspect scorers.
- Add `SampleMetadata` class for typed access to Inspect eval log metadata fields.
- Add support for Inspect `CompactionEvent` and display of native compaction data from OpenAI and Anthropic.
- Add "store" event to `EventType` enumeration.
- View Server: Add optimized `/transcripts/{dir}/{id}/info` and `/transcripts/{dir}/{id}/messages-events` endpoints for fetching transcript data. The `messages-events` endpoint streams raw (potentially compressed) JSON for improved performance.
- Bugfix: Eliminate problem with stale transcript status when deleting validation cases.

## 0.4.11 (29 January 2026)

- Projects: Always read `scout.local.yaml` even if there is no `scout.yaml` file.
- Projects: Always apply project level `filter` to scans (AND combine with scan filters).
- Validation: Label validation is now binary: validate `true` if the label is present with a truthy value; validate `false` if the label is not present or has only falsey values.
- Scan Results: Add `exclude_columns` parameter for reading parquet reuslts to optionally reduce memory usage.
- Scan Results: Pre-fetch optimization for S3/remote parquet files.
- Transcript DB: [observe()]([transcript database schema](https://meridianlabs-ai.github.io/inspect_scout/db_capturing.html).) decorator/context manager for writing transcripts based on observed LLM generations.
- Transcript DB: `langsmith()` and `logfire()` transcript sources for importing transcripts from LLM observability systems.

## 0.4.10 (21 January 2026)

- Scanning: Implement significant scanning performance improvement when scanning eval logs and events are unneeded.
- Scan config: Set 'model' to `None` if no model is specified.
- Scan config: Deprecate use of environment variables for config (in favor of project config).
- Scout View: Move 'Project' UI button to main activity bar.

## 0.4.9 (20 January 2026)

- Bugfix: Don't check index coverage when running with an active limit or other query filter.
- Bugfix: Correctly normalize relative database file paths.

## 0.4.8 (18 January 2026)

- Validation: Add support for defining and using named splits (e.g. 'dev', 'test') for validation data.
- Validation: Add support for specifying per-case predicates within validation data.
- Add `message_count` as standard transcript metadata field.
- Bugfix: Correct async generator cleanup in AsyncBytesReader.

## 0.4.7 (16 January 2026)

- Scout View: Editing UI for project settings.
- Scanning: Apply model config when resuming scans.
- Transcript DB: Warn when there is no index or the index is out of date.
- Validation: Improve error messages and documentation; deprecate (with warning) headerless CSVs.
- CLI: Add `scout --version` to print current scout version.

## 0.4.6 (08 January 2026)

- LLM Scanner: Add `value_to_float` option to for converting model reported values to numeric.
- Projects: Support local project config in `scout.local.yaml`.
- Transcripts: Enable use of SQL for specifying filters.
- Transcripts: Add `filter` field to scan job and project config.
- Scanning: Add `tool_callers()` helper function for mapping tool_call_id to assistant message.
- Rename `--results` option to `--scans`. 
- Bugfix: Avoid `UnboundLocalError` by importing Inspect AI batch reporting functions directly.
- Bugfix: Fix issue with reading large numbers of rows from transcript database.

## 0.4.5 (03 January 2026)

- [Projects](https://meridianlabs-ai.github.io/inspect_scout/projects.html) for centrally managing scanning configuration.
- [Grep Scanner](https://meridianlabs-ai.github.io/inspect_scout/grep_scanner.html) for pattern-based scanning of transcripts.
- Scanning: Add `--dry-run` option for previewing scanner counts.
- Scanners: Fixup type annotations in @scanner decorator.
- Display: Add text progress and metrics support to `display="log"` mode.
- Transcript DB: Don't remove orphaned data files.
- Transcript DB: Handle duplicate transcript ids while indexing.
- Transcript DB: Remove redundant TranscriptSource class (covered by AsyncIterable already).
- Bugfix: Store relative paths in transcript database index.

## 0.4.4 (24 December 2025)

- Bugfix: Restore compatibility with v1 view server API.

## 0.4.3 (22 December 2025)

- Add more standard fields to the [transcript database schema](https://meridianlabs-ai.github.io/inspect_scout/db_schema.html).
- Add an optional index to transcript database for higher performance queries on very large databases.
- Add `as_json` option to `messages_as_str` for JSON output format.
- Persist transcripts.where() clauses as part of scan specification.
- Bugfix: Fix LLM answer parsing for decimals, negatives, and markdown.

## 0.4.2 (14 December 2025)

- Scanning: Switch from `dill` to `cloudpickle` and restore default `max_processes` to 4 after resolving multiprocessing serialization issues.
- Track scan job completion status explicitly in the filesystem (vs. merely looking at whether buffer dir exists).
- Transcript databases: Include all `.parquet` files in directory (don't require `transcripts_` prefix).

## 0.4.1 (12 December 2025)

- Scan jobs: Correct resolution order for options (CLI, then scanjob config, then environment variables).
- Scanning: Restore default `max_processes` to 1 while we resolve some multiprocessing serialization issues.

## 0.4.0 (11 December 2025)

- Initial release.
