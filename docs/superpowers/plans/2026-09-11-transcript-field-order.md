# Transcript Field Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve requested messages, target, scores, and sample metadata when their JSON fields follow `events`.

**Architecture:** Track required top-level fields in the existing incremental parser. Allow its current early exit at `events` only after all required fields have appeared and the existing event and attachment guards permit it. Keep the reader's reducers, fallback, and public interfaces.

**Tech Stack:** Python, ijson, pytest, pytest-asyncio, Ruff, mypy.

## Execution record

Implementation completed on 2026-09-11. The parser and regression tests are
committed as `9331b6711`. The local PR draft is
`.dev/transcript-field-order-pr.md`; PR creation remains pending the user's
go-ahead.

- Regression evidence: the original reader failed 19 new cases and passed 9.
  The timeline regression separately failed with excluded events and passed
  with requested events before its correction. Initial implicated tests:
  **64 passed, 1 skipped**.
- Full suite: **3,364 passed, 107 skipped** with `TERM=xterm-256color`.
  The default `TERM=dumb` caused two unchanged display tests to fail; an
  isolated comparison reproduced both failures and passed all five display
  tests with the normal terminal setting. No display code was changed.
- Ruff lint and formatting, mypy (467 files), the suppression ledger, and
  `git diff --check` passed. The submodule gitlink is unchanged.
- Affected archive: **31,596 messages, 0 events**, versus zero messages on the
  base reader; 46.25 seconds and 490.4 MiB peak RSS in a fresh process.
  The portable reproduction also demonstrates restored messages, target,
  scores, and sample metadata.
- Review: GPT-6 Astra performed three fresh-context passes (spec compliance,
  code quality, and final whole-change review) and two follow-up passes in
  reused contexts, using a different model from author GPT-5.6 Luna. One
  important timeline-hydration regression was found and fixed; no findings
  were dismissed. The final review found no remaining issues and independently
  confirmed the portable reproduction against base and current source.

### Cleanup

The subsequent user-requested cleanup reduces new cases from 30 to seven:
four independently late fields, late attachment resolution, and stored
timelines with events excluded or included. Removed the repeated ordering/filter
matrix and two callback-focused functions. Existing tests remain unchanged.
The all-null fixture was rejected by the installed `EvalSample` producer;
the real omitted-scores timeline regression remains covered.

The Python test-to-production changed-line ratio is **16.2:1 before cleanup**
(243/15) and **6.9:1 after cleanup** (110/16), excluding these documents. The
local `.dev/transcript-field-order-cleanup.md` records every deleted and kept
case and its justification. The steps below retain the original implementation
sequence; this section records the final test set.

Final checks: **41 passed, 1 skipped** in the implicated modules; **3,341
passed, 107 skipped** in the full suite with `TERM=xterm-256color`. Ruff lint
and formatting, mypy (467 files), the suppression ledger, and whitespace
checks passed.

One additional fresh-context GPT-6 Astra cleanup review found no issues.
AST comparisons confirmed unchanged production logic and all 26 pre-existing
test/helper functions. All seven retained cases passed; the four late-field
cases and attachment case failed against `origin/main`, and removing only the
timeline guard reproduced the excluded-events validation failure. PR creation
remains pending the user's go-ahead.

---

## Context and file map

- Worktree: `/home/faber/src/aisi/inspect_scout-message-order`
- Branch: `fix/recovered-transcript-messages`
- Base: `origin/main` at `b61f5c067`
- Approved design: [transcript-field-order-design](../specs/2026-09-11-transcript-field-order-design.md), committed as `d6bc45cae`
- Use this worktree's `.venv`, which already contains an editable Scout install and `inspect_ai` from main at `52b30883d`.
- Run every command below from the worktree. Do not use `uv sync` or `uv run`.

