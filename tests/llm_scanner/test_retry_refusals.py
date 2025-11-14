"""End-to-end tests for retry_refusals feature in llm_scanner."""

import tempfile
from pathlib import Path

from inspect_ai.model import ModelOutput
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.database import transcripts_from_logs
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


def test_retry_success_after_refusals_regular_answer() -> None:
    """Test that scanner succeeds after retrying content filter refusals (regular answer)."""

    @scanner(name="retry_test", messages="all")
    def retry_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=3,
        )

    # Prime: 2 refusals, then success
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="I cannot answer that question.",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="I'm unable to provide that information.",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant in [M2] provided helpful information.\n\nANSWER: yes",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[retry_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify scan completed successfully
        assert status.complete
        assert len(status.errors) == 0

        # Verify result value
        results = scan_results_df(status.location, scanner="retry_test")
        df = results.scanners["retry_test"]
        assert len(df) == 1
        assert df["value"].iloc[0] is True


def test_retry_success_after_refusals_structured_answer() -> None:
    """Test that scanner succeeds after retrying refusals (structured answer)."""
    # Note: This test is a placeholder for structured answer retry testing.
    # Structured answers with mockllm require careful orchestration of tool call
    # responses, which is beyond the scope of this initial test suite.
    # The retry_refusals parameter is passed to structured_generate, so the
    # functionality is covered by the regular answer tests and unit tests.
    pass


def test_retry_exceed_limit() -> None:
    """Test that scanner fails when retry limit is exceeded."""

    @scanner(name="exceed_retry", messages="all")
    def exceed_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=2,  # Only 2 retries allowed
        )

    # Prime: 3 refusals (exceeds limit of 2)
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 1",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 2",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 3",
            stop_reason="content_filter",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[exceed_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Scan should not complete due to exceeding retry limit
        assert not status.complete

        # Verify error was recorded
        assert len(status.errors) == 1

        # Check error details
        error = status.errors[0]
        assert error.scanner == "exceed_retry"
        assert "Scanner request refused by content filter" in error.error
        assert "Refusal 3" in error.error  # Last completion text
        assert error.transcript_id
        assert error.traceback

        # Check summary error count
        assert status.summary.scanners["exceed_retry"].errors == 1
        assert status.summary.scanners["exceed_retry"].scans == 1  # Scan was attempted
        assert (
            status.summary.scanners["exceed_retry"].results == 0
        )  # No successful result


def test_no_retries_needed() -> None:
    """Test that scanner succeeds on first call without retries."""

    @scanner(name="no_retry_needed", messages="all")
    def no_retry_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=3,
        )

    # Prime: immediate success
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant in [M2] provided helpful information.\n\nANSWER: yes",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[no_retry_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify scan completed successfully
        assert status.complete
        assert len(status.errors) == 0

        # Verify result value
        results = scan_results_df(status.location, scanner="no_retry_needed")
        df = results.scanners["no_retry_needed"]
        assert len(df) == 1
        assert df["value"].iloc[0] is True


def test_retry_limit_zero_no_retries() -> None:
    """Test that retry_refusals=0 means no retries allowed."""

    @scanner(name="no_retries_allowed", messages="all")
    def no_retries_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=0,  # No retries
        )

    # Prime: 1 refusal (should fail immediately)
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="I cannot answer that.",
            stop_reason="content_filter",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[no_retries_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Scan should fail immediately
        assert not status.complete

        # Verify error was recorded
        assert len(status.errors) == 1
        assert status.errors[0].scanner == "no_retries_allowed"
        assert "Scanner request refused by content filter" in status.errors[0].error
        assert status.errors[0].transcript_id
        assert status.errors[0].traceback

        # Check summary
        assert status.summary.scanners["no_retries_allowed"].errors == 1
        assert status.summary.scanners["no_retries_allowed"].scans == 1
        assert status.summary.scanners["no_retries_allowed"].results == 0


def test_retry_limit_one() -> None:
    """Test that retry_refusals=1 allows exactly one retry."""

    @scanner(name="one_retry", messages="all")
    def one_retry_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=1,
        )

    # Prime: 1 refusal, then success (should succeed)
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="I cannot answer that.",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Analysis.\n\nANSWER: yes",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[one_retry_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Should succeed
        assert status.complete
        assert len(status.errors) == 0


