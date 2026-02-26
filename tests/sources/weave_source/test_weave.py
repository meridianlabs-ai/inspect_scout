"""Integration tests for W&B Weave transcript import.

These tests require real Weave data and are skipped unless:
- WEAVE_RUN_TESTS=1 (explicit opt-in)
- WANDB_API_KEY is set

Tests validate the full pipeline from Weave API to Scout Transcript
objects across different provider formats and trace structures.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tests.sources.weave_source.conftest import (
    WEAVE_TEST_PROJECT,
    skip_if_no_weave,
)
from tests.sources.weave_source.mocks import (
    create_anthropic_llm_call,
    create_openai_llm_call,
    create_openai_llm_call_with_tools,
    create_span_call,
    create_tool_call,
    create_trace_with_tool_calls,
)

# =============================================================================
# Test Helpers
# =============================================================================


def _assert_weave_transcript(
    transcript: Any,
    expected_name: str | None = None,
    model_pattern: str | None = None,
    min_model_events: int = 1,
    min_messages: int = 2,
) -> tuple[list[Any], dict[str, int]]:
    """Common assertions for Weave transcript validation.

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
    assert transcript.source_type == "weave"

    # Verify task_id if specified
    if expected_name:
        assert expected_name in (transcript.task_id or ""), (
            f"Expected {expected_name} in task_id, got {transcript.task_id}"
        )

    # Verify model if pattern specified
    if model_pattern and transcript.model:
        assert model_pattern in transcript.model.lower(), (
            f"Expected {model_pattern} model, got {transcript.model}"
        )

    # Verify source_uri is populated
    assert transcript.source_uri is not None, "Expected source_uri to be populated"
    assert "wandb" in transcript.source_uri.lower(), (
        f"Expected W&B URL in source_uri, got {transcript.source_uri}"
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
# Unit Tests with Mocks (No API Required)
# =============================================================================


class TestWeaveParameterValidation:
    """Tests for weave() function parameter validation."""

    @pytest.mark.asyncio
    async def test_requires_project(self) -> None:
        """Raise ValueError when project not provided."""
        from inspect_scout.sources._weave import weave

        with pytest.raises(ValueError, match="'project' must be provided"):
            async for _ in weave(project=""):
                pass


class TestTreeBuilding:
    """Tests for call tree building."""

    def test_builds_tree_from_flat_calls(self) -> None:
        """Verify flat calls are organized into tree structure."""
        from inspect_scout.sources._weave.tree import build_call_tree

        calls = create_trace_with_tool_calls()
        tree = build_call_tree(calls)

        # Should have one root
        assert len(tree) == 1
        root = tree[0]

        # Root should have children
        assert len(root.children) > 0

    def test_flatten_tree_chronological(self) -> None:
        """Verify tree flattening preserves chronological order."""
        from inspect_scout.sources._weave.tree import (
            build_call_tree,
            flatten_tree_chronological,
        )

        calls = create_trace_with_tool_calls()
        tree = build_call_tree(calls)
        flattened = flatten_tree_chronological(tree)

        # Should return all calls
        assert len(flattened) == len(calls)

        # Should be in chronological order
        for i in range(len(flattened) - 1):
            t1 = getattr(flattened[i], "started_at", None)
            t2 = getattr(flattened[i + 1], "started_at", None)
            if t1 and t2:
                assert t1 <= t2, "Calls should be in chronological order"


class TestDetection:
    """Tests for provider format detection."""

    def test_detect_openai_from_op_name(self) -> None:
        """Detect OpenAI format from op_name."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = create_openai_llm_call()
        format_type = detect_provider_format(call)
        assert format_type == "openai"

    def test_detect_anthropic_from_op_name(self) -> None:
        """Detect Anthropic format from op_name."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = create_anthropic_llm_call()
        format_type = detect_provider_format(call)
        assert format_type == "anthropic"

    def test_detect_from_model_name(self) -> None:
        """Detect format from model name when op_name is generic."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = create_span_call(name="llm_call")
        call.inputs = {"model": "gpt-4", "messages": []}
        format_type = detect_provider_format(call)
        assert format_type == "openai"

    def test_get_model_name(self) -> None:
        """Extract model name from call."""
        from inspect_scout.sources._weave.detection import get_model_name

        call = create_openai_llm_call()
        model = get_model_name(call)
        assert "gpt" in model.lower()


class TestEvents:
    """Tests for event conversion."""

    @pytest.mark.asyncio
    async def test_llm_call_to_model_event(self) -> None:
        """Convert LLM call to ModelEvent."""
        from inspect_scout.sources._weave.events import to_model_event

        call = create_openai_llm_call()
        event = await to_model_event(call)

        assert event.event == "model"
        assert event.model is not None
        assert len(event.input) > 0

    def test_tool_call_to_tool_event(self) -> None:
        """Convert tool call to ToolEvent."""
        from inspect_scout.sources._weave.events import to_tool_event

        call = create_tool_call()
        event = to_tool_event(call)

        assert event.event == "tool"
        assert event.function is not None

    def test_span_call_to_span_events(self) -> None:
        """Convert span call to SpanBeginEvent and SpanEndEvent."""
        from inspect_scout.sources._weave.events import (
            to_span_begin_event,
            to_span_end_event,
        )

        call = create_span_call()
        begin_event = to_span_begin_event(call)
        end_event = to_span_end_event(call)

        assert begin_event.event == "span_begin"
        assert end_event.event == "span_end"
        assert begin_event.id == end_event.id

    @pytest.mark.asyncio
    async def test_calls_to_events(self) -> None:
        """Convert list of calls to events."""
        from inspect_scout.sources._weave.events import calls_to_events

        calls = create_trace_with_tool_calls()
        events = await calls_to_events(calls)

        # Should have multiple events
        assert len(events) > 0

        # Should include model events
        model_events = [e for e in events if e.event == "model"]
        assert len(model_events) >= 1


class TestExtraction:
    """Tests for input/output extraction."""

    @pytest.mark.asyncio
    async def test_extract_openai_input_messages(self) -> None:
        """Extract messages from OpenAI format inputs."""
        from inspect_scout.sources._weave.extraction import extract_input_messages

        inputs = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello!"},
            ]
        }

        messages = await extract_input_messages(inputs, "openai")
        assert len(messages) >= 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    def test_extract_usage(self) -> None:
        """Extract usage from call."""
        from inspect_scout.sources._weave.extraction import extract_usage

        call = create_openai_llm_call()
        usage = extract_usage(call)

        assert usage is not None
        assert usage.total_tokens > 0

    def test_extract_tools(self) -> None:
        """Extract tool definitions from call."""
        from inspect_scout.sources._weave.extraction import extract_tools

        call = create_openai_llm_call_with_tools()
        tools = extract_tools(call)

        assert len(tools) >= 1
        assert tools[0].name == "get_weather"


class TestFromProjectMocked:
    """Tests for weave() using mocked client."""

    @pytest.mark.asyncio
    async def test_fetches_calls(self) -> None:
        """Verify calls are fetched from project."""
        calls = create_trace_with_tool_calls()

        # Mock the weave module and its components
        mock_client = MagicMock()
        mock_client.get_calls.return_value = iter(calls)

        mock_weave_module = MagicMock()
        mock_weave_module.init.return_value = mock_client

        mock_calls_filter = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "weave": mock_weave_module,
                "weave.trace.weave_client": MagicMock(),
                "weave.trace_server.trace_server_interface": MagicMock(
                    CallsFilter=mock_calls_filter
                ),
            },
        ):
            # Re-import to get the mocked version
            import importlib

            import inspect_scout.sources._weave as weave_module

            importlib.reload(weave_module)

            transcripts = []
            async for t in weave_module.weave(project="test/project"):
                transcripts.append(t)

        # Should have created transcript
        assert len(transcripts) >= 1

    @pytest.mark.asyncio
    async def test_limit_parameter(self) -> None:
        """Verify limit parameter stops iteration early."""
        # Create multiple traces
        all_calls = []
        for i in range(5):
            calls = create_trace_with_tool_calls()
            # Give each trace a unique id
            for call in calls:
                if not getattr(call, "parent_id", None):
                    call.id = f"root-{i}"
                    call.trace_id = f"root-{i}"
                else:
                    call.trace_id = f"root-{i}"
            all_calls.extend(calls)

        mock_client = MagicMock()
        mock_client.get_calls.return_value = iter(all_calls)

        mock_weave_module = MagicMock()
        mock_weave_module.init.return_value = mock_client

        mock_calls_filter = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "weave": mock_weave_module,
                "weave.trace.weave_client": MagicMock(),
                "weave.trace_server.trace_server_interface": MagicMock(
                    CallsFilter=mock_calls_filter
                ),
            },
        ):
            import importlib

            import inspect_scout.sources._weave as weave_module

            importlib.reload(weave_module)

            transcripts = []
            async for t in weave_module.weave(project="test/project", limit=2):
                transcripts.append(t)

        # Should only get 2 transcripts
        assert len(transcripts) <= 2


# =============================================================================
# Integration Tests (Require Real Weave Data)
# =============================================================================


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_openai_simple() -> None:
    """Test fetching simple OpenAI trace without tools."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        # Look for our test trace
        if transcript.task_id and "scout-test-openai-simple" in transcript.task_id:
            model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-openai-simple",
                model_pattern="gpt",
                min_model_events=1,
                min_messages=2,
            )

            # Simple trace should have user and assistant
            assert "user" in role_counts
            assert "assistant" in role_counts
            return

    pytest.skip("No transcript found for scout-test-openai-simple - run bootstrap")


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_openai_tools() -> None:
    """Test fetching OpenAI trace with tool calls."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if transcript.task_id and "scout-test-openai-tools" in transcript.task_id:
            model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-openai-tools",
                model_pattern="gpt",
                min_model_events=2,
                min_messages=4,
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
            return

    pytest.skip("No transcript found for scout-test-openai-tools - run bootstrap")


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_openai_multiturn() -> None:
    """Test fetching multi-turn OpenAI conversation trace."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if transcript.task_id and "scout-test-openai-multiturn" in transcript.task_id:
            if "tools" in transcript.task_id:
                continue  # Skip the tools variant

            _model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-openai-multiturn",
                model_pattern="gpt",
                min_model_events=3,
                min_messages=3,
            )

            # Multi-turn should have multiple user/assistant exchanges
            assert (
                role_counts.get("user", 0) >= 1 or role_counts.get("assistant", 0) >= 3
            )
            return

    pytest.skip("No transcript found for scout-test-openai-multiturn - run bootstrap")


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_openai_multiturn_tools() -> None:
    """Test fetching multi-turn OpenAI trace with tool calls across turns."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if (
            transcript.task_id
            and "scout-test-openai-multiturn-tools" in transcript.task_id
        ):
            model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-openai-multiturn-tools",
                model_pattern="gpt",
                min_model_events=4,
                min_messages=8,
            )

            # Verify expected roles
            assert "user" in role_counts, "Expected user messages"
            assert "assistant" in role_counts, "Expected assistant messages"
            assert "tool" in role_counts, "Expected tool result messages"

            # Multiple user messages (3 turns)
            assert role_counts.get("user", 0) >= 3, (
                f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
            )
            return

    pytest.skip(
        "No transcript found for scout-test-openai-multiturn-tools - run bootstrap"
    )


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_anthropic_simple() -> None:
    """Test fetching simple Anthropic trace without tools."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if transcript.task_id and "scout-test-anthropic-simple" in transcript.task_id:
            model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-anthropic-simple",
                model_pattern="claude",
                min_model_events=1,
                min_messages=2,
            )

            assert "user" in role_counts
            assert "assistant" in role_counts
            return

    pytest.skip("No transcript found for scout-test-anthropic-simple - run bootstrap")


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_anthropic_tools() -> None:
    """Test fetching Anthropic trace with tool calls."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if transcript.task_id and "scout-test-anthropic-tools" in transcript.task_id:
            model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-anthropic-tools",
                model_pattern="claude",
                min_model_events=2,
                min_messages=4,
            )

            # Verify expected roles
            assert "user" in role_counts, "Expected user message"
            assert "assistant" in role_counts, "Expected assistant messages"
            assert "tool" in role_counts, "Expected tool result message"
            return

    pytest.skip("No transcript found for scout-test-anthropic-tools - run bootstrap")


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_anthropic_multiturn() -> None:
    """Test fetching multi-turn Anthropic conversation trace."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if (
            transcript.task_id
            and "scout-test-anthropic-multiturn" in transcript.task_id
        ):
            if "tools" in transcript.task_id:
                continue  # Skip the tools variant

            _model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-anthropic-multiturn",
                model_pattern="claude",
                min_model_events=3,
                min_messages=6,
            )

            # Verify conversation structure
            assert "user" in role_counts, "Expected user messages"
            assert "assistant" in role_counts, "Expected assistant messages"
            assert role_counts.get("user", 0) >= 3, (
                f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
            )
            return

    pytest.skip(
        "No transcript found for scout-test-anthropic-multiturn - run bootstrap"
    )


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_anthropic_multiturn_tools() -> None:
    """Test fetching multi-turn Anthropic trace with tool calls across turns."""
    from inspect_scout.sources._weave import weave

    async for transcript in weave(
        project=WEAVE_TEST_PROJECT,
        limit=10,
    ):
        if (
            transcript.task_id
            and "scout-test-anthropic-multiturn-tools" in transcript.task_id
        ):
            model_events, role_counts = _assert_weave_transcript(
                transcript,
                expected_name="scout-test-anthropic-multiturn-tools",
                model_pattern="claude",
                min_model_events=4,
                min_messages=8,
            )

            # Verify expected roles
            assert "user" in role_counts, "Expected user messages"
            assert "assistant" in role_counts, "Expected assistant messages"
            assert "tool" in role_counts, "Expected tool result messages"

            # Multiple user messages (3 turns)
            assert role_counts.get("user", 0) >= 3, (
                f"Expected at least 3 user messages, got {role_counts.get('user', 0)}"
            )
            return

    pytest.skip(
        "No transcript found for scout-test-anthropic-multiturn-tools - run bootstrap"
    )


# =============================================================================
# Filtering Tests
# =============================================================================


@skip_if_no_weave
@pytest.mark.asyncio
async def test_weave_limit_parameter() -> None:
    """Test that limit parameter restricts results."""
    from inspect_scout.sources._weave import weave

    transcripts = []
    async for t in weave(
        project=WEAVE_TEST_PROJECT,
        limit=1,
    ):
        transcripts.append(t)

    assert len(transcripts) <= 1
