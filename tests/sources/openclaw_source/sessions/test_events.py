"""Tests for OpenClaw native session event/message construction."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    ContentImage,
    ContentReasoning,
    ContentText,
)
from inspect_scout.sources._openclaw._sessions.client import (
    load_registry,
    read_session_records,
)
from inspect_scout.sources._openclaw._sessions.events import (
    BuildContext,
    build_content,
)
from inspect_scout.sources._openclaw._sessions.parse import parse_session

FIXTURES = Path(__file__).parent / "fixtures"
FX_DEMO = FIXTURES / "fx_demo"
SUBAGENT = FX_DEMO / "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl"

# Header shared by the in-memory record lists below.
HEADER: dict[str, Any] = {
    "type": "session",
    "version": 3,
    "id": "s1",
    "timestamp": "2026-07-06T10:00:00.000Z",
    "cwd": "/w",
}
# A short (invalid but well-formed) base64 blob; the importer carries image
# bytes verbatim into a data: URI without decoding them.
IMAGE_B64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA=="


def build_fixture(path: Path) -> tuple[list[Event], list[ChatMessage]]:
    parsed = parse_session(read_session_records(path), str(path))
    ctx = BuildContext(sessions_dir=path.parent, registry=None)
    return build_content(parsed, ctx)


def build_records(
    records: list[dict[str, Any]], sessions_dir: Path
) -> tuple[list[Event], list[ChatMessage]]:
    parsed = parse_session(records, "in-memory")
    return build_content(parsed, BuildContext(sessions_dir=sessions_dir, registry=None))


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

    def test_stop_reason_and_response_id_mapped(self) -> None:
        events, _ = build_fixture(SUBAGENT)

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert [e.output.stop_reason for e in model_events] == [
            "tool_calls",
            "tool_calls",
            "stop",
        ]
        assert model_events[0].metadata == {
            "response_id": "msg_01D96KRhC582hGM2Wb94vwND"
        }

    def test_unrecognized_stop_reason_maps_to_unknown(self, tmp_path: Path) -> None:
        records: list[dict[str, Any]] = [
            {
                "type": "session",
                "version": 3,
                "id": "s1",
                "timestamp": "2026-07-06T10:00:00.000Z",
                "cwd": "/w",
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": None,
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": "hi",
                    "stopReason": "somethingNew",
                },
            },
        ]

        parsed = parse_session(records, "in-memory")
        events, _ = build_content(
            parsed, BuildContext(sessions_dir=tmp_path, registry=None)
        )

        model_events = [e for e in events if isinstance(e, ModelEvent)]
        assert model_events[0].output.stop_reason == "unknown"

    def test_tool_call_without_result(self, tmp_path: Path) -> None:
        records: list[dict[str, Any]] = [
            {
                "type": "session",
                "version": 3,
                "id": "s1",
                "timestamp": "2026-07-06T10:00:00.000Z",
                "cwd": "/w",
            },
            {
                "type": "message",
                "id": "m1",
                "parentId": None,
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": [
                        {
                            "type": "toolCall",
                            "id": "tc-orphan",
                            "name": "exec",
                            "arguments": {},
                        }
                    ],
                },
            },
        ]

        parsed = parse_session(records, "in-memory")
        events, messages = build_content(
            parsed, BuildContext(sessions_dir=tmp_path, registry=None)
        )

        tool_events = [e for e in events if isinstance(e, ToolEvent)]
        assert len(tool_events) == 1
        te = tool_events[0]
        assert te.result == ""
        assert te.failed is None
        assert te.error is None
        assert te.completed == te.timestamp
        # the orphan call still gets a ChatMessageTool in the thread
        roles = Counter(type(m).__name__ for m in messages)
        assert roles == Counter(ChatMessageAssistant=1, ChatMessageTool=1)

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


class TestSubagentSpans:
    def build_orchestrator(self) -> tuple[list[Event], list[ChatMessage]]:
        path = FX_DEMO / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"
        parsed = parse_session(read_session_records(path), str(path))
        ctx = BuildContext(sessions_dir=FX_DEMO, registry=load_registry(FX_DEMO))
        return build_content(parsed, ctx)

    def test_three_agent_spans(self) -> None:
        events, _ = self.build_orchestrator()

        begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        ends = [e for e in events if isinstance(e, SpanEndEvent)]
        assert len(begins) == len(ends) == 3
        assert all(b.type == "agent" for b in begins)
        assert sorted(str(b.name) for b in begins) == ["usd-eur", "usd-gbp", "usd-jpy"]
        for b in begins:
            assert b.metadata is not None
            assert b.metadata["session_id"] in {
                "8c6aeab3-993e-43d5-934a-04aa4a5f3804",
                "a35ff69f-56ae-453f-b290-d369e251e64d",
                "63f16c5a-1a2e-4284-90fc-96a3d22843f7",
            }
            assert b.metadata["status"] == "done"

    def test_spawn_tool_folded_into_span(self) -> None:
        events, _ = self.build_orchestrator()

        spawn_events = [
            e
            for e in events
            if isinstance(e, ToolEvent) and e.function == "sessions_spawn"
        ]
        assert len(spawn_events) == 3
        for te in spawn_events:
            assert te.agent_span_id is not None
            assert te.span_id == te.agent_span_id
            assert te.view is not None

    def test_child_events_carry_span_id(self) -> None:
        events, _ = self.build_orchestrator()

        span_ids = {e.id for e in events if isinstance(e, SpanBeginEvent)}
        child_model_events = [
            e for e in events if isinstance(e, ModelEvent) and e.span_id in span_ids
        ]
        # 3 sub-agents x 3 assistant turns each
        assert len(child_model_events) == 9
        # root thread model events carry no span id
        root_model_events = [
            e for e in events if isinstance(e, ModelEvent) and e.span_id is None
        ]
        assert len(root_model_events) == 11

    def test_child_messages_not_in_main_thread(self) -> None:
        _, messages = self.build_orchestrator()

        roles = Counter(type(m).__name__ for m in messages)
        # same thread as the registry-less build: sub-agents excluded
        assert roles == Counter(
            ChatMessageUser=7, ChatMessageAssistant=11, ChatMessageTool=11
        )

    def test_missing_child_file_skips_span(self, tmp_path: Path) -> None:
        for name in (
            "cfabe24d-8b34-4031-a393-689524b2028f.jsonl",
            "8c6aeab3-993e-43d5-934a-04aa4a5f3804.jsonl",
            "a35ff69f-56ae-453f-b290-d369e251e64d.jsonl",
            "sessions.json",
        ):  # 63f16c5a (usd-jpy) intentionally omitted
            shutil.copy(FX_DEMO / name, tmp_path / name)

        path = tmp_path / "cfabe24d-8b34-4031-a393-689524b2028f.jsonl"
        parsed = parse_session(read_session_records(path), str(path))
        ctx = BuildContext(sessions_dir=tmp_path, registry=load_registry(tmp_path))
        events, messages = build_content(parsed, ctx)

        begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        assert sorted(str(b.name) for b in begins) == ["usd-eur", "usd-gbp"]
        # the skipped spawn is still a plain tool event + thread message
        roles = Counter(type(m).__name__ for m in messages)
        assert roles["ChatMessageTool"] == 11


class TestContentMapping:
    """Mapping of message content: images, reasoning, and errored turns."""

    def test_user_image_content_maps_to_content_image(self, tmp_path: Path) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "u1",
                "parentId": None,
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "what is this?"},
                        {"type": "image", "data": IMAGE_B64, "mimeType": "image/jpeg"},
                    ],
                },
            },
        ]

        _, messages = build_records(records, tmp_path)

        (user,) = [m for m in messages if isinstance(m, ChatMessageUser)]
        assert isinstance(user.content, list)
        text, image = user.content
        assert isinstance(text, ContentText) and text.text == "what is this?"
        assert isinstance(image, ContentImage)
        assert image.image == f"data:image/jpeg;base64,{IMAGE_B64}"

    def test_tool_result_image_content_maps_to_content_image(
        self, tmp_path: Path
    ) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "a1",
                "parentId": None,
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": [
                        {
                            "type": "toolCall",
                            "id": "tc1",
                            "name": "screenshot",
                            "arguments": {},
                        }
                    ],
                },
            },
            {
                "type": "message",
                "id": "tr1",
                "parentId": "a1",
                "timestamp": "2026-07-06T10:00:02.000Z",
                "message": {
                    "role": "toolResult",
                    "toolCallId": "tc1",
                    "toolName": "screenshot",
                    "content": [
                        {"type": "text", "text": "captured"},
                        {"type": "image", "data": IMAGE_B64, "mimeType": "image/png"},
                    ],
                    "isError": False,
                },
            },
        ]

        _, messages = build_records(records, tmp_path)

        (tool,) = [m for m in messages if isinstance(m, ChatMessageTool)]
        assert isinstance(tool.content, list)
        assert any(
            isinstance(c, ContentImage)
            and c.image == f"data:image/png;base64,{IMAGE_B64}"
            for c in tool.content
        )

    def test_assistant_thinking_maps_to_reasoning(self, tmp_path: Path) -> None:
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "a1",
                "parentId": None,
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "assistant",
                    "model": "claude-opus-4-8",
                    "content": [
                        {"type": "thinking", "thinking": "let me think"},
                        {"type": "text", "text": "the answer"},
                    ],
                    "usage": {"input": 1, "output": 1, "totalTokens": 2},
                },
            },
        ]

        _, messages = build_records(records, tmp_path)

        (asst,) = [m for m in messages if isinstance(m, ChatMessageAssistant)]
        assert isinstance(asst.content, list)
        reasoning, text = asst.content
        assert isinstance(reasoning, ContentReasoning)
        assert reasoning.reasoning == "let me think"
        assert isinstance(text, ContentText) and text.text == "the answer"

    def test_errored_assistant_turn_is_kept_with_empty_content(
        self, tmp_path: Path
    ) -> None:
        # A failed/aborted turn: no content blocks, a non-standard stopReason,
        # and all-zero usage (common on non-Anthropic providers). It must not
        # crash the build; the turn survives with empty content.
        records: list[dict[str, Any]] = [
            dict(HEADER),
            {
                "type": "message",
                "id": "u1",
                "parentId": None,
                "timestamp": "2026-07-06T10:00:01.000Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "hi"}],
                },
            },
            {
                "type": "message",
                "id": "a1",
                "parentId": "u1",
                "timestamp": "2026-07-06T10:00:02.000Z",
                "message": {
                    "role": "assistant",
                    "model": "kimi-k2.5",
                    "content": [],
                    "usage": {"input": 0, "output": 0, "totalTokens": 0},
                    "stopReason": "error",
                },
            },
        ]

        events, messages = build_records(records, tmp_path)

        (asst,) = [m for m in messages if isinstance(m, ChatMessageAssistant)]
        assert asst.content == []
        (model_event,) = [e for e in events if isinstance(e, ModelEvent)]
        # OpenClaw's "error" stopReason has no Inspect equivalent -> "unknown"
        assert model_event.output.stop_reason == "unknown"
