"""Tests for llm_scanner answer parsing bugs."""

import tempfile
from pathlib import Path

from inspect_ai.model import ModelOutput
from inspect_scout import Scanner, llm_scanner, scan, scanner
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


def test_numeric_answer_non_integer() -> None:
    """Bug: llm_scanner with answer='numeric' doesn't parse non-integer values like 0.5."""

    @scanner(name="numeric_non_int", messages="all")
    def numeric_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Rate this from 0 to 1",
            answer="numeric",
        )

    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="ANSWER: 0.5",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[numeric_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        assert status.complete
        results = scan_results_df(status.location, scanner="numeric_non_int")
        df = results.scanners["numeric_non_int"]
        assert len(df) == 1
        assert df["value"].iloc[0] == 0.5


def test_numeric_answer_bolded_markdown() -> None:
    """Bug: llm_scanner doesn't parse answers wrapped in markdown bold (**ANSWER: 7**)."""

    @scanner(name="numeric_bold", messages="all")
    def numeric_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="How many messages?",
            answer="numeric",
        )

    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="**ANSWER: 7**",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[numeric_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        assert status.complete
        results = scan_results_df(status.location, scanner="numeric_bold")
        df = results.scanners["numeric_bold"]
        assert len(df) == 1
        assert df["value"].iloc[0] == 7.0


def test_boolean_answer_bolded_markdown() -> None:
    """Bug: llm_scanner doesn't parse boolean answers wrapped in markdown bold."""

    @scanner(name="bool_bold", messages="all")
    def bool_scanner() -> Scanner[Transcript]:
        return llm_scanner(
            question="Is this helpful?",
            answer="boolean",
        )

    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="**ANSWER: yes**",
            stop_reason="stop",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[bool_scanner()],
            transcripts=transcripts_from(LOGS_DIR),
            results=tmpdir,
            limit=1,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        assert status.complete
        results = scan_results_df(status.location, scanner="bool_bold")
        df = results.scanners["bool_bold"]
        assert len(df) == 1
        assert df["value"].iloc[0] is True
