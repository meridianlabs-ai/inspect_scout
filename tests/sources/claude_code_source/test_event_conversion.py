"""Tests for Claude Code event conversion (events.py)."""

from datetime import datetime, timezone
from typing import Any

import pytest
from inspect_ai.event import (
    CompactionEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import ContentReasoning, ContentText, ModelOutput, ModelUsage
from inspect_ai.model._chat_message import ChatMessageAssistant
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model_output import ChatCompletionChoice
from inspect_scout.sources._claude_code.events import (
    _extract_agent_id_from_result,
    process_parsed_events,
    to_model_event,
    to_tool_event,
)
from inspect_scout.sources._claude_code.models import (
    AssistantEvent,
    AssistantMessage,
    CompactMetadata,
    ContentToolUse,
    SystemEvent,
    Usage,
    UserEvent,
    UserMessage,
)

TS = "2026-01-15T12:00:00Z"
DT = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestModelEventConversion:
    """Tests for to_model_event()."""

    def test_text_content_with_usage(self) -> None:
        """AssistantEvent with text content + usage → produces correct ModelEvent."""
        event = AssistantEvent(
            uuid="1",
            timestamp=TS,
            sessionId="test",
            type="assistant",
            message=AssistantMessage(
                model="claude-sonnet-4-20250514",
                content=[{"type": "text", "text": "Hello there!"}],
                usage=Usage(input_tokens=100, output_tokens=50),
            ),
        )
        result = to_model_event(event, input_messages=[], timestamp=DT)

        assert isinstance(result, ModelEvent)
        assert result.model == "claude-sonnet-4-20250514"
        assert result.timestamp == DT
        assert result.input == []
        assert result.output is not None
        assert result.output.model == "claude-sonnet-4-20250514"
        assert result.output.usage is not None
        assert result.output.usage.input_tokens == 100
        assert result.output.usage.output_tokens == 50
        # Output message should be text
        msg = result.output.choices[0].message
        assert msg.content == "Hello there!"
        assert result.output.choices[0].stop_reason == "stop"

    def test_tool_use_blocks(self) -> None:
        """AssistantEvent with tool_use blocks → produces ModelEvent with tool_calls."""
        event = AssistantEvent(
            uuid="2",
            timestamp=TS,
            sessionId="test",
            type="assistant",
            message=AssistantMessage(
                model="claude-sonnet-4-20250514",
                content=[
                    {"type": "text", "text": "Let me read that file."},
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "Read",
                        "input": {"file_path": "/test.py"},
                    },
                ],
            ),
        )
        result = to_model_event(event, input_messages=[])

        msg = result.output.choices[0].message
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "tool_1"
        assert msg.tool_calls[0].function == "Read"
        assert msg.tool_calls[0].arguments == {"file_path": "/test.py"}
        assert result.output.choices[0].stop_reason == "tool_calls"

    def test_thinking_blocks(self) -> None:
        """AssistantEvent with thinking blocks → produces ModelEvent with ContentReasoning."""
        event = AssistantEvent(
            uuid="3",
            timestamp=TS,
            sessionId="test",
            type="assistant",
            message=AssistantMessage(
                model="claude-opus-4-5-20251101",
                content=[
                    {
                        "type": "thinking",
                        "thinking": "Let me reason about this...",
                        "signature": "sig123",
                    },
                    {"type": "text", "text": "Here's my answer."},
                ],
            ),
        )
        result = to_model_event(event, input_messages=[])

        msg = result.output.choices[0].message
        # Content should be a list with reasoning + text
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2
        assert isinstance(msg.content[0], ContentReasoning)
        assert msg.content[0].reasoning == "Let me reason about this..."
        assert isinstance(msg.content[1], ContentText)
        assert msg.content[1].text == "Here's my answer."