| Action | File | Responsibility |
| --- | --- | --- |
| Modify | `src/inspect_scout/_transcript/json/load_filtered.py` | Require top-level field presence before the existing early exit |
| Modify | `tests/scanner/test_load_filtered.py` | Regressions for reordered fields and completion boundaries |
| Read | `tests/conftest.py` | Existing `CallTracker` fixture |
| Read | `tests/transcript/test_eval_log_read.py` | Existing coverage of the enclosing eval-log reader |
| Create locally | `.dev/transcript-field-order-pr.md` | Reviewable PR description after verification; `.dev` is ignored |

This is one parser change. No reducer refactoring, generated files, frontend
changes, suppression additions, metadata filtering, or streaming-scanner work
is needed. Preserve the submodule gitlink.

### Task 1: Reproduce field loss and guard the early exit

**Files:**
- Modify: `tests/scanner/test_load_filtered.py`, next to the existing early-exit tests
- Modify: `src/inspect_scout/_transcript/json/load_filtered.py`, inside `_parse_and_filter`

- [x] **Step 1: Add a table-driven regression for all four fields.**

Use the existing imports and `create_json_stream` helper. The ignored `store`
contains nested decoys for every protected name; these must not count as
top-level field presence. Each invocation constructs fresh mutable data.

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field_order",
    [
        pytest.param(
            ("target", "messages", "scores", "metadata", "events"),
            id="normal",
        ),
        pytest.param(
            ("target", "events", "metadata", "scores", "messages"),
            id="recovered",
        ),
        pytest.param(
            ("target", "scores", "metadata", "events", "messages"),
            id="messages-late",
        ),
        pytest.param(
            ("messages", "scores", "metadata", "events", "target"),
            id="target-late",
        ),
        pytest.param(
            ("target", "messages", "metadata", "events", "scores"),
            id="scores-late",
        ),
        pytest.param(
            ("target", "messages", "scores", "events", "metadata"),
            id="metadata-late",
        ),
        pytest.param(
            ("events", "target", "messages", "scores", "metadata"),
            id="events-first",
        ),
    ],
)
@pytest.mark.parametrize(
    "message_filter,expected_messages",
    [
        pytest.param("all", ["Hello", "Hi"], id="all-messages"),
        pytest.param(["assistant"], ["Hi"], id="assistant-only"),
    ],
)
async def test_field_order_preserves_content(
    field_order: tuple[str, ...],
    message_filter: MessageFilter,
    expected_messages: list[str],
) -> None:
    fields: dict[str, Any] = {
        "target": "full target",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ],
        "scores": {"accuracy": {"value": "C"}},
        "metadata": {"marker": "full metadata"},
        "events": [],
    }
    sample: dict[str, Any] = {
        "store": {
            "target": "nested target",
            "messages": [],
            "scores": {},
            "metadata": {},
        }
    }
    sample.update({key: fields[key] for key in field_order})
    sample["attachments"] = {}

    result = await load_filtered_transcript(
        create_json_stream(sample),
        TranscriptInfo(
            transcript_id="field-order",
            metadata={
                "existing": "kept",
                "target": "thinned target",
                "scores": {"stale": True},
                "sample_metadata": {"thinned": True},
            },
        ),
        message_filter,
        None,
    )

    assert [message.text for message in result.messages] == expected_messages
    assert result.events == []
    assert result.metadata == {
        "existing": "kept",
        "target": fields["target"],
        "scores": fields["scores"],
        "sample_metadata": fields["metadata"],
    }
