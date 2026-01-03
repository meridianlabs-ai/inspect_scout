## Unreleased

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
