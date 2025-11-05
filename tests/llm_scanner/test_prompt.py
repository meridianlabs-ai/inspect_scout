"""Tests for prompt rendering in llm_scanner."""

from dataclasses import dataclass
from typing import Any

import pytest
from inspect_ai.model import ChatMessage, ChatMessageUser, ModelOutput
from inspect_scout._llm_scanner._llm_scanner import render_scanner_prompt
from inspect_scout._llm_scanner.answer import _BoolAnswer
from inspect_scout._llm_scanner.prompt import DEFAULT_SCANNER_TEMPLATE
from inspect_scout._scanner.result import Result
from inspect_scout._transcript.types import Transcript
from pydantic import JsonValue


@dataclass
class _TestAnswer:
    """Test answer implementation."""

    prompt: str
    format: str

    def result_for_answer(
        self, output: ModelOutput, message_id_map: dict[str, str]
    ) -> Result:
        """Stub implementation for testing."""
        return Result(value=None)


def _create_transcript(
    messages: list[ChatMessage] | None = None,
    variables: dict[str, JsonValue] | None = None,
    score: float | None = None,
    scores: dict[str, JsonValue] | None = None,
) -> Transcript:
    """Helper to create test transcripts with required fields."""
    return Transcript(
        id="test-id",
        source_id="test-source",
        source_uri="test://uri",
        messages=messages or [],
        variables=variables or {},
        score=score,
        scores=scores or {},
    )


@pytest.mark.asyncio
async def test_render_basic_prompt() -> None:
    """Render basic prompt with all required parameters substituted.

    This test documents a BUG: the DEFAULT_SCANNER_TEMPLATE has {answer_format}
    with single braces instead of {{ answer_format }} with double braces, so the
    answer_format parameter is not being rendered properly.
    """
    transcript = _create_transcript(messages=[ChatMessageUser(content="Hello")])

    result = await render_scanner_prompt(
        template=DEFAULT_SCANNER_TEMPLATE,
        transcript=transcript,
        messages="[M1] User: Hello",
        question="Did the user greet?",
        answer=_BoolAnswer(),
    )

    assert "[M1] User: Hello" in result
    assert "Did the user greet?" in result
    assert "Answer the following yes or no question" in result
    # BUG: This should pass but fails because template has {answer_format} not {{ answer_format }}
    assert "'ANSWER: $VALUE' (without quotes) where $VALUE is yes or no." in result, (
        "answer_format is not being rendered in the template"
    )


@pytest.mark.parametrize(
    "template,transcript_kwargs,expected_parts",
    [
        # Variables from transcript (accessed via transcript object)
        (
            "Name: {{ transcript.variables.name }}, Age: {{ transcript.variables.age }}",
            {"variables": {"name": "Alice", "age": 30}},
            ["Name: Alice", "Age: 30"],
        ),
        # Special characters
        (
            "Text: {{ transcript.variables.text }}",
            {"variables": {"text": 'Hello "world" & <tag>'}},
            ['Text: Hello "world" & <tag>'],
        ),
        # Score (present)
        (
            "Score: {{ transcript.score }}",
            {"score": 0.85},
            ["Score: 0.85"],
        ),
        # Score (absent - None)
        (
            "Score: {% if transcript.score %}{{ transcript.score }}{% else %}N/A{% endif %}",
            {},
            ["Score: N/A"],
        ),
        # Named scores
        (
            "Accuracy: {{ transcript.scores.accuracy }}, Fluency: {{ transcript.scores.fluency }}",
            {"scores": {"accuracy": 0.9, "fluency": 0.8}},
            ["Accuracy: 0.9", "Fluency: 0.8"],
        ),
        # Mixed: variables, score, and named scores
        (
            "Model: {{ transcript.variables.model }}, Score: {{ transcript.score }}, Help: {{ transcript.scores.helpfulness }}",
            {
                "variables": {"model": "gpt-4"},
                "score": 0.88,
                "scores": {"helpfulness": 0.92},
            },
            ["Model: gpt-4", "Score: 0.88", "Help: 0.92"],
        ),
    ],
)
@pytest.mark.asyncio
async def test_render_transcript_variable_substitution(
    template: str, transcript_kwargs: dict[str, Any], expected_parts: list[str]
) -> None:
    """Transcript variables, scores, and named scores are substituted correctly."""
    transcript = _create_transcript(**transcript_kwargs)

    result = await render_scanner_prompt(
        template=template,
        transcript=transcript,
        messages="",
        question="",
        answer=_TestAnswer(prompt="", format=""),
    )

    for expected in expected_parts:
        assert expected in result


@pytest.mark.parametrize(
    "messages,expected_in_result",
    [
        # Empty messages
        ("", "Is this empty?"),
        # Multiline messages
        (
            "[M1] User: First line\nSecond line\n\n[M2] Assistant: Response",
            ["[M1] User: First line", "Second line", "[M2] Assistant: Response"],
        ),
    ],
)
@pytest.mark.asyncio
async def test_render_with_various_message_formats(
    messages: str, expected_in_result: str | list[str]
) -> None:
    """Messages parameter is rendered correctly regardless of format."""
    transcript = _create_transcript()

    result = await render_scanner_prompt(
        template=DEFAULT_SCANNER_TEMPLATE,
        transcript=transcript,
        messages=messages,
        question="Is this empty?",
        answer=_TestAnswer(prompt="Answer", format="FORMAT"),
    )

    if isinstance(expected_in_result, list):
        for expected in expected_in_result:
            assert expected in result
    else:
        assert expected_in_result in result
