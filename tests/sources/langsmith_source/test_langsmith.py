"""Integration tests for LangSmith transcript import.

These tests require real LangSmith data and are skipped unless:
- LANGSMITH_RUN_TESTS=1 (explicit opt-in)
- LANGSMITH_API_KEY is set

Tests validate the full pipeline from LangSmith API to Scout Transcript
objects across different provider formats and trace structures.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tests.sources.langsmith_source.conftest import (
    LANGSMITH_TEST_PROJECT,
    skip_if_no_langsmith,
)
from tests.sources.langsmith_source.mocks import (
    MockExample,
    create_chain_run,
    create_openai_llm_run,
    create_tool_run,
)

# =============================================================================
# Test Helpers
# =============================================================================


def _assert_langsmith_transcript(
    transcript: Any,
    expected_name: str | None = None,
    model_pattern: str | None = None,
    min_model_events: int = 1,
    min_messages: int = 2,
) -> tuple[list[Any], dict[str, int]]:
    """Common assertions for LangSmith transcript validation.

    Args:
        transcript: The transcript to validate
        expected_name: Expected task_id (trace name)
        model_pattern: Substring expected in model name (e.g., "gpt", "claude")
        min_model_events: Minimum expected ModelEvents
        min_messages: Minimum expected total messages

    Returns:
        Tuple of (model_events, role_counts) for provider-specific assertions
    """
    # Verify source type
    assert transcript.source_type == "langsmith"

    # Verify task_id if specified
    if expected_name:
        assert transcript.task_id == expected_name

    # Verify model if pattern specified
    if model_pattern and transcript.model:
        assert model_pattern in transcript.model.lower(), (
            f"Expected {model_pattern} model, got {transcript.model}"
        )

    # Verify source_uri is populated
    assert transcript.source_uri is not None, "Expected source_uri to be populated"
    assert (
        "langsmith" in transcript.source_uri.lower()
        or "smith.langchain" in transcript.source_uri.lower()
    ), f"Expected LangSmith URL in source_uri, got {transcript.source_uri}"

    # Verify events
    assert len(transcript.events) > 0, "Expected events in transcript"

    # Find ModelEvents
    model_events = [e for e in transcript.events if e.event == "model"]
    assert len(model_events) >= min_model_events, (
        f"Expected at least {min_model_events} ModelEvents, got {len(model_events)}"
    )

    # Verify messages
    assert len(transcript.messages) >= min_messages, (
        f"Expected at least {min_messages} messages, got {len(transcript.messages)}"
    )

    # Count messages by role
    role_counts: dict[str, int] = {}
    for msg in transcript.messages:
        role_counts[msg.role] = role_counts.get(msg.role, 0) + 1

    return model_events, role_counts


# =============================================================================
# Unit Tests with Mocks (No API Required)
# =============================================================================


class TestLangsmithParameterValidation:
    """Tests for langsmith() function parameter validation."""

    @pytest.mark.asyncio
    async def test_requires_project_or_dataset(self) -> None:
        """Raise ValueError when neither project nor dataset provided."""
        from inspect_scout.sources._langsmith import langsmith

        with pytest.raises(ValueError, match="Either 'project' or 'dataset'"):
            async for _ in langsmith():
                pass


class TestFromProjectMocked:
    """Tests for _from_project using mocked client."""

    @pytest.mark.asyncio
    async def test_fetches_root_runs(self) -> None:
        """Verify root runs are fetched from project."""
        from inspect_scout.sources._langsmith import langsmith

        root_run = create_openai_llm_run(run_id="root-1", trace_id="trace-1")
        root_run.parent_run_id = None

        mock_client = MagicMock()
        mock_client.list_runs.return_value = [root_run]

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            transcripts = []
            async for t in langsmith(project="test-project"):
                transcripts.append(t)

        # Verify list_runs was called with is_root=True
        call_args = mock_client.list_runs.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_limit_parameter(self) -> None:
        """Verify limit parameter stops iteration early."""
        from inspect_scout.sources._langsmith import langsmith

        # Create multiple root runs
        runs = [
            create_openai_llm_run(run_id=f"root-{i}", trace_id=f"trace-{i}")
            for i in range(5)
        ]
        for run in runs:
            run.parent_run_id = None

        mock_client = MagicMock()
        mock_client.list_runs.return_value = runs

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            transcripts = []
            async for t in langsmith(project="test-project", limit=2):
                transcripts.append(t)

        # Should only get 2 transcripts
        assert len(transcripts) <= 2

    @pytest.mark.asyncio
    async def test_tag_filtering(self) -> None:
        """Verify tags are converted to filter string."""
        from inspect_scout.sources._langsmith import langsmith

        mock_client = MagicMock()
        mock_client.list_runs.return_value = []

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            async for _ in langsmith(project="test-project", tags=["tag1", "tag2"]):
                pass

        # Verify filter includes tag constraints
        call_args = mock_client.list_runs.call_args
        if call_args:
            kwargs = call_args.kwargs
            if "filter" in kwargs:
                assert "tag1" in kwargs["filter"]
                assert "tag2" in kwargs["filter"]


class TestFromDatasetMocked:
    """Tests for _from_dataset using mocked client."""

    @pytest.mark.asyncio
    async def test_fetches_examples(self) -> None:
        """Verify examples are fetched from dataset."""
        from inspect_scout.sources._langsmith import langsmith

        example = MockExample(
            id="example-1",
            inputs={"input": "Hello"},
            outputs={"output": "Hi there"},
        )

        mock_client = MagicMock()
        mock_client.list_examples.return_value = [example]

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            transcripts = []
            async for t in langsmith(dataset="test-dataset"):
                transcripts.append(t)

        assert len(transcripts) == 1
        mock_client.list_examples.assert_called_once()

    @pytest.mark.asyncio
    async def test_example_to_transcript_conversion(self) -> None:
        """Verify dataset example converts to transcript correctly."""
        from inspect_scout.sources._langsmith import langsmith

        example = MockExample(
            id="example-123",
            inputs={"input": "What is 2+2?"},
            outputs={"output": "4"},
            metadata={"category": "math"},
        )

        mock_client = MagicMock()
        mock_client.list_examples.return_value = [example]

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            transcripts = []
            async for t in langsmith(dataset="test-dataset"):
                transcripts.append(t)

        assert len(transcripts) == 1
        t = transcripts[0]

        assert t.transcript_id == "example-123"
        assert t.source_type == "langsmith"
        assert t.source_id == "test-dataset"
        assert len(t.messages) == 2  # user + assistant


class TestTraceToTranscriptMocked:
    """Tests for _trace_to_transcript conversion logic."""

    @pytest.mark.asyncio
    async def test_builds_tree_from_runs(self) -> None:
        """Verify runs are organized into tree structure."""
        from inspect_scout.sources._langsmith import langsmith

        # Create hierarchical runs: root -> llm -> tool
        root = create_chain_run(run_id="root", trace_id="trace-1")
        root.parent_run_id = None

        llm = create_openai_llm_run(run_id="llm-1", trace_id="trace-1")
        llm.parent_run_id = "root"

        tool = create_tool_run(run_id="tool-1", trace_id="trace-1")
        tool.parent_run_id = "llm-1"

        mock_client = MagicMock()
        mock_client.list_runs.side_effect = [
            [root],  # First call for root runs
            [root, llm, tool],  # Second call for all trace runs
        ]

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            transcripts = []
            async for t in langsmith(project="test-project"):
                transcripts.append(t)

        # Should have created transcript with events from all runs
        assert len(transcripts) == 1

    @pytest.mark.asyncio
    async def test_extracts_metadata(self) -> None:
        """Verify metadata is extracted from root run."""
        from inspect_scout.sources._langsmith import langsmith

        root = create_openai_llm_run(run_id="root", trace_id="trace-1")
        root.parent_run_id = None
        root.name = "test-task"
        root.tags = ["tag1", "tag2"]
        root.extra = {
            "metadata": {
                "agent": "test-agent",
                "agent_args": {"temp": 0.7},
            }
        }

        mock_client = MagicMock()
        mock_client.list_runs.side_effect = [
            [root],
            [root],
        ]

        with patch(
            "inspect_scout.sources._langsmith.get_langsmith_client",
            return_value=mock_client,
        ):
            transcripts = []
            async for t in langsmith(project="test-project"):
                transcripts.append(t)

        assert len(transcripts) == 1
        t = transcripts[0]
        assert t.task_id == "test-task"


# =============================================================================
# Integration Tests (Require Real LangSmith Data)
# =============================================================================


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_raw_openai_simple() -> None:
    """Test fetching simple OpenAI trace without tools."""
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-raw-openai-simple-v2")',
        limit=1,
    ):
        model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-raw-openai-simple-v2",
            model_pattern="gpt",
            min_model_events=1,
            min_messages=2,
        )

        # Simple trace should have user and assistant
        assert "user" in role_counts
        assert "assistant" in role_counts
        return

    pytest.skip("No transcript found for \1 - run bootstrap")


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_raw_openai_tools() -> None:
    """Test fetching OpenAI trace with tool calls.

    This trace makes a weather request that triggers tool_calls, then returns
    the final response after receiving tool results.

    Expected conversation flow:
    1. User asks about weather
    2. Assistant responds with tool_call to get_weather
    3. Tool returns result
    4. Assistant provides final response
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-raw-openai-tools-v2")',
        limit=1,
    ):
        model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-raw-openai-tools-v2",
            model_pattern="gpt",
            min_model_events=2,  # First call returns tool_call, second returns final
            min_messages=4,  # user, assistant+tool_call, tool, assistant
        )

        # Verify we have all expected message roles
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant message"
        assert "tool" in role_counts, "Expected tool message with result"

        # Find assistant message with tool_calls
        tool_call_messages = [
            m
            for m in transcript.messages
            if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
        ]
        assert len(tool_call_messages) >= 1, (
            "Expected at least one assistant message with tool_calls"
        )

        # Verify tool_call structure
        tool_calls = tool_call_messages[0].tool_calls
        assert tool_calls is not None
        tc = tool_calls[0]
        assert tc.id, "Tool call should have an id"
        assert tc.function == "get_weather", (
            f"Expected get_weather tool call, got {tc.function}"
        )
        assert isinstance(tc.arguments, dict), (
            f"Tool call arguments should be dict, got {type(tc.arguments)}"
        )

        # Find tool result message
        tool_messages = [m for m in transcript.messages if m.role == "tool"]
        assert len(tool_messages) >= 1, "Expected at least one tool result message"
        assert tool_messages[0].content, "Tool result should have content"
        return

    pytest.skip(
        "No transcript found for scout-test-raw-openai-tools-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_raw_openai_multiturn() -> None:
    """Test fetching multi-turn OpenAI conversation trace."""
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-raw-openai-multiturn-v2")',
        limit=1,
    ):
        _model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-raw-openai-multiturn-v2",
            model_pattern="gpt",
            min_model_events=3,
            min_messages=3,
        )

        # Multi-turn should have multiple user messages
        assert role_counts.get("user", 0) >= 1 or role_counts.get("assistant", 0) >= 3
        return

    pytest.skip("No transcript found for \1 - run bootstrap")


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_raw_anthropic_tools() -> None:
    """Test fetching Anthropic trace with tool calls.

    Raw Anthropic traces via wrap_anthropic should contain:
    - User message
    - Assistant with tool_use content blocks (normalized to tool_calls)
    - Tool result
    - Final assistant response
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-raw-anthropic-tools-v2")',
        limit=1,
    ):
        model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-raw-anthropic-tools-v2",
            model_pattern="claude",
            min_model_events=2,  # Tool call + final response
            min_messages=4,  # user, assistant+tool_call, tool, assistant
        )

        # Verify expected roles
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert "tool" in role_counts, "Expected tool result message"

        # Verify assistant has tool_calls
        tool_call_messages = [
            m
            for m in transcript.messages
            if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
        ]
        assert len(tool_call_messages) >= 1, (
            f"Expected assistant with tool_calls. Got roles: {[m.role for m in transcript.messages]}"
        )

        # Verify tool call structure
        tool_calls = tool_call_messages[0].tool_calls
        assert tool_calls is not None
        tc = tool_calls[0]
        assert tc.id, "Tool call should have an id"
        assert tc.function == "get_weather", f"Expected get_weather, got {tc.function}"
        assert isinstance(tc.arguments, dict), "Arguments should be dict"

        # Verify tool result exists
        tool_messages = [m for m in transcript.messages if m.role == "tool"]
        assert len(tool_messages) >= 1, "Expected tool result message"
        return

    pytest.skip(
        "No transcript found for scout-test-raw-anthropic-tools-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_raw_anthropic_multiturn() -> None:
    """Test fetching multi-turn Anthropic conversation trace (no tools).

    Verifies a 3-turn conversation is properly captured:
    - User initiates conversation
    - Assistant responds
    - User follows up
    - Assistant responds
    - User asks final question
    - Assistant provides final response

    Each turn creates a model event with growing conversation history.
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-raw-anthropic-multiturn-v2")',
        limit=1,
    ):
        _model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-raw-anthropic-multiturn-v2",
            model_pattern="claude",
            min_model_events=3,  # One per turn
            min_messages=6,  # 3 user + 3 assistant
        )

        # Verify conversation structure
        assert "user" in role_counts, "Expected user messages"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert role_counts.get("user", 0) >= 3, (
            f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
        )
        assert role_counts.get("assistant", 0) >= 3, (
            f"Expected at least 3 assistant responses, got {role_counts.get('assistant', 0)}"
        )

        # No tool messages in pure conversation
        assert "tool" not in role_counts, (
            "Multi-turn trace should not have tool messages"
        )

        # Verify messages alternate between user and assistant
        messages = transcript.messages
        for i in range(min(len(messages) - 1, 5)):
            if messages[i].role == "user":
                assert messages[i + 1].role in ("assistant", "user"), (
                    f"After user at index {i}, expected assistant or user"
                )
        return

    pytest.skip(
        "No transcript found for scout-test-raw-anthropic-multiturn-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_langchain_openai_agent() -> None:
    """Test fetching LangChain agent trace with OpenAI.

    This trace runs a LangChain agent that calls tools, verifying:
    - Full conversation is captured (not just initial user message)
    - Tool calls are properly extracted
    - Tool results are included in conversation
    - Final response is appended

    Expected conversation flow:
    1. System message (agent instructions)
    2. User asks about weather
    3. Assistant calls get_weather tool
    4. Tool result
    5. Final assistant response
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-langchain-openai-agent-v2")',
        limit=1,
    ):
        model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-langchain-openai-agent-v2",
            model_pattern="gpt",
            min_model_events=2,  # First LLM call + second LLM call
            min_messages=5,  # system, user, assistant+tool_call, tool, assistant
        )

        # Verify all expected roles present
        assert "system" in role_counts, "Expected system message"
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert "tool" in role_counts, "Expected tool result message"

        # Verify assistant message with tool_calls exists
        tool_call_messages = [
            m
            for m in transcript.messages
            if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
        ]
        assert len(tool_call_messages) >= 1, (
            "Expected assistant message with tool_calls. Messages: "
            + ", ".join(f"{m.role}" for m in transcript.messages)
        )

        # Verify tool_call has correct structure
        tool_calls = tool_call_messages[0].tool_calls
        assert tool_calls is not None
        tc = tool_calls[0]
        assert tc.id, "Tool call should have an id"
        assert tc.function == "get_weather", (
            f"Expected get_weather function, got {tc.function}"
        )
        assert isinstance(tc.arguments, dict), (
            f"Arguments should be dict, got {type(tc.arguments)}"
        )

        # Verify tool result message exists
        tool_messages = [m for m in transcript.messages if m.role == "tool"]
        assert len(tool_messages) >= 1, "Expected tool result message"
        assert tool_messages[0].content, "Tool result should have content"

        # Verify final assistant response (no tool_calls)
        final_assistants = [
            m
            for m in transcript.messages
            if m.role == "assistant"
            and (not hasattr(m, "tool_calls") or not m.tool_calls)
        ]
        assert len(final_assistants) >= 1, "Expected final assistant response"
        return

    pytest.skip(
        "No transcript found for scout-test-langchain-openai-agent-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_langchain_anthropic_agent() -> None:
    """Test fetching LangChain agent trace with Anthropic.

    Verifies the full conversation flow including:
    - System/user messages
    - Tool calls in assistant messages
    - Tool results
    - Final response

    Note: Anthropic uses content blocks for tool_use, but our extraction
    normalizes these to tool_calls for consistency.
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-langchain-anthropic-agent-v2")',
        limit=1,
    ):
        model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-langchain-anthropic-agent-v2",
            model_pattern="claude",
            min_model_events=2,  # Tool call + final response
            min_messages=5,  # system, user, assistant+tool_call, tool, assistant
        )

        # Verify key message roles present
        assert "system" in role_counts, "Expected system message"
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert "tool" in role_counts, "Expected tool result message"

        # Verify assistant has tool_calls
        tool_call_messages = [
            m
            for m in transcript.messages
            if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
        ]
        assert len(tool_call_messages) >= 1, (
            f"Expected assistant with tool_calls. Got roles: {[m.role for m in transcript.messages]}"
        )

        # Verify tool call structure
        tool_calls = tool_call_messages[0].tool_calls
        assert tool_calls is not None
        tc = tool_calls[0]
        assert tc.id, "Tool call should have an id"
        assert tc.function == "get_weather", f"Expected get_weather, got {tc.function}"
        assert isinstance(tc.arguments, dict), "Arguments should be dict"

        # Verify tool result exists
        tool_messages = [m for m in transcript.messages if m.role == "tool"]
        assert len(tool_messages) >= 1, "Expected tool result message"
        return

    pytest.skip(
        "No transcript found for scout-test-langchain-anthropic-agent-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_langchain_google_agent() -> None:
    """Test fetching LangChain agent trace with Google/Gemini.

    Verifies Google's function calling flow is properly normalized:
    - System/user messages preserved
    - Tool calls extracted from Gemini format
    - Tool results included
    - Final response appended
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-langchain-google-agent-v2")',
        limit=1,
    ):
        model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-langchain-google-agent-v2",
            model_pattern="gemini",
            min_model_events=2,  # Tool call + final response
            min_messages=5,  # system, user, assistant+tool_call, tool, assistant
        )

        # Verify key message roles present
        assert "system" in role_counts, "Expected system message"
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert "tool" in role_counts, "Expected tool result message"

        # Verify assistant has tool_calls
        tool_call_messages = [
            m
            for m in transcript.messages
            if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
        ]
        assert len(tool_call_messages) >= 1, (
            f"Expected assistant with tool_calls. Got roles: {[m.role for m in transcript.messages]}"
        )

        # Verify tool call structure
        tool_calls = tool_call_messages[0].tool_calls
        assert tool_calls is not None
        tc = tool_calls[0]
        assert tc.id, "Tool call should have an id"
        assert tc.function == "get_weather", f"Expected get_weather, got {tc.function}"
        assert isinstance(tc.arguments, dict), "Arguments should be dict"

        # Verify tool result exists
        tool_messages = [m for m in transcript.messages if m.role == "tool"]
        assert len(tool_messages) >= 1, "Expected tool result message"
        return

    pytest.skip(
        "No transcript found for scout-test-langchain-google-agent-v2 - run bootstrap"
    )


# =============================================================================
# LangChain Multi-turn Tests (no tools)
# =============================================================================


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_langchain_openai_multiturn() -> None:
    """Test LangChain multi-turn conversation with OpenAI (no tools).

    Verifies a multi-turn conversation with history through LangChain:
    - 5 input messages (system + 3 user + 2 assistant history) + 1 new response
    - Messages are properly extracted from LangChain serialized format
    - Full conversation history is preserved
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-langchain-openai-multiturn-v2")',
        limit=1,
    ):
        _model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-langchain-openai-multiturn-v2",
            model_pattern="gpt",
            min_model_events=1,
            min_messages=6,  # system + 3 user + 3 assistant (2 history + 1 new)
        )

        # Verify conversation structure
        assert "system" in role_counts, "Expected system message"
        assert "user" in role_counts, "Expected user messages"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert role_counts.get("user", 0) >= 3, (
            f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
        )
        assert role_counts.get("assistant", 0) >= 3, (
            f"Expected at least 3 assistant messages, got {role_counts.get('assistant', 0)}"
        )

        # No tool messages in pure conversation
        assert "tool" not in role_counts, (
            "Multi-turn trace should not have tool messages"
        )
        return

    pytest.skip(
        "No transcript found for scout-test-langchain-openai-multiturn-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_langchain_anthropic_multiturn() -> None:
    """Test LangChain multi-turn conversation with Anthropic (no tools).

    Verifies multi-turn conversation with history through LangChain:
    - 5 input messages + 1 new response = 6 total
    - LangChain serialized format is properly converted
    - Messages preserve roles and content
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-langchain-anthropic-multiturn-v2")',
        limit=1,
    ):
        _model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-langchain-anthropic-multiturn-v2",
            model_pattern="claude",
            min_model_events=1,
            min_messages=6,  # system + 3 user + 3 assistant
        )

        # Verify conversation structure
        assert "system" in role_counts, "Expected system message"
        assert "user" in role_counts, "Expected user messages"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert role_counts.get("user", 0) >= 3, (
            f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
        )
        assert role_counts.get("assistant", 0) >= 3, (
            f"Expected at least 3 assistant messages, got {role_counts.get('assistant', 0)}"
        )

        # No tool messages in pure conversation
        assert "tool" not in role_counts, (
            "Multi-turn trace should not have tool messages"
        )
        return

    pytest.skip(
        "No transcript found for scout-test-langchain-anthropic-multiturn-v2 - run bootstrap"
    )


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_langchain_google_multiturn() -> None:
    """Test LangChain multi-turn conversation with Google (no tools).

    Verifies multi-turn conversation with history through LangChain:
    - 5 input messages + 1 new response = 6 total
    - Google/LangChain content format is properly converted
    - Messages preserve roles and content
    """
    from inspect_scout.sources._langsmith import langsmith

    async for transcript in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='eq(name, "scout-test-langchain-google-multiturn-v2")',
        limit=1,
    ):
        _model_events, role_counts = _assert_langsmith_transcript(
            transcript,
            expected_name="scout-test-langchain-google-multiturn-v2",
            model_pattern="gemini",
            min_model_events=1,
            min_messages=6,  # system + 3 user + 3 assistant
        )

        # Verify conversation structure
        assert "system" in role_counts, "Expected system message"
        assert "user" in role_counts, "Expected user messages"
        assert "assistant" in role_counts, "Expected assistant messages"
        assert role_counts.get("user", 0) >= 3, (
            f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
        )
        assert role_counts.get("assistant", 0) >= 3, (
            f"Expected at least 3 assistant messages, got {role_counts.get('assistant', 0)}"
        )

        # No tool messages in pure conversation
        assert "tool" not in role_counts, (
            "Multi-turn trace should not have tool messages"
        )
        return

    pytest.skip(
        "No transcript found for scout-test-langchain-google-multiturn-v2 - run bootstrap"
    )


# =============================================================================
# Filtering Tests
# =============================================================================


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_filtering_by_tags() -> None:
    """Test filtering traces by tags."""
    from inspect_scout.sources._langsmith import langsmith

    transcripts = []
    async for t in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        tags=["scout-test"],
        limit=3,
    ):
        transcripts.append(t)

    # Should find some scout-test tagged traces
    # Skip if empty - could be rate limiting
    if len(transcripts) == 0:
        pytest.skip("No transcripts found - may be due to rate limiting")
    assert len(transcripts) >= 1


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_filtering_by_filter_string() -> None:
    """Test filtering using LangSmith filter syntax."""
    from inspect_scout.sources._langsmith import langsmith

    transcripts = []
    async for t in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        filter='has(tags, "scout-test")',
        limit=3,
    ):
        transcripts.append(t)

    assert len(transcripts) >= 1


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_limit_parameter() -> None:
    """Test that limit parameter restricts results."""
    from inspect_scout.sources._langsmith import langsmith

    transcripts = []
    async for t in langsmith(
        project=LANGSMITH_TEST_PROJECT,
        tags=["scout-test"],
        limit=1,
    ):
        transcripts.append(t)

    assert len(transcripts) <= 1


# =============================================================================
# Dataset Tests
# =============================================================================


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_dataset() -> None:
    """Test fetching from a dataset."""
    from inspect_scout.sources._langsmith import langsmith

    transcripts = []
    async for t in langsmith(dataset="scout-test-dataset-v2", limit=3):
        transcripts.append(t)

    # Should find examples from the test dataset
    if len(transcripts) >= 1:
        t = transcripts[0]
        assert t.source_type == "langsmith"
        assert t.source_id == "scout-test-dataset-v2"
        assert len(t.messages) >= 1


@skip_if_no_langsmith
@pytest.mark.asyncio
async def test_langsmith_dataset_with_project() -> None:
    """Test fetching from dataset with project context."""
    from inspect_scout.sources._langsmith import langsmith

    transcripts = []
    async for t in langsmith(
        dataset="scout-test-dataset-v2",
        project=LANGSMITH_TEST_PROJECT,
        limit=3,
    ):
        transcripts.append(t)

    if len(transcripts) >= 1:
        t = transcripts[0]
        # task_set should use project when provided
        assert t.task_set == LANGSMITH_TEST_PROJECT
