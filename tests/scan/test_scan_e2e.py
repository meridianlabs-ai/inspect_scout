import json
import tempfile
from pathlib import Path

import pytest
from inspect_ai.model import ModelOutput
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout import Result, Scanner, llm_scanner, scan, scanner, transcripts_db
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


def create_minimal_transcript(transcript_id: str, index: int) -> Transcript:
    """Create a minimal transcript for testing."""
    return Transcript(
        transcript_id=transcript_id,
        source_type="test",
        source_id=f"source-{index // 100}",
        source_uri=f"test://uri/{index}",
        metadata={"index": index},
        messages=[ChatMessageUser(content=f"Test message {index}")],
        events=[],
    )


@scanner(name="simple_scanner", messages="all")
def simple_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns simple values for testing."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return a simple result based on transcript ID
        value = len(transcript.transcript_id) % 2 == 0
        return Result(
            value=value,
            explanation=f"Scanned transcript {transcript.transcript_id[:8]}",
        )

    return scan_transcript


@scanner(name="llm_test_scanner", messages="all")
def llm_scanner_factory() -> Scanner[Transcript]:
    """LLM scanner that uses mockllm for testing."""
    return llm_scanner(question="Is this conversation helpful?", answer="boolean")


@scanner(name="llm_dynamic_question_scanner", messages="all")
def llm_dynamic_question_scanner_factory() -> Scanner[Transcript]:
    """LLM scanner with dynamic question based on transcript."""

    async def dynamic_question(transcript: Transcript) -> str:
        num_messages = len(transcript.messages)
        return (
            f"In this {num_messages}-message conversation, was the assistant helpful?"
        )

    return llm_scanner(question=dynamic_question, answer="boolean")


