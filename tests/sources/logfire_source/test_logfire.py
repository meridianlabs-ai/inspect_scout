"""Integration tests for Logfire source.

These tests require:
- LOGFIRE_RUN_TESTS=1 (explicit opt-in)
- LOGFIRE_READ_TOKEN (for API access)

Run bootstrap.py first to create test traces in Logfire.
"""

from typing import Any

import pytest

from .conftest import skip_if_no_logfire


def _assert_logfire_transcript(
    transcript: Any,
    expected_name: str | None = None,
    model_pattern: str | None = None,
    min_model_events: int = 1,
    min_messages: int = 2,
) -> tuple[list[Any], dict[str, int]]:
    """Common assertions for Logfire transcript validation.

    Args:
        transcript: The transcript to validate
        expected_name: Expected span name (task_id)
        model_pattern: Substring expected in model name (e.g., "gpt", "claude")
        min_model_events: Minimum expected ModelEvents
        min_messages: Minimum expected total messages

    Returns:
        Tuple of (model_events, role_counts) for provider-specific assertions
    """
    from inspect_scout._transcript.types import Transcript
    from inspect_scout.sources._logfire.client import LOGFIRE_SOURCE_TYPE

    assert isinstance(transcript, Transcript)
    assert transcript.source_type == LOGFIRE_SOURCE_TYPE
    assert transcript.transcript_id is not None
    assert len(transcript.transcript_id) > 0

    # Verify task_id if specified
    if expected_name:
        assert transcript.task_id == expected_name, (
            f"Expected task_id {expected_name}, got {transcript.task_id}"
        )

    # Verify model if pattern specified
    if model_pattern and transcript.model:
        assert model_pattern in transcript.model.lower(), (
            f"Expected {model_pattern} model, got {transcript.model}"
        )

    # Verify source_uri is populated
    assert transcript.source_uri is not None, "Expected source_uri to be populated"
    assert "logfire" in transcript.source_uri.lower(), (
        f"Expected logfire URL in source_uri, got {transcript.source_uri}"
    )

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
# Basic Import Tests
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_import_basic() -> None:
    """Test basic Logfire import functionality."""
    from inspect_scout.sources import logfire

    count = 0
    async for transcript in logfire(limit=1):
        _assert_logfire_transcript(transcript, min_messages=1, min_model_events=1)
        count += 1

    # Should get at least one transcript (or zero if no data)
    assert count <= 1


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_import_with_filter() -> None:
    """Test Logfire import with SQL filter."""
    from inspect_scout.sources import logfire

    # Filter for chat operations only
    filter_sql = "attributes->>'gen_ai.operation.name' = 'chat'"

    count = 0
    async for transcript in logfire(filter=filter_sql, limit=5):
        _assert_logfire_transcript(transcript, min_messages=1, min_model_events=1)
        count += 1

    # Should get 0-5 transcripts
    assert count <= 5


# =============================================================================
# OpenAI Tests
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_openai_simple() -> None:
    """Test fetching simple OpenAI trace without tools."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-openai-simple-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-openai-simple-v2",
            model_pattern="gpt",
            min_model_events=1,
            min_messages=2,
        )

        # Simple trace should have user and assistant
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant message"
        return

    pytest.skip("No transcript found for scout-test-openai-simple-v2 - run bootstrap")


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_openai_tools() -> None:
    """Test fetching OpenAI trace with tool calls.

    This trace makes a weather request that triggers tool_calls, then returns
    the final response after receiving tool results.

    Expected conversation flow:
    1. User asks about weather
    2. Assistant responds with tool_call to get_weather
    3. Tool returns result
    4. Assistant provides final response
    """
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-openai-tools-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-openai-tools-v2",
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

    pytest.skip("No transcript found for scout-test-openai-tools-v2 - run bootstrap")


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_openai_multiturn() -> None:
    """Test fetching multi-turn OpenAI conversation trace."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-openai-multiturn-v2'",
        limit=1,
    ):
        _model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-openai-multiturn-v2",
            model_pattern="gpt",
            min_model_events=3,  # One per turn
            min_messages=6,  # 3 user + 3 assistant (system may be included)
        )

        # Multi-turn should have multiple user and assistant messages
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
        return

    pytest.skip(
        "No transcript found for scout-test-openai-multiturn-v2 - run bootstrap"
    )


