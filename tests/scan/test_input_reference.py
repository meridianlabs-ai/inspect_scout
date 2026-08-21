"""Degrade-to-reference behavior of the record path."""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest
from inspect_ai.model import ModelOutput
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._scan import _transcript_for_record
from inspect_scout._scanner.result import ReferenceTranscript
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from inspect_scout._util import constants as constants_mod


@pytest.mark.asyncio
async def test_record_failure_degrades_to_reference() -> None:
    content = TranscriptContent(messages="all", events=None, timeline=None)
    info = TranscriptInfo(transcript_id="t1", source_uri="file:///log.eval")

    async def failing_load():  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    handle = MaterializedTranscriptHandle(failing_load, info, content)
    report_input = await _transcript_for_record(handle, fail_on_error=False)
    assert isinstance(report_input, ReferenceTranscript)
    assert report_input.transcript_id == "t1"
    assert report_input.source_uri == "file:///log.eval"
    assert report_input.content_json == content.to_json()


def _mock_yes_responses(n: int) -> list[ModelOutput]:
    return [
        ModelOutput.from_content(model="mockllm", content="Reasoning.\n\nANSWER: yes")
        for _ in range(n)
    ]


def test_oversized_transcript_records_reference_and_scan_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real scan over an oversized transcript must complete, not abort.

    Regression baseline: an oversized transcript used to end the scan
    `complete: false` with an empty `_errors.jsonl` and an unresumable
    location. With the cap monkeypatched so every cell is "oversized", the
    scan must complete, the scanner's real result must be preserved, and
    the row must degrade to a `reference` input row instead of an inline one.

    The scanner must be handle-capable (`llm_scanner`) so the job is
    streaming-eligible and runs the spool-side guard
    (`pooled_passthrough` -> `TranscriptTooLargeToRecordError` ->
    `_transcript_for_record`'s degrade). A plain `Transcript`-typed scanner
    materializes up front and would only exercise the separate parent-side
    backstop in `ResultReport.to_df_columns`.
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


def test_scan_options_without_record_input_default_to_copy() -> None:
    """Specs written before the field existed must still parse (resume)."""
    from inspect_scout._scanspec import ScanOptions

    assert ScanOptions.model_validate({"max_transcripts": 5}).record_input == "copy"


def test_reference_mode_handle_path_records_reference() -> None:
    """`record_input="reference"` short-circuits a handle-capable scan.

    No cap monkeypatching -- this is mode-by-choice, not the oversized-cell
    degrade. The streaming-eligible handle must go straight to
    `_reference_for_record` with real content filters, never materializing.
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

    A plain `Transcript`-typed scanner is not streaming-eligible, so this
    exercises the record site's materialized branch, which has no content
    filters available and records `input_content=None`.
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


@pytest.mark.asyncio
async def test_resolve_round_trips_what_the_scanner_saw() -> None:
    from inspect_scout import resolve_input_reference
    from inspect_scout._transcript.eval_log import EvalLogTranscriptsView

    logs_dir = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
    log = sorted(logs_dir.glob("*.eval"))[0]
    content = TranscriptContent(messages="all", events=None, timeline=None)

    view = EvalLogTranscriptsView(str(log))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        expected = await view.read(infos[0], content)
    finally:
        await view.disconnect()

    row = {
        "input_storage": "reference",
        "transcript_source_uri": str(log),
        "transcript_id": infos[0].transcript_id,
        "input_content": content.to_json(),
    }
    resolved = await resolve_input_reference(row)
    assert [m.model_dump() for m in resolved.messages] == [
        m.model_dump() for m in expected.messages
    ]


@pytest.mark.asyncio
async def test_resolve_treats_nan_input_content_as_absent() -> None:
    """A pandas row's NULL `input_content` surfaces as `float('nan')`, not `None`.

    `bool(float('nan'))` is `True`, so a plain truthiness check on
    `input_content` would send NaN into `TranscriptContent.from_json` instead
    of falling back to full content. Guard it like a DataFrame row would
    actually look.
    """
    from inspect_scout import resolve_input_reference

    logs_dir = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
    log = sorted(logs_dir.glob("*.eval"))[0]

    from inspect_scout._transcript.eval_log import EvalLogTranscriptsView

    view = EvalLogTranscriptsView(str(log))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
    finally:
        await view.disconnect()

    row = {
        "input_storage": "reference",
        "transcript_source_uri": str(log),
        "transcript_id": infos[0].transcript_id,
        "input_content": float("nan"),
    }
    resolved = await resolve_input_reference(row)
    assert resolved.messages


@pytest.mark.asyncio
async def test_resolve_failures_are_loud() -> None:
    from inspect_scout import resolve_input_reference

    with pytest.raises(ValueError, match="not a reference"):
        await resolve_input_reference({"input_storage": "inline"})
    with pytest.raises(ValueError, match="source_uri"):
        await resolve_input_reference(
            {
                "input_storage": "reference",
                "transcript_source_uri": None,
                "transcript_id": "t",
            }
        )
    with pytest.raises(ValueError, match="transcript_id"):
        await resolve_input_reference(
            {
                "input_storage": "reference",
                "transcript_source_uri": "file:///log.eval",
            }
        )
    logs_dir = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
    log = sorted(logs_dir.glob("*.eval"))[0]
    with pytest.raises(ValueError, match="not found"):
        await resolve_input_reference(
            {
                "input_storage": "reference",
                "transcript_source_uri": str(log),
                "transcript_id": "does-not-exist",
                "input_content": None,
            }
        )
