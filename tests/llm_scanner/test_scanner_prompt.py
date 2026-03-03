"""Tests for scanner_prompt — prompt template rendering through the public API."""

import pytest
from inspect_scout._llm_scanner.answer import answer_type
from inspect_scout._llm_scanner.generate import scanner_prompt
from inspect_scout._llm_scanner.types import (
    AnswerMultiLabel,
    AnswerSpec,
    AnswerStructured,
)
from pydantic import BaseModel, Field


class _StructuredModel(BaseModel):
    score: int = Field(description="Score")


@pytest.mark.parametrize(
    "answer_spec,expected_prompt_fragment,expected_format_fragment",
    [
        pytest.param(
            "boolean",
            "Answer the following yes or no question",
            "ANSWER: $VALUE",
            id="boolean",
        ),
        pytest.param(
            "numeric",
            "Answer the following numeric question",
            "ANSWER: $NUMBER",
            id="numeric",
        ),
        pytest.param(
            ["Choice A", "Choice B", "Choice C"],
            "Answer the following multiple choice question",
            "ANSWER: $LETTER",
            id="labels",
        ),
        pytest.param(
            AnswerMultiLabel(["Choice A", "Choice B", "Choice C"]),
            "Answer the following multiple choice question",
            "ANSWER: $LETTERS",
            id="multi-classification",
        ),
        pytest.param(
            "string",
            "Answer the following question",
            "ANSWER: $TEXT",
            id="string",
        ),
        pytest.param(
            AnswerStructured(type=_StructuredModel),
            "Use the answer() tool",
            "use the answer() tool",
            id="structured",
        ),
    ],
)
def test_scanner_prompt_templates(
    answer_spec: AnswerSpec,
    expected_prompt_fragment: str,
    expected_format_fragment: str,
) -> None:
    rendered = scanner_prompt(
        messages="[M1] User: Hello",
        question="Is this good?",
        answer=answer_spec,
    )
    assert expected_prompt_fragment in rendered
    assert expected_format_fragment in rendered
    assert "[M1] User: Hello" in rendered
    assert "Is this good?" in rendered


def test_scanner_prompt_labels_include_choices() -> None:
    rendered = scanner_prompt(
        messages="transcript",
        question="Pick one.",
        answer=["Alpha", "Beta", "Gamma"],
    )
    assert "A) Alpha" in rendered
    assert "B) Beta" in rendered
    assert "C) Gamma" in rendered


def test_answer_type_delegates_to_answer_from_argument() -> None:
    answer = answer_type("boolean")
    assert "yes or no" in answer.prompt
