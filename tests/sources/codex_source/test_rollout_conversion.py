"""Unit tests for codex rollout → scout event conversion."""

from typing import Any

import pytest
from inspect_ai.event import (
    CompactionEvent,
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model import ContentImage, ContentReasoning, ContentText
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_swe._codex_cli._events.rollout import process_rollout_events
from inspect_swe._codex_cli._events.rollout_extraction import (
    is_context_message,
    output_to_result,
    parse_arguments,
    reasoning_to_content,
    usage_from_token_info,
)
from inspect_swe._codex_cli._events.rollout_models import (
    ResponseReasoning,
    parse_rollout_events,
)


def _line(
    type_: str, payload: dict[str, Any], ts: str = "2026-08-01T10:00:00Z"
) -> dict[str, Any]:
    return {"timestamp": ts, "type": type_, "payload": payload}


def _user(text: str) -> dict[str, Any]:
    return _line(
        "response_item",
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
        },
    )


def _assistant(text: str) -> dict[str, Any]:
    return _line(
        "response_item",
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": text}],
        },
    )


def _function_call(name: str, arguments: str, call_id: str) -> dict[str, Any]:
    return _line(
        "response_item",
        {
            "type": "function_call",
            "name": name,
            "arguments": arguments,
            "call_id": call_id,
        },
    )


def _call_output(call_id: str, output: Any) -> dict[str, Any]:
    return _line(
        "response_item",
        {"type": "function_call_output", "call_id": call_id, "output": output},
    )


def _turn_context(model: str = "gpt-5.1-codex") -> dict[str, Any]:
    return _line("turn_context", {"model": model, "cwd": "/x"})


async def _convert(raw_lines: list[dict[str, Any]]) -> list[Event]:
    events = parse_rollout_events(raw_lines)
    return [e async for e in process_rollout_events(events)]


# ── model event grouping ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consecutive_assistant_items_become_one_model_event() -> None:
    """Reasoning + message + two tool calls = one model response."""
    scout_events = await _convert(
        [
            _turn_context(),
            _user("do two things"),
            _line(
                "response_item",
                {
                    "type": "reasoning",
                    "summary": [{"type": "summary_text", "text": "Planning"}],
                    "encrypted_content": "opaque",
                },
            ),
            _assistant("Doing both now."),
            _function_call("shell", '{"command": ["a"]}', "c1"),
            _function_call("shell", '{"command": ["b"]}', "c2"),
            _call_output("c1", "out a"),
            _call_output("c2", "out b"),
        ]
    )
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    assert len(model_events) == 1
    message = model_events[0].output.choices[0].message
    assert message.tool_calls is not None and len(message.tool_calls) == 2
    assert [tc.id for tc in message.tool_calls] == ["c1", "c2"]
    assert isinstance(message.content, list)
    assert isinstance(message.content[0], ContentReasoning)
    assert isinstance(message.content[1], ContentText)
    assert model_events[0].output.choices[0].stop_reason == "tool_calls"
    assert model_events[0].model == "gpt-5.1-codex"

    # both tool spans emitted
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert [t.id for t in tool_events] == ["c1", "c2"]
    assert tool_events[0].result == "out a"


@pytest.mark.asyncio
async def test_model_event_input_accumulates_context() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("<environment_context>cwd: /x</environment_context>"),
            _user("real question"),
            _assistant("answer one"),
            _line("event_msg", {"type": "token_count", "info": None}),
            _user("second question"),
            _assistant("answer two"),
        ]
    )
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    assert len(model_events) == 2
    # first call saw both user messages (context + question)
    assert [m.role for m in model_events[0].input] == ["user", "user"]
    # second call saw everything before it
    assert [m.role for m in model_events[1].input] == [
        "user",
        "user",
        "assistant",
        "user",
    ]


@pytest.mark.asyncio
async def test_usage_attached_from_token_count() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q"),
            _assistant("a"),
            _line(
                "event_msg",
                {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {
                            "input_tokens": 100,
                            "output_tokens": 20,
                            "total_tokens": 120,
                        },
                        "last_token_usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 80,
                            "cache_write_input_tokens": 5,
                            "output_tokens": 20,
                            "reasoning_output_tokens": 8,
                            "total_tokens": 120,
                        },
                    },
                },
            ),
        ]
    )
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    usage = model_events[0].output.usage
    assert usage is not None
    assert usage.input_tokens == 20  # excludes cached
    assert usage.input_tokens_cache_read == 80
    assert usage.input_tokens_cache_write == 5
    assert usage.output_tokens == 20
    assert usage.reasoning_tokens == 8
    assert usage.total_tokens == 120


# ── extraction units ─────────────────────────────────────────────────────


def test_is_context_message() -> None:
    assert is_context_message("<environment_context>\n<cwd>/x</cwd>")
    assert is_context_message("  <user_instructions>be nice</user_instructions>")
    assert not is_context_message("fix the tests")
    # bundled genuine user text is user speech
    assert not is_context_message(
        "<environment_context>...</environment_context>\n\n## My request for Codex:\nfix it"
    )


