"""Tests for parse_answer — parsing edge cases through the public API."""

import re

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout._llm_scanner.generate import parse_answer
from inspect_scout._llm_scanner.types import AnswerMultiLabel, AnswerSpec
from inspect_scout._scanner.result import Reference


def _no_refs(_text: str) -> list[Reference]:
    return []


def _regex_refs(text: str) -> list[Reference]:
    refs: list[Reference] = []
    for match in re.finditer(r"\[(M)(\d+)\]", text):
        refs.append(
            Reference(type="message", cite=match.group(0), id=f"msg-{match.group(2)}")
        )
    return refs


# ---------------------------------------------------------------------------
# Boolean parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "completion,expected_value,expected_answer,expected_explanation",
    [
        pytest.param("Reasoning.\n\nANSWER: yes", True, "Yes", "Reasoning.", id="yes"),
        pytest.param("Reasoning.\n\nANSWER: no", False, "No", "Reasoning.", id="no"),
        pytest.param(
            "Reasoning.\n\nANSWER: YES", True, "Yes", "Reasoning.", id="yes-uppercase"
        ),
        pytest.param(
            "Reasoning.\n\nANSWER: maybe",
            False,
            None,
            "Reasoning.\n\nANSWER: maybe",
            id="invalid-word",
        ),
        pytest.param(
            "Reasoning.\n\n**ANSWER: yes**",
            True,
            "Yes",
            "Reasoning.",
            id="markdown-bold",
        ),
        pytest.param(
            "No pattern here", False, None, "No pattern here", id="no-pattern"
        ),
        pytest.param(
            "Answer:\nANSWER: yes", True, "Yes", "Answer:", id="double-answer-yes"
        ),
        pytest.param(
            "Answer:\nANSWER: no", False, "No", "Answer:", id="double-answer-no"
        ),
    ],
)
def test_parse_boolean(
    completion: str,
    expected_value: bool,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, "boolean", _no_refs)
    assert result.value is expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


# ---------------------------------------------------------------------------
# Numeric parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "completion,expected_value,expected_explanation",
    [
        pytest.param("Calculation.\n\nANSWER: 42", 42.0, "Calculation.", id="integer"),
        pytest.param("Zero.\n\nANSWER: 0", 0.0, "Zero.", id="zero"),
        pytest.param(
            "Not numeric.\n\nANSWER: unknown",
            False,
            "Not numeric.\n\nANSWER: unknown",
            id="non-numeric",
        ),
        pytest.param("No pattern", False, "No pattern", id="no-pattern"),
        pytest.param("Decimal.\n\nANSWER: 0.5", 0.5, "Decimal.", id="decimal"),
        pytest.param("Negative.\n\nANSWER: -5", -5.0, "Negative.", id="negative"),
        pytest.param(
            "Negative decimal.\n\nANSWER: -3.14",
            -3.14,
            "Negative decimal.",
            id="negative-decimal",
        ),
        pytest.param(
            "Trailing text.\n\nANSWER: 42 points",
            42.0,
            "Trailing text.",
            id="trailing-text",
        ),
        pytest.param(
            "Whitespace.\n\nANSWER:  42  ", 42.0, "Whitespace.", id="whitespace"
        ),
        pytest.param(
            "Markdown.\n\n**ANSWER: 7**", 7.0, "Markdown.", id="markdown-bold"
        ),
        pytest.param(
            "Answer:\nANSWER: 0.5", 0.5, "Answer:", id="double-answer-decimal"
        ),
        pytest.param(
            "Answer:\nANSWER: 42", 42.0, "Answer:", id="double-answer-integer"
        ),
    ],
)
def test_parse_numeric(
    completion: str,
    expected_value: float | bool,
    expected_explanation: str,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, "numeric", _no_refs)
    assert result.value == expected_value
    assert result.explanation == expected_explanation


