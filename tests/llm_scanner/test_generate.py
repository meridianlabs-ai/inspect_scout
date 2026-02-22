"""Tests for parse_answer and generate_answer in _llm_scanner/generate.py."""

import re
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Value
from inspect_scout._llm_scanner.generate import generate_answer, parse_answer
from inspect_scout._llm_scanner.types import AnswerStructured
from inspect_scout._scanner.result import Reference, Result
from pydantic import BaseModel, Field


def _no_refs(_text: str) -> list[Reference]:
    return []


def _regex_refs(text: str) -> list[Reference]:
    """Extract [M1]-style references via regex."""
    refs: list[Reference] = []
    for match in re.finditer(r"\[(M)(\d+)\]", text):
        refs.append(
            Reference(type="message", cite=match.group(0), id=f"msg-{match.group(2)}")
        )
    return refs


# ---------------------------------------------------------------------------
# parse_answer tests
# ---------------------------------------------------------------------------


class TestParseAnswerBoolean:
    def test_yes(self) -> None:
        output = ModelOutput(model="test", completion="Reasoning.\n\nANSWER: yes")
        result = parse_answer(output, "boolean", _no_refs)
        assert result.value is True
        assert result.answer == "Yes"

    def test_no(self) -> None:
        output = ModelOutput(model="test", completion="Reasoning.\n\nANSWER: no")
        result = parse_answer(output, "boolean", _no_refs)
        assert result.value is False
        assert result.answer == "No"


class TestParseAnswerNumeric:
    def test_integer(self) -> None:
        output = ModelOutput(model="test", completion="Count.\n\nANSWER: 42")
        result = parse_answer(output, "numeric", _no_refs)
        assert result.value == 42.0

    def test_decimal(self) -> None:
        output = ModelOutput(model="test", completion="Score.\n\nANSWER: 0.75")
        result = parse_answer(output, "numeric", _no_refs)
        assert result.value == 0.75


class TestParseAnswerString:
    def test_text(self) -> None:
        output = ModelOutput(
            model="test", completion="Analysis.\n\nANSWER: The agent was helpful"
        )
        result = parse_answer(output, "string", _no_refs)
        assert result.value == "The agent was helpful"

    def test_no_pattern(self) -> None:
        output = ModelOutput(model="test", completion="No answer marker here")
        result = parse_answer(output, "string", _no_refs)
        assert result.value is None


class TestParseAnswerLabels:
    def test_single_label(self) -> None:
        output = ModelOutput(model="test", completion="Evaluation.\n\nANSWER: A")
        result = parse_answer(output, ["Good", "Bad", "Neutral"], _no_refs)
        assert result.value == "A"
        assert result.answer == "Good"

    def test_invalid_label(self) -> None:
        output = ModelOutput(model="test", completion="Unsure.\n\nANSWER: Z")
        result = parse_answer(output, ["Good", "Bad"], _no_refs)
        assert result.value is None


class TestParseAnswerReferences:
    def test_references_extracted(self) -> None:
        output = ModelOutput(
            model="test", completion="See [M1] and [M3].\n\nANSWER: yes"
        )
        result = parse_answer(output, "boolean", _regex_refs)
        assert result.value is True
        assert len(result.references) == 2
        assert result.references[0].cite == "[M1]"
        assert result.references[1].cite == "[M3]"


class TestParseAnswerValueToFloat:
    def test_value_to_float_applied(self) -> None:
        def bool_score(value: Value) -> float:
            return 1.0 if value else 0.0

        output = ModelOutput(model="test", completion="Yes.\n\nANSWER: yes")
        result = parse_answer(output, "boolean", _no_refs, value_to_float=bool_score)
        assert result.value == 1.0


class TestParseAnswerStructured:
    def test_structured_parsing(self) -> None:
        class Finding(BaseModel):
            explanation: str = Field(description="Explain the finding")
            severity: str = Field(alias="value", description="Severity level")

        output = ModelOutput(
            model="test",
            completion='{"explanation": "Found an issue", "severity": "high"}',
        )
        result = parse_answer(output, AnswerStructured(type=Finding), _no_refs)
        assert result.explanation == "Found an issue"


# ---------------------------------------------------------------------------
# generate_answer tests
# ---------------------------------------------------------------------------


def _make_mock_output(completion: str = "Reasoning.\n\nANSWER: yes") -> ModelOutput:
    return ModelOutput(model="test", completion=completion)


