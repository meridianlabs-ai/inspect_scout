"""Tests for W&B Weave event conversion."""

import pytest

from tests.sources.weave_source.mocks import (
    create_anthropic_llm_call,
    create_multiturn_trace,
    create_openai_llm_call,
    create_openai_llm_call_with_tools,
    create_span_call,
    create_tool_call,
    create_trace_with_tool_calls,
)


class TestToModelEvent:
    """Tests for to_model_event function."""

    @pytest.mark.asyncio
    async def test_openai_llm_call(self) -> None:
        """Convert OpenAI LLM call to ModelEvent."""
        from inspect_scout.sources._weave.events import to_model_event

        call = create_openai_llm_call()
        event = await to_model_event(call)

        assert event.event == "model"
        assert event.model is not None
        assert "gpt" in event.model.lower()
        assert len(event.input) >= 2  # system + user
        assert event.output is not None

    @pytest.mark.asyncio
    async def test_anthropic_llm_call(self) -> None:
        """Convert Anthropic LLM call to ModelEvent."""
        from inspect_scout.sources._weave.events import to_model_event

        call = create_anthropic_llm_call()
        event = await to_model_event(call)

        assert event.event == "model"
        assert event.model is not None
        assert "claude" in event.model.lower()
        assert event.output is not None

    @pytest.mark.asyncio
    async def test_llm_call_with_tools(self) -> None:
        """Convert LLM call with tool definitions to ModelEvent."""
        from inspect_scout.sources._weave.events import to_model_event

        call = create_openai_llm_call_with_tools()
        event = await to_model_event(call)

        assert event.event == "model"
        assert len(event.tools) >= 1
        assert event.tools[0].name == "get_weather"

    @pytest.mark.asyncio
    async def test_model_event_timestamps(self) -> None:
        """Verify ModelEvent has correct timestamps."""
        from inspect_scout.sources._weave.events import to_model_event

        call = create_openai_llm_call()
        event = await to_model_event(call)

        assert event.timestamp is not None
        assert event.completed is not None
        assert event.completed >= event.timestamp


class TestToToolEvent:
    """Tests for to_tool_event function."""

    def test_tool_call_conversion(self) -> None:
        """Convert tool call to ToolEvent."""
        from inspect_scout.sources._weave.events import to_tool_event

        call = create_tool_call(tool_name="get_weather")
        event = to_tool_event(call)

        assert event.event == "tool"
        assert event.function == "get_weather"
        assert event.arguments is not None
        assert event.result is not None

    def test_tool_call_with_error(self) -> None:
        """Convert tool call with error to ToolEvent."""
        from inspect_scout.sources._weave.events import to_tool_event

        call = create_tool_call()
        call.exception = "Tool execution failed"
        event = to_tool_event(call)

        assert event.event == "tool"
        assert event.error is not None
        assert "failed" in event.error.message.lower()

    def test_tool_event_timestamps(self) -> None:
        """Verify ToolEvent has correct timestamps."""
        from inspect_scout.sources._weave.events import to_tool_event

        call = create_tool_call()
        event = to_tool_event(call)

        assert event.timestamp is not None
        assert event.completed is not None


class TestToSpanEvents:
    """Tests for span event conversion."""

    def test_span_begin_event(self) -> None:
        """Convert span call to SpanBeginEvent."""
        from inspect_scout.sources._weave.events import to_span_begin_event

        call = create_span_call(name="agent_run")
        event = to_span_begin_event(call)

        assert event.event == "span_begin"
        assert event.name == "agent_run"
        assert event.id is not None

    def test_span_end_event(self) -> None:
        """Convert span call to SpanEndEvent."""
        from inspect_scout.sources._weave.events import to_span_end_event

        call = create_span_call(name="agent_run")
        event = to_span_end_event(call)

        assert event.event == "span_end"
        assert event.id is not None

    def test_span_parent_id(self) -> None:
        """Verify parent_id is captured in span events."""
        from inspect_scout.sources._weave.events import to_span_begin_event

        call = create_span_call(name="child_span", parent_id="parent-123")
        event = to_span_begin_event(call)

        assert event.parent_id == "parent-123"


class TestCallsToEvents:
    """Tests for calls_to_events function."""

    @pytest.mark.asyncio
    async def test_trace_with_tool_calls(self) -> None:
        """Convert trace with tool calls to events."""
        from inspect_scout.sources._weave.events import calls_to_events

        calls = create_trace_with_tool_calls()
        events = await calls_to_events(calls)

        # Should have multiple events
        assert len(events) > 0

        # Should include model events
        model_events = [e for e in events if e.event == "model"]
        assert len(model_events) >= 1

        # Should include tool events
        tool_events = [e for e in events if e.event == "tool"]
        assert len(tool_events) >= 1

        # Should include span events
        span_events = [e for e in events if e.event in ("span_begin", "span_end")]
        assert len(span_events) >= 2  # begin + end

    @pytest.mark.asyncio
    async def test_multiturn_trace(self) -> None:
        """Convert multi-turn trace to events."""
        from inspect_scout.sources._weave.events import calls_to_events

        calls = create_multiturn_trace()
        events = await calls_to_events(calls)

        # Should have model events for each turn
        model_events = [e for e in events if e.event == "model"]
        assert len(model_events) >= 3  # 3 turns

    @pytest.mark.asyncio
    async def test_events_chronological_order(self) -> None:
        """Verify events are in chronological order."""
        from inspect_scout.sources._weave.events import calls_to_events

        calls = create_trace_with_tool_calls()
        events = await calls_to_events(calls)

        # Check timestamps are in order
        for i in range(len(events) - 1):
            t1 = events[i].timestamp
            t2 = events[i + 1].timestamp
            if t1 and t2:
                assert t1 <= t2, "Events should be in chronological order"

    @pytest.mark.asyncio
    async def test_empty_calls_list(self) -> None:
        """Handle empty calls list."""
        from inspect_scout.sources._weave.events import calls_to_events

        events = await calls_to_events([])
        assert events == []
