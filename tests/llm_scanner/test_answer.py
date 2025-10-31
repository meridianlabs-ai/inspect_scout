"""Tests for answer_portion_template function in llm_scanner."""

import pytest
from inspect_scout.llm_scanner._answer import answer_portion_template
from inspect_scout.llm_scanner._types import AnswerType


def test_bool_answer_template() -> None:
    """Boolean answer type returns correct template format."""
    answer = AnswerType(type="bool")

    result = answer_portion_template(answer)

    assert "Answer the following yes or no question: {prompt}" in result
    assert "{explanation_text}" in result
    assert "'ANSWER: xxx' (without quotes) where xxx is the numeric value" in result


def test_number_answer_template() -> None:
    """Numeric answer type returns correct template format."""
    answer = AnswerType(type="number")

    result = answer_portion_template(answer)

    assert "Answer the following numeric question: {prompt}" in result
    assert "{explanation_text}" in result
    assert "'ANSWER: xxx' (without quotes) where xxx is the numeric value" in result


def test_labels_answer_template() -> None:
    """Labels answer type returns correct template format with multiple choices."""
    answer = AnswerType(type="labels", labels=["Choice A", "Choice B", "Choice C"])

    result = answer_portion_template(answer)

    assert "Answer the following multiple choice question: {prompt}" in result
    assert "A) Choice A\nB) Choice B\nC) Choice C" in result
    assert "{explanation_text}" in result
    assert "'ANSWER: $LETTER' (without quotes) where LETTER is one of A,B,C" in result


def test_unsupported_answer_type() -> None:
    """Unsupported answer types raise NotImplementedError."""
    answer = AnswerType(type="str")

    with pytest.raises(
        NotImplementedError, match="Support for 'str' not yet implemented"
    ):
        answer_portion_template(answer)
