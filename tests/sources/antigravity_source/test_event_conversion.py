"""Unit tests for Antigravity step conversion helpers."""

from __future__ import annotations

import logging

import pytest
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    ContentReasoning,
    ContentText,
    ModelUsage,
)
from inspect_scout.sources._antigravity.events import (
    Step,
    ToolCallPairer,
    checkpoint_index,
    model_from_settings,
    parse_settings_change,
    parse_user_request,
    step_to_messages,
    step_tool_calls,
    to_compaction_event,
    to_model_event,
)
from inspect_scout.sources._antigravity.transcripts import (
    _MAX_SUBAGENT_DEPTH,
    _create_subagent_span_events,
)

CHROME_CONTENT = (
    "<USER_REQUEST>\nSay hello\n</USER_REQUEST>\n"
    "<ADDITIONAL_METADATA>\nThe current local time is: 2026-08-21T04:23:13-07:00.\n"
    "</ADDITIONAL_METADATA>\n"
    "<USER_SETTINGS_CHANGE>\nThe user changed setting `Model Selection` from None "
    "to Gemini 3.7 Flash (High). No need to comment on this change if the user "
    "doesn't ask about it.\n</USER_SETTINGS_CHANGE>"
)


class TestModelEventConversion:
    """Tests for to_model_event()."""

    def test_planner_step(self) -> None:
        """Planner step → ModelEvent with sentinel fields."""
        step = Step(
            step_index=2,
            type="PLANNER_RESPONSE",
            content="Hello there!",
            created_at="2026-08-21T11:23:15Z",
        )
        msg = ChatMessageAssistant(content="Hello there!")
        usage = ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150)

        result = to_model_event(
            step,
            prior_messages=[],
            assistant_message=msg,
            model="gemini-test",
            usage=usage,
        )

        assert result.model == "gemini-test"
        assert result.tools == []
        assert result.tool_choice == "auto"
        assert result.output.usage is not None
        assert result.output.usage.input_tokens == 100
        assert result.timestamp.isoformat() == "2026-08-21T11:23:15+00:00"
        assert result.completed == result.timestamp
        assert result.output.metadata == {"antigravity_synthesized": True}

    def test_without_usage(self) -> None:
        """Usage is optional — absent generation metadata → usage None."""
        step = Step(step_index=2, type="PLANNER_RESPONSE", content="hi")
        result = to_model_event(
            step,
            prior_messages=[],
            assistant_message=ChatMessageAssistant(content="hi"),
            model="unknown",
            usage=None,
        )
        assert result.output.usage is None


class TestCompactionEventConversion:
    """Tests for checkpoint_index() and to_compaction_event()."""

    def test_checkpoint_index(self) -> None:
        """Checkpoint 0 is the session preamble; later N are compactions."""
        session_start = Step(
            step_index=1, type="CHECKPOINT", content="{{ CHECKPOINT 0 }}\nsummary"
        )
        compaction = Step(
            step_index=51, type="CHECKPOINT", content="{{ CHECKPOINT 1 }}\nsummary"
        )
        unmarked = Step(step_index=2, type="PLANNER_RESPONSE", content="hello")
        assert checkpoint_index(session_start) == 0
        assert checkpoint_index(compaction) == 1
        assert checkpoint_index(unmarked) is None

    def test_boundary_marker_only(self) -> None:
        """Compaction checkpoint → CompactionEvent carrying just the boundary.

        The checkpoint content itself enters the message stream (covered in
        the integration tests), matching claude_code.
        """
        step = Step(
            step_index=51,
            type="CHECKPOINT",
            content="{{ CHECKPOINT 1 }}\n# Previous Session Summary",
            created_at="2026-08-22T09:30:00Z",
        )
        event = to_compaction_event(step)
        assert event.source == "antigravity"
        assert event.type == "summary"  # default, matching claude_code/atif
        assert event.metadata == {"checkpoint_index": 1}


class TestUserInputParsing:
    """Tests for parse_user_request(), parse_settings_change(), model_from_settings()."""

    def test_with_chrome(self) -> None:
        """Chrome-templated content → bare request text + settings chrome."""
        assert parse_user_request(CHROME_CONTENT) == "Say hello"
        settings = parse_settings_change(CHROME_CONTENT)
        assert settings is not None
        assert "Model Selection" in settings

    def test_bare(self) -> None:
        """Content without the template passes through unchanged."""
        assert parse_user_request("Research the repo structure") == (
            "Research the repo structure"
        )
        assert parse_settings_change("Research the repo structure") is None

    def test_model_from_settings(self) -> None:
        """Model display name is parsed from the settings-change chrome."""
        settings = parse_settings_change(CHROME_CONTENT)
        assert settings is not None
        assert model_from_settings(settings) == "Gemini 3.7 Flash (High)"


