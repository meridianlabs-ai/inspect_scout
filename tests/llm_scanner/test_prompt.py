"""Tests for render_scanner_prompt — Jinja2 template variable substitution."""

from typing import Any

import pytest
from inspect_ai.model import ChatMessage
from inspect_scout._llm_scanner._llm_scanner import render_scanner_prompt
from inspect_scout._llm_scanner.answer import _BoolAnswer
from inspect_scout._transcript.types import Transcript
from pydantic import JsonValue


def _create_transcript(
    messages: list[ChatMessage] | None = None,
    model: str | None = None,
    score: JsonValue = None,
    metadata: dict[str, JsonValue] | None = None,
) -> Transcript:
    return Transcript(
        transcript_id="test-id",
        source_type="test",
        source_id="test-source",
        source_uri="test://uri",
        model=model,
        score=score,
        messages=messages or [],
        metadata=metadata or {},
    )


@pytest.mark.parametrize(
    "template,transcript_kwargs,expected_parts",
    [
        pytest.param(
            "Name: {{ metadata.name }}, Age: {{ metadata.age }}",
            {"metadata": {"name": "Alice", "age": 30}},
            ["Name: Alice", "Age: 30"],
            id="metadata-fields",
        ),
        pytest.param(
            "Text: {{ metadata.text }}",
            {"metadata": {"text": 'Hello "world" & <tag>'}},
            ['Text: Hello "world" & <tag>'],
            id="special-chars",
        ),
        pytest.param(
            "Score: {{ score }}",
            {"score": 0.85},
            ["Score: 0.85"],
            id="score-present",
        ),
        pytest.param(
            "Score: {% if score %}{{ score }}{% else %}N/A{% endif %}",
            {},
            ["Score: N/A"],
            id="score-absent",
        ),
        pytest.param(
            "Mean: {{ metadata.scores.mean }}, Fluency: {{ metadata.scores.fluency }}",
            {"metadata": {"scores": {"mean": 0.9, "fluency": 0.8}}},
            ["Mean: 0.9", "Fluency: 0.8"],
            id="nested-metadata",
        ),
        pytest.param(
            "Model: {{ model }}, Score: {{ score }}, Help: {{ metadata.scores.helpfulness }}",
            {
                "model": "gpt-4",
                "score": 0.88,
                "metadata": {"scores": {"helpfulness": 0.92}},
            },
            ["Model: gpt-4", "Score: 0.88", "Help: 0.92"],
            id="mixed-fields",
        ),
    ],
)
@pytest.mark.anyio
async def test_render_transcript_variable_substitution(
    template: str, transcript_kwargs: dict[str, Any], expected_parts: list[str]
) -> None:
    transcript = _create_transcript(**transcript_kwargs)

    result = await render_scanner_prompt(
        template=template,
        transcript=transcript,
        messages="",
        question="",
        answer=_BoolAnswer(),
    )

    for expected in expected_parts:
        assert expected in result
