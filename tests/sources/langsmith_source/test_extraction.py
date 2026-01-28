"""Tests for LangSmith input/output extraction functions.

Tests extract_input_messages(), extract_output(), extract_tools(),
sum_tokens(), sum_latency(), and metadata extraction helpers.
"""

from datetime import datetime, timedelta
from typing import Any

import pytest
from inspect_scout.sources._langsmith.extraction import (
    extract_bool,
    extract_dict,
    extract_input_messages,
    extract_int,
    extract_json,
    extract_metadata,
    extract_output,
    extract_str,
    extract_tools,
    sum_latency,
    sum_tokens,
)

from tests.sources.langsmith_source.mocks import (
    MockRun,
    create_anthropic_llm_run,
    create_google_llm_run,
    create_openai_llm_run,
    create_openai_tools,
)


class TestExtractInputMessages:
    """Tests for extract_input_messages function."""

    @pytest.mark.asyncio
    async def test_extract_openai_messages(self) -> None:
        """Extract messages from OpenAI format inputs."""
        inputs = {"messages": [{"role": "user", "content": "Hello!"}]}

        messages = await extract_input_messages(inputs, "openai")

        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hello!"

    @pytest.mark.asyncio
    async def test_extract_anthropic_messages(self) -> None:
        """Extract messages from Anthropic format inputs."""
        inputs = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "system": "You are helpful.",
        }

        messages = await extract_input_messages(inputs, "anthropic")

        # Should have both system and user message
        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_extract_google_messages(self) -> None:
        """Extract messages from Google format inputs."""
        inputs = {"contents": [{"role": "user", "parts": [{"text": "Hello!"}]}]}

        messages = await extract_input_messages(inputs, "google")

        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_extract_string_input(self) -> None:
        """String input should be wrapped as user message."""
        messages = await extract_input_messages("What is 2+2?", "openai")

        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_extract_string_input_any_format(self) -> None:
        """String input should work regardless of format type."""
        for format_type in ["openai", "anthropic", "google", "unknown"]:
            messages = await extract_input_messages("Hello", format_type)
            assert len(messages) == 1
            assert messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_extract_non_dict_input(self) -> None:
        """Non-dict input should be converted to string."""
        messages = await extract_input_messages(12345, "openai")

        assert len(messages) == 1
        assert "12345" in messages[0].content

    @pytest.mark.asyncio
    async def test_extract_empty_messages(self) -> None:
        """Empty messages list should return empty list."""
        inputs: dict[str, Any] = {"messages": []}

        messages = await extract_input_messages(inputs, "openai")

        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_unknown_format_tries_openai(self) -> None:
        """Unknown format with messages should try OpenAI parsing."""
        inputs = {"messages": [{"role": "user", "content": "Hello!"}]}

        messages = await extract_input_messages(inputs, "unknown")

        assert len(messages) >= 1

    @pytest.mark.asyncio
    async def test_anthropic_system_in_first_message(self) -> None:
        """Anthropic: system message in first position should be handled."""
        inputs = {
            "messages": [
                {"role": "system", "content": "Be helpful"},
                {"role": "user", "content": "Hello!"},
            ]
        }

        messages = await extract_input_messages(inputs, "anthropic")

        # Should handle the system message appropriately
        assert len(messages) >= 1


class TestExtractOutput:
    """Tests for extract_output function."""

    @pytest.mark.asyncio
    async def test_extract_openai_output(self) -> None:
        """Extract output from OpenAI format."""
        run = create_openai_llm_run(content="Hello there!")
        outputs = run.outputs

        output = await extract_output(outputs, run, "openai")

        assert output is not None
        assert output.message is not None

    @pytest.mark.asyncio
    async def test_extract_anthropic_output(self) -> None:
        """Extract output from Anthropic format."""
        run = create_anthropic_llm_run(
            content_blocks=[{"type": "text", "text": "Hello!"}]
        )
        outputs = run.outputs

        output = await extract_output(outputs, run, "anthropic")

        assert output is not None

    @pytest.mark.asyncio
    async def test_extract_google_output(self) -> None:
        """Extract output from Google format."""
        run = create_google_llm_run(response_text="Hello!")
        outputs = run.outputs

        output = await extract_output(outputs, run, "google")

        assert output is not None

    @pytest.mark.asyncio
    async def test_extract_empty_output(self) -> None:
        """Empty output should return ModelOutput with empty content."""
        run = MockRun(extra={"metadata": {"ls_model_name": "test-model"}})

        output = await extract_output({}, run, "openai")

        assert output is not None

    @pytest.mark.asyncio
    async def test_extract_none_output(self) -> None:
        """None output should return ModelOutput with empty content."""
        run = MockRun(extra={"metadata": {"ls_model_name": "test-model"}})

        output = await extract_output(None, run, "openai")

        assert output is not None


