"""Tests for answer implementations in llm_scanner."""

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout._llm_scanner.answer import (
    Answer,
    LabelsAnswer,
    _BoolAnswer,
    _NumberAnswer,
    _StrAnswer,
)


@pytest.mark.parametrize(
    "answer_type,expected_fragments",
    [
        (
            _BoolAnswer(),
            [
                "Answer the following yes or no question: {question}",
                "{explanation_text}",
                "'ANSWER: xxx' (without quotes) where xxx is the numeric value",
            ],
        ),
        (
            _NumberAnswer(),
            [
                "Answer the following numeric question: {question}",
                "{explanation_text}",
                "'ANSWER: xxx' (without quotes) where xxx is the numeric value",
            ],
        ),
        (
            LabelsAnswer(labels=["Choice A", "Choice B", "Choice C"]),
            [
                "Answer the following multiple choice question: {question}",
                "A) Choice A\nB) Choice B\nC) Choice C",
                "{explanation_text}",
                "'ANSWER: $LETTER' (without quotes) where LETTER is one of A,B,C",
            ],
        ),
        (
            LabelsAnswer(
                labels=["Choice A", "Choice B", "Choice C"], multi_classification=True
            ),
            [
                "Answer the following multiple choice question: {question}",
                "A) Choice A\nB) Choice B\nC) Choice C",
                "{explanation_text}",
                "'ANSWER: $LETTERS' (without quotes) where LETTERS is a comma-separated list of letters from A,B,C",
            ],
        ),
    ],
)
def test_answer_templates(answer_type: Answer, expected_fragments: list[str]) -> None:
    """Answer templates contain expected fragments."""
    result = answer_type.answer_portion_template()
    for fragment in expected_fragments:
        assert fragment in result


def test_unsupported_answer_type() -> None:
    """Unsupported answer types raise NotImplementedError."""
    with pytest.raises(
        NotImplementedError, match="Support for 'str' not yet implemented"
    ):
        _StrAnswer().answer_portion_template()


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
    answer = _BoolAnswer()
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, [])

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
    answer = _NumberAnswer()
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, [])

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
    answer = LabelsAnswer(labels=labels)
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, [])

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
    answer = LabelsAnswer(labels=labels, multi_classification=True)
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, [])

    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation
