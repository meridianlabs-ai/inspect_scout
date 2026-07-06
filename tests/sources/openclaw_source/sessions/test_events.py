"""Tests for OpenClaw native session event/message construction."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    ToolEvent,
)
from inspect_ai.model import ChatMessage
from inspect_scout.sources._openclaw._sessions.client import read_session_records
from inspect_scout.sources._openclaw._sessions.events import (
    BuildContext,
    build_content,
)
from inspect_scout.sources._openclaw._sessions.parse import parse_session

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
SUBAGENT = FX_DEMO / "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl"


def build_fixture(path: Path) -> tuple[list[Event], list[ChatMessage]]:
    parsed = parse_session(read_session_records(path), str(path))
    ctx = BuildContext(sessions_dir=path.parent, registry=None)
    return build_content(parsed, ctx)


class TestThreadContent:
    def test_model_events_thread_input(self) -> None:
        events, messages = build_fixture(SUBAGENT)
        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert len(model_events) == 3
        # each input is the running conversation up to (excluding) that turn
        assert len(model_events[0].input) == 1  # the [Subagent Context] prompt
        assert all(len(e.input) < len(messages) for e in model_events)
        assert model_events[0].output.usage is not None
        assert model_events[0].output.usage.total_tokens > 0
        assert model_events[0].model == "claude-opus-4-8"

    def test_tool_events_join_results(self) -> None:
        events, _ = build_fixture(SUBAGENT)
        tool_events = [e for e in events if isinstance(e, ToolEvent)]
        assert len(tool_events) == 2
        for te in tool_events:
            assert te.result != ""  # result joined by toolCallId
            assert te.completed is not None and te.completed >= te.timestamp
        # fixture: web_search result has isError=true, web_fetch does not
        assert {te.failed for te in tool_events} == {False, True}
        failed_event = next(te for te in tool_events if te.failed)
        assert failed_event.error is not None

    def test_message_thread_roles(self) -> None:
        _, messages = build_fixture(SUBAGENT)
        roles = Counter(type(m).__name__ for m in messages)
        assert roles == Counter(
            ChatMessageUser=1, ChatMessageAssistant=3, ChatMessageTool=2
        )

    def test_config_changes_become_info_events(self) -> None:
        events, _ = build_fixture(SUBAGENT)
        infos = [e for e in events if isinstance(e, InfoEvent)]
        assert len(infos) == 2
        assert infos[0].source == "openclaw"
        data = infos[0].data
        assert isinstance(data, dict)
        assert data["type"] == "model_change"
        assert data["model"] == "claude-opus-4-8"
        data1 = infos[1].data
        assert isinstance(data1, dict)
        assert data1["type"] == "thinking_level_change"

    def test_working_start_is_monotonic(self) -> None:
        events, _ = build_fixture(SUBAGENT)
        starts = [e.working_start for e in events]
        assert starts == sorted(starts)

    def test_no_spans_without_registry(self) -> None:
        orchestrator = FX_DEMO / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"
        events, messages = build_fixture(orchestrator)
        assert not any(isinstance(e, SpanBeginEvent) for e in events)
        # spawn calls degrade to plain tool events; thread intact
        roles = Counter(type(m).__name__ for m in messages)
        assert roles == Counter(
            ChatMessageUser=7, ChatMessageAssistant=11, ChatMessageTool=11
        )


class TestCompaction:
    def test_compaction_event(self) -> None:
        events, messages = build_fixture(FIXTURES / "compaction_session.jsonl")
        compactions = [e for e in events if isinstance(e, CompactionEvent)]
        assert len(compactions) == 1
        c = compactions[0]
        assert c.source == "openclaw"
        assert c.tokens_before == 81290
        assert c.tokens_after is None
        assert c.metadata is not None
        assert c.metadata["summary"].startswith("## Goal")
        assert c.metadata["first_kept_entry_id"] == "c1"
        assert c.metadata["from_hook"] is False
        # thread unaffected: 2 user + 2 assistant
        assert len(messages) == 4
