"""Tests for split-template rendering used by the prompt-cache path."""

from typing import Any

import pytest
from inspect_ai.model import ChatMessage
from inspect_scout._llm_scanner._llm_scanner import (
    _render_split_prompt,
    render_scanner_prompt,
)
from inspect_scout._llm_scanner.answer import _BoolAnswer
from inspect_scout._llm_scanner.prompt import (
    DEFAULT_SCANNER_TEMPLATE,
    DEFAULT_SCANNER_TEMPLATE_PREFIX,
    DEFAULT_SCANNER_TEMPLATE_SUFFIX,
)
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


def test_default_template_concat_equals_combined() -> None:
    """Combined template must equal split halves concatenated.

    Byte-for-byte. This invariant is what lets `template=None` be a no-behavior-
    change refactor for users who happened to import DEFAULT_SCANNER_TEMPLATE.
    """
    assert (
        DEFAULT_SCANNER_TEMPLATE_PREFIX + DEFAULT_SCANNER_TEMPLATE_SUFFIX
        == DEFAULT_SCANNER_TEMPLATE
    )


@pytest.mark.anyio
async def test_split_render_concatenation_matches_single_render() -> None:
    """Split-and-concat render must equal combined render.

    Rendering the two halves separately and concatenating produces the same
    string as rendering the combined template once.
    """
    transcript = _create_transcript()
    kwargs: dict[str, Any] = dict(
        template_variables=None,
        transcript=transcript,
        messages="[M1] hi",
        question="Was it helpful?",
        answer=_BoolAnswer(),
    )

    prefix, suffix = await _render_split_prompt(
        templates=(DEFAULT_SCANNER_TEMPLATE_PREFIX, DEFAULT_SCANNER_TEMPLATE_SUFFIX),
        **kwargs,
    )
    combined = await render_scanner_prompt(
        template=DEFAULT_SCANNER_TEMPLATE,
        **kwargs,
    )
    assert prefix + suffix == combined


@pytest.mark.anyio
async def test_split_render_prefix_isolates_messages() -> None:
    """Prefix block contains messages, suffix contains question.

    The prefix block is the cacheable boundary — it should contain the
    transcript messages but none of the per-scanner question/answer text.
    """
    transcript = _create_transcript()
    prefix, suffix = await _render_split_prompt(
        templates=(DEFAULT_SCANNER_TEMPLATE_PREFIX, DEFAULT_SCANNER_TEMPLATE_SUFFIX),
        template_variables=None,
        transcript=transcript,
        messages="[M1] sample message",
        question="A unique scanner question?",
        answer=_BoolAnswer(),
    )

    assert "sample message" in prefix
    assert "scanner question" not in prefix

    assert "scanner question" in suffix
    assert "sample message" not in suffix


@pytest.mark.anyio
async def test_split_render_determinism_across_scanners_same_transcript() -> None:
    """Prefix bytes must be identical across scanners on the same transcript.

    Two scanners with different questions but the same transcript must
    produce byte-identical prefix content. This is the property that lets
    cross-scanner prompt caching work.
    """
    transcript = _create_transcript(metadata={"key": "val"})
    common_kwargs: dict[str, Any] = dict(
        templates=(DEFAULT_SCANNER_TEMPLATE_PREFIX, DEFAULT_SCANNER_TEMPLATE_SUFFIX),
        template_variables=None,
        transcript=transcript,
        messages="[M1] hi",
        answer=_BoolAnswer(),
    )

    prefix_a, _ = await _render_split_prompt(question="Question A?", **common_kwargs)
    prefix_b, _ = await _render_split_prompt(question="Question B?", **common_kwargs)
    assert prefix_a == prefix_b


@pytest.mark.anyio
async def test_split_render_custom_tuple_template() -> None:
    """Custom tuple templates render with full kwargs in both halves.

    User-supplied tuple templates render with the full kwarg bag in both
    halves.
    """
    transcript = _create_transcript(metadata={"name": "Alice"})
    prefix_template = "META: {{ metadata.name }} | MSGS: {{ messages }}"
    suffix_template = "Q: {{ question }} ({{ answer_format }})"

    prefix, suffix = await _render_split_prompt(
        templates=(prefix_template, suffix_template),
        template_variables=None,
        transcript=transcript,
        messages="msgs-here",
        question="Was it good?",
        answer=_BoolAnswer(),
    )

    assert prefix == "META: Alice | MSGS: msgs-here"
    assert "Q: Was it good?" in suffix
