"""Tests for answer implementations in llm_scanner."""

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout._llm_scanner.answer import (
    Answer,
    _BoolAnswer,
    _LabelsAnswer,
    _NumberAnswer,
    _StrAnswer,
)
from inspect_scout._llm_scanner.prompt import ANSWER_FORMAT_PREAMBLE
from inspect_scout._scanner.result import Reference


def _dummy_extract_references(text: str) -> list[Reference]:
    """Dummy extract_references function for testing."""
    return []


@pytest.mark.parametrize(
    "answer_type,expected_prompt,expected_format",
    [
        (
            _BoolAnswer(),
            "Answer the following yes or no question about the transcript above:",
            "'ANSWER: $VALUE' (without quotes) where $VALUE is yes or no.",
        ),
        (
            _NumberAnswer(),
            "Answer the following numeric question about the transcript above:",
            "'ANSWER: $NUMBER' (without quotes) where $NUMBER is the numeric value.",
        ),
        (
            _LabelsAnswer(labels=["Choice A", "Choice B", "Choice C"]),
            "Answer the following multiple choice question about the transcript above:",
            "'ANSWER: $LETTER' (without quotes) where $LETTER is one of A,B,C representing:\nA) Choice A\nB) Choice B\nC) Choice C",
        ),
        (
            _LabelsAnswer(
                labels=["Choice A", "Choice B", "Choice C"], multi_classification=True
            ),
            "Answer the following multiple choice question about the transcript above:",
            "'ANSWER: $LETTERS' (without quotes) where $LETTERS is a comma-separated list of letters from A,B,C representing:\nA) Choice A\nB) Choice B\nC) Choice C",
        ),
        (
            _StrAnswer(),
            "Answer the following question about the transcript above:",
            "'ANSWER: $TEXT' (without quotes) where $TEXT is your answer.",
        ),
    ],
)
def test_answer_templates(
    answer_type: Answer, expected_prompt: str, expected_format: str
) -> None:
    """Answer prompt and format properties return expected values."""
    assert answer_type.prompt == expected_prompt
    assert answer_type.format == ANSWER_FORMAT_PREAMBLE + expected_format


@pytest.mark.parametrize(
    "completion,expected_value,expected_answer,expected_explanation",
    [
        ("Reasoning.\n\nANSWER: yes", True, "Yes", "Reasoning."),
        ("Reasoning.\n\nANSWER: no", False, "No", "Reasoning."),
        ("Reasoning.\n\nANSWER: YES", True, "Yes", "Reasoning."),
        ("Reasoning.\n\nANSWER: maybe", False, None, "Reasoning.\n\nANSWER: maybe"),
        ("No pattern here", False, None, "No pattern here"),
        # Bug: bolded markdown not parsed
        ("**ANSWER: yes**", True, "Yes", ""),
    ],
)
def test_bool_results(
    completion: str,
    expected_value: bool,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    """Bool results parse various completion patterns."""
    answer = _BoolAnswer()
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, _dummy_extract_references)

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
        # Bug: non-integer numerics not parsed
        ("ANSWER: 0.5", 0.5, ""),
        # Bug: bolded markdown not parsed
        ("**ANSWER: 7**", 7.0, ""),
    ],
)
def test_number_results(
    completion: str, expected_value: float | bool, expected_explanation: str
) -> None:
    """Number results parse various completion patterns."""
    answer = _NumberAnswer()
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, _dummy_extract_references)

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
    answer = _LabelsAnswer(labels=labels)
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, _dummy_extract_references)

    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


