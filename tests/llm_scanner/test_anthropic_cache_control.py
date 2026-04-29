"""Validate Anthropic cache_control placement for llm_scanner prompts.

This is the end-to-end claim that scout's two-block prompt structure plus
inspect_ai's Anthropic provider produce a request with `cache_control:
ephemeral` on the shared prefix block — the boundary that lets cross-scanner
prompt caching kick in.
"""

import pytest
from inspect_ai._util.content import ContentText
from inspect_ai.model import ChatMessageUser, GenerateConfig
from inspect_ai.model._providers.anthropic import AnthropicAPI
from inspect_scout._llm_scanner._llm_scanner import _render_split_prompt
from inspect_scout._llm_scanner.answer import _BoolAnswer
from inspect_scout._llm_scanner.prompt import (
    DEFAULT_SCANNER_TEMPLATE_PREFIX,
    DEFAULT_SCANNER_TEMPLATE_SUFFIX,
)
from inspect_scout._transcript.types import Transcript


def _make_transcript(transcript_id: str = "t1") -> Transcript:
    return Transcript(
        transcript_id=transcript_id,
        source_type="test",
        source_id="src",
        source_uri="test://uri",
        messages=[],
        metadata={},
    )


async def _render_default_user_message(
    *,
    messages: str,
    question: str,
) -> ChatMessageUser:
    """Build the user message llm_scanner emits on the default-template path."""
    prefix_str, suffix_str = await _render_split_prompt(
        templates=(DEFAULT_SCANNER_TEMPLATE_PREFIX, DEFAULT_SCANNER_TEMPLATE_SUFFIX),
        template_variables=None,
        transcript=_make_transcript(),
        messages=messages,
        question=question,
        answer=_BoolAnswer(),
    )
    return ChatMessageUser(
        content=[
            ContentText(text=prefix_str),
            ContentText(text=suffix_str),
        ]
    )


def _anthropic_api() -> AnthropicAPI:
    # Fake api_key — we never call generate, only resolve_chat_input which
    # is a pure transformation.
    return AnthropicAPI(model_name="claude-opus-4-7", api_key="sk-test")


@pytest.mark.anyio
async def test_default_template_marks_prefix_block_for_anthropic_cache() -> None:
    """Prefix block gets cache_control: ephemeral; suffix block does not.

    Anthropic's auto-cache marks the last block server-side, so we only need
    an explicit marker on the second-to-last.
    """
    user_msg = await _render_default_user_message(
        messages="[M1] sample", question="Was it helpful?"
    )
    api = _anthropic_api()

    (
        system_param,
        tools_params,
        _mcp,
        message_params,
        cache_prompt,
    ) = await api.resolve_chat_input(
        input=[user_msg],
        tools=[],
        config=GenerateConfig(cache_prompt=True),
    )

    assert cache_prompt is True
    assert system_param is None
    assert tools_params == []
    assert len(message_params) == 1

    content = message_params[0]["content"]
    assert isinstance(content, list)
    assert len(content) == 2

    prefix_block, suffix_block = content
    assert prefix_block.get("cache_control") == {"type": "ephemeral"}
    assert "cache_control" not in suffix_block


@pytest.mark.anyio
async def test_two_scanners_produce_byte_identical_prefix_block() -> None:
    """Two scanners on same transcript produce identical prefix bytes.

    Cross-scanner cache hit requires byte-identical prefix bytes for the
    same transcript. Two scanners with different questions but the same
    transcript must serialize to the same prefix TextBlockParam text.
    """
    api = _anthropic_api()

    msg_a = await _render_default_user_message(
        messages="[M1] shared transcript", question="Question A?"
    )
    msg_b = await _render_default_user_message(
        messages="[M1] shared transcript", question="Question B?"
    )

    (_s, _t, _m, params_a, _c) = await api.resolve_chat_input(
        input=[msg_a], tools=[], config=GenerateConfig(cache_prompt=True)
    )
    (_s2, _t2, _m2, params_b, _c2) = await api.resolve_chat_input(
        input=[msg_b], tools=[], config=GenerateConfig(cache_prompt=True)
    )

    content_a = params_a[0]["content"]
    content_b = params_b[0]["content"]
    assert isinstance(content_a, list) and isinstance(content_b, list)

    prefix_a, suffix_a = content_a
    prefix_b, suffix_b = content_b

    # Same text bytes → same cache key on Anthropic's side.
    assert prefix_a["text"] == prefix_b["text"]
    # Both marked.
    assert prefix_a.get("cache_control") == {"type": "ephemeral"}
    assert prefix_b.get("cache_control") == {"type": "ephemeral"}

    # Suffix bytes must differ (the per-scanner question is here).
    assert suffix_a["text"] != suffix_b["text"]


@pytest.mark.anyio
async def test_cache_prompt_false_disables_marker() -> None:
    """cache_prompt=False suppresses the marker.

    If a caller explicitly sets cache_prompt=False, no cache_control is
    added even though the message structure supports it.
    """
    user_msg = await _render_default_user_message(
        messages="[M1] sample", question="Was it helpful?"
    )
    api = _anthropic_api()

    (_s, _t, _m, message_params, cache_prompt) = await api.resolve_chat_input(
        input=[user_msg],
        tools=[],
        config=GenerateConfig(cache_prompt=False),
    )

    assert cache_prompt is False
    content = message_params[0]["content"]
    for block in content:
        assert "cache_control" not in block