```

- [x] **Step 2: Cover empty, null, and omitted fields.**

Use the existing callback only to verify the documented early-exit behavior;
the content assertions verify that the reader preserves its existing defaults.
Do not inspect parser state or add a new test hook.

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides,omitted_field,expected_metadata,should_exit",
    [
        pytest.param({}, None, {"target": ""}, True, id="empty-fields"),
        pytest.param(
            {"target": []}, None, {"target": []}, True, id="empty-target-list"
        ),
        pytest.param(
            {"target": None, "messages": None, "scores": None, "metadata": None},
            None,
            {},
            True,
            id="null-fields",
        ),
        pytest.param({}, "messages", {"target": ""}, False, id="missing-messages"),
        pytest.param({}, "target", {}, False, id="missing-target"),
        pytest.param({}, "scores", {"target": ""}, False, id="missing-scores"),
        pytest.param({}, "metadata", {"target": ""}, False, id="missing-metadata"),
    ],
)
async def test_early_exit_requires_field_presence(
    overrides: dict[str, Any],
    omitted_field: str | None,
    expected_metadata: dict[str, Any],
    should_exit: bool,
    call_tracker: CallTracker,
) -> None:
    sample: dict[str, Any] = {
        "target": "",
        "messages": [],
        "scores": {},
        "metadata": {},
    }
    sample.update(overrides)
    if omitted_field is not None:
        del sample[omitted_field]
    sample["events"] = []
    base_metadata: dict[str, Any] = {
        "existing": "kept",
        "target": "base target",
        "scores": {"base_score": True},
        "sample_metadata": {"base_metadata": True},
    }

    result = await load_filtered_transcript(
        create_json_stream(sample),
        TranscriptInfo(transcript_id="field-presence", metadata=base_metadata),
        "all",
        None,
        on_early_exit=call_tracker,
    )

    assert result.messages == []
    assert result.events == []
    assert result.metadata == base_metadata | expected_metadata
    assert call_tracker.called is should_exit
```

- [x] **Step 3: Cover message exclusion and filters that retain no messages.**

`None` excludes the messages field from the required set. Empty or nonmatching
role filters still require that field to be encountered, regardless of how
many messages the reducer retains. The explicit table also checks that there
is no new exit point after `events`.

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_filter,position,should_exit",
    [
        pytest.param(None, "before", True, id="excluded-before"),
        pytest.param(None, "after", True, id="excluded-after"),
        pytest.param([], "before", True, id="empty-filter-before"),
        pytest.param([], "after", False, id="empty-filter-after"),
        pytest.param(["tool"], "before", True, id="no-match-before"),
        pytest.param(["tool"], "after", False, id="no-match-after"),
    ],
)
async def test_early_exit_with_no_retained_messages(
    message_filter: MessageFilter,
    position: Literal["before", "after"],
    should_exit: bool,
    call_tracker: CallTracker,
) -> None:
    sample: dict[str, Any] = {"target": "", "scores": {}, "metadata": {}}
    messages = [{"role": "user", "content": "Not selected"}]
    if position == "before":
        sample["messages"] = messages
    sample["events"] = []
    if position == "after":
        sample["messages"] = messages

    result = await load_filtered_transcript(
        create_json_stream(sample),
        TranscriptInfo(transcript_id="no-retained-messages"),
        message_filter,
        None,
        on_early_exit=call_tracker,
    )

    assert result.messages == []
    assert result.events == []
    assert result.metadata == {"target": ""}
    assert call_tracker.called is should_exit
```

- [x] **Step 4: Cover attachment resolution after reordered events.**

```python
@pytest.mark.asyncio
async def test_messages_after_events_resolve_attachments() -> None:
    attachment_id = "a" * 32
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "target": "",
                "scores": {},
                "metadata": {},
                "events": [],
                "messages": [
                    {"role": "user", "content": f"attachment://{attachment_id}"}
                ],
                "attachments": {attachment_id: "Resolved content"},
            }
        ),
        TranscriptInfo(transcript_id="reordered-attachment"),
        "all",
        None,
    )

    assert [message.text for message in result.messages] == ["Resolved content"]
    assert result.events == []
