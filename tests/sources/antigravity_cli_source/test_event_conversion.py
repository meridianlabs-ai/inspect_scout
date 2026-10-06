"""Unit tests for Antigravity step conversion helpers."""

from __future__ import annotations

import logging

import pytest
from inspect_ai.event import Event, InfoEvent, ModelEvent, SpanBeginEvent, ToolEvent
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    ContentReasoning,
    ContentText,
    ModelUsage,
)
from inspect_scout.sources._antigravity_cli.client import GenerationInfo
from inspect_scout.sources._antigravity_cli.events import (
    Step,
    StepToolCall,
    ToolCallPairer,
    checkpoint_index,
    is_tool_result_step,
    model_from_settings,
    parse_settings_change,
    parse_user_request,
    step_to_messages,
    step_tool_calls,
    to_compaction_event,
    to_model_event,
)
from inspect_scout.sources._antigravity_cli.transcripts import (
    _MAX_SUBAGENT_DEPTH,
    _ConversionInfo,
    _convert_steps,
    _create_subagent_span_events,
    _extract_child_conversation_ids,
)

SPAWN_RESULT = (
    "Created the following subagents:\n"
    '{"conversationId": "dddddddd-0000-0000-0000-000000000004"}'
)

CHROME_CONTENT = (
    "<USER_REQUEST>\nSay hello\n</USER_REQUEST>\n"
    "<ADDITIONAL_METADATA>\nThe current local time is: 2026-08-21T04:23:13-07:00.\n"
    "</ADDITIONAL_METADATA>\n"
    "<USER_SETTINGS_CHANGE>\nThe user changed setting `Model Selection` from None "
    "to Gemini 3.7 Flash (High). No need to comment on this change if the user "
    "doesn't ask about it.\n</USER_SETTINGS_CHANGE>"
)


def _planner(
    step_index: int,
    *calls: tuple[str, dict[str, object]],
    content: str | None = None,
    created_at: str | None = None,
) -> Step:
    return Step(
        step_index=step_index,
        source="MODEL",
        type="PLANNER_RESPONSE",
        content=content,
        created_at=created_at,
        tool_calls=[StepToolCall(name=name, args=dict(args)) for name, args in calls]
        or None,
    )


def _result(step_index: int, content: str) -> Step:
    return Step(step_index=step_index, source="MODEL", type="GENERIC", content=content)