def test_output_to_result_polymorphism() -> None:
    # plain string
    result, exit_code = output_to_result("Exit code: 0\nOutput:\nok")
    assert result == "Exit code: 0\nOutput:\nok" and exit_code is None

    # legacy JSON-encoded form with metadata
    result, exit_code = output_to_result(
        '{"output": "boom", "metadata": {"exit_code": 2, "duration_seconds": 1.5}}'
    )
    assert result == "boom" and exit_code == 2

    # content-item array with an image
    result, exit_code = output_to_result(
        [
            {"type": "output_text", "text": "see image"},
            {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
        ]
    )
    assert isinstance(result, list)
    assert isinstance(result[0], ContentText)
    assert isinstance(result[1], ContentImage)

    # text-only array collapses to a string
    result, _ = output_to_result([{"type": "output_text", "text": "just text"}])
    assert result == "just text"

    assert output_to_result(None) == ("", None)


def test_parse_arguments_tolerates_bad_json() -> None:
    assert parse_arguments('{"a": 1}') == {"a": 1}
    assert parse_arguments("") == {}
    assert parse_arguments("not json") == {"arguments": "not json"}
    assert parse_arguments('"bare string"') == {"arguments": "bare string"}


def test_reasoning_to_content() -> None:
    # encrypted-only with summary: summary used, marked redacted
    encrypted = ResponseReasoning(
        summary=[{"type": "summary_text", "text": "**Thinking**"}],
        encrypted_content="opaque",
    )
    content = reasoning_to_content(encrypted)
    assert content is not None
    assert content.reasoning == "**Thinking**" and content.redacted

    # plaintext reasoning available: not redacted
    plaintext = ResponseReasoning(
        summary=[],
        content=[{"type": "reasoning_text", "text": "step by step"}],
        encrypted_content="opaque",
    )
    content = reasoning_to_content(plaintext)
    assert content is not None
    assert content.reasoning == "step by step" and not content.redacted

    # encrypted only, no summary: empty redacted block
    opaque = ResponseReasoning(summary=[], encrypted_content="opaque")
    content = reasoning_to_content(opaque)
    assert content is not None
    assert content.reasoning == "" and content.redacted

    assert reasoning_to_content(ResponseReasoning(summary=[])) is None


def test_usage_from_token_info_none_cases() -> None:
    assert usage_from_token_info({}) is None
    assert usage_from_token_info({"last_token_usage": {"total_tokens": 0}}) is None


# ── boundary behaviors ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rollback_truncates_accumulated_messages() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q1"),
            _assistant("a1"),
            _user("q2"),
            _assistant("a2"),
            _line("event_msg", {"type": "thread_rolled_back", "num_turns": 1}),
            _user("q3"),
            _assistant("a3"),
        ]
    )
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    assert len(model_events) == 3
    third_input = model_events[2].input
    texts = [m.text for m in third_input]
    assert texts == ["q1", "a1", "q3"]
    info_events = [e for e in scout_events if isinstance(e, InfoEvent)]
    assert any(
        isinstance(e.data, dict) and e.data.get("type") == "thread_rolled_back"
        for e in info_events
    )


@pytest.mark.asyncio
async def test_compaction_resets_input_to_replacement_history() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q1"),
            _assistant("a1"),
            _line(
                "event_msg",
                {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {"total_tokens": 50000},
                        "last_token_usage": {
                            "input_tokens": 40,
                            "output_tokens": 10,
                            "total_tokens": 50,
                        },
                    },
                },
            ),
            _line(
                "compacted",
                {
                    "message": "Summary of q1/a1.",
                    "replacement_history": [
                        {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "q1"}],
                        },
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {"type": "output_text", "text": "Summary of q1/a1."}
                            ],
                        },
                    ],
                },
            ),
            _user("q2"),
            _assistant("a2"),
        ]
    )
    compactions = [e for e in scout_events if isinstance(e, CompactionEvent)]
    assert len(compactions) == 1
    assert compactions[0].tokens_before == 50000
    assert compactions[0].type == "summary"

    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    second_input = model_events[1].input
    assert [m.text for m in second_input] == ["q1", "Summary of q1/a1.", "q2"]


@pytest.mark.asyncio
async def test_remote_compaction_clears_messages() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q1"),
            _assistant("a1"),
            _line("response_item", {"type": "compaction", "encrypted_content": "xyz"}),
            _user("q2"),
            _assistant("a2"),
        ]
    )
    compactions = [e for e in scout_events if isinstance(e, CompactionEvent)]
    assert len(compactions) == 1
    assert compactions[0].metadata == {"trigger": "remote", "encrypted": True}
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    assert [m.text for m in model_events[1].input] == ["q2"]


@pytest.mark.asyncio
async def test_turn_aborted_flushes_dangling_call_with_error() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q"),
            _function_call("shell", '{"command": ["sleep"]}', "c9"),
            _line("event_msg", {"type": "turn_aborted", "reason": "interrupted"}),
        ]
    )
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].error is not None
    assert "interrupted" in tool_events[0].error.message
    info_events = [e for e in scout_events if isinstance(e, InfoEvent)]
    assert any(
        isinstance(e.data, dict) and e.data.get("type") == "turn_aborted"
        for e in info_events
    )


