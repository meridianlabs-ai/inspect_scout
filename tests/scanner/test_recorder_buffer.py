from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Generator

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._recorder.buffer import RecorderBuffer, scanner_table
from inspect_scout._scanner.result import Reference, Result, ResultReport
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._transcript.types import TranscriptInfo


@pytest.fixture
def recorder_buffer() -> Generator[RecorderBuffer]:
    """Create a temporary RecorderBuffer for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = ScanSpec(
            scan_name="myscan",
            scanners={
                "test_scanner": ScannerSpec(name="test_scanner"),
                "test-scanner.with:special/chars": ScannerSpec(
                    name="test-scanner.with:special/chars"
                ),
            },
        )
        buffer = RecorderBuffer(tmpdir, spec)
        yield buffer
        buffer.cleanup()


@pytest.fixture
def sample_transcript() -> TranscriptInfo:
    """Create a sample TranscriptInfo for testing."""
    return TranscriptInfo(
        transcript_id="test-transcript-123",
        source_type="test",
        source_id="source-42",
        source_uri="/path/to/source.log",
        metadata={"model": "gpt-4", "temperature": 0.7},
    )


@pytest.fixture
def sample_results() -> list[ResultReport]:
    """Create sample Results for testing."""
    return [
        ResultReport(
            input_type="message",
            input_ids=[],
            input=ChatMessageUser(content=""),
            result=Result(
                value="correct",
                explanation="The answer to everything",
                metadata={"confidence": 0.95},
                references=[Reference(type="message", id="msg-1")],
            ),
            validation=None,
            error=None,
            events=[],
            model_usage={},
        ),
        ResultReport(
            input_type="message",
            input_ids=[],
            input=ChatMessageUser(content=""),
            result=Result(
                value=True,
                explanation="Affirmative response",
                metadata={"confidence": 0.88},
                references=[Reference(type="event", id="evt-1")],
            ),
            validation=None,
            error=None,
            events=[],
            model_usage={},
        ),
        ResultReport(
            input_type="message",
            input_ids=[],
            input=ChatMessageUser(content=""),
            result=Result(
                value=3.14159,
                explanation="Pi value",
                metadata=None,
                references=[],
            ),
            validation=None,
            error=None,
            events=[],
            model_usage={},
        ),
    ]


@pytest.mark.asyncio
async def test_is_recorded(
    recorder_buffer: RecorderBuffer,
    sample_transcript: TranscriptInfo,
    sample_results: list[ResultReport],
) -> None:
    """Test is_recorded method."""
    scanner_name = "test_scanner"

    # Check before recording
    is_recorded = await recorder_buffer.is_recorded(
        sample_transcript.transcript_id, scanner_name
    )
    assert is_recorded is False

    # Record data
    await recorder_buffer.record(sample_transcript, scanner_name, sample_results, None)

    # Check after recording
    is_recorded = await recorder_buffer.is_recorded(
        sample_transcript.transcript_id, scanner_name
    )
    assert is_recorded is True

    # Check with different transcript ID
    other_transcript = TranscriptInfo(
        transcript_id="other-transcript-456",
        source_type="test",
        source_id="42",
        source_uri="/other/source.log",
    )
    is_recorded = await recorder_buffer.is_recorded(
        other_transcript.transcript_id, scanner_name
    )
    assert is_recorded is False


@pytest.mark.asyncio
async def test_sanitize_table_names(
    recorder_buffer: RecorderBuffer,
    sample_transcript: TranscriptInfo,
    sample_results: list[ResultReport],
) -> None:
    """Test that table names with special characters are sanitized."""
    scanner_name = "test-scanner.with:special/chars"

    # Record with special characters in scanner name
    await recorder_buffer.record(sample_transcript, scanner_name, sample_results, None)

    # Should still be able to retrieve
    scanner_table(recorder_buffer._buffer_dir, scanner_name)


@pytest.mark.asyncio
async def test_scanner_table_casts_mixed_transcript_score_to_string(
    recorder_buffer: RecorderBuffer,
    sample_results: list[ResultReport],
) -> None:
    scanner_name = "test_scanner"
    await recorder_buffer.record(
        TranscriptInfo(
            transcript_id="score-int",
            source_type="test",
            source_id="source-1",
            source_uri="/path/to/source-1.log",
            score=1,
        ),
        scanner_name,
        sample_results,
        None,
    )
    await recorder_buffer.record(
        TranscriptInfo(
            transcript_id="score-json",
            source_type="test",
            source_id="source-2",
            source_uri="/path/to/source-2.log",
            score={"value": 0, "answer": "nope", "history": []},
        ),
        scanner_name,
        sample_results,
        None,
    )

    parquet_bytes = scanner_table(recorder_buffer._buffer_dir, scanner_name)
    assert parquet_bytes is not None

    table = pq.read_table(io.BytesIO(parquet_bytes))
    assert table.schema.field("transcript_score").type == pa.string()


def test_buffer_dir_respects_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that SCOUT_SCANBUFFER_DIR env var overrides the default buffer location."""
    custom_dir = tmp_path / "custom_buffer"
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(custom_dir))
    result = RecorderBuffer.buffer_dir("/some/scan/location")
    assert result.parent == custom_dir


