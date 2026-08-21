"""Degrade-to-reference behavior of the record path."""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest
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


@pytest.mark.asyncio
async def test_record_failure_degrades_to_reference() -> None:
    info = TranscriptInfo(transcript_id="t1", source_uri="file:///log.eval")

    async def failing_load() -> Transcript:
        raise RuntimeError("boom")

    handle = MaterializedTranscriptHandle(failing_load, info)
    job = ScannerJob(
        union_transcript=handle, scanner=_streaming_scanner(), scanner_name="s"
    )
    reports = await _scan_one(job, validation=None, fail_on_error=False)
    assert len(reports) == 1
    report_input = reports[0].input
    assert isinstance(report_input, ReferenceTranscript)
    assert report_input.transcript_id == "t1"
    assert report_input.source_uri == "file:///log.eval"
    assert (
        report_input.content_json
        == TranscriptContent(messages="all", events="all", timeline=None).to_json()
    )
    # The scan's value is kept; the read failure is surfaced as the row error.
    assert reports[0].result is not None
    assert reports[0].error is not None


def _mock_yes_responses(n: int) -> list[ModelOutput]:
    return [
        ModelOutput.from_content(model="mockllm", content="Reasoning.\n\nANSWER: yes")
        for _ in range(n)
    ]


def test_oversized_transcript_records_reference_and_scan_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An oversized transcript used to leave the scan incomplete and unresumable.

    It must instead complete with the scanner's result and a reference input,
    even under fail_on_error: oversize is a degrade, not a failure.
    """
    # llm_scanner is handle-capable, so the job streams and reaches the
    # spool-side guard; a plain Transcript scanner would only exercise the
    # parent-side backstop in ResultReport.to_df_columns.
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
            fail_on_error=True,
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


def test_record_input_persists_in_scan_options() -> None:
    from inspect_scout._scanspec import ScanOptions

    assert ScanOptions().record_input == "copy"
    assert ScanOptions(record_input="reference").record_input == "reference"
    assert ScanOptions.model_validate({"max_transcripts": 5}).record_input == "copy"


def test_reference_mode_handle_path_records_reference() -> None:
    """`record_input="reference"` short-circuits a handle-capable scan.

    `llm_scanner` is handle-capable (mirrors the streaming pattern used by
    `test_oversized_transcript_records_reference_and_scan_completes`), so the
    job is streaming-eligible and its `TranscriptHandle` input reaches the
    record site directly. This is mode-by-choice (`record_input="reference"`),
    not the oversized-cell degrade, so no cap monkeypatching: the handle
    should short-circuit straight to `_reference_for_record` -- with real
    content filters -- rather than materializing.
    """

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
            max_processes=1,  # in-process, streaming-eligible
            model="mockllm/model",
            model_args={"custom_outputs": _mock_yes_responses(40)},
            record_input="reference",
            display="none",
        )
        assert status.complete
        assert status.location is not None

        files = list(Path(status.location).rglob("*.parquet"))
        assert files
        rows = (
            duckdb.connect()
            .execute(
                "SELECT input, input_storage, input_content, transcript_source_uri, "
                "transcript_id FROM read_parquet(?)",
                [files[0].as_posix()],
            )
            .fetchall()
        )
        assert len(rows) == 1
        input_cell, storage, content, source_uri, transcript_id = rows[0]
        assert input_cell is None
        assert storage == "reference"
        assert content is not None and "messages" in content
        assert source_uri and transcript_id


def test_reference_mode_materialized_path_records_reference() -> None:
    """`record_input="reference"` also covers a materialized `Transcript` input.

    A plain `Transcript`-typed scanner is not streaming-eligible -- the
    pipeline materializes it up front via `reader.read()` -- so this exercises
    the `isinstance(loader_input, Transcript)` branch at the record site,
    which has no content filters available and always records
    `input_content=None`.
    """
    from inspect_scout._scanner.result import Result

    @scanner(messages="all")
    def probe() -> Scanner[Transcript]:
        async def scan_fn(t: Transcript) -> Result:
            return Result(value=len(t.messages))

        # This module's `from __future__ import annotations` makes
        # `scan_fn`'s parameter annotation a string at runtime, but
        # `create_implicit_loader` reads `inspect.signature(...).annotation`
        # directly (no `get_type_hints`); restore the real class so it
        # recognizes the identity (materializing) loader.
        scan_fn.__annotations__["t"] = Transcript
        return scan_fn

    logs_dir = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
    with tempfile.TemporaryDirectory() as scans:
        status = scan(
            scanners=[probe()],
            transcripts=transcripts_from(logs_dir),
            scans=scans,
            limit=1,
            max_processes=1,
            record_input="reference",
            display="none",
        )
        assert status.complete
        assert status.location is not None

        files = list(Path(status.location).rglob("*.parquet"))
        assert files
        rows = (
            duckdb.connect()
            .execute(
                "SELECT input, input_storage, input_content FROM read_parquet(?)",
                [files[0].as_posix()],
            )
            .fetchall()
        )
        assert len(rows) == 1
        input_cell, storage, content = rows[0]
        assert input_cell is None
        assert storage == "reference"
        assert content is None


def test_reference_report_pickles_small() -> None:
    import pickle

    from inspect_scout._scanner.result import Result, ResultReport

    report = ResultReport(
        input_type="transcript",
        input_ids=["t"],
        input=ReferenceTranscript(
            source_uri="s3://b/l.eval", transcript_id="t", content_json="{}"
        ),
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )
    assert len(pickle.dumps(report)) < 50_000
