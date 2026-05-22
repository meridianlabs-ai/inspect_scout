"""Tests for llm_scanner: content attr, integration."""

from unittest.mock import patch

import pytest
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    ModelOutput,
    get_model,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import llm_scanner
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.types import Transcript, TranscriptContent

# ---------------------------------------------------------------------------
# content parameter tests
# ---------------------------------------------------------------------------


class TestContentParameter:
    def test_content_sets_attr(self) -> None:
        """content= sets SCANNER_CONTENT_ATTR on the scan function."""
        scan_fn = llm_scanner(
            question="test?",
            answer="boolean",
            content=TranscriptContent(timeline=True),
        )
        assert hasattr(scan_fn, SCANNER_CONTENT_ATTR)
        tc = getattr(scan_fn, SCANNER_CONTENT_ATTR)
        assert tc.timeline is True

    def test_no_content_no_attr(self) -> None:
        """Without content=, SCANNER_CONTENT_ATTR is not set."""
        scan_fn = llm_scanner(question="test?", answer="boolean")
        assert not hasattr(scan_fn, SCANNER_CONTENT_ATTR)

    def test_content_with_events(self) -> None:
        """content= with events filter."""
        scan_fn = llm_scanner(
            question="test?",
            answer="boolean",
            content=TranscriptContent(events="all"),
        )
        tc = getattr(scan_fn, SCANNER_CONTENT_ATTR)
        assert tc.events == "all"


# ---------------------------------------------------------------------------
# model_role parameter tests
# ---------------------------------------------------------------------------


class TestModelRoleParameter:
    def test_model_role_passed_to_get_model(self) -> None:
        """model_role= is forwarded to get_model(role=...) at scan time."""
        with patch(
            "inspect_scout._llm_scanner._llm_scanner.get_model"
        ) as mock_get_model:
            # Construction should NOT call get_model — role resolution is deferred
            llm_scanner(
                question="test?",
                answer="boolean",
                model="openai/gpt-4o",
                model_role="scanner",
            )
            mock_get_model.assert_not_called()

    def test_model_role_none_by_default(self) -> None:
        """model_role defaults to None and does not affect construction."""
        # Should construct without error when model_role is omitted
        scan_fn = llm_scanner(question="test?", answer="boolean")
        assert scan_fn is not None


# ---------------------------------------------------------------------------
# template_overhead / context_window interaction
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_long_template_does_not_overflow_context_window() -> None:
    """Template tokens must be counted against the segment budget.

    With a very long template, the rendered prompt (template + messages)
    must still fit inside ``context_window``. Previously, only message
    tokens counted, so a long template could push the rendered prompt
    past the model's context window.
    """
    msgs: list[ChatMessage] = [
        ChatMessageUser(content="word " * 50, id=f"m{i}") for i in range(4)
    ]
    transcript = Transcript(transcript_id="t", messages=msgs)

    captured_prompts: list[list[ChatMessage]] = []

    def capture(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        captured_prompts.append(list(input_msgs))
        return ModelOutput.from_content(
            model="mockllm",
            content="Reason.\n\nANSWER: yes",
            stop_reason="stop",
        )

    mock_model = get_model("mockllm/model", custom_outputs=capture, memoize=False)

    # ~330 tokens of fixed template text — large enough that combined with
    # messages it would overflow context_window=500 if not accounted for.
    long_template = (
        "filler " * 300
    ) + "\n{{ messages }}\n{{ answer_prompt }}\n{{ question }}\n{{ answer_format }}"

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        template=long_template,
        context_window=500,
    )
    await scan_fn(transcript)

    assert captured_prompts, "model should have been called at least once"
    for prompt in captured_prompts:
        token_count = await mock_model.count_tokens(prompt)
        assert token_count <= 500, (
            f"prompt overflowed context_window: {token_count} > 500"
        )


@pytest.mark.anyio
async def test_default_template_does_not_overflow_context_window() -> None:
    """Default split-template prompts must respect ``context_window``.

    This exercises the default ``template=None`` path that most callers
    use, ensuring the reserved template overhead is applied before
    segmenting messages.
    """
    msgs: list[ChatMessage] = [
        ChatMessageUser(content="word " * 10, id=f"m{i}") for i in range(4)
    ]
    transcript = Transcript(transcript_id="t", messages=msgs)

    captured_prompts: list[list[ChatMessage]] = []

    def capture(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        captured_prompts.append(list(input_msgs))
        return ModelOutput.from_content(
            model="mockllm",
            content="Reason.\n\nANSWER: yes",
            stop_reason="stop",
        )

    mock_model = get_model("mockllm/model", custom_outputs=capture, memoize=False)

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        context_window=200,
    )
    await scan_fn(transcript)

    assert len(captured_prompts) > 1
    for prompt in captured_prompts:
        token_count = await mock_model.count_tokens(prompt)
        assert token_count <= 200, (
            f"prompt overflowed context_window: {token_count} > 200"
        )


@pytest.mark.anyio
async def test_template_overhead_exceeding_budget_raises_runtime_error() -> None:
    """Scanning should fail when template overhead alone exceeds budget."""
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="word " * 5, id="m1")],
    )

    mock_model = get_model("mockllm/model", memoize=False)
    oversized_template = (
        "filler " * 1000
    ) + "\n{{ messages }}\n{{ answer_prompt }}\n{{ question }}\n{{ answer_format }}"

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        template=oversized_template,
        context_window=500,
    )

    with pytest.raises(RuntimeError, match="template|context window|budget"):
        await scan_fn(transcript)
