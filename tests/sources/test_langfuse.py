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
        self.startTime = start_time or datetime.now()
        self.endTime = end_time
        self.usageDetails = usage_details
        self.modelParameters = model_parameters
        self.parentObservationId = parent_observation_id
        self.latency = latency
        self.level = level
        self.statusMessage = status_message
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
        self.sessionId = session_id
        self.name = name
        self.userId = user_id
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
        self.createdAt = created_at or datetime.now()
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
        """Detect Anthropic format from model name."""
        gen = MockObservation(model="claude-3-opus-20240229", input={}, output={})
        assert _detect_provider_format(gen) == "anthropic"

        gen = MockObservation(model="claude-3-sonnet", input={}, output={})
        assert _detect_provider_format(gen) == "anthropic"

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

    def test_detect_anthropic_by_output_structure(self) -> None:
        """Detect Anthropic format from output structure (stop_reason + content list)."""
        output = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "Hi"}],
        }
        gen = MockObservation(model=None, input={}, output=output)
        assert _detect_provider_format(gen) == "anthropic"

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
            output={
                "choices": [{"message": {"role": "assistant", "content": "Hi!"}}]
            },
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
            output={
                "choices": [{"message": {"role": "assistant", "content": "Hi!"}}]
            },
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        trace = MockTrace(trace_id="trace-1", observations=[generation])
        session = MockSession(session_id="session-1", traces=[trace])

        mock_client = MagicMock()
        mock_client.api.trace.get.return_value = trace

        transcript = await _session_to_transcript(
            session, mock_client, project_id="proj-123", host="https://langfuse.mycompany.com/"
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
        page1_meta.totalPages = 2

        page2_traces = [
            MockTrace(trace_id="t3", session_id="s3"),
        ]
        page2_meta = MagicMock()
        page2_meta.totalPages = 2

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
        meta.totalPages = 1

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
