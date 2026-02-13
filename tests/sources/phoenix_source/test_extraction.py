"""Tests for Phoenix message/output extraction."""

import json
from typing import Any

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout.sources._phoenix.detection import Provider
from inspect_scout.sources._phoenix.extraction import (
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
)


class TestExtractInputMessages:
    """Tests for extract_input_messages function."""

    @pytest.mark.asyncio
    async def test_extract_from_raw_input_openai(self) -> None:
        """Extract messages from raw input.value (OpenAI format)."""
        span = create_openai_llm_span(
            input_messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"},
            ]
        )
        messages = await extract_input_messages(span, Provider.OPENAI)

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    @pytest.mark.asyncio
    async def test_extract_from_raw_input_anthropic(self) -> None:
        """Extract messages from raw input.value (Anthropic format)."""
        span = create_anthropic_llm_span(
            system="You are helpful.",
            input_messages=[{"role": "user", "content": "Hello!"}],
        )
        messages = await extract_input_messages(span, Provider.ANTHROPIC)

        assert len(messages) >= 1
        # Should have user message
        user_msgs = [m for m in messages if m.role == "user"]
        assert len(user_msgs) >= 1

    @pytest.mark.asyncio
    async def test_extract_from_openinference_attributes(self) -> None:
        """Extract messages from OpenInference flattened attributes."""
        span: dict[str, Any] = {
            "attributes": {
                "llm.input_messages.0.message.role": "system",
                "llm.input_messages.0.message.content": "You are helpful.",
                "llm.input_messages.1.message.role": "user",
                "llm.input_messages.1.message.content": "What is 2+2?",
            }
        }
        messages = await extract_input_messages(span, Provider.OPENAI)

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    @pytest.mark.asyncio
    async def test_extract_empty_when_no_messages(self) -> None:
        """Return empty list when no messages found."""
        span: dict[str, Any] = {"attributes": {}}
        messages = await extract_input_messages(span, Provider.OPENAI)
        assert messages == []

    @pytest.mark.asyncio
    async def test_extract_with_tool_messages(self) -> None:
        """Extract messages including tool response messages."""
        span: dict[str, Any] = {
            "attributes": {
                "llm.input_messages.0.message.role": "user",
                "llm.input_messages.0.message.content": "What's the weather?",
                "llm.input_messages.1.message.role": "assistant",
                "llm.input_messages.1.message.content": "",
                "llm.input_messages.2.message.role": "tool",
                "llm.input_messages.2.message.content": "Sunny, 72F",
                "llm.input_messages.2.message.tool_call_id": "call_123",
            }
        }
        messages = await extract_input_messages(span, Provider.OPENAI)

        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[2].role == "tool"

    @pytest.mark.asyncio
    async def test_extract_multiturn_messages(self) -> None:
        """Extract multi-turn conversation messages."""
        span = create_openai_llm_span(
            input_messages=[
                {"role": "system", "content": "You are a math tutor."},
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4."},
                {"role": "user", "content": "What about 3+3?"},
            ]
        )
        messages = await extract_input_messages(span, Provider.OPENAI)

        assert len(messages) == 4
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"
        assert messages[3].role == "user"


class TestExtractOutput:
    """Tests for extract_output function."""

    @pytest.mark.asyncio
    async def test_extract_openai_output(self) -> None:
        """Extract output from OpenAI-format raw payload."""
        span = create_openai_llm_span(output_content="Hello there!")
        output = await extract_output(span)

        assert isinstance(output, ModelOutput)
        assert output.message is not None
        assert "Hello there!" in str(output.message.content)

    @pytest.mark.asyncio
    async def test_extract_anthropic_output(self) -> None:
        """Extract output from Anthropic-format raw payload."""
        span = create_anthropic_llm_span(output_content="Hello there!")
        output = await extract_output(span)

        assert isinstance(output, ModelOutput)
        assert output.message is not None

    @pytest.mark.asyncio
    async def test_extract_output_with_tool_calls(self) -> None:
        """Extract output containing tool calls."""
        raw_output = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "SF"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            }
        )
        span: dict[str, Any] = {
            "attributes": {
                "llm.model_name": "gpt-4o",
                "output.value": raw_output,
            }
        }
        output = await extract_output(span)

        assert output.message is not None
        assert output.message.tool_calls is not None
        assert len(output.message.tool_calls) == 1
        assert output.message.tool_calls[0].function == "get_weather"

    @pytest.mark.asyncio
    async def test_extract_output_from_openinference(self) -> None:
        """Extract output from OpenInference flattened attributes."""
        span: dict[str, Any] = {
            "attributes": {
                "llm.model_name": "gpt-4o",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "The answer is 42.",
            }
        }
        output = await extract_output(span)

        assert output.message is not None
        assert "42" in str(output.message.content)

    @pytest.mark.asyncio
    async def test_extract_empty_output_fallback(self) -> None:
        """Return empty output when no data found."""
        span: dict[str, Any] = {"attributes": {"llm.model_name": "unknown"}}
        output = await extract_output(span)

        assert isinstance(output, ModelOutput)


