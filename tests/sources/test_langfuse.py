"""Tests for LangFuse transcript import functionality.

These tests verify the conversion of LangFuse sessions/traces/observations
to Scout Transcript objects with proper format detection and event mapping.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from inspect_scout.sources._langfuse import (
    _detect_from_messages,
    _detect_provider_format,
    _extract_metadata,
    _sum_latency,
    _sum_tokens,
)

from tests.conftest import skip_if_no_langfuse_project


class MockObservation:
    """Mock LangFuse observation for testing."""

    def __init__(
        self,
        obs_id: str = "obs-1",
        obs_type: str = "GENERATION",
        name: str | None = None,
        model: str | None = None,
        input: Any = None,
        output: Any = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        usage_details: dict[str, int] | None = None,
        model_parameters: dict[str, Any] | None = None,
        parent_observation_id: str | None = None,
        latency: float | None = None,
        level: str | None = None,
        status_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = obs_id
        self.type = obs_type
        self.name = name
        self.model = model
        self.input = input
        self.output = output
        self.start_time = start_time or datetime.now()
        self.end_time = end_time
        self.usage_details = usage_details
        self.model_parameters = model_parameters
        self.parent_observation_id = parent_observation_id
        self.latency = latency
        self.level = level
        self.status_message = status_message
        self.metadata = metadata


class MockTrace:
    """Mock LangFuse trace for testing."""

    def __init__(
        self,
        trace_id: str = "trace-1",
        session_id: str | None = None,
        name: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        version: str | None = None,
        release: str | None = None,
        environment: str | None = None,
        metadata: dict[str, Any] | None = None,
        observations: list[MockObservation] | None = None,
    ) -> None:
        self.id = trace_id
        self.session_id = session_id
        self.name = name
        self.user_id = user_id
        self.tags = tags
        self.version = version
        self.release = release
        self.environment = environment
        self.metadata = metadata
        self.observations = observations or []


class MockSession:
    """Mock LangFuse session for testing."""

    def __init__(
        self,
        session_id: str = "session-1",
        created_at: datetime | None = None,
        traces: list[MockTrace] | None = None,
    ) -> None:
        self.id = session_id
        self.created_at = created_at or datetime.now()
        self.traces = traces or []


# ============================================================================
# Format Detection Tests
# ============================================================================


class TestDetectProviderFormat:
    """Tests for _detect_provider_format function."""

    def test_detect_openai_by_model_name(self) -> None:
        """Detect OpenAI format from model name."""
        gen = MockObservation(model="gpt-4", input={}, output={})
        assert _detect_provider_format(gen) == "openai"

        gen = MockObservation(model="gpt-3.5-turbo", input={}, output={})
        assert _detect_provider_format(gen) == "openai"

        gen = MockObservation(model="o1-preview", input={}, output={})
        assert _detect_provider_format(gen) == "openai"

    def test_detect_anthropic_by_model_name(self) -> None:
        """Detect Anthropic format from model name with native format data.

        Anthropic uses OTEL instrumentation which normalizes data to OpenAI format
        (finish_reason instead of stop_reason, tool_calls instead of tool_use).
        Therefore Claude models always return 'openai' format.
        """
        # OTEL-normalized Claude data: detected as 'openai' format
        otel_output = [
            {"content": "Hello", "role": "assistant", "finish_reason": "stop"}
        ]
        gen = MockObservation(model="claude-3-sonnet", input={}, output=otel_output)
        assert _detect_provider_format(gen) == "openai"

        gen = MockObservation(
            model="claude-3-opus-20240229", input={}, output=otel_output
        )
        assert _detect_provider_format(gen) == "openai"

        # Empty data with Claude model: defaults to 'openai' (OTEL format)
        gen = MockObservation(model="claude-3-sonnet", input={}, output={})
        assert _detect_provider_format(gen) == "openai"

    def test_detect_google_by_model_name(self) -> None:
        """Detect Google format from model name."""
        gen = MockObservation(model="gemini-pro", input={}, output={})
        assert _detect_provider_format(gen) == "google"

        gen = MockObservation(model="gemini-1.5-flash", input={}, output={})
        assert _detect_provider_format(gen) == "google"

    def test_detect_openai_by_output_structure(self) -> None:
        """Detect OpenAI format from output structure (choices array)."""
        output = {"choices": [{"message": {"role": "assistant", "content": "Hi"}}]}
        gen = MockObservation(model=None, input={}, output=output)
        assert _detect_provider_format(gen) == "openai"

    def test_detect_google_by_output_structure(self) -> None:
        """Detect Google format from output structure (candidates array)."""
        output = {"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]}
        gen = MockObservation(model=None, input={}, output=output)
        assert _detect_provider_format(gen) == "google"

    def test_detect_google_by_input_contents(self) -> None:
        """Detect Google format from input structure (contents key)."""
        input_data = {"contents": [{"role": "user", "parts": [{"text": "Hello"}]}]}
        gen = MockObservation(model=None, input=input_data, output={})
        assert _detect_provider_format(gen) == "google"

    def test_detect_string_input(self) -> None:
        """Detect string format for plain text input."""
        gen = MockObservation(model=None, input="Hello, world!", output={})
        assert _detect_provider_format(gen) == "string"

    def test_detect_unknown_format(self) -> None:
        """Fall back to unknown for unrecognized structures."""
        gen = MockObservation(model=None, input=None, output=None)
        assert _detect_provider_format(gen) == "unknown"


class TestDetectFromMessages:
    """Tests for _detect_from_messages function."""

    def test_detect_google_by_parts_key(self) -> None:
        """Detect Google format when messages have 'parts' key."""
        messages = [{"role": "user", "parts": [{"text": "Hello"}]}]
        assert _detect_from_messages(messages) == "google"

    def test_detect_google_by_model_role(self) -> None:
        """Detect Google format when role is 'model'."""
        messages = [{"role": "model", "content": "Hello"}]
        assert _detect_from_messages(messages) == "google"

    def test_detect_openai_by_string_content(self) -> None:
        """Detect OpenAI format when content is string."""
        messages = [{"role": "user", "content": "Hello"}]
        assert _detect_from_messages(messages) == "openai"

    def test_detect_anthropic_by_tool_use_block(self) -> None:
        """Detect Anthropic format when content has tool_use block."""
        messages = [
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1"}]}
        ]
        assert _detect_from_messages(messages) == "anthropic"

    def test_detect_anthropic_by_tool_result_block(self) -> None:
        """Detect Anthropic format when content has tool_result block."""
        messages = [
            {"role": "user", "content": [{"type": "tool_result", "result": "ok"}]}
        ]
        assert _detect_from_messages(messages) == "anthropic"

    def test_detect_openai_by_image_url_block(self) -> None:
        """Detect OpenAI format when content has image_url block."""
        messages = [
            {
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": "..."}}],
            }
        ]
        assert _detect_from_messages(messages) == "openai"

    def test_detect_anthropic_by_image_with_source(self) -> None:
        """Detect Anthropic format when content has image block with source."""
        messages = [
            {
                "role": "user",
                "content": [{"type": "image", "source": {"type": "base64"}}],
            }
        ]
        assert _detect_from_messages(messages) == "anthropic"

    def test_empty_messages_returns_unknown(self) -> None:
        """Return unknown for empty message list."""
        assert _detect_from_messages([]) == "unknown"

    def test_non_dict_messages_returns_unknown(self) -> None:
        """Return unknown when messages are not dicts."""
        assert _detect_from_messages(["not a dict"]) == "unknown"


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestSumTokens:
    """Tests for _sum_tokens helper function."""

    def test_sum_tokens_from_generations(self) -> None:
        """Sum tokens across multiple generations."""
        generations = [
            MockObservation(usage_details={"input": 100, "output": 50}),
            MockObservation(usage_details={"input": 200, "output": 100}),
        ]
        assert _sum_tokens(generations) == 450

    def test_sum_tokens_with_none_usage(self) -> None:
        """Handle generations with no usage details."""
        generations = [
            MockObservation(usage_details={"input": 100, "output": 50}),
            MockObservation(usage_details=None),
        ]
        assert _sum_tokens(generations) == 150

    def test_sum_tokens_empty_list(self) -> None:
        """Return 0 for empty generation list."""
        assert _sum_tokens([]) == 0


class TestSumLatency:
    """Tests for _sum_latency helper function."""

    def test_sum_latency_from_observations(self) -> None:
        """Sum latency across multiple observations."""
        observations = [
            MockObservation(latency=1.5),
            MockObservation(latency=2.5),
        ]
        assert _sum_latency(observations) == 4.0

    def test_sum_latency_with_none(self) -> None:
        """Handle observations with no latency."""
        observations = [
            MockObservation(latency=1.5),
            MockObservation(latency=None),
        ]
        assert _sum_latency(observations) == 1.5

    def test_sum_latency_empty_list(self) -> None:
        """Return 0 for empty observation list."""
        assert _sum_latency([]) == 0.0


class TestExtractMetadata:
    """Tests for _extract_metadata helper function."""

    def test_extract_all_metadata_fields(self) -> None:
        """Extract all available metadata fields from trace."""
        trace = MockTrace(
            user_id="user-123",
            session_id="session-456",
            name="test-trace",
            tags=["tag1", "tag2"],
            version="1.0.0",
            release="release-1",
            environment="production",
            metadata={"custom": "value"},
        )
        metadata = _extract_metadata(trace)

        assert metadata["user_id"] == "user-123"
        assert metadata["session_id"] == "session-456"
        assert metadata["name"] == "test-trace"
        assert metadata["tags"] == ["tag1", "tag2"]
        assert metadata["version"] == "1.0.0"
        assert metadata["release"] == "release-1"
        assert metadata["environment"] == "production"
        assert metadata["custom"] == "value"

    def test_extract_partial_metadata(self) -> None:
        """Handle trace with only some metadata fields."""
        trace = MockTrace(user_id="user-123", name="test-trace")
        metadata = _extract_metadata(trace)

        assert metadata["user_id"] == "user-123"
        assert metadata["name"] == "test-trace"
        assert "tags" not in metadata
        assert "version" not in metadata

    def test_extract_metadata_none_trace(self) -> None:
        """Return empty dict for None trace."""
        assert _extract_metadata(None) == {}


# ============================================================================
# Event Conversion Tests
# ============================================================================


class TestToModelEvent:
    """Tests for _to_model_event conversion."""

    @pytest.mark.asyncio
    async def test_convert_openai_generation(self) -> None:
        """Convert OpenAI-format generation to ModelEvent."""
        from inspect_scout.sources._langfuse import _to_model_event

        gen = MockObservation(
            model="gpt-4",
            input={"messages": [{"role": "user", "content": "Hello"}]},
            output={
                "choices": [{"message": {"role": "assistant", "content": "Hi there!"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 1),
            model_parameters={"temperature": 0.7},
            parent_observation_id="span-1",
        )

        event = await _to_model_event(gen)

        assert event.model == "gpt-4"
        assert event.span_id == "span-1"
        # Check input messages were parsed
        assert len(event.input) == 1
        assert event.input[0].role == "user"
        # Check config was extracted
        assert event.config.temperature == 0.7

    @pytest.mark.asyncio
    async def test_convert_generation_with_string_input(self) -> None:
        """Convert generation with plain string input."""
        from inspect_scout.sources._langfuse import _to_model_event

        gen = MockObservation(
            model="gpt-4",
            input="What is 2+2?",
            output={"choices": [{"message": {"role": "assistant", "content": "4"}}]},
        )

        event = await _to_model_event(gen)

        assert len(event.input) == 1
        assert event.input[0].role == "user"
        assert event.input[0].content == "What is 2+2?"


class TestToToolEvent:
    """Tests for _to_tool_event conversion."""

    def test_convert_tool_observation(self) -> None:
        """Convert TOOL observation to ToolEvent."""
        from inspect_scout.sources._langfuse import _to_tool_event

        obs = MockObservation(
            obs_type="TOOL",
            name="search_web",
            input={"query": "weather"},
            output="sunny",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 1),
            parent_observation_id="span-1",
        )

        event = _to_tool_event(obs)

        assert event.function == "search_web"
        assert event.arguments == {"query": "weather"}
        assert event.result == "sunny"
        assert event.span_id == "span-1"
        assert event.error is None

    def test_convert_tool_observation_with_error(self) -> None:
        """Convert TOOL observation with error."""
        from inspect_scout.sources._langfuse import _to_tool_event

        obs = MockObservation(
            obs_type="TOOL",
            name="search_web",
            input={},
            output=None,
            level="ERROR",
            status_message="Tool execution failed",
        )

        event = _to_tool_event(obs)

        assert event.error is not None
        assert event.error.message == "Tool execution failed"


class TestToSpanEvents:
    """Tests for span event conversion."""

    def test_convert_span_begin_event(self) -> None:
        """Convert SPAN observation to SpanBeginEvent."""
        from inspect_scout.sources._langfuse import _to_span_begin_event

        obs = MockObservation(
            obs_id="span-123",
            obs_type="SPAN",
            name="agent_step",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            parent_observation_id="parent-span",
            metadata={"step": 1},
        )

        event = _to_span_begin_event(obs)

        assert event.id == "span-123"
        assert event.name == "agent_step"
        assert event.parent_id == "parent-span"
        assert event.metadata == {"step": 1}

    def test_convert_span_end_event(self) -> None:
        """Convert SPAN observation to SpanEndEvent."""
        from inspect_scout.sources._langfuse import _to_span_end_event

        obs = MockObservation(
            obs_id="span-123",
            obs_type="SPAN",
            end_time=datetime(2024, 1, 1, 12, 0, 5),
            metadata={"completed": True},
        )

        event = _to_span_end_event(obs)

        # SpanEndEvent uses `id` field
        assert event.id == "span-123"
        assert event.metadata == {"completed": True}


class TestToInfoEvent:
    """Tests for _to_info_event conversion."""

    def test_convert_event_observation(self) -> None:
        """Convert EVENT observation to InfoEvent."""
        from inspect_scout.sources._langfuse import _to_info_event

        obs = MockObservation(
            obs_type="EVENT",
            name="user_action",
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            metadata={"action": "click"},
        )

        event = _to_info_event(obs)

        # InfoEvent uses source and data fields
        assert event.source == "user_action"
        assert event.data == "user_action"  # Fallback to name when no input/output
        assert event.metadata == {"action": "click"}


# ============================================================================
# Observations to Events Conversion Tests
# ============================================================================


class TestObservationsToEvents:
    """Tests for _observations_to_events function."""

    @pytest.mark.asyncio
    async def test_convert_mixed_observations(self) -> None:
        """Convert a mix of observation types to events."""
        from inspect_scout.sources._langfuse import _observations_to_events

        observations = [
            MockObservation(
                obs_id="gen-1",
                obs_type="GENERATION",
                model="gpt-4",
                input={"messages": [{"role": "user", "content": "Hi"}]},
                output={
                    "choices": [{"message": {"role": "assistant", "content": "Hello"}}]
                },
                start_time=datetime(2024, 1, 1, 12, 0, 0),
            ),
            MockObservation(
                obs_id="tool-1",
                obs_type="TOOL",
                name="search",
                input={"q": "test"},
                output="result",
                start_time=datetime(2024, 1, 1, 12, 0, 1),
            ),
            MockObservation(
                obs_id="span-1",
                obs_type="SPAN",
                name="step",
                start_time=datetime(2024, 1, 1, 12, 0, 2),
                end_time=datetime(2024, 1, 1, 12, 0, 3),
            ),
        ]

        events = await _observations_to_events(observations)

        # Should have: 1 ModelEvent, 1 ToolEvent, 1 SpanBegin, 1 SpanEnd
        assert len(events) == 4

        # Verify events are sorted by timestamp
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_skip_unsupported_observation_types(self) -> None:
        """Skip RETRIEVER, EMBEDDING, GUARDRAIL observations."""
        from inspect_scout.sources._langfuse import _observations_to_events

        observations = [
            MockObservation(obs_type="RETRIEVER", start_time=datetime(2024, 1, 1)),
            MockObservation(obs_type="EMBEDDING", start_time=datetime(2024, 1, 1)),
            MockObservation(obs_type="GUARDRAIL", start_time=datetime(2024, 1, 1)),
        ]

        events = await _observations_to_events(observations)

        assert len(events) == 0


# ============================================================================
# Session to Transcript Conversion Tests
# ============================================================================


class TestSessionToTranscript:
    """Tests for _session_to_transcript function."""

    @pytest.mark.asyncio
    async def test_convert_simple_session(self) -> None:
        """Convert a simple session with one trace to transcript."""
        from inspect_scout.sources._langfuse import _session_to_transcript

        # Create mock session with one trace and one generation
        generation = MockObservation(
            obs_type="GENERATION",
            model="gpt-4",
            input={"messages": [{"role": "user", "content": "Hello"}]},
            output={
                "choices": [{"message": {"role": "assistant", "content": "Hi there!"}}]
            },
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            usage_details={"input": 10, "output": 5},
            latency=1.0,
        )

        trace = MockTrace(
            trace_id="trace-1",
            name="test-conversation",
            user_id="user-1",
            observations=[generation],
        )

        session = MockSession(
            session_id="session-1",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            traces=[trace],
        )

        # Mock the langfuse client
        mock_client = MagicMock()
        mock_client.api.trace.get.return_value = trace

        transcript = await _session_to_transcript(session, mock_client)

        assert transcript is not None
        assert transcript.transcript_id == "session-1"
        assert transcript.source_type == "langfuse"
        assert transcript.source_id == "session-1"
        assert transcript.source_uri == "https://cloud.langfuse.com/sessions/session-1"
        assert transcript.task_id == "test-conversation"
        assert transcript.model == "gpt-4"
        assert transcript.total_tokens == 15
        assert transcript.total_time == 1.0

        # Check messages derived from final ModelEvent
        assert len(transcript.messages) == 2
        assert transcript.messages[0].role == "user"
        assert transcript.messages[1].role == "assistant"

        # Check events
        assert len(transcript.events) == 1
        assert transcript.events[0].event == "model"

        # Check metadata
        assert transcript.metadata.get("user_id") == "user-1"

    @pytest.mark.asyncio
    async def test_convert_session_with_project_id(self) -> None:
        """Convert session with project_id for proper URL construction."""
        from inspect_scout.sources._langfuse import _session_to_transcript

        generation = MockObservation(
            obs_type="GENERATION",
            model="gpt-4",
            input={"messages": [{"role": "user", "content": "Hello"}]},
            output={"choices": [{"message": {"role": "assistant", "content": "Hi!"}}]},
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        trace = MockTrace(trace_id="trace-1", observations=[generation])
        session = MockSession(session_id="session-1", traces=[trace])

        mock_client = MagicMock()
        mock_client.api.trace.get.return_value = trace

        transcript = await _session_to_transcript(
            session, mock_client, project_id="proj-uuid-123"
        )

        assert transcript is not None
        assert (
            transcript.source_uri
            == "https://cloud.langfuse.com/project/proj-uuid-123/sessions/session-1"
        )

    @pytest.mark.asyncio
    async def test_convert_session_with_custom_host(self) -> None:
        """Convert session with custom host URL."""
        from inspect_scout.sources._langfuse import _session_to_transcript

        generation = MockObservation(
            obs_type="GENERATION",
            model="gpt-4",
            input={"messages": [{"role": "user", "content": "Hello"}]},
            output={"choices": [{"message": {"role": "assistant", "content": "Hi!"}}]},
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        trace = MockTrace(trace_id="trace-1", observations=[generation])
        session = MockSession(session_id="session-1", traces=[trace])

        mock_client = MagicMock()
        mock_client.api.trace.get.return_value = trace

        transcript = await _session_to_transcript(
            session,
            mock_client,
            project_id="proj-123",
            host="https://langfuse.mycompany.com/",
        )

        assert transcript is not None
        assert (
            transcript.source_uri
            == "https://langfuse.mycompany.com/project/proj-123/sessions/session-1"
        )

    @pytest.mark.asyncio
    async def test_empty_session_returns_none(self) -> None:
        """Return None for session with no observations."""
        from inspect_scout.sources._langfuse import _session_to_transcript

        trace = MockTrace(trace_id="trace-1", observations=[])
        session = MockSession(session_id="session-1", traces=[trace])

        mock_client = MagicMock()
        mock_client.api.trace.get.return_value = trace

        transcript = await _session_to_transcript(session, mock_client)

        assert transcript is None


# ============================================================================
# Project Resolution Tests
# ============================================================================


class TestResolveProjectId:
    """Tests for _resolve_project_id function."""

    def test_resolve_by_project_id(self) -> None:
        """Resolve when value matches a project ID directly."""
        from inspect_scout.sources._langfuse import _resolve_project_id

        # Create mock projects
        proj1 = MagicMock()
        proj1.id = "cmk8zhiw2008jad07i5r6wqlk"
        proj1.name = "scout-pytest"

        proj2 = MagicMock()
        proj2.id = "other-project-id"
        proj2.name = "other-project"

        mock_client = MagicMock()
        mock_client.api.projects.get.return_value = MagicMock(data=[proj1, proj2])

        result = _resolve_project_id(mock_client, "cmk8zhiw2008jad07i5r6wqlk")

        assert result == "cmk8zhiw2008jad07i5r6wqlk"

    def test_resolve_by_project_name(self) -> None:
        """Resolve when value matches a project name."""
        from inspect_scout.sources._langfuse import _resolve_project_id

        proj1 = MagicMock()
        proj1.id = "cmk8zhiw2008jad07i5r6wqlk"
        proj1.name = "scout-pytest"

        mock_client = MagicMock()
        mock_client.api.projects.get.return_value = MagicMock(data=[proj1])

        result = _resolve_project_id(mock_client, "scout-pytest")

        assert result == "cmk8zhiw2008jad07i5r6wqlk"

    def test_resolve_not_found_raises_error(self) -> None:
        """Raise ValueError when project not found."""
        from inspect_scout.sources._langfuse import _resolve_project_id

        proj1 = MagicMock()
        proj1.id = "some-id"
        proj1.name = "some-project"

        mock_client = MagicMock()
        mock_client.api.projects.get.return_value = MagicMock(data=[proj1])

        with pytest.raises(ValueError, match="Project 'nonexistent' not found"):
            _resolve_project_id(mock_client, "nonexistent")

    def test_resolve_fallback_on_api_error(self) -> None:
        """Fall back to using value as-is when API call fails."""
        from inspect_scout.sources._langfuse import _resolve_project_id

        mock_client = MagicMock()
        mock_client.api.projects.get.side_effect = Exception("API error")

        # Should return the input value as-is
        result = _resolve_project_id(mock_client, "some-project-id")

        assert result == "some-project-id"


# ============================================================================
# Main Function Tests
# ============================================================================


class TestTranscriptsFromLangfuse:
    """Tests for transcripts_from_langfuse main function."""

    @pytest.mark.asyncio
    async def test_import_error_when_langfuse_not_installed(self) -> None:
        """Raise ImportError when langfuse package is not installed."""
        from inspect_scout.sources._langfuse import _get_langfuse_client

        with patch.dict("sys.modules", {"langfuse": None}):
            with pytest.raises(ImportError, match="langfuse package is required"):
                _get_langfuse_client("pk", "sk")

    @pytest.mark.asyncio
    async def test_pagination_through_traces(self) -> None:
        """Verify pagination through traces to collect session IDs."""
        from inspect_scout.sources._langfuse import langfuse

        # Create mock responses for pagination
        page1_traces = [
            MockTrace(trace_id="t1", session_id="s1"),
            MockTrace(trace_id="t2", session_id="s2"),
        ]
        page1_meta = MagicMock()
        page1_meta.total_pages = 2

        page2_traces = [
            MockTrace(trace_id="t3", session_id="s3"),
        ]
        page2_meta = MagicMock()
        page2_meta.total_pages = 2

        # Mock langfuse client
        mock_langfuse = MagicMock()
        mock_langfuse.api.trace.list.side_effect = [
            MagicMock(data=page1_traces, meta=page1_meta),
            MagicMock(data=page2_traces, meta=page2_meta),
        ]

        # Mock session fetch to return empty sessions (for simplicity)
        empty_trace = MockTrace(observations=[])
        mock_langfuse.api.trace.get.return_value = empty_trace
        mock_langfuse.api.sessions.get.return_value = MockSession(traces=[empty_trace])

        with patch(
            "inspect_scout.sources._langfuse._get_langfuse_client",
            return_value=mock_langfuse,
        ):
            transcripts = []
            async for t in langfuse(public_key="pk", secret_key="sk"):
                transcripts.append(t)

        # Verify trace API was called twice (2 pages)
        assert mock_langfuse.api.trace.list.call_count == 2

        # Verify sessions API was called for each unique session
        assert mock_langfuse.api.sessions.get.call_count == 3

    @pytest.mark.asyncio
    async def test_limit_parameter(self) -> None:
        """Verify limit parameter stops iteration early."""
        from inspect_scout.sources._langfuse import langfuse

        # Create mock traces and sessions
        traces = [MockTrace(trace_id=f"t{i}", session_id=f"s{i}") for i in range(5)]
        meta = MagicMock()
        meta.total_pages = 1

        generation = MockObservation(
            obs_type="GENERATION",
            model="gpt-4",
            input={"messages": [{"role": "user", "content": "Hi"}]},
            output={
                "choices": [{"message": {"role": "assistant", "content": "Hello"}}]
            },
            start_time=datetime.now(),
        )

        mock_langfuse = MagicMock()
        mock_langfuse.api.trace.list.return_value = MagicMock(data=traces, meta=meta)
        mock_langfuse.api.trace.get.return_value = MockTrace(observations=[generation])
        mock_langfuse.api.sessions.get.return_value = MockSession(
            traces=[MockTrace(observations=[generation])]
        )

        with patch(
            "inspect_scout.sources._langfuse._get_langfuse_client",
            return_value=mock_langfuse,
        ):
            transcripts = []
            async for t in langfuse(public_key="pk", secret_key="sk", limit=2):
                transcripts.append(t)

        # Should only get 2 transcripts despite 5 sessions
        assert len(transcripts) == 2


# ============================================================================
# Integration Test Helpers
# ============================================================================


async def _fetch_langfuse_session(session_id: str) -> Any:
    """Fetch a specific LangFuse session by ID.

    Args:
        session_id: The session ID to fetch

    Returns:
        The transcript for the session

    Raises:
        AssertionError: If the session is not found
    """
    from inspect_scout.sources import langfuse

    async for t in langfuse(project="scout-pytest", tags=["scout"]):
        if t.transcript_id == session_id:
            return t

    raise AssertionError(f"Session {session_id} not found")


def _assert_langfuse_transcript(
    transcript: Any,
    session_id: str,
    model_pattern: str,
    min_model_events: int = 5,
    min_messages: int = 10,
    min_user_messages: int = 5,
    min_assistant_messages: int = 5,
) -> tuple[list[Any], dict[str, int]]:
    """Common assertions for LangFuse transcript tests.

    Args:
        transcript: The transcript to validate
        session_id: Expected session/transcript ID
        model_pattern: Substring expected in model name (e.g., "claude", "gpt")
        min_model_events: Minimum expected ModelEvents
        min_messages: Minimum expected total messages
        min_user_messages: Minimum expected user messages (varies by OTEL instrumentation)
        min_assistant_messages: Minimum expected assistant messages

    Returns:
        Tuple of (model_events, role_counts) for provider-specific assertions
    """
    # Verify basic transcript fields
    assert transcript.source_type == "langfuse"
    assert transcript.transcript_id == session_id
    assert transcript.model is not None
    assert model_pattern in transcript.model.lower(), (
        f"Expected {model_pattern} model, got {transcript.model}"
    )

    # Verify aggregated metrics are populated
    # Note: total_tokens depends on the OpenTelemetry instrumentation capturing usage
    assert transcript.total_tokens is not None, "Expected total_tokens to be set"

    assert transcript.total_time is not None, "Expected total_time to be populated"
    assert transcript.total_time > 0, (
        f"Expected positive total_time, got {transcript.total_time}"
    )

    # Verify date is populated
    assert transcript.date is not None, "Expected date to be populated"

    # Verify source_uri is populated (link back to LangFuse)
    assert transcript.source_uri is not None, "Expected source_uri to be populated"
    assert "langfuse" in transcript.source_uri.lower(), (
        f"Expected LangFuse URL in source_uri, got {transcript.source_uri}"
    )

    # Verify we have events
    assert len(transcript.events) > 0, "Expected events in transcript"

    # Find ModelEvents and verify we have multiple (multi-turn conversation)
    model_events = [e for e in transcript.events if e.event == "model"]
    assert len(model_events) >= min_model_events, (
        f"Expected at least {min_model_events} ModelEvents, got {len(model_events)}"
    )
    print(f"\nModelEvents: {len(model_events)}")

    # Check that at least one model event has tools
    has_tools = any(len(e.tools) > 0 for e in model_events)
    assert has_tools, "Expected at least one ModelEvent with tools"

    # Verify tool structure
    for event in model_events:
        for tool in event.tools:
            assert tool.name, "Tool should have a name"
            assert tool.description, "Tool should have a description"
            assert tool.parameters is not None, "Tool should have parameters"

    # Verify ModelEvent timestamps are populated
    for event in model_events:
        assert event.timestamp is not None, "ModelEvent should have timestamp"
        assert event.completed is not None, "ModelEvent should have completed time"

    # Verify messages are populated with multiple messages of each type
    assert len(transcript.messages) > 0, "Expected messages in transcript"

    # Count messages by role
    role_counts: dict[str, int] = {}
    for msg in transcript.messages:
        role_counts[msg.role] = role_counts.get(msg.role, 0) + 1

    # Verify we have user and assistant messages
    assert "user" in role_counts, "Expected user messages"
    assert "assistant" in role_counts, "Expected assistant messages"

    # Verify we have multiple messages (multi-turn conversation with tool use)
    # Note: User message count varies by OTEL instrumentation - OpenAI captures fewer
    assert role_counts["user"] >= min_user_messages, (
        f"Expected at least {min_user_messages} user messages, got {role_counts['user']}"
    )
    assert role_counts["assistant"] >= min_assistant_messages, (
        f"Expected at least {min_assistant_messages} assistant messages, "
        f"got {role_counts['assistant']}"
    )

    # Verify total message count is substantial
    total_messages = sum(role_counts.values())
    assert total_messages >= min_messages, (
        f"Expected at least {min_messages} total messages, got {total_messages}"
    )

    # Log message counts for visibility
    print(f"Message counts: {role_counts} (total: {total_messages})")

    # Verify metadata is populated with LangFuse-specific fields
    assert transcript.metadata is not None, "Expected metadata to be populated"
    assert "tags" in transcript.metadata, "Expected tags in metadata"
    assert "scout" in transcript.metadata["tags"], "Expected 'scout' tag in metadata"

    return model_events, role_counts


# ============================================================================
# Integration Tests with Real LangFuse Data
# ============================================================================


@skip_if_no_langfuse_project
@pytest.mark.asyncio
async def test_langfuse_anthropic() -> None:
    """Test LangFuse integration with real Anthropic traces.

    Validates the full integration against production data from an
    Anthropic (Claude) model session.
    """
    transcript = await _fetch_langfuse_session(session_id="fu4epGBdMGZ84KXSCY6aWB")

    model_events, role_counts = _assert_langfuse_transcript(
        transcript,
        session_id="fu4epGBdMGZ84KXSCY6aWB",
        model_pattern="claude",
    )

    # Anthropic-specific: system message should be present
    assert "system" in role_counts, "Expected system messages for Anthropic"


@skip_if_no_langfuse_project
@pytest.mark.asyncio
async def test_langfuse_openai() -> None:
    """Test LangFuse integration with real OpenAI traces.

    Validates the full integration against production data from an
    OpenAI (GPT) model session.

    Note: The OpenAI Responses API format for this eval has only 1 user message
    (the task prompt) since all interaction happens via function calls. Through
    hybrid extraction, we merge messages from Responses API format (which has
    complete system/user context) with OTEL-captured generations for the most
    complete message history.
    """
    transcript = await _fetch_langfuse_session(session_id="SsZiMRBMvPH5GPnsu6Jk69")

    # OpenAI OTEL captures fewer user messages - the eval task only has 1 user turn
    _model_events, role_counts = _assert_langfuse_transcript(
        transcript,
        session_id="SsZiMRBMvPH5GPnsu6Jk69",
        model_pattern="gpt",
        min_user_messages=1,  # Only 1 user message in this eval
        min_assistant_messages=5,
    )

    # OpenAI with hybrid extraction: system message should now be present
    # (extracted from Responses API format generation which has complete context)
    assert "system" in role_counts, (
        "Expected system message for OpenAI (via hybrid Responses API extraction)"
    )


@skip_if_no_langfuse_project
@pytest.mark.asyncio
async def test_langfuse_openai_completions() -> None:
    """Test LangFuse integration with real OpenAI Chat Completions API traces.

    Validates the full integration against production data from an
    OpenAI session using the Chat Completions API (not Responses API).

    The OTEL instrumentation preserves native Chat Completions format:
    - Input: dict with 'messages', 'model', 'tools', 'tool_choice'
    - Output: dict with 'choices' array
    - Messages have 'developer' role for system messages
    """
    transcript = await _fetch_langfuse_session(session_id="LhXbgLJvb4KCsuDV5rffpR")

    _model_events, role_counts = _assert_langfuse_transcript(
        transcript,
        session_id="LhXbgLJvb4KCsuDV5rffpR",
        model_pattern="gpt",
        min_model_events=5,
        min_user_messages=1,  # Eval task has 1 user message
        min_assistant_messages=5,
    )

    # Chat Completions API: system message should be present
    # (developer role in OpenAI maps to system role in ChatMessage)
    assert "system" in role_counts, (
        "Expected system message for OpenAI Chat Completions API"
    )


@skip_if_no_langfuse_project
@pytest.mark.asyncio
async def test_langfuse_google() -> None:
    """Test LangFuse integration with real Google (Gemini) traces.

    Validates the full integration against production data from a
    Google Gemini model session.

    The Google OTEL instrumentation serializes SDK objects using repr(),
    requiring parsing of Content and FunctionDeclaration strings back
    into structured data that messages_from_google can consume.
    """
    transcript = await _fetch_langfuse_session(session_id="EG2UfE9MvpBSmy73R6a2UH")

    _model_events, role_counts = _assert_langfuse_transcript(
        transcript,
        session_id="EG2UfE9MvpBSmy73R6a2UH",
        model_pattern="gemini",
        min_model_events=5,
        min_user_messages=1,  # Eval task has 1 user message
        min_assistant_messages=5,
    )

    # Google: system message should be present (from config.system_instruction)
    assert "system" in role_counts, (
        "Expected system message for Google (from config.system_instruction)"
    )