class TestToolEventConversion:
    """Tests for to_tool_event()."""

    def test_text_result(self) -> None:
        """User event with text tool result → produces ToolEvent with correct fields."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_1",
            name="Read",
            input={"file_path": "/test.py"},
        )
        tool_result: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": "tool_1",
            "content": "file contents here",
        }
        completed = datetime(2026, 1, 15, 12, 0, 5, tzinfo=timezone.utc)
        result = to_tool_event(block, tool_result, DT, completed=completed)

        assert isinstance(result, ToolEvent)
        assert result.function == "Read"
        assert result.id == "tool_1"
        assert result.arguments == {"file_path": "/test.py"}
        assert result.result == "file contents here"
        assert result.timestamp == DT
        assert result.completed == completed
        assert result.error is None

    def test_error_result(self) -> None:
        """User event with error tool result → produces ToolEvent with error info."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_2",
            name="Bash",
            input={"command": "rm -rf /"},
        )
        tool_result: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": "tool_2",
            "content": "Permission denied",
            "is_error": True,
        }
        result = to_tool_event(block, tool_result, DT)

        assert result.error is not None
        assert result.error.message == "Permission denied"
        assert result.result == "Permission denied"

    def test_list_content_result(self) -> None:
        """User event with list content tool result → text is extracted and joined."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_3",
            name="Read",
            input={"file_path": "/big.py"},
        )
        tool_result: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": "tool_3",
            "content": [
                {"type": "text", "text": "line one"},
                {"type": "text", "text": "line two"},
            ],
        }
        result = to_tool_event(block, tool_result, DT)
        assert result.result == "line one\nline two"

    def test_no_result(self) -> None:
        """Tool with None result → produces ToolEvent with empty result."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_4",
            name="Bash",
            input={"command": "echo hello"},
        )
        result = to_tool_event(block, None, DT)
        assert result.result == ""
        assert result.error is None


class TestAgentIdExtraction:
    """Tests for _extract_agent_id_from_result()."""

    def test_json_agent_id(self) -> None:
        """String result containing JSON with agentId → extracts via JSON parse."""
        tool_result: dict[str, Any] = {
            "content": [
                {
                    "type": "text",
                    "text": '{"agentId": "abc123", "other": "data"}',
                }
            ]
        }
        assert _extract_agent_id_from_result(tool_result) == "abc123"

    def test_regex_agent_id(self) -> None:
        """String result containing agentId=xxx → extracts via regex."""
        tool_result: dict[str, Any] = {
            "content": [
                {
                    "type": "text",
                    "text": "agentId: a842e4a (for resuming to continue)",
                }
            ]
        }
        assert _extract_agent_id_from_result(tool_result) == "a842e4a"

    def test_plain_string_no_agent_id(self) -> None:
        """Plain string with no agent ID → returns None."""
        tool_result: dict[str, Any] = {
            "content": [{"type": "text", "text": "Some regular output text"}]
        }
        assert _extract_agent_id_from_result(tool_result) is None

    def test_empty_content(self) -> None:
        """Empty content list → returns None."""
        tool_result: dict[str, Any] = {"content": []}
        assert _extract_agent_id_from_result(tool_result) is None

    def test_non_list_content(self) -> None:
        """Non-list content → returns None."""
        tool_result: dict[str, Any] = {"content": "just a string"}
        assert _extract_agent_id_from_result(tool_result) is None

    def test_embedded_json_in_text(self) -> None:
        """Text with embedded JSON containing agentId → extracts via regex fallback."""
        tool_result: dict[str, Any] = {
            "content": [
                {
                    "type": "text",
                    "text": 'Result was good. "agentId": "def456" found.',
                }
            ]
        }
        assert _extract_agent_id_from_result(tool_result) == "def456"


