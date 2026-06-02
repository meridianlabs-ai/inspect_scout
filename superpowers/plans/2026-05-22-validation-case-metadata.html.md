# validation-case-metadata – Inspect Scout

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional `task_id` and `task_repeat` fields to validation case files so they’re human-readable outside the app.

**Architecture:** Add the fields to the Pydantic model, API request dataclass, and API endpoints. Regenerate the OpenAPI schema and TypeScript types. Thread the values from the frontend’s transcript context into upsert requests.

**Tech Stack:** Python (Pydantic, FastAPI, dataclasses), TypeScript (React, React Query), OpenAPI codegen

------------------------------------------------------------------------

## File Map

| Action | File | Responsibility |
|----|----|----|
| Modify | `src/inspect_scout/_validation/types.py` | Add `task_id` and `task_repeat` to [ValidationCase](../../reference/results.html.md#validationcase) |
| Modify | `src/inspect_scout/_view/_api_v2_types.py` | Add fields to `ValidationCaseRequest` dataclass |
| Modify | `src/inspect_scout/_view/_api_v2_validations.py` | Thread fields through `create_validation` and `upsert_validation_case` |
| Modify | `src/inspect_scout/openapi.json` | Regenerated (not hand-edited) |
| Modify | `src/inspect_scout/_view/ts-mono/apps/scout/src/types/generated.ts` | Regenerated (not hand-edited) |
| Modify | `src/inspect_scout/_view/ts-mono/apps/scout/src/app/validation/components/ValidationCaseEditor.tsx` | Pass `task_id` / `task_repeat` in upsert requests |
| Test | `tests/view/test_validation_api.py` | Add tests for metadata round-trip |

## Branching

This feature requires coordinated branches in two repos:

1.  **inspect_scout** (base repo): branch `feat/validation-case-metadata`
2.  **ts-mono** (submodule): branch `feat/validation-case-metadata`

Create the ts-mono branch first (Tasks 1-2), then the base repo branch (remaining tasks). The submodule pointer update happens when committing the base repo.

------------------------------------------------------------------------

### Task 1: Create branches

**Files:** None (git operations only)

**Step 1: Create the ts-mono feature branch**

``` bash
cd src/inspect_scout/_view/ts-mono
git checkout -b feat/validation-case-metadata
cd -
```

**Step 2: Create the base repo feature branch**

``` bash
git checkout -b feat/validation-case-metadata
```

------------------------------------------------------------------------

### Task 2: Add fields to [ValidationCase](../../reference/results.html.md#validationcase) model

**Files:** - Modify: `src/inspect_scout/_validation/types.py:10-61`

**Step 1: Write the failing test**

In `tests/view/test_validation_api.py`, add a test that creates a case with `task_id` and `task_repeat`, then reads it back and verifies the fields are present.

``` python
def test_upsert_case_with_metadata(client: TestClient, validation_csv: Path) -> None:
    """task_id and task_repeat are stored and returned when provided."""
    uri = validation_csv.as_uri()
    encoded_uri = _base64url(uri)
    case_id = _base64url("t_meta")

    resp = client.post(
        f"/api/v2/validations/{encoded_uri}/{case_id}",
        json={
            "target": True,
            "task_id": "sample_42",
            "task_repeat": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "sample_42"
    assert data["task_repeat"] == 3

    # Read back
    get_resp = client.get(f"/api/v2/validations/{encoded_uri}/{case_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["task_id"] == "sample_42"
    assert get_data["task_repeat"] == 3
```

**Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/view/test_validation_api.py::test_upsert_case_with_metadata -v` Expected: FAIL — `task_id` not in response (fields don’t exist yet on the model).

**Step 3: Add fields to [ValidationCase](../../reference/results.html.md#validationcase)**

In `src/inspect_scout/_validation/types.py`, add after the `split` field (line 44):

``` python
    task_id: str | None = Field(default=None)
    """Optional sample identifier from the source eval log (informational only)."""

    task_repeat: int | None = Field(default=None)
    """Optional epoch/repeat number from the source eval log (informational only)."""
```

**Step 4: Add fields to `ValidationCaseRequest`**

In `src/inspect_scout/_view/_api_v2_types.py`, add after the `predicate` field (line 204) in the `ValidationCaseRequest` dataclass:

``` python
    task_id: str | None = None
    """Optional sample identifier (informational, written to file but not used in validation)."""

    task_repeat: int | None = None
    """Optional epoch/repeat number (informational, written to file but not used in validation)."""
```

**Step 5: Thread fields through `create_validation` endpoint**

In `src/inspect_scout/_view/_api_v2_validations.py`, in `create_validation()` (around line 92), update the [ValidationCase](../../reference/results.html.md#validationcase) constructor to include the new fields:

``` python
            cases.append(
                ValidationCase(
                    id=case_req.id,
                    target=case_req.target,
                    labels=case_req.labels,
                    split=case_req.split,
                    predicate=cast(PredicateType | None, case_req.predicate),
                    task_id=case_req.task_id,
                    task_repeat=case_req.task_repeat,
                )
            )
```

**Step 6: Thread fields through `upsert_validation_case` endpoint**

In `src/inspect_scout/_view/_api_v2_validations.py`, in `upsert_validation_case()` (around line 286), update the [ValidationCase](../../reference/results.html.md#validationcase) constructor:

``` python
            case = ValidationCase(
                id=decoded_case_id,
                target=body.target,
                labels=body.labels,
                split=body.split,
                predicate=cast(PredicateType | None, body.predicate),
                task_id=body.task_id,
                task_repeat=body.task_repeat,
            )
```

**Step 7: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/view/test_validation_api.py::test_upsert_case_with_metadata -v` Expected: PASS

**Step 8: Commit**

``` bash
git add src/inspect_scout/_validation/types.py src/inspect_scout/_view/_api_v2_types.py src/inspect_scout/_view/_api_v2_validations.py tests/view/test_validation_api.py
git commit -m "feat: add task_id and task_repeat metadata to validation cases"
```

------------------------------------------------------------------------

### Task 3: Add test for metadata omission (optional fields)

**Files:** - Test: `tests/view/test_validation_api.py`

**Step 1: Write test that metadata fields are absent when not provided**

``` python
def test_upsert_case_without_metadata(client: TestClient, validation_csv: Path) -> None:
    """task_id and task_repeat are absent from response when not provided."""
    uri = validation_csv.as_uri()
    encoded_uri = _base64url(uri)
    case_id = _base64url("t_no_meta")

    resp = client.post(
        f"/api/v2/validations/{encoded_uri}/{case_id}",
        json={"target": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" not in data
    assert "task_repeat" not in data
```

**Step 2: Run test to verify it passes**

Run: `.venv/bin/pytest tests/view/test_validation_api.py::test_upsert_case_without_metadata -v` Expected: PASS (fields use `exclude_none=True` via `model_dump`)

**Step 3: Commit**

``` bash
git add tests/view/test_validation_api.py
git commit -m "test: verify metadata fields omitted when not provided"
```

------------------------------------------------------------------------

### Task 4: Add test for CSV round-trip with metadata

**Files:** - Test: `tests/view/test_validation_api.py`

**Step 1: Write test that metadata persists in CSV file**

``` python
def test_metadata_persists_in_csv(client: TestClient, validation_csv: Path) -> None:
    """task_id and task_repeat appear as columns in the CSV file."""
    uri = validation_csv.as_uri()
    encoded_uri = _base64url(uri)
    case_id = _base64url("t_csv_meta")

    client.post(
        f"/api/v2/validations/{encoded_uri}/{case_id}",
        json={"target": True, "task_id": "sample_7", "task_repeat": 2},
    )

    # Read the raw CSV and verify columns exist
    csv_content = validation_csv.read_text()
    assert "task_id" in csv_content
    assert "task_repeat" in csv_content
    assert "sample_7" in csv_content

    # Read back via API — list all cases
    all_resp = client.get(f"/api/v2/validations/{encoded_uri}")
    assert all_resp.status_code == 200
    cases = all_resp.json()
    meta_case = next(c for c in cases if c["id"] == "t_csv_meta")
    assert meta_case["task_id"] == "sample_7"
    assert meta_case["task_repeat"] == 2
```

**Step 2: Run test**

Run: `.venv/bin/pytest tests/view/test_validation_api.py::test_metadata_persists_in_csv -v` Expected: PASS

**Step 3: Commit**

``` bash
git add tests/view/test_validation_api.py
git commit -m "test: verify metadata round-trips through CSV files"
```

------------------------------------------------------------------------

### Task 5: Run full validation test suite

**Step 1: Run all validation-related tests**

Run: `.venv/bin/pytest tests/view/test_validation_api.py tests/scanner/test_validation.py tests/validation/ -v` Expected: All PASS

**Step 2: Run type checker**

Run: `.venv/bin/mypy src/inspect_scout/_validation/types.py src/inspect_scout/_view/_api_v2_types.py src/inspect_scout/_view/_api_v2_validations.py` Expected: No errors

------------------------------------------------------------------------

### Task 6: Regenerate OpenAPI schema and TypeScript types

**Files:** - Modify: `src/inspect_scout/openapi.json` (generated) - Modify: `src/inspect_scout/_view/ts-mono/apps/scout/src/types/generated.ts` (generated)

**Step 1: Regenerate OpenAPI schema**

Run: `.venv/bin/python scripts/export_openapi_schema.py`

**Step 2: Verify the schema includes the new fields**

Check that `openapi.json` now contains `task_id` and `task_repeat` in both the [ValidationCase](../../reference/results.html.md#validationcase) and `ValidationCaseRequest` schemas.

Run: `grep -A2 task_id src/inspect_scout/openapi.json | head -20`

**Step 3: Build ts-mono to regenerate TypeScript types**

``` bash
cd src/inspect_scout/_view/ts-mono
pnpm install
pnpm build
cd -
```

**Step 4: Verify generated types include new fields**

Check that `generated.ts` now has `task_id` and `task_repeat` on both [ValidationCase](../../reference/results.html.md#validationcase) and `ValidationCaseRequest`.

Run: `grep -A2 task_id src/inspect_scout/_view/ts-mono/apps/scout/src/types/generated.ts | head -20`

**Step 5: Commit generated files**

``` bash
cd src/inspect_scout/_view/ts-mono
git add apps/scout/src/types/generated.ts
git commit -m "chore: regenerate types with task_id and task_repeat"
cd -
git add src/inspect_scout/openapi.json
git commit -m "chore: regenerate openapi schema with task_id and task_repeat"
```

------------------------------------------------------------------------

### Task 7: Thread metadata through frontend upsert

**Files:** - Modify: `src/inspect_scout/_view/ts-mono/apps/scout/src/app/validation/components/ValidationCaseEditor.tsx:59-62,171-177,256-266,291-297`

The `ValidationCaseEditor` component receives `transcriptId` but doesn’t have access to `task_id` / `task_repeat`. The parent components (`TranscriptBody` and `ScannerResultPanel`) have this data. We need to:

1.  Add optional `taskId` and `taskRepeat` props to `ValidationCaseEditor`
2.  Pass them from both parent call sites
3.  Include them in the `ValidationCaseRequest` when upserting

**Step 1: Add props to `ValidationCaseEditor`**

In `ValidationCaseEditor.tsx`, update the `ValidationCaseEditorProps` interface (line 59):

``` typescript
interface ValidationCaseEditorProps {
  transcriptId: string;
  taskId?: string | null;
  taskRepeat?: number | null;
  className?: string | string[];
}
```

Update the component to destructure the new props (line 64):

``` typescript
export const ValidationCaseEditor: FC<ValidationCaseEditorProps> = ({
  transcriptId,
  taskId,
  taskRepeat,
  className,
}) => {
```

Update `ValidationCaseEditorComponentProps` (line 171):

``` typescript
interface ValidationCaseEditorComponentProps {
  transcriptId: string;
  taskId?: string | null;
  taskRepeat?: number | null;
  validationSets: string[];
  editorValidationSetUri?: string;
  validationCase?: ValidationCase | null;
  validationCases?: ValidationCase[];
  className?: string | string[];
}
```

Pass the props through to `ValidationCaseEditorComponent` (around line 153):

``` typescript
            <ValidationCaseEditorComponent
              key={validatedSetUri}
              transcriptId={transcriptId}
              taskId={taskId}
              taskRepeat={taskRepeat}
              validationSets={setsData}
              editorValidationSetUri={validatedSetUri}
              validationCase={caseData}
              validationCases={casesData}
              className={className}
            />
```

Update the inner component destructuring (line 180):

``` typescript
const ValidationCaseEditorComponent: FC<ValidationCaseEditorComponentProps> = ({
  transcriptId,
  taskId,
  taskRepeat,
  validationSets,
  editorValidationSetUri,
  validationCase: caseData,
  validationCases,
  className,
}) => {
```

**Step 2: Include metadata in the upsert request**

In `handleFieldChange` (around line 291), add `task_id` and `task_repeat` to the request object:

``` typescript
      const request: ValidationCaseRequest = {
        id: updatedCase.id,
        target: updatedCase.target,
        labels: updatedCase.labels,
        predicate: updatedCase.predicate,
        split: updatedCase.split,
        task_id: updatedCase.task_id ?? (taskId !== null ? taskId : undefined),
        task_repeat:
          updatedCase.task_repeat ??
          (taskRepeat !== null ? taskRepeat : undefined),
      };
```

This logic: use the value already on the case if it exists (e.g., when editing an existing case that already has metadata), otherwise use the prop values from the parent transcript context. This ensures metadata is set on first save but preserved on subsequent edits.

Also add `taskId` and `taskRepeat` to the `handleFieldChange` `useCallback` dependency array (around line 317):

``` typescript
    [
      editorValidationSetUri,
      transcriptId,
      caseData,
      queryClient,
      updateValidationCaseMutation,
      taskId,
      taskRepeat,
    ]
```

**Step 3: Pass props from `TranscriptBody`**

In `src/inspect_scout/_view/ts-mono/apps/scout/src/app/transcript/TranscriptBody.tsx` (line 565), update the `ValidationCaseEditor` usage:

``` typescript
            <ValidationCaseEditor
              transcriptId={transcript.transcript_id}
              taskId={transcript.task_id}
              taskRepeat={transcript.task_repeat}
            />
```

**Step 4: Pass props from `ScannerResultPanel`**

In `src/inspect_scout/_view/ts-mono/apps/scout/src/app/scannerResult/ScannerResultPanel.tsx` (line 486), update the `ValidationCaseEditor` usage:

``` typescript
                <ValidationCaseEditor
                  transcriptId={selectedResult.transcriptId}
                  taskId={selectedResult.transcriptTaskId != null ? String(selectedResult.transcriptTaskId) : undefined}
                  taskRepeat={selectedResult.transcriptTaskRepeat}
                />
```

Note: `selectedResult.transcriptTaskId` is typed as `string | number | undefined`, so we coerce to string to match the `task_id` field type.

**Step 5: Run TypeScript checks**

``` bash
cd src/inspect_scout/_view/ts-mono
pnpm check
cd -
```

Expected: No errors

**Step 6: Build**

``` bash
cd src/inspect_scout/_view/ts-mono
pnpm build
cd -
```

Expected: Build succeeds

**Step 7: Commit**

``` bash
cd src/inspect_scout/_view/ts-mono
git add apps/scout/src/app/validation/components/ValidationCaseEditor.tsx apps/scout/src/app/transcript/TranscriptBody.tsx apps/scout/src/app/scannerResult/ScannerResultPanel.tsx
git commit -m "feat: pass task_id and task_repeat through validation case editor"
cd -
```

------------------------------------------------------------------------

### Task 8: Commit built assets and update submodule

**Step 1: Build final dist assets**

``` bash
cd src/inspect_scout/_view/ts-mono
pnpm build
cd -
```

**Step 2: Commit built dist in base repo**

``` bash
git add src/inspect_scout/_view/dist/
git add src/inspect_scout/_view/ts-mono
git commit -m "chore: update built assets and submodule pointer"
```

------------------------------------------------------------------------

### Task 9: Final verification

**Step 1: Run full Python test suite**

Run: `.venv/bin/pytest tests/view/test_validation_api.py -v` Expected: All PASS

**Step 2: Run Python checks**

Run: `make check` (from repo root) Expected: No errors

**Step 3: Run TypeScript checks and build**

``` bash
cd src/inspect_scout/_view/ts-mono
pnpm check && pnpm build
cd -
```

Expected: No errors
