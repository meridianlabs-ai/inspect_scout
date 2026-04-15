"""Integration tests for the Codex import source."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from inspect_ai.event import ModelEvent, SpanBeginEvent, SpanEndEvent, ToolEvent
from inspect_ai.model._chat_message import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_scout.sources._codex.client import CODEX_SOURCE_TYPE


def _write_rollout_file(
    directory: Path,
    *,
    session_id: str,
    started_at: str,
    cwd: str,
    final_text: str,
) -> Path:
    records = [
        {
            "timestamp": started_at,
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "timestamp": started_at,
                "cwd": cwd,
                "originator": "codex-tui",
                "cli_version": "0.120.0",
                "source": "cli",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.001Z",
            "type": "turn_context",
            "payload": {"model": "gpt-5.4"},
        },
        {
            "timestamp": "2026-04-13T14:00:00.002Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": "Follow repo rules."}],
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.003Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Inspect the repo"}],
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.004Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 11,
                        "cached_input_tokens": 2,
                        "output_tokens": 5,
                        "reasoning_output_tokens": 1,
                        "total_tokens": 19,
                    }
                },
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.005Z",
            "type": "response_item",
            "payload": {
                "type": "reasoning",
                "summary": [{"text": "Search the tree."}],
                "content": None,
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.006Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "commentary",
                "content": [{"type": "output_text", "text": "Checking files."}],
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.007Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "exec_command",
                "call_id": "call_1",
                "arguments": '{"cmd":"pwd"}',
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.008Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call_1",
                "output": f"{cwd}\n",
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.009Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 20,
                        "cached_input_tokens": 0,
                        "output_tokens": 8,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 28,
                    }
                },
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.010Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final",
                "content": [{"type": "output_text", "text": final_text}],
            },
        },
    ]

    rollout_file = directory / f"rollout-2026-04-13T14-00-00-{session_id}.jsonl"
    rollout_file.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return rollout_file


def _write_custom_tool_rollout_file(directory: Path, session_id: str) -> Path:
    records = [
        {
            "timestamp": "2026-04-13T14:30:00.000Z",
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "timestamp": "2026-04-13T14:30:00.000Z",
                "cwd": "/Users/example/project",
                "originator": "codex-tui",
                "cli_version": "0.120.0",
                "source": "cli",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.001Z",
            "type": "turn_context",
            "payload": {"model": "gpt-5.4"},
        },
        {
            "timestamp": "2026-04-13T14:30:00.002Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Patch the file."}],
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.003Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 0,
                        "output_tokens": 4,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 14,
                    }
                },
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.004Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "commentary",
                "content": [{"type": "output_text", "text": "Applying patch."}],
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.005Z",
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "status": "completed",
                "call_id": "call_patch",
                "name": "apply_patch",
                "input": "*** Begin Patch\n*** End Patch\n",
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.006Z",
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "call_patch",
                "output": json.dumps(
                    {
                        "output": "Success. Updated the following files:\nM sample.txt\n",
                        "metadata": {"exit_code": 0},
                    }
                ),
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.007Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 18,
                        "cached_input_tokens": 0,
                        "output_tokens": 6,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 24,
                    }
                },
            },
        },
        {
            "timestamp": "2026-04-13T14:30:00.008Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final",
                "content": [{"type": "output_text", "text": "Patch applied."}],
            },
        },
    ]

    rollout_file = directory / f"rollout-2026-04-13T14-30-00-{session_id}.jsonl"
    rollout_file.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return rollout_file


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def _write_subagent_rollout_files(base_dir: Path) -> tuple[Path, Path]:
    parent_file = (
        base_dir
        / "sessions"
        / "2026"
        / "04"
        / "13"
        / "rollout-2026-04-13T14-00-00-parent-thread.jsonl"
    )
    child_file = (
        base_dir
        / "sessions"
        / "2026"
        / "04"
        / "13"
        / "rollout-2026-04-13T14-00-01-child-thread.jsonl"
    )

    parent_records: list[dict[str, object]] = [
        {
            "timestamp": "2026-04-13T14:00:00.000Z",
            "type": "session_meta",
            "payload": {
                "id": "parent-thread",
                "timestamp": "2026-04-13T14:00:00.000Z",
                "cwd": "/Users/example/project",
                "originator": "codex-tui",
                "cli_version": "0.120.0",
                "source": "cli",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.001Z",
            "type": "turn_context",
            "payload": {"model": "gpt-5.4"},
        },
        {
            "timestamp": "2026-04-13T14:00:00.002Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Run a child task"}],
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.003Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "spawn_agent",
                "call_id": "call_spawn_1",
                "arguments": json.dumps(
                    {
                        "agent_type": "worker",
                        "model": "gpt-5.4-mini",
                        "reasoning_effort": "low",
                        "message": "Run exactly one task.",
                    }
                ),
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.004Z",
            "type": "event_msg",
            "payload": {
                "type": "collab_agent_spawn_end",
                "call_id": "call_spawn_1",
                "sender_thread_id": "parent-thread",
                "new_thread_id": "child-thread",
                "new_agent_nickname": "Sagan",
                "new_agent_role": "worker",
                "prompt": "Run exactly one task.",
                "model": "gpt-5.4-mini",
                "reasoning_effort": "low",
                "status": "pending_init",
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.005Z",
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "call_id": "call_spawn_1",
                "output": {"agent_id": "child-thread", "nickname": "Sagan"},
            },
        },
        {
            "timestamp": "2026-04-13T14:00:00.006Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final",
                "content": [{"type": "output_text", "text": "Parent finished."}],
            },
        },
    ]
    child_records: list[dict[str, object]] = [
        {
            "timestamp": "2026-04-13T14:00:01.000Z",
            "type": "session_meta",
            "payload": {
                "id": "child-thread",
                "timestamp": "2026-04-13T14:00:01.000Z",
                "forked_from_id": "parent-thread",
                "agent_nickname": "Sagan",
                "agent_role": "worker",
                "model_provider": "openai",
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": "parent-thread",
                            "depth": 1,
                            "agent_nickname": "Sagan",
                            "agent_role": "worker",
                        }
                    }
                },
            },
        },
        {
            "timestamp": "2026-04-13T14:00:01.001Z",
            "type": "turn_context",
            "payload": {"model": "gpt-5.4-mini"},
        },
        {
            "timestamp": "2026-04-13T14:00:01.002Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Child task"}],
            },
        },
        {
            "timestamp": "2026-04-13T14:00:01.003Z",
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "phase": "final",
                "content": [{"type": "output_text", "text": "Child finished."}],
            },
        },
    ]

    return (
        _write_jsonl(parent_file, parent_records),
        _write_jsonl(child_file, child_records),
    )


@pytest.mark.asyncio
async def test_codex_import_reads_rollout_file(tmp_path: Path) -> None:
    """Codex rollout files should convert into Scout transcripts."""
    from inspect_scout.sources import codex

    session_id = "019d8739-0fa5-7a43-9bb7-805000da67af"
    cwd = "/Users/example/project"
    rollout_file = _write_rollout_file(
        tmp_path,
        session_id=session_id,
        started_at="2026-04-13T14:00:00.000Z",
        cwd=cwd,
        final_text="Done.",
    )

    transcripts = [transcript async for transcript in codex(path=rollout_file)]

    assert len(transcripts) == 1

    transcript = transcripts[0]
    assert transcript.transcript_id == session_id
    assert transcript.source_type == CODEX_SOURCE_TYPE
    assert transcript.source_id == session_id
    assert transcript.source_uri == str(rollout_file.resolve())
    assert transcript.date == "2026-04-13T14:00:00+00:00"
    assert transcript.task_set == cwd
    assert transcript.task_id == session_id
    assert transcript.agent == "codex"
    assert transcript.model == "openai/gpt-5.4"
    assert transcript.message_count == 5
    assert transcript.total_tokens == 47
    assert transcript.total_time is not None
    assert transcript.metadata == {
        "rollout_path": str(rollout_file.resolve()),
        "session_id": session_id,
        "session_timestamp": "2026-04-13T14:00:00+00:00",
        "cwd": cwd,
        "originator": "codex-tui",
        "cli_version": "0.120.0",
        "source": "cli",
        "model_provider": "openai",
    }

    assert [type(event) for event in transcript.events] == [
        ModelEvent,
        SpanBeginEvent,
        ToolEvent,
        SpanEndEvent,
        ModelEvent,
    ]
    assert isinstance(transcript.messages[0], ChatMessageSystem)
    assert isinstance(transcript.messages[1], ChatMessageUser)
    assert isinstance(transcript.messages[3], ChatMessageTool)
    assert isinstance(transcript.messages[4], ChatMessageAssistant)
    assert transcript.messages[4].content == "Done."


@pytest.mark.asyncio
async def test_codex_import_filters_by_session_id_and_limit(tmp_path: Path) -> None:
    """Codex discovery should support newest-first ordering, limits, and filters."""
    from inspect_scout.sources import codex

    older_id = "019d8739-0fa5-7a43-9bb7-805000da67aa"
    newer_id = "019d8739-0fa5-7a43-9bb7-805000da67bb"
    older_file = _write_rollout_file(
        tmp_path,
        session_id=older_id,
        started_at="2026-04-13T13:00:00.000Z",
        cwd="/Users/example/older",
        final_text="Older transcript.",
    )
    newer_file = _write_rollout_file(
        tmp_path,
        session_id=newer_id,
        started_at="2026-04-13T15:00:00.000Z",
        cwd="/Users/example/newer",
        final_text="Newer transcript.",
    )

    now = datetime.now().timestamp()
    os.utime(older_file, (now - 120, now - 120))
    os.utime(newer_file, (now - 60, now - 60))

    limited = [transcript async for transcript in codex(path=tmp_path, limit=1)]
    assert [transcript.transcript_id for transcript in limited] == [newer_id]

    filtered = [
        transcript
        async for transcript in codex(path=tmp_path, session_id=older_id, limit=5)
    ]
    assert [transcript.transcript_id for transcript in filtered] == [older_id]

    recent_only = [
        transcript
        async for transcript in codex(
            path=tmp_path,
            from_time=datetime.fromtimestamp(now - 90),
            to_time=datetime.fromtimestamp(now - 30),
        )
    ]
    assert [transcript.transcript_id for transcript in recent_only] == [newer_id]


@pytest.mark.asyncio
async def test_codex_import_supports_custom_tool_calls(tmp_path: Path) -> None:
    """Codex imports should handle newer custom tool rollout records."""
    from inspect_scout.sources import codex

    session_id = "019d8739-0fa5-7a43-9bb7-805000da67cc"
    rollout_file = _write_custom_tool_rollout_file(tmp_path, session_id)

    transcripts = [transcript async for transcript in codex(path=rollout_file)]

    assert len(transcripts) == 1
    transcript = transcripts[0]

    tool_events = [
        event
        for event in transcript.events
        if isinstance(event, ToolEvent) and event.function == "apply_patch"
    ]
    assert len(tool_events) == 1
    assert tool_events[0].arguments == {"input": "*** Begin Patch\n*** End Patch\n"}
    assert (
        tool_events[0].result == "Success. Updated the following files:\nM sample.txt\n"
    )


@pytest.mark.asyncio
async def test_codex_import_nests_subagent_rollouts_and_skips_children(
    tmp_path: Path,
) -> None:
    """Codex imports should nest child rollouts under spawn_agent spans."""
    from inspect_scout.sources import codex

    codex_home = tmp_path / ".codex"
    parent_file, _ = _write_subagent_rollout_files(codex_home)

    transcripts = [
        transcript async for transcript in codex(path=codex_home / "sessions")
    ]

    assert [transcript.transcript_id for transcript in transcripts] == [
        "parent-thread"
    ]

    transcript = transcripts[0]
    assert [type(event) for event in transcript.events] == [
        ModelEvent,
        SpanBeginEvent,
        ToolEvent,
        ModelEvent,
        SpanEndEvent,
        ModelEvent,
    ]

    agent_span = transcript.events[1]
    assert isinstance(agent_span, SpanBeginEvent)
    assert agent_span.id == "agent-call_spawn_1"
    assert agent_span.type == "agent"
    assert agent_span.name == "Sagan"
    assert agent_span.metadata == {
        "thread_id": "child-thread",
        "prompt": "Run exactly one task.",
        "role": "worker",
        "model": "gpt-5.4-mini",
        "reasoning_effort": "low",
    }

    child_model = transcript.events[3]
    assert isinstance(child_model, ModelEvent)
    assert child_model.model == "openai/gpt-5.4-mini"
    assert child_model.output is not None
    assert child_model.output.message.content == "Child finished."

    assert transcript.metadata == {
        "rollout_path": str(parent_file.resolve()),
        "session_id": "parent-thread",
        "session_timestamp": "2026-04-13T14:00:00+00:00",
        "cwd": "/Users/example/project",
        "originator": "codex-tui",
        "cli_version": "0.120.0",
        "source": "cli",
        "model_provider": "openai",
    }


@pytest.mark.asyncio
async def test_codex_import_skips_direct_child_rollout_file(tmp_path: Path) -> None:
    """Child Codex rollouts should not import as standalone transcripts."""
    from inspect_scout.sources import codex

    _, child_file = _write_subagent_rollout_files(tmp_path / ".codex")

    transcripts = [transcript async for transcript in codex(path=child_file)]

    assert transcripts == []