class TestExtractTools:
    """Tests for extract_tools function."""

    def test_extract_openai_tools(self) -> None:
        """Extract tool definitions from OpenAI format."""
        run = MockRun(
            inputs={"tools": create_openai_tools()},
        )

        tools = extract_tools(run)

        assert len(tools) == 2
        assert tools[0].name == "get_weather"
        assert tools[0].description == "Get the current weather for a city."
        assert tools[1].name == "get_time"

    def test_extract_legacy_functions(self) -> None:
        """Extract tool definitions from legacy functions format."""
        run = MockRun(
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
            },
        )

        tools = extract_tools(run)

        assert len(tools) == 1
        assert tools[0].name == "search"
        assert tools[0].description == "Search the web"

    def test_extract_tools_from_invocation_params(self) -> None:
        """Extract tools from extra.invocation_params."""
        run = MockRun(
            inputs={},
            extra={"invocation_params": {"tools": create_openai_tools()}},
        )

        tools = extract_tools(run)

        assert len(tools) == 2

    def test_extract_tools_empty(self) -> None:
        """Return empty list when no tools present."""
        run = MockRun(inputs={}, extra={})

        tools = extract_tools(run)

        assert len(tools) == 0

    def test_extract_tools_handles_invalid(self) -> None:
        """Handle invalid tool definitions gracefully."""
        run = MockRun(
            inputs={
                "tools": [
                    {"type": "function"},  # Missing function key
                    {"type": "function", "function": {}},  # Missing name
                    "not a dict",  # Invalid type
                ]
            },
        )

        tools = extract_tools(run)

        assert len(tools) == 0


class TestSumTokens:
    """Tests for sum_tokens helper function."""

    def test_sum_tokens_from_runs(self) -> None:
        """Sum tokens across multiple runs."""
        runs = [
            MockRun(prompt_tokens=100, completion_tokens=50),
            MockRun(prompt_tokens=200, completion_tokens=100),
        ]

        total = sum_tokens(runs)

        assert total == 450

    def test_sum_tokens_with_none(self) -> None:
        """Handle runs with None token counts."""
        runs = [
            MockRun(prompt_tokens=100, completion_tokens=50),
            MockRun(prompt_tokens=None, completion_tokens=None),
        ]

        total = sum_tokens(runs)

        assert total == 150

    def test_sum_tokens_empty_list(self) -> None:
        """Return 0 for empty run list."""
        assert sum_tokens([]) == 0


class TestSumLatency:
    """Tests for sum_latency helper function."""

    def test_sum_latency_from_runs(self) -> None:
        """Sum latency across multiple runs."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        runs = [
            MockRun(
                start_time=base_time,
                end_time=base_time + timedelta(seconds=1.5),
            ),
            MockRun(
                start_time=base_time + timedelta(seconds=2),
                end_time=base_time + timedelta(seconds=4.5),
            ),
        ]

        total = sum_latency(runs)

        assert total == 4.0  # 1.5 + 2.5

    def test_sum_latency_with_missing_times(self) -> None:
        """Handle runs with missing start/end times."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        runs = [
            MockRun(
                start_time=base_time,
                end_time=base_time + timedelta(seconds=1.5),
            ),
            MockRun(start_time=base_time, end_time=None),
        ]

        total = sum_latency(runs)

        assert total == 1.5

    def test_sum_latency_empty_list(self) -> None:
        """Return 0 for empty run list."""
        assert sum_latency([]) == 0.0


class TestExtractMetadata:
    """Tests for extract_metadata helper function."""

    def test_extract_basic_metadata(self) -> None:
        """Extract basic metadata fields from run."""
        run = MockRun(
            name="test-run",
            run_type="llm",
            tags=["tag1", "tag2"],
        )

        metadata = extract_metadata(run)

        assert metadata["name"] == "test-run"
        assert metadata["run_type"] == "llm"
        assert metadata["tags"] == ["tag1", "tag2"]

    def test_extract_extra_metadata(self) -> None:
        """Extract metadata from run.extra."""
        run = MockRun(
            name="test",
            extra={"metadata": {"custom_key": "custom_value", "another": 123}},
        )

        metadata = extract_metadata(run)

        assert metadata["custom_key"] == "custom_value"
        assert metadata["another"] == 123

    def test_extract_metadata_no_tags(self) -> None:
        """Handle run with no tags."""
        run = MockRun(name="test", tags=None)

        metadata = extract_metadata(run)

        assert "tags" not in metadata

    def test_extract_metadata_empty_extra(self) -> None:
        """Handle run with empty extra."""
        run = MockRun(name="test", extra={})

        metadata = extract_metadata(run)

        assert metadata["name"] == "test"