# ---------------------------------------------------------------------------
# Labels (single classification) parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "labels,completion,expected_value,expected_answer,expected_explanation",
    [
        pytest.param(
            ["First", "Second", "Third"],
            "Think.\n\nANSWER: B",
            "B",
            "Second",
            "Think.",
            id="valid-label",
        ),
        pytest.param(
            ["First", "Second"],
            "Clear.\n\nANSWER: a",
            "A",
            "First",
            "Clear.",
            id="lowercase",
        ),
        pytest.param(
            ["First", "Second"],
            "Unsure.\n\nANSWER: Z",
            None,
            None,
            "Unsure.\n\nANSWER: Z",
            id="invalid-label",
        ),
        pytest.param(
            ["First", "Second"], "No pattern", None, None, "No pattern", id="no-pattern"
        ),
        pytest.param(
            [f"Choice {i + 1}" for i in range(27)],
            "Analysis.\n\nANSWER: 1",
            "1",
            "Choice 27",
            "Analysis.",
            id="27-labels-numeric",
        ),
        pytest.param(
            ["First", "Second", "Third"],
            "Answer:\nANSWER: B",
            "B",
            "Second",
            "Answer:",
            id="double-answer",
        ),
    ],
)
def test_parse_labels(
    labels: list[str],
    completion: str,
    expected_value: str | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, labels, _no_refs)
    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


# ---------------------------------------------------------------------------
# Multi-classification parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "labels,completion,expected_value,expected_answer,expected_explanation",
    [
        pytest.param(
            ["Violence or harm", "Illegal activity", "Privacy violations"],
            "Analysis.\n\nANSWER: C",
            ["Privacy violations"],
            "C",
            "Analysis.",
            id="single",
        ),
        pytest.param(
            ["Violence or harm", "Illegal activity", "Privacy violations"],
            "Analysis.\n\nANSWER: B,C",
            ["Illegal activity", "Privacy violations"],
            "B,C",
            "Analysis.",
            id="multiple",
        ),
        pytest.param(
            ["First", "Second", "Third", "Fourth"],
            "Clear.\n\nANSWER: A, C, D",
            ["First", "Third", "Fourth"],
            "A, C, D",
            "Clear.",
            id="spaces-in-commas",
        ),
        pytest.param(
            ["First", "Second", "Third"],
            "Think.\n\nANSWER: b,c",
            ["Second", "Third"],
            "b,c",
            "Think.",
            id="lowercase",
        ),
        pytest.param(
            ["First", "Second", "Third"],
            "Mixed.\n\nANSWER: a, B,c",
            ["First", "Second", "Third"],
            "a, B,c",
            "Mixed.",
            id="mixed-case-spacing",
        ),
        pytest.param(
            ["First", "Second"],
            "Some invalid.\n\nANSWER: A,Z,B",
            ["First", "Second"],
            "A,Z,B",
            "Some invalid.",
            id="partial-invalid-filtered",
        ),
        pytest.param(
            ["First", "Second"],
            "All invalid.\n\nANSWER: X,Y,Z",
            None,
            None,
            "All invalid.\n\nANSWER: X,Y,Z",
            id="all-invalid",
        ),
        pytest.param(
            ["First", "Second"],
            "No answer pattern here",
            None,
            None,
            "No answer pattern here",
            id="no-pattern",
        ),
        pytest.param(
            ["First", "Second"],
            "Empty.\n\nANSWER: ",
            None,
            None,
            "Empty.\n\nANSWER: ",
            id="empty",
        ),
        pytest.param(
            ["First", "Second", "Third"],
            "Duplicates.\n\nANSWER: A,A,B",
            ["First", "Second"],
            "A,A,B",
            "Duplicates.",
            id="deduplication",
        ),
        pytest.param(
            [f"Choice {i + 1}" for i in range(27)],
            "Many.\n\nANSWER: A,Z,1",
            ["Choice 1", "Choice 26", "Choice 27"],
            "A,Z,1",
            "Many.",
            id="large-label-set",
        ),
        pytest.param(
            ["First", "Second", "Third"],
            "Answer:\nANSWER: B,C",
            ["Second", "Third"],
            "B,C",
            "Answer:",
            id="double-answer",
        ),
    ],
)
def test_parse_multi_classification(
    labels: list[str],
    completion: str,
    expected_value: list[str] | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, AnswerMultiLabel(labels), _no_refs)
    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