class TestProcessParsedEvents:
    """Tests for process_parsed_events() — lightweight integration."""

    @pytest.mark.asyncio
    async def test_user_assistant_sequence(self) -> None:
        """List of user + assistant events → produces correct sequence of ModelEvents."""
        events = [
            UserEvent(
                uuid="1",
                timestamp="2026-01-15T12:00:00Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Hello"),
            ),
            AssistantEvent(
                uuid="2",
                parentUuid="1",
                timestamp="2026-01-15T12:00:01Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    model="claude-sonnet-4-20250514",
                    content=[{"type": "text", "text": "Hi there!"}],
                    usage=Usage(input_tokens=50, output_tokens=20),
                ),
            ),
            UserEvent(
                uuid="3",
                parentUuid="2",
                timestamp="2026-01-15T12:00:02Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Thanks"),
            ),
            AssistantEvent(
                uuid="4",
                parentUuid="3",
                timestamp="2026-01-15T12:00:03Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    model="claude-sonnet-4-20250514",
                    content=[{"type": "text", "text": "You're welcome!"}],
                    usage=Usage(input_tokens=80, output_tokens=15),
                ),
            ),
        ]

        result: list[Any] = []
        async for evt in process_parsed_events(events, max_depth=0):
            result.append(evt)

        model_events = [e for e in result if isinstance(e, ModelEvent)]
        assert len(model_events) == 2
        assert model_events[0].model == "claude-sonnet-4-20250514"
        # Second model event should have accumulated input messages
        assert len(model_events[1].input) > 0

    @pytest.mark.asyncio
    async def test_compaction_boundary(self) -> None:
        """Events with compaction boundary → produces CompactionEvent."""
        events = [
            UserEvent(
                uuid="1",
                timestamp="2026-01-15T12:00:00Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Hello"),
            ),
            SystemEvent(
                uuid="2",
                timestamp="2026-01-15T12:01:00Z",
                sessionId="test",
                type="system",
                subtype="compact_boundary",
                content="Conversation compacted",
                compactMetadata=CompactMetadata(trigger="auto", preTokens=150000),
            ),
        ]

        result: list[Any] = []
        async for evt in process_parsed_events(events, max_depth=0):
            result.append(evt)

        compaction_events = [e for e in result if isinstance(e, CompactionEvent)]
        assert len(compaction_events) == 1
        assert compaction_events[0].tokens_before == 150000

    @pytest.mark.asyncio
    async def test_task_tool_call_produces_spans(self) -> None:
        """Events with Task tool call + result → produces SpanBegin/End events."""
        events = [
            UserEvent(
                uuid="1",
                timestamp="2026-01-15T12:00:00Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Search for config files"),
            ),
            AssistantEvent(
                uuid="2",
                parentUuid="1",
                timestamp="2026-01-15T12:00:01Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    model="claude-sonnet-4-20250514",
                    content=[
                        {"type": "text", "text": "Let me search for that."},
                        {
                            "type": "tool_use",
                            "id": "task_1",
                            "name": "Task",
                            "input": {
                                "subagent_type": "Explore",
                                "description": "Find config files",
                                "prompt": "Search for config files",
                            },
                        },
                    ],
                ),
            ),
            UserEvent(
                uuid="3",
                parentUuid="2",
                timestamp="2026-01-15T12:00:05Z",
                sessionId="test",
                type="user",
                message=UserMessage(
                    content=[
                        {
                            "type": "tool_result",
                            "tool_use_id": "task_1",
                            "content": "Found 3 config files",
                        }
                    ]
                ),
            ),
        ]

        result: list[Any] = []
        async for evt in process_parsed_events(events, max_depth=0):
            result.append(evt)

        span_begins = [e for e in result if isinstance(e, SpanBeginEvent)]
        span_ends = [e for e in result if isinstance(e, SpanEndEvent)]
        tool_events = [e for e in result if isinstance(e, ToolEvent)]

        # Should have an agent span (begin + end)
        assert len(span_begins) >= 1
        assert len(span_ends) >= 1
        # Should have a tool event inside the span
        assert len(tool_events) >= 1
        assert tool_events[0].function == "Task"

        # Agent span should be named after the subagent type
        agent_spans = [s for s in span_begins if s.type == "agent"]
        assert len(agent_spans) == 1
        assert agent_spans[0].name == "Explore"

    @pytest.mark.asyncio
    async def test_compaction_resets_accumulated_messages(self) -> None:
        """Post-compaction ModelEvent.input contains only post-compaction messages."""
        events = [
            # Pre-compaction: user + assistant
            UserEvent(
                uuid="1",
                timestamp="2026-01-15T12:00:00Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Hello before compaction"),
            ),
            AssistantEvent(
                uuid="2",
                parentUuid="1",
                timestamp="2026-01-15T12:00:01Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    model="claude-sonnet-4-20250514",
                    content=[{"type": "text", "text": "Response before compaction"}],
                    usage=Usage(input_tokens=50, output_tokens=20),
                ),
            ),
            # Compaction boundary
            SystemEvent(
                uuid="3",
                timestamp="2026-01-15T12:01:00Z",
                sessionId="test",
                type="system",
                subtype="compact_boundary",
                content="Conversation compacted",
                compactMetadata=CompactMetadata(trigger="auto", preTokens=100000),
            ),
            # Post-compaction: summary + new user + assistant
            UserEvent(
                uuid="4",
                timestamp="2026-01-15T12:01:01Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Summary of previous conversation"),
            ),
            UserEvent(
                uuid="5",
                timestamp="2026-01-15T12:01:02Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Continue the work"),
            ),
            AssistantEvent(
                uuid="6",
                parentUuid="5",
                timestamp="2026-01-15T12:01:03Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    model="claude-sonnet-4-20250514",
                    content=[{"type": "text", "text": "Continuing after compaction"}],
                    usage=Usage(input_tokens=80, output_tokens=15),
                ),
            ),
        ]

        result: list[Any] = []
        async for evt in process_parsed_events(events, max_depth=0):
            result.append(evt)

        model_events = [e for e in result if isinstance(e, ModelEvent)]
        assert len(model_events) == 2

        # Pre-compaction ModelEvent should have the user message
        pre_input = model_events[0].input
        pre_content = [m.content for m in pre_input if hasattr(m, "content")]
        assert any("Hello before compaction" in str(c) for c in pre_content)

        # Post-compaction ModelEvent should NOT have pre-compaction messages
        post_input = model_events[1].input
        post_content = [m.content for m in post_input if hasattr(m, "content")]
        assert not any("Hello before compaction" in str(c) for c in post_content)
        assert not any("Response before compaction" in str(c) for c in post_content)
        # But should have the summary and new user message
        assert any("Summary of previous conversation" in str(c) for c in post_content)
        assert any("Continue the work" in str(c) for c in post_content)