class TestExtractStr:
    """Tests for extract_str helper function."""

    def test_extract_existing_field(self) -> None:
        """Extract and remove existing string field."""
        metadata = {"field1": "value1", "field2": "value2"}

        result = extract_str("field1", metadata)

        assert result == "value1"
        assert "field1" not in metadata
        assert "field2" in metadata

    def test_extract_missing_field(self) -> None:
        """Return None for missing field."""
        metadata = {"field2": "value2"}

        result = extract_str("field1", metadata)

        assert result is None

    def test_extract_non_string_converts(self) -> None:
        """Convert non-string value to string."""
        metadata = {"field1": 123}

        result = extract_str("field1", metadata)

        assert result == "123"


class TestExtractInt:
    """Tests for extract_int helper function."""

    def test_extract_int_field(self) -> None:
        """Extract and remove integer field."""
        metadata = {"count": 42}

        result = extract_int("count", metadata)

        assert result == 42
        assert "count" not in metadata

    def test_extract_float_as_int(self) -> None:
        """Convert float to int."""
        metadata = {"count": 3.7}

        result = extract_int("count", metadata)

        assert result == 3

    def test_extract_string_as_int(self) -> None:
        """Convert string number to int."""
        metadata = {"count": "42"}

        result = extract_int("count", metadata)

        assert result == 42

    def test_extract_invalid_returns_none(self) -> None:
        """Return None for non-numeric value."""
        metadata = {"count": "not a number"}

        result = extract_int("count", metadata)

        assert result is None


class TestExtractBool:
    """Tests for extract_bool helper function."""

    def test_extract_true(self) -> None:
        """Extract true value."""
        metadata = {"flag": True}

        result = extract_bool("flag", metadata)

        assert result is True
        assert "flag" not in metadata

    def test_extract_false(self) -> None:
        """Extract false value."""
        metadata = {"flag": False}

        result = extract_bool("flag", metadata)

        assert result is False

    def test_extract_truthy_value(self) -> None:
        """Convert truthy value to bool."""
        metadata = {"flag": "yes"}

        result = extract_bool("flag", metadata)

        assert result is True

    def test_extract_missing_returns_none(self) -> None:
        """Return None for missing field."""
        metadata: dict[str, Any] = {}

        result = extract_bool("flag", metadata)

        assert result is None


class TestExtractDict:
    """Tests for extract_dict helper function."""

    def test_extract_dict_field(self) -> None:
        """Extract and remove dict field."""
        metadata = {"config": {"key": "value"}}

        result = extract_dict("config", metadata)

        assert result == {"key": "value"}
        assert "config" not in metadata

    def test_extract_non_dict_returns_none(self) -> None:
        """Return None for non-dict value."""
        metadata = {"config": "not a dict"}

        result = extract_dict("config", metadata)

        assert result is None


class TestExtractJson:
    """Tests for extract_json helper function."""

    def test_extract_json_object_string(self) -> None:
        """Extract JSON object from string."""
        metadata = {"data": '{"key": "value"}'}

        result = extract_json("data", metadata)

        assert result == {"key": "value"}
        assert "data" not in metadata

    def test_extract_json_array_string(self) -> None:
        """Extract JSON array from string."""
        metadata = {"data": "[1, 2, 3]"}

        result = extract_json("data", metadata)

        assert result == [1, 2, 3]

    def test_extract_plain_string(self) -> None:
        """Return plain string as-is."""
        metadata = {"data": "just a string"}

        result = extract_json("data", metadata)

        assert result == "just a string"

    def test_extract_invalid_json(self) -> None:
        """Return original string for invalid JSON."""
        metadata = {"data": "{invalid json}"}

        result = extract_json("data", metadata)

        assert result == "{invalid json}"

    def test_extract_non_string_value(self) -> None:
        """Return non-string value as-is."""
        metadata = {"data": {"already": "parsed"}}

        result = extract_json("data", metadata)

        assert result == {"already": "parsed"}