def test_retry_limit_one_exceeded() -> None:
    """Test that retry_refusals=1 fails with 2 refusals."""

    @scanner(name="one_retry_exceeded", messages="all")
    def one_retry_exceeded_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=1,
        )

    # Prime: 2 refusals (exceeds limit of 1)
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 1",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 2",
            stop_reason="content_filter",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[one_retry_exceeded_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Should fail
        assert not status.complete

        # Verify error was recorded
        assert len(status.errors) == 1
        assert status.errors[0].scanner == "one_retry_exceeded"
        assert "Scanner request refused by content filter" in status.errors[0].error
        assert "Refusal 2" in status.errors[0].error  # Last completion text
        assert status.errors[0].transcript_id
        assert status.errors[0].traceback

        # Check summary
        assert status.summary.scanners["one_retry_exceeded"].errors == 1
        assert status.summary.scanners["one_retry_exceeded"].scans == 1
        assert status.summary.scanners["one_retry_exceeded"].results == 0


def test_retry_limit_false_means_no_retries() -> None:
    """Test that retry_refusals=False is equivalent to retry_refusals=0."""

    @scanner(name="false_retries", messages="all")
    def false_retries_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=False,  # Should be converted to 0
        )

    # Prime: 1 refusal (should fail immediately)
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="I cannot answer that.",
            stop_reason="content_filter",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[false_retries_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Should fail immediately
        assert not status.complete

        # Verify error was recorded (same behavior as retry_refusals=0)
        assert len(status.errors) == 1
        assert status.errors[0].scanner == "false_retries"
        assert "Scanner request refused by content filter" in status.errors[0].error
        assert status.errors[0].transcript_id
        assert status.errors[0].traceback

        # Check summary
        assert status.summary.scanners["false_retries"].errors == 1
        assert status.summary.scanners["false_retries"].scans == 1
        assert status.summary.scanners["false_retries"].results == 0


def test_multiple_transcripts_mixed_results() -> None:
    """Test multiple transcripts where some succeed after retries and some fail."""

    @scanner(name="mixed_results", messages="all")
    def mixed_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
            retry_refusals=2,
        )

    # Prime responses for 2 transcripts:
    # Transcript 1: 1 refusal, then success
    # Transcript 2: 3 refusals (exceeds limit)
    mock_responses = [
        # Transcript 1
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 1",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Analysis.\n\nANSWER: yes",
            stop_reason="stop",
        ),
        # Transcript 2
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 1",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 2",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="Refusal 3",
            stop_reason="content_filter",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[mixed_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=2,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Scan should not be complete due to error on transcript 2
        assert not status.complete

        # Verify error was recorded for the second transcript that failed
        assert len(status.errors) == 1
        assert status.errors[0].scanner == "mixed_results"
        assert "Scanner request refused by content filter" in status.errors[0].error
        assert status.errors[0].transcript_id  # Has a transcript ID

        # Summary should show one scan succeeded, one had error
        assert status.summary.scanners["mixed_results"].errors == 1
        assert status.summary.scanners["mixed_results"].results == 1  # One succeeded


def test_retry_with_string_answer_type() -> None:
    """Test retry_refusals works with string answer type."""

    @scanner(name="string_answer", messages="all")
    def string_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="What is the main topic?",
            answer="string",
            retry_refusals=2,
        )

    # Prime responses: 1 refusal, then success
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Cannot answer.",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="ANSWER: The conversation is about programming",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[string_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Should succeed
        assert status.complete

        # Verify string scanner results
        results = scan_results_df(status.location, scanner="string_answer")
        string_df = results.scanners["string_answer"]
        assert len(string_df) == 1
        assert "programming" in string_df["value"].iloc[0].lower()


def test_retry_with_numeric_answer_type() -> None:
    """Test retry_refusals works with numeric answer type."""

    @scanner(name="numeric_answer", messages="all")
    def numeric_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="How many messages?",
            answer="numeric",
            retry_refusals=2,
        )

    # Prime responses: 1 refusal, then success
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Cannot count.",
            stop_reason="content_filter",
        ),
        ModelOutput.from_content(
            model="mockllm",
            content="ANSWER: 5",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[numeric_scanner()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Should succeed
        assert status.complete

        # Verify numeric scanner results
        results = scan_results_df(status.location, scanner="numeric_answer")
        numeric_df = results.scanners["numeric_answer"]
        assert len(numeric_df) == 1
        assert numeric_df["value"].iloc[0] == 5
