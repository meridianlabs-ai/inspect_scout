"""Tests for W&B Weave extraction functions."""

import pytest

from tests.sources.weave_source.mocks import (
    MockWeaveCall,
    create_openai_llm_call,
    create_openai_llm_call_with_tools,
)


class TestExtractInputMessages:
    """Tests for extract_input_messages function."""

    @pytest.mark.asyncio
    async def test_extract_openai_messages(self) -> None:
        """Extract messages from OpenAI format inputs."""
        from inspect_scout.sources._weave.extraction import extract_input_messages

        inputs = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"},
            ]
        }

        messages = await extract_input_messages(inputs, "openai")
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    @pytest.mark.asyncio
    async def test_extract_anthropic_messages(self) -> None:
        """Extract messages from Anthropic format inputs."""
        from inspect_scout.sources._weave.extraction import extract_input_messages

        inputs = {
            "system": "You are helpful.",
            "messages": [{"role": "user", "content": "Hello!"}],
        }

        messages = await extract_input_messages(inputs, "anthropic")
        assert len(messages) >= 1
        # Anthropic format may include system message differently
        user_messages = [m for m in messages if m.role == "user"]
        assert len(user_messages) >= 1

    @pytest.mark.asyncio
    async def test_extract_string_input(self) -> None:
        """Handle string input by creating user message."""
        from inspect_scout.sources._weave.extraction import extract_input_messages

        messages = await extract_input_messages("Hello!", "openai")
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert "Hello" in str(messages[0].content)

    @pytest.mark.asyncio
    async def test_extract_empty_inputs(self) -> None:
        """Handle empty inputs."""
        from inspect_scout.sources._weave.extraction import extract_input_messages

        messages = await extract_input_messages({}, "openai")
        assert len(messages) == 0 or (len(messages) == 1 and messages[0].role == "user")


class TestExtractOutput:
    """Tests for extract_output function."""

    @pytest.mark.asyncio
    async def test_extract_openai_output(self) -> None:
        """Extract output from OpenAI format."""
        from inspect_scout.sources._weave.extraction import extract_output

        call = create_openai_llm_call()
        output = await extract_output(call.output, call, "openai")

        assert output is not None
        assert output.message is not None
        assert output.message.content is not None

    @pytest.mark.asyncio
    async def test_extract_empty_output(self) -> None:
        """Handle empty output."""
        from inspect_scout.sources._weave.extraction import extract_output

        call = MockWeaveCall()
        output = await extract_output(None, call, "openai")

        assert output is not None
        assert output.message is not None


class TestExtractUsage:
    """Tests for extract_usage function."""

    def test_extract_usage_from_summary(self) -> None:
        """Extract usage from call summary."""
        from inspect_scout.sources._weave.extraction import extract_usage

        call = MockWeaveCall(
            summary={
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                }
            }
        )

        usage = extract_usage(call)
        assert usage is not None
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150

    def test_extract_usage_from_output(self) -> None:
        """Extract usage from output dict."""
        from inspect_scout.sources._weave.extraction import extract_usage

        call = MockWeaveCall(
            output={
                "usage": {
                    "prompt_tokens": 80,
                    "completion_tokens": 40,
                    "total_tokens": 120,
                }
            }
        )

        usage = extract_usage(call)
        assert usage is not None
        assert usage.total_tokens == 120

    def test_extract_usage_missing(self) -> None:
        """Return None when usage is not available."""
        from inspect_scout.sources._weave.extraction import extract_usage

        call = MockWeaveCall()
        usage = extract_usage(call)
        assert usage is None


class TestExtractTools:
    """Tests for extract_tools function."""

    def test_extract_openai_tools(self) -> None:
        """Extract tools from OpenAI format."""
        from inspect_scout.sources._weave.extraction import extract_tools

        call = create_openai_llm_call_with_tools()
        tools = extract_tools(call)

        assert len(tools) >= 1
        assert tools[0].name == "get_weather"
        assert tools[0].description is not None
        assert tools[0].parameters is not None

    def test_extract_legacy_functions(self) -> None:
        """Extract tools from legacy 'functions' format."""
        from inspect_scout.sources._weave.extraction import extract_tools

        call = MockWeaveCall(
            inputs={
                "functions": [
                    {
                        "name": "search",
                        "description": "Search the web",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ]
            }
        )

        tools = extract_tools(call)
        assert len(tools) == 1
        assert tools[0].name == "search"

    def test_extract_no_tools(self) -> None:
        """Return empty list when no tools defined."""
        from inspect_scout.sources._weave.extraction import extract_tools

        call = create_openai_llm_call()
        tools = extract_tools(call)
        assert len(tools) == 0


class TestSumTokens:
    """Tests for sum_tokens function."""

    def test_sum_tokens_single_call(self) -> None:
        """Sum tokens from single call."""
        from inspect_scout.sources._weave.extraction import sum_tokens

        call = create_openai_llm_call()
        total = sum_tokens([call])
        assert total > 0

    def test_sum_tokens_multiple_calls(self) -> None:
        """Sum tokens across multiple calls."""
        from inspect_scout.sources._weave.extraction import sum_tokens

        calls = [create_openai_llm_call(), create_openai_llm_call()]
        total = sum_tokens(calls)
        assert total >= 60  # 30 tokens per call minimum


class TestSumLatency:
    """Tests for sum_latency function."""

    def test_sum_latency_single_call(self) -> None:
        """Sum latency from single call."""
        from inspect_scout.sources._weave.extraction import sum_latency

        call = create_openai_llm_call()
        total = sum_latency([call])
        assert total > 0

    def test_sum_latency_multiple_calls(self) -> None:
        """Sum latency across multiple calls."""
        from inspect_scout.sources._weave.extraction import sum_latency

        calls = [create_openai_llm_call(), create_openai_llm_call()]
        total = sum_latency(calls)
        assert total >= 2  # 1 second per call


class TestExtractMetadata:
    """Tests for extract_metadata function."""

    def test_extract_metadata_basic(self) -> None:
        """Extract basic metadata from call."""
        from inspect_scout.sources._weave.extraction import extract_metadata

        call = MockWeaveCall(
            op_name="test_op",
            display_name="Test Operation",
            attributes={"key": "value"},
        )

        metadata = extract_metadata(call)
        assert "op_name" in metadata
        assert "display_name" in metadata
        assert "key" in metadata

    def test_extract_metadata_empty(self) -> None:
        """Handle call with no metadata."""
        from inspect_scout.sources._weave.extraction import extract_metadata

        call = MockWeaveCall()
        metadata = extract_metadata(call)
        assert isinstance(metadata, dict)