@pytest.mark.parametrize("max_processes", [1, 2])
def test_scan_basic_e2e(max_processes: int) -> None:
    """Test basic scan functionality end-to-end with mock LLM."""
    # Configure mockllm to return properly formatted responses for llm_scanner
    # The llm_scanner expects responses ending with "ANSWER: yes" or "ANSWER: no"
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant in [M2] provided helpful information.\n\nANSWER: yes",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="The response in [M2] failed to address the user's question.\n\nANSWER: NO",
        ),
    ]

    # Run scan with both a simple scanner and an LLM scanner
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[simple_scanner_factory(), llm_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=2,
            max_processes=max_processes,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify status
        assert status.complete
        assert status.location is not None

        # Verify simple scanner results
        results = scan_results_df(status.location, scanner="simple_scanner")
        simple_df = results.scanners["simple_scanner"]
        assert len(simple_df) == 2
        assert "value" in simple_df.columns
        assert "explanation" in simple_df.columns

        # Verify LLM scanner results
        results = scan_results_df(status.location, scanner="llm_test_scanner")
        llm_df = results.scanners["llm_test_scanner"]
        assert len(llm_df) == 2
        assert "value" in llm_df.columns
        assert "explanation" in llm_df.columns
        # Verify the LLM scanner parsed the responses correctly
        # In single-process mode, mock responses are consumed in order
        # In multi-process mode, each process gets its own copy starting at index 0
        if max_processes == 1:
            assert sorted(llm_df["value"].tolist()) == [False, True]
        else:
            assert all(isinstance(v, bool) for v in llm_df["value"].tolist())


@pytest.mark.parametrize("max_processes", [1, 2])
def test_scan_with_dynamic_question(max_processes: int) -> None:
    """Test LLM scanner with dynamic question callable."""
    # Configure mockllm to return properly formatted responses
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Yes, the assistant was helpful.\n\nANSWER: yes",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[llm_dynamic_question_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=max_processes,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify status
        assert status.complete
        assert status.location is not None

        # Verify dynamic question scanner results
        results = scan_results_df(
            status.location, scanner="llm_dynamic_question_scanner"
        )
        scanner_df = results.scanners["llm_dynamic_question_scanner"]
        assert len(scanner_df) == 1
        assert "value" in scanner_df.columns
        assert scanner_df["value"].tolist() == [True]


@scanner(name="count_scanner", messages="all")
def count_scanner_factory() -> Scanner[Transcript]:
    """Simple scanner that just counts transcripts for testing large batches."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=transcript.metadata.get("index", 0),
            explanation=f"Scanned {transcript.transcript_id}",
        )

    return scan_transcript


def test_scan_processes_all_transcripts_beyond_1000(tmp_path: Path) -> None:
    """Test that scans process ALL transcripts when count exceeds 1000.

    This is an end-to-end test that verifies no artificial limit of 1000
    is applied during scanning. It creates 1500 transcripts in a database,
    runs a scan without any limit, and verifies all 1500 are processed.
    """
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    # Create 1500 transcripts in the database (exceeds the batch_size=1000)
    transcript_count = 1500

    # Insert transcripts
    import asyncio

    async def insert_transcripts() -> None:
        transcripts = [
            create_minimal_transcript(f"test-{i:05d}", i)
            for i in range(transcript_count)
        ]
        async with transcripts_db(str(db_path)) as db:
            await db.insert(transcripts)

    asyncio.run(insert_transcripts())

    # Run scan WITHOUT any limit - should process all transcripts
    status = scan(
        scanners=[count_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,  # Single process for deterministic testing
        display="none",
    )

    # Verify scan completed
    assert status.complete, f"Scan did not complete: {status}"
    assert status.location is not None

    # Verify ALL transcripts were scanned
    results = scan_results_df(status.location, scanner="count_scanner")
    scanner_df = results.scanners["count_scanner"]

    assert len(scanner_df) == transcript_count, (
        f"Expected {transcript_count} scan results, got {len(scanner_df)}. "
        "This indicates a limit is being applied during scanning."
    )


def test_scan_model_usage_not_cumulative(tmp_path: Path) -> None:
    """Test that scan_total_tokens reflects per-scan usage, not cumulative.

    Regression test for a bug where init_model_usage() didn't reset the
    model usage context between sequential scans within the same worker task,
    causing scan_total_tokens to accumulate across scans.
    """
    db_path = tmp_path / "transcript_db"
    scans_path = tmp_path / "scans"
    db_path.mkdir()
    scans_path.mkdir()

    transcript_count = 5

    import asyncio

    async def insert_transcripts() -> None:
        transcripts = [
            create_minimal_transcript(f"token-test-{i:03d}", i)
            for i in range(transcript_count)
        ]
        async with transcripts_db(str(db_path)) as db:
            await db.insert(transcripts)

    asyncio.run(insert_transcripts())

    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant was helpful.\n\nANSWER: yes",
        )
        for _ in range(transcript_count)
    ]

    # max_transcripts=1 forces a single worker to process all scans
    # sequentially, which is where the cumulative bug manifests
    status = scan(
        scanners=[llm_scanner_factory()],
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans_path),
        max_processes=1,
        max_transcripts=1,
        model="mockllm/model",
        model_args={"custom_outputs": mock_responses},
        display="none",
    )

    assert status.complete
    assert status.location is not None

    results = scan_results_df(
        status.location, scanner="llm_test_scanner", rows="transcripts"
    )
    df = results.scanners["llm_test_scanner"]
    assert len(df) == transcript_count

    # Every scan uses the same prompt/response, so each should report
    # identical token counts. Before the fix, tokens grew cumulatively:
    # [187, 374, 561, 748, 935] instead of [187, 187, 187, 187, 187].
    first_tokens = int(df["scan_total_tokens"].iloc[0])
    assert first_tokens > 0
    assert df["scan_total_tokens"].tolist() == [first_tokens] * transcript_count

    first_usage_str = df["scan_model_usage"].iloc[0]
    first_usage = json.loads(first_usage_str)
    model_name = next(iter(first_usage))
    assert first_usage[model_name]["input_tokens"] > 0
    assert first_usage[model_name]["output_tokens"] > 0
    assert first_usage[model_name]["total_tokens"] == first_tokens

    for i in range(1, transcript_count):
        usage = json.loads(df["scan_model_usage"].iloc[i])
        assert usage == first_usage, (
            f"scan_model_usage for scan {i} differs from scan 0: {usage} != {first_usage}"
        )