# ---------------------------------------------------------------------------
# Multi-classification allow_none parsing
# ---------------------------------------------------------------------------

_ALLOW_NONE_LABELS = ["Violence or harm", "Illegal activity", "Privacy violations"]


@pytest.mark.parametrize(
    "allow_none,completion,expected_value,expected_answer,expected_explanation",
    [
        pytest.param(
            True,
            "None apply.\n\nANSWER: NONE",
            [],
            "NONE",
            "None apply.",
            id="none-accepted",
        ),
        pytest.param(
            True,
            "None apply.\n\nANSWER: none",
            [],
            "none",
            "None apply.",
            id="none-lowercase",
        ),
        pytest.param(
            True,
            "Analysis.\n\nANSWER: A,C",
            ["Violence or harm", "Privacy violations"],
            "A,C",
            "Analysis.",
            id="valid-letters-still-work",
        ),
        pytest.param(
            False,
            "None apply.\n\nANSWER: NONE",
            None,
            None,
            "None apply.\n\nANSWER: NONE",
            id="none-rejected",
        ),
    ],
)
def test_parse_multi_classification_allow_none(
    allow_none: bool,
    completion: str,
    expected_value: list[str] | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(
        output, AnswerMultiLabel(_ALLOW_NONE_LABELS, allow_none=allow_none), _no_refs
    )
    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


# ---------------------------------------------------------------------------
# String parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "completion,expected_value,expected_answer,expected_explanation",
    [
        pytest.param(
            "Explanation here.\n\nANSWER: Simple response",
            "Simple response",
            "Simple response",
            "Explanation here.",
            id="basic",
        ),
        pytest.param(
            "Analysis.\n\nANSWER: Empathetic, patient, and solution-focused with professional warmth",
            "Empathetic, patient, and solution-focused with professional warmth",
            "Empathetic, patient, and solution-focused with professional warmth",
            "Analysis.",
            id="multi-word",
        ),
        pytest.param(
            "Context.\n\nANSWER: The user's question is unclear.",
            "The user's question is unclear.",
            "The user's question is unclear.",
            "Context.",
            id="punctuation",
        ),
        pytest.param(
            "Reasoning.\n\nANSWER: 50% improvement (approximately)",
            "50% improvement (approximately)",
            "50% improvement (approximately)",
            "Reasoning.",
            id="special-chars",
        ),
        pytest.param(
            "First paragraph.\n\nSecond paragraph with details.\n\nANSWER: Short answer",
            "Short answer",
            "Short answer",
            "First paragraph.\n\nSecond paragraph with details.",
            id="longer-explanation",
        ),
        pytest.param(
            "Explain.\n\nANSWER: Response text   ",
            "Response text",
            "Response text",
            "Explain.",
            id="trailing-whitespace",
        ),
        pytest.param(
            "No answer pattern here",
            None,
            None,
            "No answer pattern here",
            id="no-pattern",
        ),
        pytest.param(
            "Empty.\n\nANSWER: ", None, None, "Empty.\n\nANSWER: ", id="empty"
        ),
        pytest.param(
            "Whitespace.\n\nANSWER:    ",
            None,
            None,
            "Whitespace.\n\nANSWER:    ",
            id="whitespace-only",
        ),
        pytest.param("Think.\n\nANSWER: Yes", "Yes", "Yes", "Think.", id="single-word"),
        pytest.param(
            "Answer:\nANSWER: The response was helpful",
            "The response was helpful",
            "The response was helpful",
            "Answer:",
            id="double-answer",
        ),
    ],
)
def test_parse_string(
    completion: str,
    expected_value: str | None,
    expected_answer: str | None,
    expected_explanation: str,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, "string", _no_refs)
    assert result.value == expected_value
    assert result.answer == expected_answer
    assert result.explanation == expected_explanation