```

- [x] **Step 5: Run the new tests against the unchanged reader.**

```bash
.venv/bin/python -m pytest tests/scanner/test_load_filtered.py -n 0 -q -k 'field_order_preserves_content or early_exit_requires_field_presence or early_exit_with_no_retained_messages or messages_after_events_resolve_attachments'
```

Expected: reordered-content and attachment cases fail with missing content;
omitted-field and late empty-filter cases show an unexpected early exit.
Normal ordering and several boundary cases pass. Record these failures before
editing production code; collection or environment errors do not prove the
regression.

- [x] **Step 6: Add the minimal guard in `_parse_and_filter`.**

Replace the block starting at `last_prefix = ""` through the current early-exit
`break` with this code. Leave prefix classification and reducer dispatch below
it intact.

```python
    pending_fields = {"target", "scores", "metadata"}
    if messages_filter is not None:
        pending_fields.add("messages")

    last_prefix = ""
    current_section = _SECTION_OTHER

    async for prefix, event, value in ijson.parse_async(sample_json, use_float=True):
        if prefix == "" and event == "map_key":
            pending_fields.discard(value)

        # Earlier top-level fields are complete when the events array starts.
        if (
            events_coro is None
            and prefix == "events"
            and event == "start_array"
            and not pending_fields
            and not state.attachment_refs
        ):
            if on_early_exit is not None:
                on_early_exit()
            break
```

The set contains at most four names. Updating it on top-level map keys avoids
per-token allocations and ignores nested names. Removing a field at its key is
safe because the exit is tested only when the later `events` value begins.

Also guard timeline dispatch when events are excluded:

```python
        elif current_section == _SECTION_TIMELINES and events_coro is not None:
            timelines_coro.send((prefix, event, value))
```

The code-quality review demonstrated that an unscored sample with a stored
timeline after `events` otherwise raises a validation error after this change:
timeline UUIDs cannot resolve against excluded events. Add a deterministic
regression using real `InfoEvent`, `TimelineEvent`, `TimelineSpan`, and
`Timeline` objects, with a fixed event timestamp and UUID. Parameterize the
event filter as `None` and `"all"`; messages must load in both cases, with an
empty timeline for `None` and the original hydrated timeline for `"all"`.
Capture its failing case before this dispatch correction. Public readers
already request all events when timelines are requested, so this guard needs
no reducer, fallback, or public API change.

- [x] **Step 7: Format the two changed Python files and run implicated tests.**

```bash
.venv/bin/ruff format src/inspect_scout/_transcript/json/load_filtered.py tests/scanner/test_load_filtered.py
.venv/bin/python -m pytest tests/scanner/test_load_filtered.py tests/transcript/test_eval_log_read.py -n 0 -q
```

Expected: all new tests and existing reader tests pass; the existing S3 test
remains skipped. Existing tests cover requested events, pools, fallback,
ordinary attachment guards, and the normal fast path. Keep the fix and tests
together for the verified commit in Task 2.

### Task 2: Review and verify the complete change

**Files:** Read the two modified Python files and the approved design. No new
tracked files are required.

- [x] **Step 1: Review the diff against the design.**

Use `superpowers:requesting-code-review` for a focused review of
`git diff origin/main`, with particular attention to nested keys, optional
fields, falsey message filters, and the unchanged event/attachment guards.
Include the uncommitted parser and test changes: reviewing only committed
`HEAD` at this step would miss the implementation.
Record the actual reviewer, model/tool, context freshness, number of passes,
and findings for the PR disclosure. Resolve findings within this defect's
scope; report unrelated findings without fixing them. Review must not trigger
PR creation.

- [x] **Step 2: Re-read the affected archive through the public reader.**

The locally available artifact is the same one used for the baseline
reproduction. Keep it local; do not add the archive to Git.

```bash
.venv/bin/python - /mnt/data/scratch/coordscan/target.eval <<'PY'
import asyncio
import json
import resource
import sys
import time

from inspect_scout import TranscriptContent, transcripts_from


async def main() -> None:
    started = time.monotonic()
    async with transcripts_from(sys.argv[1]).reader() as reader:
        async for info in reader.index():
            if info.task_id != "0":
                continue
            transcript = await reader.read(info, TranscriptContent(messages="all"))
            assert len(transcript.messages) == 31596
            assert transcript.events == []
            print(json.dumps({
                "messages": len(transcript.messages),
                "events": len(transcript.events),
                "seconds": round(time.monotonic() - started, 2),
                "peak_rss_mib": round(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1
                ),
            }))
            return
    raise AssertionError("Affected sample 0 was not found")