class TestExtractUsage:
    """Tests for extract_usage function."""

    def test_extract_openinference_tokens(self) -> None:
        """Extract tokens from OpenInference attributes."""
        span = create_openai_llm_span(input_tokens=100, output_tokens=50)
        usage = extract_usage(span)

        assert usage is not None
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_extract_gen_ai_tokens(self) -> None:
        """Extract tokens from gen_ai attributes as fallback."""
        span: dict[str, Any] = {
            "attributes": {
                "gen_ai.usage.input_tokens": 80,
                "gen_ai.usage.output_tokens": 40,
            }
        }
        usage = extract_usage(span)

        assert usage is not None
        assert usage.input_tokens == 80
        assert usage.output_tokens == 40

    def test_no_usage_returns_none(self) -> None:
        """Return None when no token counts available."""
        span: dict[str, Any] = {"attributes": {}}
        usage = extract_usage(span)
        assert usage is None


class TestExtractTools:
    """Tests for extract_tools function."""

    def test_extract_tool_definitions(self) -> None:
        """Extract tool definitions from llm.tools attributes."""
        tool_schema = json.dumps(
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                        },
                        "required": ["city"],
                    },
                },
            }
        )
        span: dict[str, Any] = {
            "attributes": {
                "llm.tools.0.tool.json_schema": tool_schema,
            }
        }
        tools = extract_tools(span)

        assert len(tools) == 1
        assert tools[0].name == "get_weather"
        assert tools[0].description == "Get the weather."

    def test_extract_multiple_tools(self) -> None:
        """Extract multiple tool definitions."""
        tool1 = json.dumps(
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        )
        tool2 = json.dumps(
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "Get time.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        )
        span: dict[str, Any] = {
            "attributes": {
                "llm.tools.0.tool.json_schema": tool1,
                "llm.tools.1.tool.json_schema": tool2,
            }
        }
        tools = extract_tools(span)

        assert len(tools) == 2
        assert tools[0].name == "get_weather"
        assert tools[1].name == "get_time"

    def test_no_tools_returns_empty(self) -> None:
        """Return empty list when no tool definitions."""
        span: dict[str, Any] = {"attributes": {}}
        tools = extract_tools(span)
        assert tools == []


class TestSumTokens:
    """Tests for sum_tokens function."""

    def test_sum_across_spans(self) -> None:
        """Sum tokens across multiple spans."""
        span1 = create_openai_llm_span(span_id="s1", input_tokens=100, output_tokens=50)
        span2 = create_openai_llm_span(
            span_id="s2", input_tokens=200, output_tokens=100
        )

        total = sum_tokens([span1, span2])
        assert total == 450  # 100+50+200+100

    def test_sum_empty_spans(self) -> None:
        """Sum tokens with no spans."""
        assert sum_tokens([]) == 0


class TestSumLatency:
    """Tests for sum_latency function."""

    def test_sum_latency(self) -> None:
        """Sum latency from start/end times."""
        span = create_openai_llm_span(
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:02Z",
        )
        latency = sum_latency([span])
        assert latency == pytest.approx(2.0, abs=0.1)

    def test_sum_latency_multiple_spans(self) -> None:
        """Sum latency across multiple spans."""
        span1 = create_openai_llm_span(
            span_id="s1",
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-01T00:00:01Z",
        )
        span2 = create_openai_llm_span(
            span_id="s2",
            start_time="2025-01-01T00:00:01Z",
            end_time="2025-01-01T00:00:03Z",
        )

        latency = sum_latency([span1, span2])
        assert latency == pytest.approx(3.0, abs=0.1)  # 1s + 2s

    def test_sum_latency_empty(self) -> None:
        """Sum latency with no spans."""
        assert sum_latency([]) == 0.0