class TestSumScoutTokens:
    """Tests for sum_scout_tokens()."""

    def _make_model_event(self, input_tokens: int, output_tokens: int) -> ModelEvent:
        """Helper to create a ModelEvent with usage."""
        msg = ChatMessageAssistant(content="response")
        return ModelEvent(
            model="test-model",
            input=[],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput(
                model="test-model",
                choices=[ChatCompletionChoice(message=msg, stop_reason="stop")],
                usage=ModelUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                ),
            ),
        )

    def test_sums_across_multiple_events(self) -> None:
        """Multiple ModelEvents → sums all total_tokens."""
        from inspect_scout.sources._claude_code.extraction import sum_scout_tokens

        events: list[Any] = [
            self._make_model_event(100, 50),
            self._make_model_event(200, 80),
        ]
        assert sum_scout_tokens(events) == 430

    def test_skips_non_model_events(self) -> None:
        """Non-ModelEvent objects are ignored."""
        from inspect_scout.sources._claude_code.extraction import sum_scout_tokens

        events: list[Any] = [
            self._make_model_event(100, 50),
            ToolEvent(
                function="Read",
                id="t1",
                arguments={},
                result="ok",
            ),
        ]
        assert sum_scout_tokens(events) == 150

    def test_empty_list(self) -> None:
        """Empty event list → returns 0."""
        from inspect_scout.sources._claude_code.extraction import sum_scout_tokens

        assert sum_scout_tokens([]) == 0

    def test_model_event_without_usage(self) -> None:
        """ModelEvent with no usage → contributes 0."""
        from inspect_scout.sources._claude_code.extraction import sum_scout_tokens

        msg = ChatMessageAssistant(content="response")
        event = ModelEvent(
            model="test-model",
            input=[],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput(
                model="test-model",
                choices=[ChatCompletionChoice(message=msg, stop_reason="stop")],
            ),
        )
        assert sum_scout_tokens([event]) == 0