@pytest.mark.asyncio
async def test_scanner_table_dedupes_extra_inputs_against_buffer(
    recorder_buffer: RecorderBuffer,
    sample_results: list[ResultReport],
    tmp_path: Path,
) -> None:
    """`scanner_table` drops `extra_inputs` rows whose transcript_id is
    already covered by a buffer file.

    Otherwise, calling `scanner_table` against a buffer that wasn't
    cleaned up after a prior compaction (e.g. inspect_ai's eval_set
    resume cycle, where the prior compacted parquet is passed via
    `extra_inputs`) would double-count every transcript present in
    both — once from the buffer file, once from the prior compacted.
    """
    from upath import UPath
    from inspect_ai.model import ChatMessageUser

    scanner_name = "test_scanner"
    # write two transcripts to the buffer
    for tid in ("tid-A", "tid-B"):
        await recorder_buffer.record(
            TranscriptInfo(
                transcript_id=tid,
                source_type="test",
                source_id=f"src-{tid}",
                source_uri=f"/path/{tid}.log",
            ),
            scanner_name,
            sample_results,
            None,
        )

    # snapshot the buffer's compacted output and use it as extra_inputs
    # — this mirrors what `_compact_with_prior` passes into `sync`.
    first = scanner_table(recorder_buffer._buffer_dir, scanner_name)
    assert first is not None
    prior_path = tmp_path / "prior.parquet"
    prior_path.write_bytes(first)

    # second compaction with the prior as extra_inputs. Without dedup
    # the output would have each tid's rows twice.
    second = scanner_table(
        recorder_buffer._buffer_dir,
        scanner_name,
        extra_inputs=[UPath(prior_path)],
    )
    assert second is not None

    # load and check: same row count as the original (no doubling),
    # same set of transcript_ids
    first_tbl = pq.read_table(io.BytesIO(first))
    second_tbl = pq.read_table(io.BytesIO(second))
    assert second_tbl.num_rows == first_tbl.num_rows, (
        f"extra_inputs duplicated buffer rows: {second_tbl.num_rows} "
        f"vs expected {first_tbl.num_rows}"
    )
    assert set(second_tbl.column("transcript_id").to_pylist()) == {"tid-A", "tid-B"}


@pytest.mark.asyncio
async def test_scanner_table_keeps_extra_inputs_for_transcripts_not_in_buffer(
    recorder_buffer: RecorderBuffer,
    sample_results: list[ResultReport],
    tmp_path: Path,
) -> None:
    """`extra_inputs` rows for transcripts NOT in the buffer are preserved.

    The dedup fix must only filter overlapping transcript_ids — rows
    from `extra_inputs` for transcripts that aren't represented in the
    buffer (e.g. transcripts compacted in an earlier sync whose buffer
    files have since been cleaned) must still flow through.
    """
    from upath import UPath

    scanner_name = "test_scanner"
    # snapshot a buffer with one transcript ("tid-old"), use it as the
    # prior compacted output, then clear and write a different one
    # ("tid-new") to the buffer.
    await recorder_buffer.record(
        TranscriptInfo(
            transcript_id="tid-old",
            source_type="test",
            source_id="src-old",
            source_uri="/path/old.log",
        ),
        scanner_name,
        sample_results,
        None,
    )
    prior_bytes = scanner_table(recorder_buffer._buffer_dir, scanner_name)
    assert prior_bytes is not None
    prior_path = tmp_path / "prior.parquet"
    prior_path.write_bytes(prior_bytes)

    # clear the buffer file for tid-old and write tid-new
    sdir = recorder_buffer._buffer_dir / f"scanner={scanner_name}"
    for f in sdir.glob("*.parquet"):
        f.unlink()
    await recorder_buffer.record(
        TranscriptInfo(
            transcript_id="tid-new",
            source_type="test",
            source_id="src-new",
            source_uri="/path/new.log",
        ),
        scanner_name,
        sample_results,
        None,
    )

    out = scanner_table(
        recorder_buffer._buffer_dir,
        scanner_name,
        extra_inputs=[UPath(prior_path)],
    )
    assert out is not None
    tbl = pq.read_table(io.BytesIO(out))
    # both transcripts present: tid-new from buffer, tid-old from extras
    assert set(tbl.column("transcript_id").to_pylist()) == {"tid-old", "tid-new"}


def test_buffer_dir_expands_tilde(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that ~ in SCOUT_SCANBUFFER_DIR is expanded to the home directory."""
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", "~/my_scout_buffer")
    monkeypatch.setenv("HOME", str(tmp_path))
    result = RecorderBuffer.buffer_dir("/some/scan/location")
    assert result.parent == tmp_path / "my_scout_buffer"
