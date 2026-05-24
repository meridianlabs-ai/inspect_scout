# Validation Case Metadata: `task_id` and `task_repeat`

## Problem

Validation case files (CSV/JSON/YAML/JSONL) contain an opaque `id` (the transcript ID) that isn't meaningful to humans reviewing the file externally. When a user opens a validation CSV in a spreadsheet or text editor, they can't tell which sample or epoch a case corresponds to without cross-referencing the database.

## Solution

Add two optional, informational fields to validation cases:

- **`task_id`** (`str | None`) — The sample identifier from the eval log (e.g., dataset sample id).
- **`task_repeat`** (`int | None`) — The epoch/repeat number for the sample.

These fields are **write-through metadata only**: they are stored in the file and returned by the API, but do not participate in validation logic, matching, or predicate evaluation. The frontend provides them when creating/upserting cases from a transcript context.

## Changes

### Python — `ValidationCase` model (`_validation/types.py`)

Add two optional fields with `Field(default=None)`. They serialize into the file when present (via `exclude_none=True` in `model_dump`) and are ignored when absent.

### Python — `ValidationCaseRequest` dataclass (`_view/_api_v2_types.py`)

Add matching optional fields so the API accepts them from the frontend.

### Python — API endpoints (`_view/_api_v2_validations.py`)

Thread the new fields through `create_validation` and `upsert_validation_case` when constructing `ValidationCase` objects.

### File I/O — No changes

The writer uses `model_dump(exclude_none=True)` and writes raw dicts, so new fields flow through naturally. The reader loads raw dicts and passes them to Pydantic, which accepts (and ignores during validation logic) the extra fields. CSV files get `task_id`/`task_repeat` columns; structured formats get inline fields.

### OpenAPI + generated TypeScript types

Regenerate `openapi.json` and `generated.ts` after the Python model changes.

### Frontend — Pass metadata when creating/upserting cases

Where the frontend constructs upsert requests from a transcript context, include `task_id` and `task_repeat` from the transcript metadata if available.

## What doesn't change

- Validation logic, matching, predicates
- File scanning / discovery
- Split handling
- Read path (extra fields in existing files are already tolerated)

## File format examples

**CSV:**
```csv
id,target,task_id,task_repeat
abc123,true,sample_42,1
def456,false,sample_42,2
```

**JSON/YAML:**
```json
[
  {"id": "abc123", "target": true, "task_id": "sample_42", "task_repeat": 1},
  {"id": "def456", "target": false, "task_id": "sample_42", "task_repeat": 2}
]
```

## Branching

Requires coordinated branches in both repos:
- **inspect_scout** (base repo) — Python model, API, and schema changes
- **ts-mono** (submodule) — Frontend changes to pass metadata through
