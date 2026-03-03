"""Tests for OpenCode event conversion (events.py)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from inspect_ai.event import (
    CompactionEvent,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    ToolEvent,
)
from inspect_scout.sources._opencode.client import MessageRow, PartRow
from inspect_scout.sources._opencode.events import (
    _build_model_event,
    _build_tool_event,
    _split_into_steps,
    process_session,
)

DT = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _part(
    part_id: str,
    data: dict[str, Any],
    *,
    msg_id: str = "msg_1",
    session_id: str = "ses_1",
    time_created: int = 1_706_745_600_000,
) -> PartRow:
    return PartRow(
        id=part_id,
        message_id=msg_id,
        session_id=session_id,
        time_created=time_created,
        data=data,
    )


def _msg(
    msg_id: str,
    role: str,
    *,
    session_id: str = "ses_1",
    time_created: int = 1_706_745_600_000,
    model_id: str | None = None,
) -> MessageRow:
    data: dict[str, Any] = {"role": role}
    if model_id:
        data["modelID"] = model_id
    return MessageRow(
        id=msg_id, session_id=session_id, time_created=time_created, data=data
    )


# ---------------------------------------------------------------------------
# _split_into_steps
# ---------------------------------------------------------------------------


class TestSplitIntoSteps:
    """Tests for _split_into_steps()."""

    def test_step_grouping(self) -> None:
        """Steps are grouped by step-start/step-finish boundaries."""
        parts = [
            _part("p1", {"type": "step-start"}),
            _part("p2", {"type": "text", "text": "first"}),
            _part("p3", {"type": "step-finish", "tokens": {}}),
            _part("p4", {"type": "step-start"}),
            _part("p5", {"type": "text", "text": "second"}),
            _part("p6", {"type": "step-finish", "tokens": {}}),
        ]
        steps = _split_into_steps(parts)
        assert len(steps) == 2

    def test_trailing_parts_attach_to_last_step(self) -> None:
        """Trailing parts (e.g. patch) after last step-finish attach to that step."""
        parts = [
            _part("p1", {"type": "step-start"}),
            _part("p2", {"type": "text", "text": "hello"}),
            _part("p3", {"type": "step-finish", "tokens": {}}),
            _part("p4", {"type": "patch", "hash": "abc", "files": []}),
        ]
        steps = _split_into_steps(parts)
        assert len(steps) == 1
        assert len(steps[0]) == 4  # includes trailing patch

    def test_no_boundaries_forms_single_group(self) -> None:
        """Parts without step-start/finish form a single group; empty → empty."""
        parts = [
            _part("p1", {"type": "text", "text": "hello"}),
            _part("p2", {"type": "tool", "tool": "Read"}),
        ]
        assert len(_split_into_steps(parts)) == 1
        assert _split_into_steps([]) == []


# ---------------------------------------------------------------------------
# _build_model_event
# ---------------------------------------------------------------------------


class TestBuildModelEvent:
    """Tests for _build_model_event()."""

    def test_text_content_and_stop_reason(self) -> None:
        """Text parts → text content with stop_reason='stop'."""
        text_parts = [
            _part("p1", {"type": "text", "text": "first"}),
            _part("p2", {"type": "text", "text": "second"}),
        ]
        result = _build_model_event(text_parts, [], None, "test-model", [], DT)

        assert result.model == "test-model"
        assert result.output.choices[0].message.content == "first\n\nsecond"
        assert result.output.choices[0].stop_reason == "stop"
        assert result.output.usage is None

    def test_tool_calls_and_usage(self) -> None:
        """Tool parts → tool_calls with stop_reason='tool_calls'; step-finish → usage."""
        tool_parts = [
            _part(
                "p1",
                {
                    "type": "tool",
                    "tool": "Read",
                    "callID": "call_1",
                    "state": {"input": {"file_path": "/test.py"}},
                },
            )
        ]
        step_finish = _part(
            "sf",
            {
                "type": "step-finish",
                "tokens": {
                    "input": 100,
                    "output": 50,
                    "reasoning": 10,
                    "total": 160,
                    "cache": {"read": 20, "write": 5},
                },
            },
        )
        result = _build_model_event([], tool_parts, step_finish, "test-model", [], DT)

        msg = result.output.choices[0].message
        assert msg.tool_calls is not None
        assert msg.tool_calls[0].id == "call_1"
        assert msg.tool_calls[0].function == "Read"
        assert result.output.choices[0].stop_reason == "tool_calls"

        usage = result.output.usage
        assert usage is not None
        assert usage.input_tokens == 100
        assert usage.output_tokens == 60  # output + reasoning
        assert usage.total_tokens == 160
        assert usage.input_tokens_cache_read == 20


# ---------------------------------------------------------------------------
# _build_tool_event
# ---------------------------------------------------------------------------


class TestBuildToolEvent:
    """Tests for _build_tool_event()."""

    def test_successful_tool(self) -> None:
        """Completed tool part → ToolEvent with result, no error."""
        part = _part(
            "p1",
            {
                "type": "tool",
                "tool": "Read",
                "callID": "call_1",
                "state": {
                    "input": {"file_path": "/test.py"},
                    "output": "file contents",
                    "status": "completed",
                    "time": {"start": 1_706_745_601_000, "end": 1_706_745_602_000},
                },
            },
        )
        result = _build_tool_event(part, DT)

        assert result.function == "Read"
        assert result.id == "call_1"
        assert result.result == "file contents"
        assert result.error is None

    def test_error_tool(self) -> None:
        """Error tool part → ToolEvent with error; missing callID → falls back to part.id."""
        part = _part(
            "part_xyz",
            {
                "type": "tool",
                "tool": "Bash",
                "state": {
                    "input": {"command": "bad"},
                    "status": "error",
                    "error": "Command failed",
                },
            },
        )
        result = _build_tool_event(part, DT)

        assert result.error is not None
        assert result.error.message == "Command failed"
        assert result.id == "part_xyz"  # fallback to part.id


# ---------------------------------------------------------------------------
# process_session
# ---------------------------------------------------------------------------


class TestProcessSession:
    """Tests for process_session() — the main conversion function."""

    @pytest.mark.asyncio
    async def test_simple_conversation(self) -> None:
        """User + assistant → ModelEvent with accumulated input."""
        messages = [
            _msg("msg_u", "user", time_created=1_000),
            _msg(
                "msg_a",
                "assistant",
                time_created=2_000,
                model_id="claude-sonnet-4-20250514",
            ),
        ]
        parts = [
            _part(
                "p_u",
                {"type": "text", "text": "Hello"},
                msg_id="msg_u",
                time_created=1_000,
            ),
            _part("p_ss", {"type": "step-start"}, msg_id="msg_a", time_created=2_000),
            _part(
                "p_a",
                {"type": "text", "text": "Hi there!"},
                msg_id="msg_a",
                time_created=2_100,
            ),
            _part(
                "p_sf",
                {
                    "type": "step-finish",
                    "tokens": {"input": 50, "output": 20, "total": 70},
                },
                msg_id="msg_a",
                time_created=2_200,
            ),
        ]

        events = await process_session(messages, parts)

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert len(model_events) == 1
        assert model_events[0].model == "claude-sonnet-4-20250514"
        assert model_events[0].output.choices[0].message.content == "Hi there!"
        assert len(model_events[0].input) == 1

    @pytest.mark.asyncio
    async def test_tool_call_produces_spans(self) -> None:
        """Tool parts → ModelEvent (stop_reason=tool_calls) + SpanBegin/ToolEvent/SpanEnd."""
        messages = [
            _msg("msg_u", "user", time_created=1_000),
            _msg("msg_a", "assistant", time_created=2_000, model_id="test-model"),
        ]
        parts = [
            _part(
                "p_u",
                {"type": "text", "text": "Read file"},
                msg_id="msg_u",
                time_created=1_000,
            ),
            _part("p_ss", {"type": "step-start"}, msg_id="msg_a", time_created=2_000),
            _part(
                "p_tool",
                {
                    "type": "tool",
                    "tool": "Read",
                    "callID": "call_1",
                    "state": {
                        "input": {"file_path": "/test.py"},
                        "output": "content",
                        "status": "completed",
                        "time": {"start": 2_200, "end": 2_300},
                    },
                },
                msg_id="msg_a",
                time_created=2_200,
            ),
            _part(
                "p_sf",
                {"type": "step-finish", "tokens": {"total": 70}},
                msg_id="msg_a",
                time_created=2_400,
            ),
        ]

        events = await process_session(messages, parts)

        assert any(
            isinstance(e, ModelEvent)
            and e.output.choices[0].stop_reason == "tool_calls"
            for e in events
        )
        span_begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        assert any(s.name == "Read" and s.type == "tool" for s in span_begins)
        assert any(isinstance(e, ToolEvent) and e.function == "Read" for e in events)

    @pytest.mark.asyncio
    async def test_compaction_emits_event_and_resets_input(self) -> None:
        """Compaction → CompactionEvent; post-compaction ModelEvent has only new input."""
        messages = [
            _msg("msg_u1", "user", time_created=1_000),
            _msg("msg_a1", "assistant", time_created=2_000, model_id="test-model"),
            _msg("msg_a2", "assistant", time_created=3_000, model_id="test-model"),
            _msg("msg_u2", "user", time_created=4_000),
            _msg("msg_a3", "assistant", time_created=5_000, model_id="test-model"),
        ]
        parts = [
            _part(
                "p_u1",
                {"type": "text", "text": "Hello"},
                msg_id="msg_u1",
                time_created=1_000,
            ),
            _part("p_ss1", {"type": "step-start"}, msg_id="msg_a1", time_created=2_000),
            _part(
                "p_a1",
                {"type": "text", "text": "Response 1"},
                msg_id="msg_a1",
                time_created=2_100,
            ),
            _part(
                "p_sf1",
                {"type": "step-finish", "tokens": {"total": 50}},
                msg_id="msg_a1",
                time_created=2_200,
            ),
            _part(
                "p_comp", {"type": "compaction"}, msg_id="msg_a2", time_created=3_000
            ),
            _part(
                "p_u2",
                {"type": "text", "text": "Continue"},
                msg_id="msg_u2",
                time_created=4_000,
            ),
            _part("p_ss3", {"type": "step-start"}, msg_id="msg_a3", time_created=5_000),
            _part(
                "p_a3",
                {"type": "text", "text": "Response 3"},
                msg_id="msg_a3",
                time_created=5_100,
            ),
            _part(
                "p_sf3",
                {"type": "step-finish", "tokens": {"total": 30}},
                msg_id="msg_a3",
                time_created=5_200,
            ),
        ]

        events = await process_session(messages, parts)

        assert len([e for e in events if isinstance(e, CompactionEvent)]) == 1

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        post_input = model_events[1].input
        content_strs = [str(m.content) for m in post_input if hasattr(m, "content")]
        assert not any("Hello" in c for c in content_strs)
        assert any("Continue" in c for c in content_strs)

    @pytest.mark.asyncio
    async def test_patch_and_task_tool(self) -> None:
        """Patch parts → InfoEvent; task tool → agent span."""
        messages = [
            _msg("msg_u", "user", time_created=1_000),
            _msg("msg_a", "assistant", time_created=2_000, model_id="test-model"),
        ]
        parts = [
            _part(
                "p_u",
                {"type": "text", "text": "Go"},
                msg_id="msg_u",
                time_created=1_000,
            ),
            _part("p_ss", {"type": "step-start"}, msg_id="msg_a", time_created=2_000),
            _part(
                "p_task",
                {
                    "type": "tool",
                    "tool": "task",
                    "callID": "task_1",
                    "state": {
                        "input": {
                            "subagent_type": "Explore",
                            "description": "Find files",
                        },
                        "output": "Found 3 files",
                        "status": "completed",
                        "time": {"start": 2_100, "end": 2_500},
                    },
                },
                msg_id="msg_a",
                time_created=2_100,
            ),
            _part(
                "p_sf",
                {"type": "step-finish", "tokens": {"total": 100}},
                msg_id="msg_a",
                time_created=2_600,
            ),
            _part(
                "p_patch",
                {"type": "patch", "hash": "abc123", "files": ["file.py"]},
                msg_id="msg_a",
                time_created=2_700,
            ),
        ]

        events = await process_session(messages, parts, db_path=None)

        # Patch → InfoEvent
        info_events = [e for e in events if isinstance(e, InfoEvent)]
        assert len(info_events) == 1
        assert info_events[0].data["hash"] == "abc123"

        # Task → agent span
        agent_spans = [
            e for e in events if isinstance(e, SpanBeginEvent) and e.type == "agent"
        ]
        assert len(agent_spans) == 1
        assert agent_spans[0].name == "Explore"

    @pytest.mark.asyncio
    async def test_multi_step_assistant(self) -> None:
        """Multiple steps in one assistant message → multiple ModelEvents."""
        messages = [
            _msg("msg_u", "user", time_created=1_000),
            _msg("msg_a", "assistant", time_created=2_000, model_id="test-model"),
        ]
        parts = [
            _part(
                "p_u",
                {"type": "text", "text": "Go"},
                msg_id="msg_u",
                time_created=1_000,
            ),
            _part("p_ss1", {"type": "step-start"}, msg_id="msg_a", time_created=2_000),
            _part(
                "p_a1",
                {"type": "text", "text": "Step 1"},
                msg_id="msg_a",
                time_created=2_100,
            ),
            _part(
                "p_sf1",
                {"type": "step-finish", "tokens": {"total": 50}},
                msg_id="msg_a",
                time_created=2_200,
            ),
            _part("p_ss2", {"type": "step-start"}, msg_id="msg_a", time_created=3_000),
            _part(
                "p_a2",
                {"type": "text", "text": "Step 2"},
                msg_id="msg_a",
                time_created=3_100,
            ),
            _part(
                "p_sf2",
                {"type": "step-finish", "tokens": {"total": 40}},
                msg_id="msg_a",
                time_created=3_200,
            ),
        ]

        events = await process_session(messages, parts)

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert len(model_events) == 2
        assert model_events[0].output.choices[0].message.content == "Step 1"
        assert model_events[1].output.choices[0].message.content == "Step 2"
