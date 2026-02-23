# Scout Import

## Overview

Add a `scout import` CLI command that imports transcripts from any registered source into a local transcript database. Sources are the async generator functions exported from `inspect_scout.sources` (`claude_code`, `logfire`, `langsmith`, `phoenix`).

## Motivation

Currently, importing transcripts requires writing a Python script (see `examples/import_cc/import_cc.py`). A CLI command makes this accessible without code, supports quick exploration, and provides a consistent interface across all sources.

## Usage

```bash
# Basic import
scout import claude_code
scout import logfire -P project=my-project

# With common filters
scout import claude_code --limit 10
scout import langsmith --from 2025-01-01 --to 2025-02-01

# Source-specific parameters via -P
scout import claude_code -P session_id=abc123
scout import phoenix -P tags='[tag1, tag2]' -P metadata='{key: value}'

# Output control
scout import claude_code --transcripts ./my-transcripts
scout import claude_code -T ./my-transcripts

# Discovery
scout import --sources

# Dry run
scout import claude_code --dry-run
scout import claude_code --dry-run --limit 5
```

## CLI Parameters

| Parameter | Short | Description | Default |
|-----------|-------|-------------|---------|
| `SOURCE` | | Positional: source function name | required (except with `--sources`) |
| `--transcripts` | `-T` | Transcripts database directory | `./transcripts` |
| `--limit` | | Max transcripts to import | None (all) |
| `--from` | | Only transcripts on/after this time (ISO 8601) | None |
| `--to` | | Only transcripts before this time (ISO 8601) | None |
| `-P` | | Source parameter as `name=value` (repeatable) | None |
| `--sources` | | List available sources and their parameters | False |
| `--dry-run` | | Fetch and display summary without writing | False |

The import command always prints the `scout view` command after a successful import.

## Parameter Parsing (`-P`)

Values passed via `-P name=value` are parsed with a YAML parser to support rich types:

| Input | Parsed as | Python type |
|-------|-----------|-------------|
| `-P limit=10` | `10` | `int` |
| `-P project=my-proj` | `"my-proj"` | `str` |
| `-P tags='[a, b, c]'` | `["a", "b", "c"]` | `list[str]` |
| `-P metadata='{k: v}'` | `{"k": "v"}` | `dict[str, str]` |
| `-P trace_id=abc123` | `"abc123"` | `str` |

**Special handling for `datetime` parameters**: If a source function's type annotation indicates `datetime`, the string value is parsed with `datetime.fromisoformat()` rather than YAML. This allows natural ISO 8601 input like `-P from_time=2025-01-01` or `-P from_time=2025-01-01T10:00:00`.

**Promoted parameters**: `limit`, `from_time`, and `to_time` can be specified either as top-level CLI params (`--limit`, `--from`, `--to`) or via `-P`. The top-level params take precedence if both are specified.

## Source Discovery

Sources are discovered dynamically from `inspect_scout.sources.__all__`. For each name in `__all__`, we import the function and use `inspect.signature()` to get its parameters for validation and `--sources` display.

### `--sources` Output

```
Available sources:

  claude_code
    path          str
    session_id    str
    from_time     datetime
    to_time       datetime
    limit         int

  logfire
    project       str
    from_time     datetime
    to_time       datetime
    filter        str
    trace_id      str
    limit         int
    read_token    str

  ...
```

Shows parameter names and types, extracted via `inspect.signature()`.

## Progress Reporting

The current progress display in `_insert_from_transcripts` shows a spinner with transcript_id and count. We should improve this to provide a richer import experience:

**During import** — Enhanced progress showing:
- Source name and parameters being used
- Running count of transcripts imported
- Elapsed time

**After import** — Summary showing:
- Total transcripts imported (and skipped as duplicates)
- Total time elapsed
- Database location
- The `scout view` command to run

**Dry run output** — Table showing:
- Transcript ID, date, model, agent, message count, token count
- Summary count at the bottom

## Existing Transcripts Directory

If the `--transcripts` directory already exists, prompt the user:

```
Transcripts directory './transcripts' already exists.
Add transcripts to it? (existing transcripts won't be re-imported) [y/N]
```

If the user confirms, proceed with the import — the database's built-in deduplication by `transcript_id` ensures no duplicates. If declined, exit without importing.

This prompt is skipped when the directory does not exist (fresh import).

## Error Handling

- If a source function raises during iteration, report the error and keep any transcripts already written (the database batching already handles partial writes).
- If an unknown source name is given, show available sources and exit.
- If an unknown `-P` parameter is given for a source, show that source's valid parameters and exit.
- Validate parameter types before calling the source function (e.g., confirm `limit` parses as int).

## Implementation

### New Files

- `src/inspect_scout/_cli/import_command.py` — The Click command implementation

### Modified Files

- `src/inspect_scout/_cli/main.py` — Register the new command

### Key Implementation Details

1. **Command registration** follows the existing pattern in `main.py`:
   ```python
   scout.add_command(import_command)
   ```

2. **Source function invocation** — Use `inspect.signature()` to bind parsed parameters, coerce types based on annotations, then call the async generator.

3. **Database write** — Use `transcripts_db(to_dir)` context manager and `db.insert()`, matching the pattern in `examples/import_cc/import_cc.py`.

4. **Async execution** — Wrap the async import in `asyncio.run()` at the CLI boundary, consistent with other commands.