asyncio.run(main())
PY
```

Expected: 31,596 messages and zero events, compared with zero messages on the
base reader. Record elapsed time and peak RSS as observations, not thresholds.
Do not run an `events="all"` experiment on this artifact: it is unnecessary for
this defect and the original investigation already measured its large pool
expansion. If the scratch artifact has disappeared, disclose that validation
limit and retain the self-contained reproduction below.

- [x] **Step 3: Run all required static checks.**

```bash
.venv/bin/ruff check
.venv/bin/ruff format --check
.venv/bin/mypy src examples tests
.venv/bin/python scripts/check_suppressions.py
git diff --check
```

Expected: every command exits successfully. Fix errors rather than adding
suppressions. Investigate failures before attributing them to the branch;
report verified unrelated baseline failures separately.

- [x] **Step 4: Run the full default test suite once the reviewed code is final.**

```bash
.venv/bin/python -m pytest
```

Expected: no failures; slow, API, and flaky tests retain their normal skips.
Use the repository's xdist configuration. If host concurrency is impractical,
`-n 4` runs the same full suite with fewer workers. Repeat broader checks only
if subsequent changes or failures justify it.

- [x] **Step 5: Inspect scope and commit the verified fix.**

```bash
git diff --stat origin/main
git diff origin/main -- src/inspect_scout/_view/ts-mono
git status --short
git add src/inspect_scout/_transcript/json/load_filtered.py tests/scanner/test_load_filtered.py
git diff --cached --check
git commit -m "fix: preserve transcript content across JSON field order"
```

Expected: the submodule diff is empty. The implementation commit contains only
the parser and tests; the design and plan are separate documentation changes.

### Task 3: Prepare PR material and stop before creation

**Files:** Create `.dev/transcript-field-order-pr.md` locally after the checks
and review have completed.

- [x] **Step 1: Run and preserve this portable minimal reproduction.**

```bash
.venv/bin/python - <<'PY'
import asyncio
import io
import json
from typing import Any

from inspect_scout import TranscriptInfo
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript


async def main() -> None:
    sample: dict[str, Any] = {
        "events": [],
        "messages": [{"role": "user", "content": "Hello"}],
        "target": "expected",
        "scores": {"accuracy": {"value": "C"}},
        "metadata": {"marker": "present"},
    }
    result = await load_filtered_transcript(
        io.BytesIO(json.dumps(sample).encode()),
        TranscriptInfo(transcript_id="repro"),
        "all",
        None,
    )
    print(json.dumps({"messages": len(result.messages), "metadata": result.metadata}))


asyncio.run(main())
PY
```

Expected after the fix: one message, with `target`, `scores`, and
`sample_metadata` preserved. The base reader returns zero messages and empty
metadata for this input. Include the input and before/after result in the
draft so reviewers can reproduce the bug without private data.

- [x] **Step 2: Draft the PR locally using `writing-pull-requests`.**

Proposed title: `fix: preserve transcript content across JSON field order`.

Lead the description with the concrete trigger: recovered or reordered sample
JSON places requested fields after `events`, so messages-only scans can
receive empty or incomplete transcripts. Explain that the fix preserves these
fields while retaining early exit when all required fields precede `events`.
Include the omitted-field parsing tradeoff, the runnable reproduction, the
actual archive result if available, and any material validation limits.
Summarize routine automated checks in the user handoff rather than repeating
CI's checklist in the PR description. Check for a repository PR template when
drafting; none was present when this plan was written.

Add the repository-required `### Agent review` section using the review record
from Task 2. Name each finding and its disposition; explicitly disclose if no
review ran. Do not claim future checks or reviews as completed.

- [x] **Step 3: Present the verified result for PR readiness.**

Report the branch, change, validation results, review findings, and link to the
local PR draft. **Stop before `gh pr create`; PR creation remains pending the
user's go-ahead.** If later authorized, follow repository instructions to watch
the PR's checks and address failures.