# =============================================================================
# Anthropic Tests
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_anthropic_simple() -> None:
    """Test fetching simple Anthropic trace without tools."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-anthropic-simple-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-anthropic-simple-v2",
            model_pattern="claude",
            min_model_events=1,
            min_messages=2,
        )

        # Simple trace should have user and assistant
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant message"
        return

    pytest.skip(
        "No transcript found for scout-test-anthropic-simple-v2 - run bootstrap"
    )


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_anthropic_tools() -> None:
    """Test fetching Anthropic trace with tool calls.

    Anthropic uses tool_use content blocks which should be normalized to tool_calls.
    """
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-anthropic-tools-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-anthropic-tools-v2",
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

    pytest.skip("No transcript found for scout-test-anthropic-tools-v2 - run bootstrap")


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_anthropic_multiturn() -> None:
    """Test fetching multi-turn Anthropic conversation trace (no tools).

    Verifies a 3-turn conversation is properly captured.
    """
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-anthropic-multiturn-v2'",
        limit=1,
    ):
        _model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-anthropic-multiturn-v2",
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
        return

    pytest.skip(
        "No transcript found for scout-test-anthropic-multiturn-v2 - run bootstrap"
    )


# =============================================================================
# Pydantic AI Tests
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_simple() -> None:
    """Test fetching simple Pydantic AI agent trace."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-pydantic-ai-simple-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-pydantic-ai-simple-v2",
            model_pattern="gpt",
            min_model_events=1,
            min_messages=2,
        )

        # Simple agent trace should have user and assistant
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant message"
        return

    pytest.skip(
        "No transcript found for scout-test-pydantic-ai-simple-v2 - run bootstrap"
    )


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_tools() -> None:
    """Test fetching Pydantic AI agent trace with tool calls."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-pydantic-ai-tools-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-pydantic-ai-tools-v2",
            model_pattern="gpt",
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
        assert tc.function == "get_weather", f"Expected get_weather, got {tc.function}"
        assert isinstance(tc.arguments, dict), "Arguments should be dict"

        # Verify tool result exists
        tool_messages = [m for m in transcript.messages if m.role == "tool"]
        assert len(tool_messages) >= 1, "Expected tool result message"
        return

    pytest.skip(
        "No transcript found for scout-test-pydantic-ai-tools-v2 - run bootstrap"
    )


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_openai_multiturn() -> None:
    """Test Pydantic AI multi-turn conversation with OpenAI."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-pydantic-ai-openai-multiturn-v2'",
        limit=1,
    ):
        _model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-pydantic-ai-openai-multiturn-v2",
            model_pattern="gpt",
            min_model_events=3,
            min_messages=6,  # 3 user + 3 assistant
        )

        # Verify conversation structure
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
        "No transcript found for scout-test-pydantic-ai-openai-multiturn-v2 - run bootstrap"
    )


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_anthropic_multiturn() -> None:
    """Test Pydantic AI multi-turn conversation with Anthropic."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-pydantic-ai-anthropic-multiturn-v2'",
        limit=1,
    ):
        _model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-pydantic-ai-anthropic-multiturn-v2",
            model_pattern="claude",
            min_model_events=3,
            min_messages=6,  # 3 user + 3 assistant
        )

        # Verify conversation structure
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
        "No transcript found for scout-test-pydantic-ai-anthropic-multiturn-v2 - run bootstrap"
    )


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_google_multiturn() -> None:
    """Test Pydantic AI multi-turn conversation with Google."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-pydantic-ai-google-multiturn-v2'",
        limit=1,
    ):
        _model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-pydantic-ai-google-multiturn-v2",
            model_pattern="gemini",
            min_model_events=3,
            min_messages=6,  # 3 user + 3 assistant
        )

        # Verify conversation structure
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
        "No transcript found for scout-test-pydantic-ai-google-multiturn-v2 - run bootstrap"
    )


# =============================================================================
# Google GenAI Tests (Direct Instrumentation)
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_google_genai_simple() -> None:
    """Test fetching simple Google GenAI trace (direct instrumentation)."""
    from inspect_scout.sources import logfire

    async for transcript in logfire(
        filter="span_name = 'scout-test-google-genai-simple-v2'",
        limit=1,
    ):
        model_events, role_counts = _assert_logfire_transcript(
            transcript,
            expected_name="scout-test-google-genai-simple-v2",
            model_pattern="gemini",
            min_model_events=1,
            min_messages=2,
        )

        # Simple trace should have user and assistant
        assert "user" in role_counts, "Expected user message"
        assert "assistant" in role_counts, "Expected assistant message"
        return

    pytest.skip(
        "No transcript found for scout-test-google-genai-simple-v2 - run bootstrap"
    )


# =============================================================================
# Filtering Tests
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_limit_parameter() -> None:
    """Test that limit parameter restricts results."""
    from inspect_scout.sources import logfire

    transcripts = []
    async for t in logfire(limit=2):
        transcripts.append(t)

    assert len(transcripts) <= 2
