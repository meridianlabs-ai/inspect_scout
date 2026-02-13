## Unrelased

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
