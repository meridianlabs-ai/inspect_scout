"""Degrade-to-reference behavior of the record path."""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import ModelOutput
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._concurrency.common import ScannerJob
from inspect_scout._scan import _scan_one
from inspect_scout._scanner.result import ReferenceTranscript, Result
from inspect_scout._scanner.scanner import mark_streaming_support
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from inspect_scout._util import constants as constants_mod


@scanner(messages="all", events="all")
def _streaming_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    mark_streaming_support(scan, True)
    return scan


def _failing_handle(
    error: Exception, content: TranscriptContent
) -> MaterializedTranscriptHandle:
    info = TranscriptInfo(transcript_id="t1", source_uri="file:///log.eval")

    async def failing_load() -> Transcript:
        raise error

    return MaterializedTranscriptHandle(failing_load, info, content)


@pytest.mark.asyncio
async def test_record_failure_degrades_to_reference() -> None:
    content = TranscriptContent(messages="all", events=None, timeline=None)
    handle = _failing_handle(RuntimeError("boom"), content)
    job = ScannerJob(
        union_transcript=handle, scanner=_streaming_scanner(), scanner_name="s"
    )
    reports = await _scan_one(job, validation=None, fail_on_error=False)
    assert len(reports) == 1
    report_input = reports[0].input
    assert isinstance(report_input, ReferenceTranscript)
    assert report_input.transcript_id == "t1"
    assert report_input.source_uri == "file:///log.eval"
    assert report_input.content_json == content.to_json()
    # The scan's value is kept; the read failure is surfaced as the row error.
    assert reports[0].result is not None
    assert reports[0].error is not None


@pytest.mark.parametrize(
    ("error", "fail_on_error"),
    [
        pytest.param(RuntimeError("boom"), True, id="fail_on_error"),
        pytest.param(PrerequisiteError("boom"), False, id="prerequisite"),
    ],
)
@pytest.mark.asyncio
async def test_record_failure_raises(error: Exception, fail_on_error: bool) -> None:
    handle = _failing_handle(error, TranscriptContent(None, None, None))
    job = ScannerJob(
        union_transcript=handle, scanner=_streaming_scanner(), scanner_name="s"
    )
    with pytest.raises(type(error)):
        await _scan_one(job, validation=None, fail_on_error=fail_on_error)


def _mock_yes_responses(n: int) -> list[ModelOutput]:
    return [
        ModelOutput.from_content(model="mockllm", content="Reasoning.\n\nANSWER: yes")
        for _ in range(n)
    ]


def test_oversized_transcript_records_reference_and_scan_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real scan over an oversized transcript must complete, not abort.

    Regression baseline: before this branch, one oversized transcript ended
    the scan `complete: false` with an empty `_errors.jsonl` (verified on a
    real 6-sample log -- 5 recorded, the scan uncompletable). With the cap
    monkeypatched to make every cell "oversized", the scan must still
    complete, the scanner's real result must be preserved, and the row must
    degrade to a `reference` input row instead of an inline one.

    The scanner must be handle-capable (`llm_scanner`, like the streaming
    tests in `test_scan_streaming.py`) so the job is streaming-eligible and
    actually runs through `SpooledTranscriptHandle` -> `pooled_passthrough`
    -> `TranscriptTooLargeToRecordError` -> `_transcript_for_record`'s
    degrade path (Tasks 4-5). A plain `Transcript`-typed scanner is not
    streaming-eligible: the pipeline materializes it up front via
    `reader.read()`, which never reaches that guard at all -- it would
    instead (accidentally) hit the pre-existing, unrelated oversized-cell
    fallback inside `ResultReport.to_df_columns` (which has no content
    filters available and always records `input_content=None`), so it
    would not actually exercise -- or guard -- this PR's mechanism.
    """
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)  # force spooled
    monkeypatch.setattr(
        constants_mod, "RECORD_CELL_MAX_BYTES", 1000
    )  # every cell "oversized"

    @scanner(name="probe", messages="all", events="all")
    def probe() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            content=TranscriptContent(messages="all", events="all"),
        )

    logs_dir = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
    with tempfile.TemporaryDirectory() as scans:
        status = scan(
            scanners=[probe()],
            transcripts=transcripts_from(logs_dir),
            scans=scans,
            limit=1,
            max_processes=1,  # in-process so the monkeypatched constants apply
            model="mockllm/model",
            model_args={"custom_outputs": _mock_yes_responses(40)},
            display="none",
        )
        assert status.complete, "oversized input must not prevent completion"
        assert status.location is not None

        files = list(Path(status.location).rglob("*.parquet"))
        assert files
        rows = (
            duckdb.connect()
            .execute(
                "SELECT value, input, input_storage, input_content FROM read_parquet(?)",
                [files[0].as_posix()],
            )
            .fetchall()
        )
        assert len(rows) == 1
        value, input_cell, storage, content = rows[0]
        # The compacted parquet's "value" column is always string-typed
        # (`scanner_table` forces mixed-type columns to string), so the
        # boolean round-trips as pyarrow's cast of `True`: "true".
        assert value == "true"  # scanner's real result preserved
        assert input_cell is None  # nothing inline
        assert storage == "reference"
        assert content is not None and "messages" in content
