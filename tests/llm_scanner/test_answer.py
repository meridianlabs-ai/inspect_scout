"""Tests for answer_portion_template function in llm_scanner."""

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout._llm_scanner.answer import answer_portion_template, result_for_answer
from inspect_scout._llm_scanner.types import LLMScannerAnswer


@pytest.mark.parametrize(
    "answer_type,expected_fragments",
    [
        (
            LLMScannerAnswer(type="bool"),
            [
                "Answer the following yes or no question: {question}",
                "{explanation_text}",
                "'ANSWER: xxx' (without quotes) where xxx is the numeric value",
            ],
        ),
        (
            LLMScannerAnswer(type="number"),
            [
                "Answer the following numeric question: {question}",
                "{explanation_text}",
                "'ANSWER: xxx' (without quotes) where xxx is the numeric value",
            ],
        ),
        (
            LLMScannerAnswer(
                type="labels", labels=["Choice A", "Choice B", "Choice C"]
            ),
            [
                "Answer the following multiple choice question: {question}",
                "A) Choice A\nB) Choice B\nC) Choice C",
                "{explanation_text}",
                "'ANSWER: $LETTER' (without quotes) where LETTER is one of A,B,C",
            ],
        ),
    ],
)
def test_answer_templates(
    answer_type: LLMScannerAnswer, expected_fragments: list[str]
) -> None:
    """Answer templates contain expected fragments."""
    result = answer_portion_template(answer_type)
    for fragment in expected_fragments:
        assert fragment in result


def test_unsupported_answer_type() -> None:
    """Unsupported answer types raise NotImplementedError."""
    with pytest.raises(
        NotImplementedError, match="Support for 'str' not yet implemented"
    ):
        answer_portion_template(LLMScannerAnswer(type="str"))


@pytest.mark.parametrize(
    "completion,expected_value,expected_answer,expected_explanation",
    [
        ("Reasoning.\n\nANSWER: yes", True, "Yes", "Reasoning."),
        ("Reasoning.\n\nANSWER: no", False, "No", "Reasoning."),
        ("Reasoning.\n\nANSWER: YES", True, "Yes", "Reasoning."),
        ("Reasoning.\n\nANSWER: maybe", False, None, "Reasoning.\n\nANSWER: maybe"),
        ("No pattern here", False, None, "No pattern here"),
    ],
)
def test_bool_results(
    completion: str,
    expected_value: bool,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    """Bool results parse various completion patterns."""
    answer = LLMScannerAnswer(type="bool")
    output = ModelOutput(model="test", completion=completion)

    result = result_for_answer(answer, output, [])

    assert result.value is expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


@pytest.mark.parametrize(
    "completion,expected_value,expected_explanation",
    [
        ("Calculation.\n\nANSWER: 42", 42.0, "Calculation."),
        ("Zero.\n\nANSWER: 0", 0.0, "Zero."),
        ("Not numeric.\n\nANSWER: unknown", False, "Not numeric.\n\nANSWER: unknown"),
        ("No pattern", False, "No pattern"),
    ],
)
def test_number_results(
    completion: str, expected_value: float | bool, expected_explanation: str
) -> None:
    """Number results parse various completion patterns."""
    answer = LLMScannerAnswer(type="number")
    output = ModelOutput(model="test", completion=completion)

    result = result_for_answer(answer, output, [])

    assert result.value == expected_value
    assert result.explanation == expected_explanation


@pytest.mark.parametrize(
    "labels,completion,expected_value,expected_answer,expected_explanation",
    [
        (
            ["First", "Second", "Third"],
            "Think.\n\nANSWER: B",
            "B",
            "Second",
            "Think.",
        ),
        (["First", "Second"], "Clear.\n\nANSWER: a", "A", "First", "Clear."),
        (
            ["First", "Second"],
            "Unsure.\n\nANSWER: Z",
            None,
            None,
            "Unsure.\n\nANSWER: Z",
        ),
        (["First", "Second"], "No pattern", None, None, "No pattern"),
        (
            [f"Choice {i + 1}" for i in range(27)],
            "Analysis.\n\nANSWER: 1",
            "1",
            "Choice 27",
            "Analysis.",
        ),
    ],
)
def test_labels_results(
    labels: list[str],
    completion: str,
    expected_value: int | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    """Labels results parse various completion patterns."""
    answer = LLMScannerAnswer(type="labels", labels=labels)
    output = ModelOutput(model="test", completion=completion)

    result = result_for_answer(answer, output, [])

    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation
