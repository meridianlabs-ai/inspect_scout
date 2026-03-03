"""Tests for generate_answer — dispatch, retry, and parse flag behavior."""

import re
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout._llm_scanner.generate import generate_answer
from inspect_scout._llm_scanner.types import (
    AnswerMultiLabel,
    AnswerSpec,
    AnswerStructured,
)
from inspect_scout._scanner.result import Reference, Result
from pydantic import BaseModel, Field


def _regex_refs(text: str) -> list[Reference]:
    refs: list[Reference] = []
    for match in re.finditer(r"\[(M)(\d+)\]", text):
        refs.append(
            Reference(type="message", cite=match.group(0), id=f"msg-{match.group(2)}")
        )
    return refs


def _make_mock_output(completion: str = "Reasoning.\n\nANSWER: yes") -> ModelOutput:
    return ModelOutput.from_content(model="test", content=completion)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_normal_dispatch() -> None:
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
async def test_generate_structured_dispatch() -> None:
    class MyAnswer(BaseModel):
        explanation: str = Field(description="Reasoning")
        score: int = Field(alias="value", description="Score")

    mock_output = ModelOutput.from_content(
        model="test",
        content='{"explanation": "Good work", "score": 5}',
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


# ---------------------------------------------------------------------------
# Parse flag
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_parse_false_returns_model_output() -> None:
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
async def test_generate_parse_true_returns_result() -> None:
    mock_output = _make_mock_output("Analysis.\n\nANSWER: 42")

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        return_value=mock_output,
    ):
        result = await generate_answer("Count?", "numeric", model="mockllm/model")

    assert isinstance(result, Result)
    assert result.value == 42.0


# ---------------------------------------------------------------------------
# References through generate_answer
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_extract_references() -> None:
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
async def test_generate_no_references_by_default() -> None:
    mock_output = _make_mock_output("See [M1].\n\nANSWER: yes")

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        return_value=mock_output,
    ):
        result = await generate_answer("Question?", "boolean", model="mockllm/model")

    assert isinstance(result, Result)
    assert len(result.references) == 0


# ---------------------------------------------------------------------------
# Structured null value
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_structured_null_value() -> None:
    class MyAnswer(BaseModel):
        explanation: str = Field(description="Reasoning")
        score: int = Field(alias="value", description="Score")

    mock_output = ModelOutput.from_content(model="test", content="Could not determine.")

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


# ---------------------------------------------------------------------------
# Text answer retry
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_generate_no_retry_when_parse_succeeds() -> None:
    mock_output = _make_mock_output("Reasoning.\n\nANSWER: yes")

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        return_value=mock_output,
    ) as mock_gen:
        result = await generate_answer(
            "Is this good?", "boolean", model="mockllm/model"
        )

    assert mock_gen.await_count == 1
    assert isinstance(result, Result)
    assert result.value is True
    assert result.answer == "Yes"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "answer_spec,malformed,valid,expected_value",
    [
        pytest.param(
            "boolean", "I think yes", "R.\n\nANSWER: yes", True, id="bool-no-marker"
        ),
        pytest.param(
            "boolean",
            "R.\n\nANSWER: maybe",
            "R.\n\nANSWER: no",
            False,
            id="bool-invalid-word",
        ),
        pytest.param(
            "numeric",
            "The answer is 42",
            "C.\n\nANSWER: 42",
            42.0,
            id="numeric-no-marker",
        ),
        pytest.param(
            "numeric",
            "R.\n\nANSWER: unknown",
            "C.\n\nANSWER: 0.5",
            0.5,
            id="numeric-non-numeric",
        ),
        pytest.param(
            "string",
            "No marker here",
            "A.\n\nANSWER: helpful",
            "helpful",
            id="string-no-marker",
        ),
        pytest.param(
            "string",
            "R.\n\nANSWER:  ",
            "A.\n\nANSWER: clear",
            "clear",
            id="string-empty",
        ),
        pytest.param(
            ["Good", "Bad"],
            "I'd say good",
            "E.\n\nANSWER: A",
            "A",
            id="labels-no-marker",
        ),
        pytest.param(
            ["Good", "Bad"],
            "R.\n\nANSWER: Z",
            "E.\n\nANSWER: B",
            "B",
            id="labels-invalid-letter",
        ),
        pytest.param(
            AnswerMultiLabel(["Cat A", "Cat B", "Cat C"]),
            "I'd pick A and C",
            "A.\n\nANSWER: A,C",
            ["Cat A", "Cat C"],
            id="multi-no-marker",
        ),
        pytest.param(
            AnswerMultiLabel(["Cat A", "Cat B"]),
            "R.\n\nANSWER: X,Y,Z",
            "A.\n\nANSWER: A,B",
            ["Cat A", "Cat B"],
            id="multi-all-invalid",
        ),
    ],
)
async def test_generate_retry_on_malformed_then_valid(
    answer_spec: AnswerSpec,
    malformed: str,
    valid: str,
    expected_value: object,
) -> None:
    outputs = [_make_mock_output(malformed), _make_mock_output(valid)]

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        side_effect=outputs,
    ) as mock_gen:
        result = await generate_answer("Question?", answer_spec, model="mockllm/model")

    assert mock_gen.await_count == 2
    assert isinstance(result, Result)
    assert result.value == expected_value
    assert result.answer is not None


@pytest.mark.anyio
async def test_generate_exhausts_max_attempts() -> None:
    bad = _make_mock_output("No answer marker here")

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        return_value=bad,
    ) as mock_gen:
        result = await generate_answer("Question?", "boolean", model="mockllm/model")

    assert mock_gen.await_count == 3
    assert isinstance(result, Result)
    assert result.answer is None


@pytest.mark.anyio
async def test_generate_feedback_contains_format_string() -> None:
    from inspect_scout._llm_scanner.answer import answer_from_argument

    outputs = [
        _make_mock_output("No marker"),
        _make_mock_output("Reasoning.\n\nANSWER: yes"),
    ]
    expected_format = answer_from_argument("boolean").format

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        side_effect=outputs,
    ) as mock_gen:
        await generate_answer("Question?", "boolean", model="mockllm/model")

    second_call_messages = mock_gen.call_args_list[1].kwargs.get(
        "input", mock_gen.call_args_list[1].args[1]
    )
    feedback_text = second_call_messages[-1].content
    assert expected_format in feedback_text


@pytest.mark.anyio
async def test_generate_parse_false_skips_retry() -> None:
    bad = _make_mock_output("No marker here")

    with patch(
        "inspect_scout._llm_scanner.generate.generate_retry_refusals",
        new_callable=AsyncMock,
        return_value=bad,
    ) as mock_gen:
        output = await generate_answer(
            "Question?", "boolean", model="mockllm/model", parse=False
        )

    assert mock_gen.await_count == 1
    assert isinstance(output, ModelOutput)
    assert output.completion == "No marker here"
