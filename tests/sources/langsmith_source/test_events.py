"""Tests for LangSmith run to event conversion.

Tests to_model_event(), to_tool_event(), to_span_begin_event(),
to_span_end_event(), to_info_event(), and runs_to_events() functions.
"""

from datetime import datetime, timedelta, timezone

import pytest
from inspect_ai.event import (
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_scout.sources._langsmith.events import (
    runs_to_events,
    to_info_event,
    to_model_event,
    to_span_begin_event,
    to_span_end_event,
    to_tool_event,
)

from tests.sources.langsmith_source.mocks import (
    MockRun,
    create_anthropic_llm_run,
    create_chain_run,
    create_google_llm_run,
    create_openai_llm_run,
    create_tool_run,
)


class TestToModelEvent:
    """Tests for to_model_event conversion."""

    @pytest.mark.asyncio
    async def test_convert_openai_llm_run(self) -> None:
        """Convert OpenAI-format LLM run to ModelEvent."""
        run = create_openai_llm_run(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello!"}],
            content="Hi there!",
        )

        event = await to_model_event(run)

        assert isinstance(event, ModelEvent)
        assert event.model == "gpt-4o-mini"
        # Input messages should be parsed
        assert len(event.input) == 1
        assert event.input[0].role == "user"
        # Output should be present
        assert event.output is not None
        assert event.output.message is not None

    @pytest.mark.asyncio
    async def test_convert_anthropic_llm_run(self) -> None:
        """Convert Anthropic-format LLM run to ModelEvent."""
        run = create_anthropic_llm_run(
            model="claude-3-5-haiku-latest",
            messages=[{"role": "user", "content": "Hello!"}],
            content_blocks=[{"type": "text", "text": "Hi there!"}],
        )

        event = await to_model_event(run)

        assert isinstance(event, ModelEvent)
        assert event.model == "claude-3-5-haiku-latest"

    @pytest.mark.asyncio
    async def test_convert_google_llm_run(self) -> None:
        """Convert Google-format LLM run to ModelEvent."""
        run = create_google_llm_run(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": [{"text": "Hello!"}]}],
            response_text="Hi there!",
        )

        event = await to_model_event(run)

        assert isinstance(event, ModelEvent)
        assert event.model == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_model_event_timestamps(self) -> None:
        """ModelEvent should have timestamps from run."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

        run = create_openai_llm_run()
        run.start_time = start
        run.end_time = end

        event = await to_model_event(run)

        assert event.timestamp == start
        assert event.completed == end

    @pytest.mark.asyncio
    async def test_model_event_span_id(self) -> None:
        """ModelEvent should have span_id from parent_run_id."""
        run = create_openai_llm_run(parent_run_id="parent-123")

        event = await to_model_event(run)

        assert event.span_id == "parent-123"

    @pytest.mark.asyncio
    async def test_model_event_config(self) -> None:
        """ModelEvent should extract config from invocation_params."""
        run = create_openai_llm_run()
        assert run.extra is not None
        run.extra["invocation_params"]["temperature"] = 0.8
        run.extra["invocation_params"]["max_tokens"] = 100

        event = await to_model_event(run)

        assert event.config.temperature == 0.8
        assert event.config.max_tokens == 100


class TestToToolEvent:
    """Tests for to_tool_event conversion."""

    def test_convert_tool_run(self) -> None:
        """Convert tool run to ToolEvent."""
        run = create_tool_run(
            name="get_weather",
            inputs={"city": "San Francisco"},
            output="Sunny, 72F",
        )

        event = to_tool_event(run)

        assert isinstance(event, ToolEvent)
        assert event.function == "get_weather"
        assert event.arguments == {"city": "San Francisco"}
        assert event.result == "Sunny, 72F"
        assert event.error is None

    def test_tool_event_with_error(self) -> None:
        """ToolEvent should capture error from run."""
        run = create_tool_run(
            name="get_weather",
            inputs={"city": "Unknown"},
            error="City not found",
        )

        event = to_tool_event(run)

        assert event.error is not None
        assert event.error.message == "City not found"

    def test_tool_event_timestamps(self) -> None:
        """ToolEvent should have timestamps from run."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 12, 0, 1, tzinfo=timezone.utc)

        run = create_tool_run()
        run.start_time = start
        run.end_time = end

        event = to_tool_event(run)

        assert event.timestamp == start
        assert event.completed == end

    def test_tool_event_span_id(self) -> None:
        """ToolEvent should have span_id from parent_run_id."""
        run = create_tool_run(parent_run_id="llm-123")

        event = to_tool_event(run)

        assert event.span_id == "llm-123"

    def test_tool_event_dict_output(self) -> None:
        """ToolEvent should handle dict output."""
        run = create_tool_run(
            name="get_weather",
            output={"temperature": 72, "condition": "sunny"},
        )

        event = to_tool_event(run)

        # Dict output should be stringified
        result_str = str(event.result)
        assert "72" in result_str or "temperature" in result_str

    def test_tool_event_uses_run_id(self) -> None:
        """ToolEvent should use run ID."""
        run = create_tool_run(run_id="tool-uuid-123")

        event = to_tool_event(run)

        assert event.id == "tool-uuid-123"


class TestToSpanBeginEvent:
    """Tests for to_span_begin_event conversion."""

    def test_convert_chain_run(self) -> None:
        """Convert chain run to SpanBeginEvent."""
        run = create_chain_run(
            run_id="chain-123",
            name="my-agent",
            run_type="chain",
        )

        event = to_span_begin_event(run)

        assert isinstance(event, SpanBeginEvent)
        assert event.id == "chain-123"
        assert event.name == "my-agent"

    def test_span_begin_parent_id(self) -> None:
        """SpanBeginEvent should have parent_id from parent_run_id."""
        run = create_chain_run(parent_run_id="outer-chain")

        event = to_span_begin_event(run)

        assert event.parent_id == "outer-chain"

    def test_span_begin_timestamp(self) -> None:
        """SpanBeginEvent should have timestamp from start_time."""
        start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        run = create_chain_run()
        run.start_time = start

        event = to_span_begin_event(run)

        assert event.timestamp == start

    def test_span_begin_metadata(self) -> None:
        """SpanBeginEvent should include metadata from run."""
        run = create_chain_run(tags=["test", "demo"])
        run.extra = {"metadata": {"custom_key": "custom_value"}}

        event = to_span_begin_event(run)

        assert event.metadata is not None
        assert event.metadata.get("tags") == ["test", "demo"]
        assert event.metadata.get("custom_key") == "custom_value"


class TestToSpanEndEvent:
    """Tests for to_span_end_event conversion."""

    def test_convert_chain_run_end(self) -> None:
        """Convert chain run to SpanEndEvent."""
        run = create_chain_run(run_id="chain-123")

        event = to_span_end_event(run)

        assert isinstance(event, SpanEndEvent)
        assert event.id == "chain-123"

    def test_span_end_timestamp(self) -> None:
        """SpanEndEvent should have timestamp from end_time."""
        end = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        run = create_chain_run()
        run.end_time = end

        event = to_span_end_event(run)

        assert event.timestamp == end


class TestToInfoEvent:
    """Tests for to_info_event conversion."""

    def test_convert_retriever_run(self) -> None:
        """Convert retriever run to InfoEvent."""
        run = MockRun(
            id="retriever-123",
            run_type="retriever",
            name="vector_store",
            inputs={"query": "search term"},
            start_time=datetime(2024, 1, 1, 12, 0, 0),
        )

        event = to_info_event(run)

        assert event.source == "vector_store"
        assert event.data == {"query": "search term"}

    def test_info_event_uses_outputs_when_no_inputs(self) -> None:
        """InfoEvent should use outputs when inputs is None."""
        run = MockRun(
            run_type="embedding",
            name="embedder",
            inputs=None,
            outputs={"vectors": [0.1, 0.2]},
        )

        event = to_info_event(run)

        assert event.data == {"vectors": [0.1, 0.2]}

    def test_info_event_fallback_to_name(self) -> None:
        """InfoEvent should fall back to name when no inputs/outputs."""
        run = MockRun(
            run_type="embedding",
            name="embedder",
            inputs=None,
            outputs=None,
        )

        event = to_info_event(run)

        assert event.data == "embedder"


class TestRunsToEvents:
    """Tests for runs_to_events batch conversion."""

    @pytest.mark.asyncio
    async def test_convert_mixed_runs(self) -> None:
        """Convert a mix of run types to events."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        llm_run = create_openai_llm_run()
        llm_run.start_time = base_time

        tool_run = create_tool_run()
        tool_run.start_time = base_time + timedelta(seconds=1)

        chain_run = create_chain_run()
        chain_run.start_time = base_time + timedelta(seconds=2)
        chain_run.end_time = base_time + timedelta(seconds=3)

        runs = [llm_run, tool_run, chain_run]
        events = await runs_to_events(runs)

        # Should have: 1 ModelEvent, 1 ToolEvent, 1 SpanBegin, 1 SpanEnd
        assert len(events) == 4

        # Check types
        event_types = [type(e).__name__ for e in events]
        assert "ModelEvent" in event_types
        assert "ToolEvent" in event_types
        assert "SpanBeginEvent" in event_types
        assert "SpanEndEvent" in event_types

    @pytest.mark.asyncio
    async def test_events_sorted_chronologically(self) -> None:
        """Events should be sorted by timestamp."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        # Create runs out of order
        late_run = create_openai_llm_run(run_id="late")
        late_run.start_time = base_time + timedelta(seconds=10)

        early_run = create_openai_llm_run(run_id="early")
        early_run.start_time = base_time

        middle_run = create_openai_llm_run(run_id="middle")
        middle_run.start_time = base_time + timedelta(seconds=5)

        runs = [late_run, early_run, middle_run]
        events = await runs_to_events(runs)

        # Verify chronological order
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_skip_unsupported_run_types(self) -> None:
        """Skip parser, prompt, and other unsupported run types."""
        runs = [
            MockRun(id="parser-1", run_type="parser"),
            MockRun(id="prompt-1", run_type="prompt"),
            MockRun(id="other-1", run_type="unknown"),
        ]

        events = await runs_to_events(runs)

        # No events should be created for these types
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_retriever_creates_info_event(self) -> None:
        """Retriever runs should create InfoEvent."""
        run = MockRun(
            id="retriever-1",
            run_type="retriever",
            name="vector_search",
            start_time=datetime.now(),
        )

        events = await runs_to_events([run])

        assert len(events) == 1
        assert isinstance(events[0], InfoEvent)
        assert events[0].source == "vector_search"

    @pytest.mark.asyncio
    async def test_embedding_creates_info_event(self) -> None:
        """Embedding runs should create InfoEvent."""
        run = MockRun(
            id="embedding-1",
            run_type="embedding",
            name="embedder",
            start_time=datetime.now(),
        )

        events = await runs_to_events([run])

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_chain_without_end_time_no_span_end(self) -> None:
        """Chain run without end_time should not create SpanEndEvent."""
        run = create_chain_run()
        run.end_time = None

        events = await runs_to_events([run])

        # Only SpanBeginEvent, no SpanEndEvent
        assert len(events) == 1
        assert isinstance(events[0], SpanBeginEvent)

    @pytest.mark.asyncio
    async def test_empty_runs_list(self) -> None:
        """Empty runs list should return empty events list."""
        events = await runs_to_events([])
        assert len(events) == 0