def _convert(
    steps: list[Step],
    generations: list[GenerationInfo] | None = None,
    roles: dict[str, str] | None = None,
) -> tuple[list[ChatMessage], list[Event], _ConversionInfo]:
    return _convert_steps(
        steps,
        generations or [],
        conversation_id="root",
        records_by_id={},
        roles=roles if roles is not None else {},
        depth=0,
        inlining=frozenset(),
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
        assert result.output.metadata == {"antigravity_cli_synthesized": True}

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
        assert event.source == "antigravity_cli"
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
        """Consecutive result steps pair FIFO with a planner's parallel calls."""
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
        assert pairer.advance(planner, calls).call is None

        result_1 = Step(
            step_index=2, source="MODEL", type="GENERIC", content="src/ tests/"
        )
        result_2 = Step(
            step_index=3, source="MODEL", type="GREP_SEARCH", content="2 matches"
        )
        [tool_1] = step_to_messages(result_1, [], pairer.advance(result_1, []).call)
        [tool_2] = step_to_messages(result_2, [], pairer.advance(result_2, []).call)
        assert isinstance(tool_1, ChatMessageTool)
        assert isinstance(tool_2, ChatMessageTool)
        assert tool_1.function == "list_dir"
        assert tool_1.tool_call_id == calls[0].id
        assert tool_2.function == "grep_search"
        assert tool_2.tool_call_id == calls[1].id

    def test_generic_without_pending_call(self) -> None:
        """Orphaned results (interrupted turns) get an unknown function."""
        [tool] = step_to_messages(
            Step(step_index=5, source="MODEL", type="GENERIC", content="orphan"),
            [],
            None,
        )
        assert isinstance(tool, ChatMessageTool)
        assert tool.function == "unknown"
        assert tool.tool_call_id == "antigravity_cli_5_0"

    def test_new_turn_abandons_pending(self) -> None:
        """Calls still pending when the next planner step arrives are abandoned."""
        pairer = ToolCallPairer()
        first = _planner(1, ("view_file", {}), created_at="2026-08-25T10:00:01Z")
        second = _planner(2, ("run_command", {}))
        pairer.advance(first, step_tool_calls(first))

        pairing = pairer.advance(second, step_tool_calls(second))
        assert [c.function for c in pairing.abandoned] == ["view_file"]
        assert pairing.started is not None
        assert pairing.started.isoformat() == "2026-08-25T10:00:01+00:00"
        assert pairing.call is None

        result = pairer.advance(_result(3, "src/"), [])
        assert result.call is not None
        assert result.call.function == "run_command"
        assert not result.abandoned

    def test_gap_abandons_pending(self) -> None:
        """A step_index jump (a dropped step) abandons pending calls."""
        pairer = ToolCallPairer()
        planner = _planner(1, ("list_dir", {}), ("grep_search", {}))
        pairer.advance(planner, step_tool_calls(planner))
        first = pairer.advance(_result(2, "src/"), [])
        assert first.call is not None
        assert first.call.function == "list_dir"
        assert not first.gap

        # step 3 is missing: it may have been grep_search's result or a new
        # planner step, so the result at step 4 can't be attributed
        after_gap = pairer.advance(_result(4, "2 matches"), [])
        assert after_gap.gap
        assert [c.function for c in after_gap.abandoned] == ["grep_search"]
        assert after_gap.call is None

    def test_finish_abandons_remaining(self) -> None:
        """Calls still pending when the steps run out are abandoned."""
        pairer = ToolCallPairer()
        planner = _planner(1, ("view_file", {}))
        pairer.advance(planner, step_tool_calls(planner))
        assert [c.function for c in pairer.finish().abandoned] == ["view_file"]
        assert pairer.finish().abandoned == []


class TestToolResultDetection:
    """Tests for is_tool_result_step() and the spawn-result scan built on it."""

    @pytest.mark.parametrize(
        ("source", "type_", "expected"),
        [
            ("MODEL", "GENERIC", True),
            ("MODEL", "RUN_COMMAND", True),
            ("MODEL", "INVOKE_SUBAGENT", True),
            ("MODEL", "PLANNER_RESPONSE", False),
            ("SYSTEM", "SYSTEM_MESSAGE", False),
            ("USER_EXPLICIT", "USER_INPUT", False),
            ("", "FUTURE_TYPE", False),
        ],
    )
    def test_is_tool_result_step(self, source: str, type_: str, expected: bool) -> None:
        """Any MODEL-sourced step other than a planner response is a result."""
        assert (
            is_tool_result_step(Step(step_index=0, source=source, type=type_))
            is expected
        )

    def test_typed_spawn_result_yields_child_ids(self) -> None:
        """A typed INVOKE_SUBAGENT result is scanned for child ids like GENERIC."""
        typed = Step(
            step_index=1, source="MODEL", type="INVOKE_SUBAGENT", content=SPAWN_RESULT
        )
        # the marker text inside a system message is not a spawn result
        system = Step(
            step_index=2, source="SYSTEM", type="SYSTEM_MESSAGE", content=SPAWN_RESULT
        )
        assert _extract_child_conversation_ids([typed, system]) == [
            "dddddddd-0000-0000-0000-000000000004"
        ]

    def test_marker_in_ordinary_tool_output_is_not_a_spawn(self) -> None:
        """Only a result paired with invoke_subagent (or typed) names children."""
        quoted = [
            _planner(1, ("run_command", {"CommandLine": "grep"})),
            _result(2, SPAWN_RESULT),
        ]
        assert _extract_child_conversation_ids(quoted) == []

        spawned = [_planner(1, ("invoke_subagent", {})), _result(2, SPAWN_RESULT)]
        assert _extract_child_conversation_ids(spawned) == [
            "dddddddd-0000-0000-0000-000000000004"
        ]


class TestStepToMessages:
    """Tests for step_to_messages()."""

    def test_user_input_strips_chrome(self) -> None:
        """USER_INPUT chrome is stripped down to the bare request text."""
        step = Step(step_index=0, type="USER_INPUT", content=CHROME_CONTENT)
        [message] = step_to_messages(step, [], None)
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
        messages = step_to_messages(step, step_tool_calls(step), None)
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
        assert step_to_messages(step, [], None) == []

    def test_error_and_system_steps_become_system_messages(self) -> None:
        """ERROR_MESSAGE and SYSTEM_MESSAGE steps → ChatMessageSystem."""
        error = Step(step_index=5, type="ERROR_MESSAGE", content="Error: interrupted.")
        system = Step(step_index=6, type="SYSTEM_MESSAGE", content="[Message] hi")
        [error_message] = step_to_messages(error, [], None)
        [system_message] = step_to_messages(system, [], None)
        assert isinstance(error_message, ChatMessageSystem)
        assert isinstance(system_message, ChatMessageSystem)

    def test_unknown_step_type_with_content(self) -> None:
        """Unknown step types from future CLI versions degrade to system text."""
        step = Step(step_index=7, type="FUTURE_TYPE", content="something new")
        [message] = step_to_messages(step, [], None)
        assert isinstance(message, ChatMessageSystem)
        assert message.text == "something new"

    def test_unknown_step_type_without_content(self) -> None:
        """Unknown step types without content are dropped."""
        step = Step(step_index=8, type="FUTURE_TYPE")
        assert step_to_messages(step, [], None) == []


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
                inlining=frozenset(),
            )
        assert events == []
        assert any("not found on disk" in r.message for r in caplog.records)

    def test_max_depth_produces_no_events(self) -> None:
        """Depth-capped nesting → no events."""
        events = _create_subagent_span_events(
            "dddddddd-0000-0000-0000-000000000004",
            records_by_id={},
            roles={},
            depth=_MAX_SUBAGENT_DEPTH,
            inlining=frozenset(),
        )
        assert events == []

    def test_ancestor_produces_no_events(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A child already on the inlining path (spawn cycle) → no events + warning."""
        child_id = "dddddddd-0000-0000-0000-000000000004"
        with caplog.at_level(logging.WARNING):
            events = _create_subagent_span_events(
                child_id,
                records_by_id={},
                roles={},
                depth=0,
                inlining=frozenset({child_id}),
            )
        assert events == []
        assert any("spawns an ancestor" in r.message for r in caplog.records)


class TestConvertSteps:
    """Tests for _convert_steps()."""

    def test_abandoned_call_does_not_claim_later_result(self) -> None:
        """A call with no result is abandoned when the next planner turn begins."""
        steps = [
            Step(
                step_index=0,
                source="MODEL",
                type="PLANNER_RESPONSE",
                tool_calls=[
                    StepToolCall(name="view_file", args={"AbsolutePath": "/x"})
                ],
            ),
            Step(
                step_index=1,
                source="MODEL",
                type="PLANNER_RESPONSE",
                tool_calls=[
                    StepToolCall(name="run_command", args={"CommandLine": "ls"})
                ],
            ),
            Step(step_index=2, source="MODEL", type="GENERIC", content="src/"),
        ]
        messages, _, _ = _convert(steps)
        [tool_message] = [m for m in messages if isinstance(m, ChatMessageTool)]
        assert tool_message.function == "run_command"
        assert tool_message.tool_call_id == "antigravity_cli_1_0"

    def test_abandoned_spawn_does_not_claim_later_role(self) -> None:
        """A spawn with no result is abandoned when the next planner turn begins."""
        steps = [
            Step(
                step_index=0,
                source="MODEL",
                type="PLANNER_RESPONSE",
                tool_calls=[
                    StepToolCall(
                        name="invoke_subagent", args={"Subagents": [{"Role": "first"}]}
                    )
                ],
            ),
            Step(
                step_index=1,
                source="MODEL",
                type="PLANNER_RESPONSE",
                tool_calls=[
                    StepToolCall(
                        name="invoke_subagent", args={"Subagents": [{"Role": "second"}]}
                    )
                ],
            ),
            Step(step_index=2, source="MODEL", type="GENERIC", content=SPAWN_RESULT),
        ]
        roles: dict[str, str] = {}
        _convert(steps, roles=roles)
        assert roles == {"dddddddd-0000-0000-0000-000000000004": "second"}

    def test_unmarked_checkpoint_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        """A CHECKPOINT without a {{ CHECKPOINT N }} marker is dropped with a warning."""
        steps = [
            Step(step_index=0, source="SYSTEM", type="CHECKPOINT", content="summary")
        ]
        with caplog.at_level(logging.WARNING):
            messages, events, info = _convert(steps)
        assert messages == []
        assert events == []
        assert info.compaction_count == 0
        assert any(
            "without a {{ CHECKPOINT N }} marker" in r.message for r in caplog.records
        )

    def test_ordinary_tool_output_does_not_inline(self) -> None:
        """A run_command result quoting the spawn marker inlines nothing."""
        steps = [_planner(1, ("run_command", {})), _result(2, SPAWN_RESULT)]
        _, events, info = _convert(steps)
        assert info.child_ids == []
        assert not any(
            isinstance(e, SpanBeginEvent) and e.type == "agent" for e in events
        )

    def test_later_model_selection_applies_to_later_events(self) -> None:
        """Without generation metadata, each ModelEvent uses the current selection."""
        switch = CHROME_CONTENT.replace(
            "from None to Gemini 3.7 Flash (High)",
            "from Gemini 3.7 Flash (High) to Claude Sonnet 5",
        )
        steps = [
            Step(step_index=0, type="USER_INPUT", content=CHROME_CONTENT),
            _planner(1, content="Sure."),
            Step(step_index=2, type="USER_INPUT", content=switch),
            _planner(3, content="Done."),
        ]
        _, events, info = _convert(steps)
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert [e.model for e in model_events] == [
            "Gemini 3.7 Flash (High)",
            "Claude Sonnet 5",
        ]
        # the transcript-level fallback stays first-selection-wins
        assert info.settings_model == "Gemini 3.7 Flash (High)"

    def test_tool_result_yields_tool_span(self) -> None:
        """Each tool result becomes a ToolEvent inside a tool span."""
        steps = [
            _planner(
                1,
                ("view_file", {"AbsolutePath": "/x"}),
                created_at="2026-08-25T10:00:01Z",
            ),
            Step(
                step_index=2,
                source="MODEL",
                type="GENERIC",
                content="def foo(): ...",
                created_at="2026-08-25T10:00:03Z",
            ),
        ]
        _, events, _ = _convert(steps)
        [span_begin] = [e for e in events if isinstance(e, SpanBeginEvent)]
        [tool_event] = [e for e in events if isinstance(e, ToolEvent)]
        assert span_begin.type == "tool"
        assert span_begin.name == "view_file"
        assert span_begin.id == "tool-root-antigravity_cli_1_0"
        assert tool_event.span_id == span_begin.id
        assert tool_event.id == "antigravity_cli_1_0"
        assert tool_event.arguments == {"AbsolutePath": "/x"}
        assert tool_event.result == "def foo(): ..."
        assert tool_event.timestamp.isoformat() == "2026-08-25T10:00:01+00:00"
        assert tool_event.completed is not None
        assert tool_event.completed.isoformat() == "2026-08-25T10:00:03+00:00"

    def test_unresolved_call_yields_empty_tool_event(self) -> None:
        """A call that never gets a result still appears in the timeline."""
        steps = [_planner(1, ("view_file", {}), created_at="2026-08-25T10:00:01Z")]
        _, events, _ = _convert(steps)
        [tool_event] = [e for e in events if isinstance(e, ToolEvent)]
        assert tool_event.function == "view_file"
        assert tool_event.result == ""
        assert tool_event.completed == tool_event.timestamp

    def test_system_text_yields_info_event(self) -> None:
        """ERROR_MESSAGE/SYSTEM_MESSAGE steps are kept in the timeline as InfoEvents."""
        steps = [
            _planner(1, content="Working."),
            Step(
                step_index=2,
                source="SYSTEM",
                type="ERROR_MESSAGE",
                content="Error: interrupted",
            ),
        ]
        messages, events, _ = _convert(steps)
        [info_event] = [e for e in events if isinstance(e, InfoEvent)]
        assert info_event.source == "antigravity_cli"
        assert info_event.data == "Error: interrupted"
        assert info_event.metadata == {"step_type": "ERROR_MESSAGE"}
        assert isinstance(messages[-1], ChatMessageSystem)

    def test_result_after_dropped_result_is_unknown(self) -> None:
        """A valid result after a dropped step is not attributed to a stale call."""
        steps = [
            _planner(1, ("view_file", {}), ("run_command", {})),
            # step 2 (view_file's result) could not be parsed
            _result(3, "src/"),
        ]
        messages, events, _ = _convert(steps)
        [tool_message] = [m for m in messages if isinstance(m, ChatMessageTool)]
        assert tool_message.function == "unknown"
        assert tool_message.tool_call_id == "antigravity_cli_3_0"
        # both calls are abandoned (empty results); the orphan result is kept
        assert [(e.function, e.result) for e in events if isinstance(e, ToolEvent)] == [
            ("view_file", ""),
            ("run_command", ""),
            ("unknown", "src/"),
        ]

    def test_dropped_planner_resets_turn_and_generations(self) -> None:
        """Steps after a dropped planner step get unknown call and generation."""
        steps = [
            _planner(1, ("grep_search", {}), ("view_file", {})),
            _result(2, "3 matches"),
            # step 3, a planner step with one call, could not be parsed
            _result(4, "def foo(): ..."),
            _planner(5, content="Done."),
        ]
        # one gen_metadata row per real planner step, including the dropped one
        generations = [GenerationInfo(model=f"model-{i}", usage=None) for i in range(3)]
        messages, events, _ = _convert(steps, generations)

        tool_messages = [m for m in messages if isinstance(m, ChatMessageTool)]
        assert [m.function for m in tool_messages] == ["grep_search", "unknown"]
        # the row count no longer matches the planner steps, so ordinals are
        # untrustworthy past the gap: model-1 belonged to the dropped step
        assert [e.model for e in events if isinstance(e, ModelEvent)] == [
            "model-0",
            "unknown",
        ]

    def test_gap_keeps_generations_when_counts_match(self) -> None:
        """A dropped non-planner step leaves the generation ordinals valid."""
        steps = [
            _planner(1, ("view_file", {})),
            # step 2 (view_file's result) could not be parsed
            _planner(3, content="Done."),
        ]
        generations = [GenerationInfo(model=f"model-{i}", usage=None) for i in range(2)]
        _, events, _ = _convert(steps, generations)
        assert [e.model for e in events if isinstance(e, ModelEvent)] == [
            "model-0",
            "model-1",
        ]