# ---------------------------------------------------------------------------
# Markdown stripping (verified through parse_answer)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer_spec,completion,expected_value",
    [
        pytest.param("boolean", "R.\n\n**ANSWER: yes**", True, id="bold-double-star"),
        pytest.param("boolean", "R.\n\n*ANSWER: yes*", True, id="italic-star"),
        pytest.param("boolean", "R.\n\n__ANSWER: yes__", True, id="bold-underscore"),
        pytest.param("boolean", "R.\n\n_ANSWER: yes_", True, id="italic-underscore"),
        pytest.param("boolean", "R.\n\n`ANSWER: yes`", True, id="backtick"),
        pytest.param("numeric", "R.\n\n**ANSWER: 7**", 7.0, id="numeric-bold"),
    ],
)
def test_parse_markdown_stripping(
    answer_spec: AnswerSpec,
    completion: str,
    expected_value: object,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, answer_spec, _no_refs)
    assert result.value == expected_value


# ---------------------------------------------------------------------------
# value_to_float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer_spec,completion,value_to_float,expected_value",
    [
        pytest.param(
            "boolean",
            "Reasoning.\n\nANSWER: yes",
            lambda v: 1.0 if v else 0.0,
            1.0,
            id="bool-true",
        ),
        pytest.param(
            "boolean",
            "Reasoning.\n\nANSWER: no",
            lambda v: 1.0 if v else 0.0,
            0.0,
            id="bool-false",
        ),
        pytest.param(
            "numeric",
            "Score.\n\nANSWER: 7",
            lambda v: float(v) / 10.0 * 100,
            70.0,
            id="numeric-scale",
        ),
        pytest.param(
            ["Low", "Medium", "High"],
            "Analysis.\n\nANSWER: C",
            lambda v: {"A": 0.0, "B": 0.5, "C": 1.0}.get(str(v), 0.0),
            1.0,
            id="labels-letter-to-score",
        ),
        pytest.param(
            "string",
            "Analysis.\n\nANSWER: Mostly positive sentiment",
            lambda v: 1.0 if "positive" in str(v).lower() else 0.5,
            1.0,
            id="string-sentiment",
        ),
    ],
)
def test_parse_value_to_float(
    answer_spec: AnswerSpec,
    completion: str,
    value_to_float: object,
    expected_value: float,
) -> None:
    output = ModelOutput(model="test", completion=completion)
    result = parse_answer(output, answer_spec, _no_refs, value_to_float=value_to_float)  # type: ignore[arg-type]
    assert result.value == expected_value


def test_parse_multi_classification_value_to_float_raises() -> None:
    output = ModelOutput(model="test", completion="Analysis.\n\nANSWER: A,B")
    with pytest.raises(NotImplementedError):
        parse_answer(
            output,
            AnswerMultiLabel(["A", "B", "C"]),
            _no_refs,
            value_to_float=lambda _: 0.0,
        )


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def test_parse_labels_empty_raises() -> None:
    output = ModelOutput(model="test", completion="R.\n\nANSWER: A")
    with pytest.raises(ValueError, match="Must have labels"):
        parse_answer(output, [], _no_refs)


def test_parse_references() -> None:
    output = ModelOutput(model="test", completion="See [M1] and [M3].\n\nANSWER: yes")
    result = parse_answer(output, "boolean", _regex_refs)
    assert result.value is True
    assert len(result.references) == 2
    assert result.references[0].cite == "[M1]"
    assert result.references[1].cite == "[M3]"
