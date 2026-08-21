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


@pytest.mark.asyncio
async def test_record_failure_raises_with_fail_on_error() -> None:
    content = TranscriptContent(None, None, None)
    info = TranscriptInfo(transcript_id="t1")

    async def failing_load():  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    handle = MaterializedTranscriptHandle(failing_load, info, content)
    with pytest.raises(RuntimeError):
        await _transcript_for_record(handle, fail_on_error=True)


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


@pytest.mark.asyncio
async def test_resolve_round_trips_what_the_scanner_saw(tmp_path: Path) -> None:
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
