"""Tests for Logfire event conversion."""

from datetime import datetime

import pytest
from inspect_ai.event import ModelEvent, SpanBeginEvent, SpanEndEvent, ToolEvent
from inspect_scout.sources._logfire.events import (
    spans_to_events,
    to_model_event,
    to_span_begin_event,
    to_span_end_event,
    to_tool_event,
)

from .mocks import (
    create_agent_span,
    create_anthropic_llm_span,
    create_multiturn_openai_spans,
    create_openai_llm_span,
    create_pydantic_ai_agent_trace,
    create_pydantic_ai_span,
    create_tool_span,
)


class TestToModelEvent:
    """Tests for to_model_event function."""

    @pytest.mark.asyncio
    async def test_basic_openai_span(self) -> None:
        """Convert basic OpenAI LLM span to ModelEvent."""
        span = create_openai_llm_span(model="gpt-4o-mini")
        event = await to_model_event(span)

        assert isinstance(event, ModelEvent)
        assert event.model == "gpt-4o-mini"
        assert event.timestamp is not None

    @pytest.mark.asyncio
    async def test_anthropic_span(self) -> None:
        """Convert Anthropic LLM span to ModelEvent."""
        span = create_anthropic_llm_span(model="claude-3-5-haiku-latest")
        event = await to_model_event(span)

        assert isinstance(event, ModelEvent)
        assert event.model == "claude-3-5-haiku-latest"

    @pytest.mark.asyncio
    async def test_model_event_has_output(self) -> None:
        """ModelEvent should have output from span."""
        span = create_openai_llm_span(output_content="Hello! I can help.")
        event = await to_model_event(span)

        assert event.output is not None

    @pytest.mark.asyncio
    async def test_model_event_span_id(self) -> None:
        """ModelEvent should have span_id from parent."""
        span = create_openai_llm_span(parent_span_id="parent-123")
        event = await to_model_event(span)

        assert event.span_id == "parent-123"


class TestToToolEvent:
    """Tests for to_tool_event function."""

    def test_basic_tool_span(self) -> None:
        """Convert basic tool span to ToolEvent."""
        span = create_tool_span(
            tool_name="get_weather",
            arguments={"city": "San Francisco"},
            result="Sunny, 72F",
        )
        event = to_tool_event(span)

        assert isinstance(event, ToolEvent)
        assert event.function == "get_weather"
        assert event.arguments == {"city": "San Francisco"}
        assert event.result == "Sunny, 72F"

    def test_tool_event_with_error(self) -> None:
        """Convert tool span with error to ToolEvent."""
        span = create_tool_span(
            tool_name="get_weather",
            error="City not found",
        )
        event = to_tool_event(span)

        assert isinstance(event, ToolEvent)
        assert event.error is not None
        assert "City not found" in event.error.message

    def test_tool_event_span_id(self) -> None:
        """ToolEvent should have span_id from parent."""
        span = create_tool_span(parent_span_id="llm-span-123")
        event = to_tool_event(span)

        assert event.span_id == "llm-span-123"


class TestToSpanEvents:
    """Tests for span begin/end event conversion."""

    def test_span_begin_event(self) -> None:
        """Convert agent span to SpanBeginEvent."""
        span = create_agent_span(span_id="agent-1", agent_name="assistant")
        event = to_span_begin_event(span)

        assert isinstance(event, SpanBeginEvent)
        assert event.id == "agent-1"
        assert "assistant" in event.name

    def test_span_end_event(self) -> None:
        """Convert agent span to SpanEndEvent."""
        span = create_agent_span(span_id="agent-1")
        event = to_span_end_event(span)

        assert isinstance(event, SpanEndEvent)
        assert event.id == "agent-1"


class TestPydanticAIModelEvent:
    """Tests for Pydantic AI model event conversion."""

    @pytest.mark.asyncio
    async def test_pydantic_ai_span_to_model_event(self) -> None:
        """Convert Pydantic AI LLM span to ModelEvent."""
        span = create_pydantic_ai_span(model="gpt-4o-mini")
        event = await to_model_event(span)

        assert isinstance(event, ModelEvent)
        assert event.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_pydantic_ai_agent_trace_events(self) -> None:
        """Convert full Pydantic AI agent trace to events."""
        spans = create_pydantic_ai_agent_trace(with_tools=True)
        events = await spans_to_events(spans)

        # Should have ModelEvents, ToolEvent, SpanBegin/End
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        tool_events = [e for e in events if isinstance(e, ToolEvent)]
        span_begin_events = [e for e in events if isinstance(e, SpanBeginEvent)]

        assert len(model_events) >= 1  # At least one LLM call
        assert len(tool_events) == 1  # One tool execution
        assert len(span_begin_events) == 1  # Agent span


class TestMultiturnEvents:
    """Tests for multi-turn conversation event conversion."""

    @pytest.mark.asyncio
    async def test_multiturn_events_count(self) -> None:
        """Multi-turn conversation produces correct number of events."""
        spans = create_multiturn_openai_spans()
        events = await spans_to_events(spans)

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert len(model_events) == 3  # Three turns

    @pytest.mark.asyncio
    async def test_multiturn_events_ordered(self) -> None:
        """Multi-turn events are in chronological order."""
        spans = create_multiturn_openai_spans()
        events = await spans_to_events(spans)

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert len(model_events) == 3

        # Events should be in chronological order
        for i in range(len(model_events) - 1):
            assert model_events[i].timestamp <= model_events[i + 1].timestamp


class TestSpansToEvents:
    """Tests for spans_to_events function."""

    @pytest.mark.asyncio
    async def test_convert_mixed_spans(self) -> None:
        """Convert list of mixed span types to events."""
        llm_span = create_openai_llm_span(span_id="llm-1")
        tool_span = create_tool_span(span_id="tool-1")
        agent_span = create_agent_span(span_id="agent-1")

        events = await spans_to_events([llm_span, tool_span, agent_span])

        # Should have ModelEvent, ToolEvent, SpanBeginEvent, SpanEndEvent
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        tool_events = [e for e in events if isinstance(e, ToolEvent)]
        span_begin_events = [e for e in events if isinstance(e, SpanBeginEvent)]
        span_end_events = [e for e in events if isinstance(e, SpanEndEvent)]

        assert len(model_events) == 1
        assert len(tool_events) == 1
        assert len(span_begin_events) == 1
        assert len(span_end_events) == 1

    @pytest.mark.asyncio
    async def test_events_sorted_by_timestamp(self) -> None:
        """Events should be sorted by timestamp."""
        now = datetime.now()

        # Create spans with different timestamps
        span1 = create_openai_llm_span(span_id="span-1")
        span1["start_timestamp"] = now

        span2 = create_openai_llm_span(span_id="span-2")
        # Make span2 earlier by subtracting time
        from datetime import timedelta

        span2["start_timestamp"] = now - timedelta(seconds=10)

        events = await spans_to_events([span1, span2])

        # Events should be sorted chronologically
        assert len(events) == 2
        assert events[0].timestamp <= events[1].timestamp

    @pytest.mark.asyncio
    async def test_empty_spans_returns_empty_events(self) -> None:
        """Empty span list returns empty event list."""
        events = await spans_to_events([])
        assert events == []