class TestGenerateAnswerDispatch:
    @pytest.mark.anyio
    async def test_normal_dispatch(self) -> None:
        """Non-structured answer dispatches to generate_retry_refusals."""
        mock_output = _make_mock_output()

        with patch(
            "inspect_scout._llm_scanner.generate.generate_retry_refusals",
            new_callable=AsyncMock,
            return_value=mock_output,
        ) as mock_gen:
            result = await generate_answer(
                "Is this good?", "boolean", model="mockllm/model"
            )

        mock_gen.assert_awaited_once()
        assert isinstance(result, Result)
        assert result.value is True

    @pytest.mark.anyio
    async def test_structured_dispatch(self) -> None:
        """AnswerStructured dispatches to structured_generate."""

        class MyAnswer(BaseModel):
            explanation: str = Field(description="Reasoning")
            score: int = Field(alias="value", description="Score")

        mock_output = ModelOutput(
            model="test",
            completion='{"explanation": "Good work", "score": 5}',
        )

        with patch(
            "inspect_scout._llm_scanner.generate.structured_generate",
            new_callable=AsyncMock,
            return_value=({"explanation": "Good work", "score": 5}, [], mock_output),
        ):
            result = await generate_answer(
                "Rate this.",
                AnswerStructured(type=MyAnswer),
                model="mockllm/model",
            )

        assert isinstance(result, Result)


class TestGenerateAnswerParse:
    @pytest.mark.anyio
    async def test_parse_false_returns_model_output(self) -> None:
        """parse=False returns raw ModelOutput."""
        mock_output = _make_mock_output("Reasoning.\n\nANSWER: yes")

        with patch(
            "inspect_scout._llm_scanner.generate.generate_retry_refusals",
            new_callable=AsyncMock,
            return_value=mock_output,
        ):
            output = await generate_answer(
                "Question?", "boolean", model="mockllm/model", parse=False
            )

        assert isinstance(output, ModelOutput)
        assert output.completion == "Reasoning.\n\nANSWER: yes"

    @pytest.mark.anyio
    async def test_parse_true_default_returns_result(self) -> None:
        """Default parse=True returns Result."""
        mock_output = _make_mock_output("Analysis.\n\nANSWER: 42")

        with patch(
            "inspect_scout._llm_scanner.generate.generate_retry_refusals",
            new_callable=AsyncMock,
            return_value=mock_output,
        ):
            result = await generate_answer("Count?", "numeric", model="mockllm/model")

        assert isinstance(result, Result)
        assert result.value == 42.0

    @pytest.mark.anyio
    async def test_extract_references_used(self) -> None:
        """extract_references is used when parsing."""
        mock_output = _make_mock_output("See [M1].\n\nANSWER: yes")

        with patch(
            "inspect_scout._llm_scanner.generate.generate_retry_refusals",
            new_callable=AsyncMock,
            return_value=mock_output,
        ):
            result = await generate_answer(
                "Question?",
                "boolean",
                model="mockllm/model",
                extract_refs=_regex_refs,
            )

        assert isinstance(result, Result)
        assert len(result.references) == 1
        assert result.references[0].cite == "[M1]"

    @pytest.mark.anyio
    async def test_no_references_by_default(self) -> None:
        """Without extract_references, no references are extracted."""
        mock_output = _make_mock_output("See [M1].\n\nANSWER: yes")

        with patch(
            "inspect_scout._llm_scanner.generate.generate_retry_refusals",
            new_callable=AsyncMock,
            return_value=mock_output,
        ):
            result = await generate_answer(
                "Question?", "boolean", model="mockllm/model"
            )

        assert isinstance(result, Result)
        assert len(result.references) == 0


class TestGenerateAnswerStructuredNull:
    @pytest.mark.anyio
    async def test_structured_null_value(self) -> None:
        """Structured answer with null value returns Result(value=None)."""

        class MyAnswer(BaseModel):
            explanation: str = Field(description="Reasoning")
            score: int = Field(alias="value", description="Score")

        mock_output = ModelOutput(model="test", completion="Could not determine.")

        with patch(
            "inspect_scout._llm_scanner.generate.structured_generate",
            new_callable=AsyncMock,
            return_value=(None, [], mock_output),
        ):
            result = await generate_answer(
                "Rate this.",
                AnswerStructured(type=MyAnswer),
                model="mockllm/model",
            )

        assert isinstance(result, Result)
        assert result.value is None
        assert result.answer == "Could not determine."
