import tempfile
from pathlib import Path

from inspect_ai.model import ModelOutput
from inspect_scout import Result, Scanner, llm_scanner, scan, scanner
from inspect_scout._scanresults import scan_results
from inspect_scout._transcript.database import transcripts_from_logs
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


@scanner(name="simple_scanner", messages="all")
def simple_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns simple values for testing."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return a simple result based on transcript ID
        value = len(transcript.id) % 2 == 0
        return Result(
            value=value,
            explanation=f"Scanned transcript {transcript.id[:8]}",
        )

    return scan_transcript


@scanner(name="llm_test_scanner", messages="all")
def llm_scanner_factory() -> Scanner[Transcript]:
    """LLM scanner that uses mockllm for testing."""
    return llm_scanner(
        prompt="Is this conversation helpful?",
        answer="boolean",
    )


def test_scan_basic_e2e() -> None:
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
            content="The response in [M2] addresses the user's question.\n\nANSWER: yes",
        ),
    ]

    # Run scan with both a simple scanner and an LLM scanner
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[simple_scanner_factory(), llm_scanner_factory()],
            transcripts=transcripts_from_logs(LOGS_DIR),
            results=tmpdir,
            limit=2,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        # Verify status
        assert status.complete
        assert status.location is not None

        # Verify simple scanner results
        results = scan_results(status.location, scanner="simple_scanner")
        simple_df = results.scanners["simple_scanner"]
        assert len(simple_df) == 2
        assert "value" in simple_df.columns
        assert "explanation" in simple_df.columns

        # Verify LLM scanner results
        results = scan_results(status.location, scanner="llm_test_scanner")
        llm_df = results.scanners["llm_test_scanner"]
        assert len(llm_df) == 2
        assert "value" in llm_df.columns
        assert "explanation" in llm_df.columns
        # Verify the LLM scanner parsed the responses correctly
        assert llm_df["value"].tolist() == [True, True]
