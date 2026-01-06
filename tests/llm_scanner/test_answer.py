"""Tests for answer implementations in llm_scanner."""

import pytest
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Value
from inspect_scout._llm_scanner.answer import (
    Answer,
    _BoolAnswer,
    _LabelsAnswer,
    _NumberAnswer,
    _StrAnswer,
    _strip_markdown_formatting,
)
from inspect_scout._llm_scanner.prompt import ANSWER_FORMAT_PREAMBLE
from inspect_scout._scanner.result import Reference


def _dummy_extract_references(text: str) -> list[Reference]:
    """Dummy extract_references function for testing."""
    return []


@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("**bold**", "bold"),
        ("before **bold** after", "before bold after"),
        ("*italic*", "italic"),
        ("before *italic* after", "before italic after"),
        ("__bold__", "bold"),
        ("before __bold__ after", "before bold after"),
        ("_italic_", "italic"),
        ("before _italic_ after", "before italic after"),
        ("`code`", "code"),
        ("before `code` after", "before code after"),
        ("**bold** and *italic*", "bold and italic"),
        ("**ANSWER: yes**", "ANSWER: yes"),
        ("plain text", "plain text"),
        ("ANSWER: 42", "ANSWER: 42"),
        ("**bold *nested* bold**", "bold nested bold"),
        ("**a** and **b**", "a and b"),
        ("", ""),
    ],
)
def test_strip_markdown_formatting(input_text: str, expected: str) -> None:
    """Strip markdown formatting from text."""
    assert _strip_markdown_formatting(input_text) == expected


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
        ("Reasoning.\n\n**ANSWER: yes**", True, "Yes", "Reasoning."),
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

    result = answer.result_for_answer(output, _dummy_extract_references, None)

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
        ("Decimal.\n\nANSWER: 0.5", 0.5, "Decimal."),
        ("Negative.\n\nANSWER: -5", -5.0, "Negative."),
        ("Negative decimal.\n\nANSWER: -3.14", -3.14, "Negative decimal."),
        ("Trailing text.\n\nANSWER: 42 points", 42.0, "Trailing text."),
        ("Whitespace.\n\nANSWER:  42  ", 42.0, "Whitespace."),
        ("Markdown.\n\n**ANSWER: 7**", 7.0, "Markdown."),
    ],
)
def test_number_results(
    completion: str, expected_value: float | bool, expected_explanation: str
) -> None:
    """Number results parse various completion patterns."""
    answer = _NumberAnswer()
    output = ModelOutput(model="test", completion=completion)

    result = answer.result_for_answer(output, _dummy_extract_references, None)

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

    result = answer.result_for_answer(output, _dummy_extract_references, None)

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

    result = answer.result_for_answer(output, _dummy_extract_references, None)

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

    result = answer.result_for_answer(output, _dummy_extract_references, None)

    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


# Tests for value_to_float parameter


def test_bool_value_to_float() -> None:
    """Bool answer applies value_to_float to True/False."""

    def bool_to_score(value: Value) -> float:
        return 1.0 if value else 0.0

    answer = _BoolAnswer()
    output_yes = ModelOutput(model="test", completion="Reasoning.\n\nANSWER: yes")
    output_no = ModelOutput(model="test", completion="Reasoning.\n\nANSWER: no")

    result_yes = answer.result_for_answer(
        output_yes, _dummy_extract_references, bool_to_score
    )
    result_no = answer.result_for_answer(
        output_no, _dummy_extract_references, bool_to_score
    )

    assert result_yes.value == 1.0
    assert result_yes.answer == "Yes"
    assert result_no.value == 0.0
    assert result_no.answer == "No"


def test_number_value_to_float() -> None:
    """Numeric answer applies value_to_float to the number."""

    def scale_to_percentage(value: Value) -> float:
        return float(value) / 10.0 * 100  # type: ignore[arg-type]

    answer = _NumberAnswer()
    output = ModelOutput(model="test", completion="Score.\n\nANSWER: 7")

    result = answer.result_for_answer(
        output, _dummy_extract_references, scale_to_percentage
    )

    assert result.value == 70.0
    assert result.answer == "7.0"


def test_labels_single_value_to_float() -> None:
    """Single-classification labels apply value_to_float to the letter."""

    def letter_to_score(value: Value) -> float:
        return {"A": 0.0, "B": 0.5, "C": 1.0}.get(str(value), 0.0)

    answer = _LabelsAnswer(labels=["Low", "Medium", "High"])
    output = ModelOutput(model="test", completion="Analysis.\n\nANSWER: C")

    result = answer.result_for_answer(
        output, _dummy_extract_references, letter_to_score
    )

    assert result.value == 1.0
    assert result.answer == "High"


def test_labels_multi_value_to_float_raises() -> None:
    """Multi-classification labels raise NotImplementedError for value_to_float."""

    def dummy_converter(_value: Value) -> float:
        return 0.0

    answer = _LabelsAnswer(labels=["A", "B", "C"], multi_classification=True)
    output = ModelOutput(model="test", completion="Analysis.\n\nANSWER: A,B")

    with pytest.raises(NotImplementedError):
        answer.result_for_answer(output, _dummy_extract_references, dummy_converter)


def test_str_value_to_float() -> None:
    """String answer applies value_to_float to the answer text."""

    def sentiment_to_score(value: Value) -> float:
        value_lower = str(value).lower()
        if "positive" in value_lower:
            return 1.0
        elif "negative" in value_lower:
            return 0.0
        else:
            return 0.5

    answer = _StrAnswer()
    output = ModelOutput(
        model="test", completion="Analysis.\n\nANSWER: Mostly positive sentiment"
    )

    result = answer.result_for_answer(
        output, _dummy_extract_references, sentiment_to_score
    )

    assert result.value == 1.0
    assert result.answer == "Mostly positive sentiment"