class TestToolCallPairing:
    """Tests for step_tool_calls() and positional result pairing."""

    def test_parallel_calls(self) -> None:
        """Consecutive GENERIC results pair FIFO with a planner's parallel calls."""
        pairer = ToolCallPairer()
        planner = Step.model_validate(
            {
                "step_index": 1,
                "type": "PLANNER_RESPONSE",
                "tool_calls": [
                    {"name": "list_dir", "args": {"DirectoryPath": "/repo"}},
                    {"name": "grep_search", "args": {"Query": "package"}},
                ],
            }
        )
        calls = step_tool_calls(planner)
        step_to_messages(planner, calls, pairer)
        pairer.push(calls)

        result_1 = Step(step_index=2, type="GENERIC", content="src/ tests/")
        result_2 = Step(step_index=3, type="GENERIC", content="2 matches")
        [tool_1] = step_to_messages(result_1, [], pairer)
        [tool_2] = step_to_messages(result_2, [], pairer)
        assert isinstance(tool_1, ChatMessageTool)
        assert isinstance(tool_2, ChatMessageTool)
        assert tool_1.function == "list_dir"
        assert tool_1.tool_call_id == calls[0].id
        assert tool_2.function == "grep_search"
        assert tool_2.tool_call_id == calls[1].id

    def test_generic_without_pending_call(self) -> None:
        """Orphaned results (interrupted turns) get an unknown function."""
        [tool] = step_to_messages(
            Step(step_index=5, type="GENERIC", content="orphan"), [], ToolCallPairer()
        )
        assert isinstance(tool, ChatMessageTool)
        assert tool.function == "unknown"


class TestStepToMessages:
    """Tests for step_to_messages()."""

    def test_user_input_strips_chrome(self) -> None:
        """USER_INPUT chrome is stripped down to the bare request text."""
        step = Step(step_index=0, type="USER_INPUT", content=CHROME_CONTENT)
        [message] = step_to_messages(step, [], ToolCallPairer())
        assert isinstance(message, ChatMessageUser)
        assert message.text == "Say hello"

    def test_planner_step_with_thinking(self) -> None:
        """Thinking → leading ContentReasoning part."""
        step = Step.model_validate(
            {
                "step_index": 2,
                "type": "PLANNER_RESPONSE",
                "thinking": "I should check.",
                "content": "Checking now.",
            }
        )
        messages = step_to_messages(step, step_tool_calls(step), ToolCallPairer())
        assert len(messages) == 1
        assistant = messages[0]
        assert isinstance(assistant, ChatMessageAssistant)
        assert isinstance(assistant.content, list)
        assert isinstance(assistant.content[0], ContentReasoning)
        assert assistant.content[0].reasoning == "I should check."
        assert isinstance(assistant.content[1], ContentText)

    def test_empty_planner_step_yields_no_messages(self) -> None:
        """Empty planner steps (preceding stream errors) are dropped."""
        step = Step(step_index=3, type="PLANNER_RESPONSE")
        assert step_to_messages(step, [], ToolCallPairer()) == []

    def test_error_and_system_steps_become_system_messages(self) -> None:
        """ERROR_MESSAGE and SYSTEM_MESSAGE steps → ChatMessageSystem."""
        error = Step(step_index=5, type="ERROR_MESSAGE", content="Error: interrupted.")
        system = Step(step_index=6, type="SYSTEM_MESSAGE", content="[Message] hi")
        [error_msg] = step_to_messages(error, [], ToolCallPairer())
        [system_msg] = step_to_messages(system, [], ToolCallPairer())
        assert isinstance(error_msg, ChatMessageSystem)
        assert isinstance(system_msg, ChatMessageSystem)

    def test_unknown_step_type_with_content(self) -> None:
        """Unknown step types from future CLI versions degrade to system text."""
        step = Step(step_index=7, type="FUTURE_TYPE", content="something new")
        [message] = step_to_messages(step, [], ToolCallPairer())
        assert isinstance(message, ChatMessageSystem)
        assert message.text == "something new"

    def test_unknown_step_type_without_content(self) -> None:
        """Unknown step types without content are dropped."""
        step = Step(step_index=8, type="FUTURE_TYPE")
        assert step_to_messages(step, [], ToolCallPairer()) == []


class TestCreateSubagentSpanEvents:
    """Tests for _create_subagent_span_events()."""

    def test_missing_child_produces_no_events(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A child with no on-disk data (e.g. a cancelled spawn) → no events + warning."""
        with caplog.at_level(logging.WARNING):
            events = _create_subagent_span_events(
                "dddddddd-0000-0000-0000-000000000004",
                records_by_id={},
                roles={},
                depth=0,
            )
        assert events == []
        assert any("not found on disk" in r.message for r in caplog.records)

    def test_max_depth_produces_no_events(self) -> None:
        """Depth-capped recursion (guards reference cycles) → no events."""
        events = _create_subagent_span_events(
            "dddddddd-0000-0000-0000-000000000004",
            records_by_id={},
            roles={},
            depth=_MAX_SUBAGENT_DEPTH,
        )
        assert events == []