@pytest.mark.parametrize(
    "labels,completion,expected_value,expected_answer,expected_explanation",
    [
        # Single answer
        (
            ["Violence or harm", "Illegal activity", "Privacy violations"],
            "Analysis.\n\nANSWER: C",
            ["Privacy violations"],
            "C",
            "Analysis.",
        ),
        # Multiple answers
        (
            ["Violence or harm", "Illegal activity", "Privacy violations"],
            "Analysis.\n\nANSWER: B,C",
            ["Illegal activity", "Privacy violations"],
            "B,C",
            "Analysis.",
        ),
        # Multiple answers with spaces
        (
            ["First", "Second", "Third", "Fourth"],
            "Clear.\n\nANSWER: A, C, D",
            ["First", "Third", "Fourth"],
            "A, C, D",
            "Clear.",
        ),
        # Case insensitive
        (
            ["First", "Second", "Third"],
            "Think.\n\nANSWER: b,c",
            ["Second", "Third"],
            "b,c",
            "Think.",
        ),
        # Mixed case and spacing
        (
            ["First", "Second", "Third"],
            "Mixed.\n\nANSWER: a, B,c",
            ["First", "Second", "Third"],
            "a, B,c",
            "Mixed.",
        ),
        # Invalid letters filtered out
        (
            ["First", "Second"],
            "Some invalid.\n\nANSWER: A,Z,B",
            ["First", "Second"],
            "A,Z,B",
            "Some invalid.",
        ),
        # All invalid letters
        (
            ["First", "Second"],
            "All invalid.\n\nANSWER: X,Y,Z",
            None,
            None,
            "All invalid.\n\nANSWER: X,Y,Z",
        ),
        # No pattern
        (
            ["First", "Second"],
            "No answer pattern here",
            None,
            None,
            "No answer pattern here",
        ),
        # Empty answer
        (
            ["First", "Second"],
            "Empty.\n\nANSWER: ",
            None,
            None,
            "Empty.\n\nANSWER: ",
        ),
        # Duplicate letters (should deduplicate)
        (
            ["First", "Second", "Third"],
            "Duplicates.\n\nANSWER: A,A,B",
            ["First", "Second"],
            "A,A,B",
            "Duplicates.",
        ),
        # Large number of choices
        (
            [f"Choice {i + 1}" for i in range(27)],
            "Many.\n\nANSWER: A,Z,1",
            ["Choice 1", "Choice 26", "Choice 27"],
            "A,Z,1",
            "Many.",
        ),
    ],
)
def test_multi_classification_results(
    labels: list[str],
    completion: str,
    expected_value: list[str] | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    """Multi-classification results parse comma-separated letters."""
    answer = _LabelsAnswer(labels=labels, multi_classification=True)
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, _dummy_extract_references)

    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


@pytest.mark.parametrize(
    "completion,expected_value,expected_answer,expected_explanation",
    [
        # Basic text extraction
        (
            "Explanation here.\n\nANSWER: Simple response",
            "Simple response",
            "Simple response",
            "Explanation here.",
        ),
        # Multi-word answer
        (
            "Analysis.\n\nANSWER: Empathetic, patient, and solution-focused with professional warmth",
            "Empathetic, patient, and solution-focused with professional warmth",
            "Empathetic, patient, and solution-focused with professional warmth",
            "Analysis.",
        ),
        # Answer with punctuation
        (
            "Context.\n\nANSWER: The user's question is unclear.",
            "The user's question is unclear.",
            "The user's question is unclear.",
            "Context.",
        ),
        # Answer with special characters
        (
            "Reasoning.\n\nANSWER: 50% improvement (approximately)",
            "50% improvement (approximately)",
            "50% improvement (approximately)",
            "Reasoning.",
        ),
        # Longer explanation
        (
            "First paragraph.\n\nSecond paragraph with details.\n\nANSWER: Short answer",
            "Short answer",
            "Short answer",
            "First paragraph.\n\nSecond paragraph with details.",
        ),
        # Answer with trailing whitespace
        (
            "Explain.\n\nANSWER: Response text   ",
            "Response text",
            "Response text",
            "Explain.",
        ),
        # No pattern
        (
            "No answer pattern here",
            None,
            None,
            "No answer pattern here",
        ),
        # Empty answer
        (
            "Empty.\n\nANSWER: ",
            None,
            None,
            "Empty.\n\nANSWER: ",
        ),
        # Answer with only whitespace
        (
            "Whitespace.\n\nANSWER:    ",
            None,
            None,
            "Whitespace.\n\nANSWER:    ",
        ),
        # Single word answer
        (
            "Think.\n\nANSWER: Yes",
            "Yes",
            "Yes",
            "Think.",
        ),
    ],
)
def test_str_results(
    completion: str,
    expected_value: str | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    """Str results parse free-text answers."""
    answer = _StrAnswer()
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, _dummy_extract_references)

    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation
