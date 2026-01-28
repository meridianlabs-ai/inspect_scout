"""Tests for Logfire data extraction."""

from typing import Any

import pytest
from inspect_scout.sources._logfire.detection import Instrumentor
from inspect_scout.sources._logfire.extraction import (
    extract_input_messages,
    extract_output,
    extract_tools,
    extract_usage,
    sum_latency,
    sum_tokens,
)

from .mocks import (
    create_anthropic_llm_span,
    create_openai_llm_span,
    create_openai_tools,
)


class TestExtractInputMessages:
    """Tests for extract_input_messages function."""

    @pytest.mark.asyncio
    async def test_extract_from_events_openai(self) -> None:
        """Extract messages from span events for OpenAI."""
        span = create_openai_llm_span(
            input_messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"},
            ]
        )
        messages = await extract_input_messages(span, Instrumentor.OPENAI)

        # Should have system and user messages
        assert len(messages) >= 1
        # Check that we got the user message at minimum
        user_msgs = [m for m in messages if hasattr(m, "role") and m.role == "user"]
        assert len(user_msgs) >= 1

    @pytest.mark.asyncio
    async def test_extract_from_events_anthropic(self) -> None:
        """Extract messages from span events for Anthropic."""
        span = create_anthropic_llm_span(
            input_messages=[{"role": "user", "content": "Hello!"}],
            system="You are helpful.",
        )
        messages = await extract_input_messages(span, Instrumentor.ANTHROPIC)

        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_extract_from_indexed_attributes(self) -> None:
        """Extract messages from indexed attributes."""
        span = {
            "attributes": {
                "gen_ai.prompt.0.role": "user",
                "gen_ai.prompt.0.content": "Hello!",
                "gen_ai.prompt.1.role": "assistant",
                "gen_ai.prompt.1.content": "Hi there!",
            },
            "otel_events": [],
        }
        messages = await extract_input_messages(span, Instrumentor.OPENAI)

        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_empty_span_returns_empty_list(self) -> None:
        """Empty span attributes returns empty message list."""
        span: dict[str, Any] = {"attributes": {}, "otel_events": []}
        messages = await extract_input_messages(span, Instrumentor.OPENAI)

        assert messages == []


class TestExtractOutput:
    """Tests for extract_output function."""

    @pytest.mark.asyncio
    async def test_extract_output_from_events(self) -> None:
        """Extract output from span events."""
        span = create_openai_llm_span(output_content="Hello! I can help.")
        output = await extract_output(span, Instrumentor.OPENAI)

        assert output.model == "gpt-4o-mini"
        # Check that output has content
        if output.choices:
            assert output.choices[0].message.content is not None

    @pytest.mark.asyncio
    async def test_extract_output_with_usage(self) -> None:
        """Extract output includes usage information."""
        span = create_openai_llm_span(input_tokens=100, output_tokens=50)
        output = await extract_output(span, Instrumentor.OPENAI)

        assert output.usage is not None
        assert output.usage.input_tokens == 100
        assert output.usage.output_tokens == 50


class TestExtractUsage:
    """Tests for extract_usage function."""

    def test_extract_usage_from_attributes(self) -> None:
        """Extract usage from gen_ai.usage attributes."""
        span = {
            "attributes": {
                "gen_ai.usage.input_tokens": 100,
                "gen_ai.usage.output_tokens": 50,
            }
        }
        usage = extract_usage(span)

        assert usage is not None
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_extract_usage_missing_returns_none(self) -> None:
        """Return None when no usage attributes."""
        span: dict[str, Any] = {"attributes": {}}
        usage = extract_usage(span)

        assert usage is None

    def test_extract_usage_partial(self) -> None:
        """Extract usage with only input or output tokens."""
        span = {"attributes": {"gen_ai.usage.input_tokens": 100}}
        usage = extract_usage(span)

        assert usage is not None
        assert usage.input_tokens == 100
        assert usage.output_tokens == 0


class TestExtractTools:
    """Tests for extract_tools function."""

    def test_extract_tools_from_definitions(self) -> None:
        """Extract tools from gen_ai.tool.definitions."""
        import json

        tools = create_openai_tools()
        span = {"attributes": {"gen_ai.tool.definitions": json.dumps(tools)}}

        extracted = extract_tools(span)

        assert len(extracted) == 2
        assert extracted[0].name == "get_weather"
        assert extracted[1].name == "get_time"

    def test_extract_tools_empty(self) -> None:
        """Empty attributes returns empty tool list."""
        span: dict[str, Any] = {"attributes": {}}
        extracted = extract_tools(span)

        assert extracted == []


class TestSumTokens:
    """Tests for sum_tokens function."""

    def test_sum_tokens_single_span(self) -> None:
        """Sum tokens from single span."""
        span = create_openai_llm_span(input_tokens=100, output_tokens=50)
        total = sum_tokens([span])

        assert total == 150

    def test_sum_tokens_multiple_spans(self) -> None:
        """Sum tokens across multiple spans."""
        span1 = create_openai_llm_span(input_tokens=100, output_tokens=50)
        span2 = create_anthropic_llm_span(input_tokens=200, output_tokens=100)

        total = sum_tokens([span1, span2])

        assert total == 450

    def test_sum_tokens_missing_attributes(self) -> None:
        """Handle spans without token attributes."""
        span: dict[str, Any] = {"attributes": {}}
        total = sum_tokens([span])

        assert total == 0


class TestSumLatency:
    """Tests for sum_latency function."""

    def test_sum_latency_single_span(self) -> None:
        """Sum latency from single span."""
        span = {"duration": 1.5}
        total = sum_latency([span])

        assert total == 1.5

    def test_sum_latency_multiple_spans(self) -> None:
        """Sum latency across multiple spans."""
        span1 = {"duration": 1.0}
        span2 = {"duration": 2.0}

        total = sum_latency([span1, span2])

        assert total == 3.0

    def test_sum_latency_missing_duration(self) -> None:
        """Handle spans without duration."""
        span: dict[str, Any] = {}
        total = sum_latency([span])

        assert total == 0.0
