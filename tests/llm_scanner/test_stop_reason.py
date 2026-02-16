"""Tests for stop_reason metadata in llm_scanner results."""

import json
import tempfile
from pathlib import Path

import pytest
from inspect_ai.model import ModelOutput, StopReason
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


@pytest.mark.parametrize(
    "stop_reason",
    ["stop", "max_tokens", "model_length", "tool_calls", "unknown"],
)
def test_stop_reason_in_result_metadata(stop_reason: StopReason) -> None:
    """stop_reason from model output is stored in result metadata."""

    @scanner(name="stop_reason_test", messages="all")
    def stop_reason_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this conversation helpful?",
            answer="boolean",
        )

    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="The assistant was helpful.\n\nANSWER: yes",
            stop_reason=stop_reason,
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[stop_reason_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        assert status.complete
        assert status.location is not None

        results = scan_results_df(status.location, scanner="stop_reason_test")
        df = results.scanners["stop_reason_test"]
        assert len(df) == 1

        metadata = json.loads(df["metadata"].iloc[0])
        assert metadata["stop_reason"] == stop_reason