@pytest.mark.asyncio
async def test_dangling_call_flushed_at_end_without_error() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q"),
            _function_call("shell", '{"command": ["x"]}', "c1"),
        ]
    )
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].result == "" and tool_events[0].error is None


@pytest.mark.asyncio
async def test_web_search_call_emits_self_contained_span() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("look this up"),
            _line(
                "response_item",
                {
                    "type": "web_search_call",
                    "id": "ws_1",
                    "status": "completed",
                    "action": {"type": "search", "query": "weather"},
                },
            ),
            _assistant("It is sunny."),
        ]
    )
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].function == "web_search"
    assert tool_events[0].arguments == {"query": "weather"}
    # tool span closed (no dangling pending call)
    span_begins = [e for e in scout_events if isinstance(e, SpanBeginEvent)]
    span_ends = [e for e in scout_events if isinstance(e, SpanEndEvent)]
    assert len(span_begins) == len(span_ends) == 1


@pytest.mark.asyncio
async def test_local_shell_call_pairs_with_output() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q"),
            _line(
                "response_item",
                {
                    "type": "local_shell_call",
                    "call_id": "lsc_1",
                    "status": "completed",
                    "action": {"type": "exec", "command": ["ls"], "timeout_ms": 1000},
                },
            ),
            _call_output("lsc_1", "file.txt"),
        ]
    )
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].function == "local_shell"
    assert tool_events[0].arguments == {"command": ["ls"], "timeout_ms": 1000}
    assert tool_events[0].result == "file.txt"


@pytest.mark.asyncio
async def test_legacy_output_exit_code_sets_error() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _user("q"),
            _function_call("shell", '{"command": ["false"]}', "c1"),
            _call_output(
                "c1", '{"output": "command failed", "metadata": {"exit_code": 1}}'
            ),
        ]
    )
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert tool_events[0].result == "command failed"
    assert tool_events[0].error is not None


@pytest.mark.asyncio
async def test_spawn_agent_span_with_child_loader() -> None:
    child_model_event_calls: list[tuple[str, int]] = []

    async def fake_loader(thread_id: str, max_depth: int) -> list[Event]:
        child_model_event_calls.append((thread_id, max_depth))
        from datetime import datetime, timezone

        from inspect_ai.model import ModelOutput
        from inspect_ai.model._generate_config import GenerateConfig

        return [
            ModelEvent(
                model="child-model",
                input=[ChatMessageUser(content="child task")],
                tools=[],
                tool_choice="auto",
                config=GenerateConfig(),
                output=ModelOutput.from_content("child-model", "child answer"),
                timestamp=datetime(2026, 8, 1, 10, 0, 5, tzinfo=timezone.utc),
            )
        ]

    events = parse_rollout_events(
        [
            _turn_context(),
            _user("spawn a helper"),
            _function_call(
                "spawn_agent",
                '{"agent_type": "explorer", "message": "explore"}',
                "call_sp",
            ),
            _call_output(
                "call_sp", '{"agent_id": "child-thread-id", "nickname": "zippy"}'
            ),
        ]
    )
    scout_events = [
        e async for e in process_rollout_events(events, child_loader=fake_loader)
    ]

    assert child_model_event_calls == [("child-thread-id", 4)]
    agent_spans = [
        e for e in scout_events if isinstance(e, SpanBeginEvent) and e.type == "agent"
    ]
    assert len(agent_spans) == 1
    assert agent_spans[0].name == "zippy"
    assert agent_spans[0].metadata is not None
    assert agent_spans[0].metadata["thread_id"] == "child-thread-id"

    # child ModelEvent nested (re-parented onto the agent span)
    child_events = [
        e
        for e in scout_events
        if isinstance(e, ModelEvent) and e.model == "child-model"
    ]
    assert len(child_events) == 1
    assert child_events[0].span_id == agent_spans[0].id

    # the spawn ToolEvent lives inside the agent span
    tool_events = [e for e in scout_events if isinstance(e, ToolEvent)]
    assert tool_events[0].function == "spawn_agent"
    assert tool_events[0].agent_span_id == agent_spans[0].id


@pytest.mark.asyncio
async def test_developer_message_becomes_system() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _line(
                "response_item",
                {
                    "type": "message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": "dev instructions"}],
                },
            ),
            _user("q"),
            _assistant("a"),
        ]
    )
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    assert [m.role for m in model_events[0].input] == ["system", "user"]


@pytest.mark.asyncio
async def test_output_without_matching_call_is_accumulated() -> None:
    scout_events = await _convert(
        [
            _turn_context(),
            _call_output("orphan", "orphan output"),
            _user("q"),
            _assistant("a"),
        ]
    )
    # no tool span, but message accumulated for fidelity
    assert not [e for e in scout_events if isinstance(e, ToolEvent)]
    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    assert [m.role for m in model_events[0].input] == ["tool", "user"]
