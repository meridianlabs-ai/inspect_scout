"""Integration tests for Claude Code import source."""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def slug_fixtures_dir(tmp_path: Path) -> Path:
    """Create a temp directory with two session files sharing the same slug.

    Returns a directory (like a Claude Code project dir) containing
    the two fixture files, so discover_session_files can find them.
    """
    fixtures = Path(__file__).parent / "fixtures"
    # Copy slug fixtures into tmp_path so they form their own isolated directory
    for name in ["slug_session_1.jsonl", "slug_session_2.jsonl"]:
        src = fixtures / name
        (tmp_path / name).write_text(src.read_text())
    return tmp_path


@pytest.fixture
def streaming_events_with_subagent() -> list[dict[str, Any]]:
    """Create test events simulating streaming with interleaved subagent events.

    This simulates headless mode where subagent events come inline with
    different sessionIds, rather than being in separate files.
    """
    return [
        # Main session: user message
        {
            "uuid": "main-001",
            "parentUuid": None,
            "isSidechain": False,
            "sessionId": "main-session-001",
            "type": "user",
            "message": {"role": "user", "content": "Explore the codebase"},
            "timestamp": "2026-01-31T10:00:00.000Z",
        },
        # Main session: assistant with Task tool call
        {
            "uuid": "main-002",
            "parentUuid": "main-001",
            "isSidechain": False,
            "sessionId": "main-session-001",
            "type": "assistant",
            "message": {
                "id": "msg_001",
                "model": "claude-opus-4-5-20251101",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll explore the codebase for you."},
                    {
                        "type": "tool_use",
                        "id": "toolu_task_001",
                        "name": "Task",
                        "input": {
                            "description": "Explore codebase",
                            "prompt": "Explore the codebase structure.",
                            "subagent_type": "Explore",
                        },
                    },
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
            "timestamp": "2026-01-31T10:00:01.000Z",
        },
        # Subagent events (different sessionId)
        {
            "uuid": "sub-001",
            "parentUuid": None,
            "isSidechain": True,
            "sessionId": "subagent-session-001",
            "type": "user",
            "message": {"role": "user", "content": "Explore the codebase structure."},
            "timestamp": "2026-01-31T10:00:02.000Z",
        },
        {
            "uuid": "sub-002",
            "parentUuid": "sub-001",
            "isSidechain": True,
            "sessionId": "subagent-session-001",
            "type": "assistant",
            "message": {
                "id": "msg_sub_001",
                "model": "claude-sonnet-4-20250514",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll list the directories."},
                    {
                        "type": "tool_use",
                        "id": "toolu_bash_001",
                        "name": "Bash",
                        "input": {"command": "ls -la"},
                    },
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 80, "output_tokens": 30},
            },
            "timestamp": "2026-01-31T10:00:03.000Z",
        },
        {
            "uuid": "sub-003",
            "parentUuid": "sub-002",
            "isSidechain": True,
            "sessionId": "subagent-session-001",
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_bash_001",
                        "content": "src/\ntests/\ndocs/",
                    }
                ],
            },
            "timestamp": "2026-01-31T10:00:04.000Z",
        },
        {
            "uuid": "sub-004",
            "parentUuid": "sub-003",
            "isSidechain": True,
            "sessionId": "subagent-session-001",
            "type": "assistant",
            "message": {
                "id": "msg_sub_002",
                "model": "claude-sonnet-4-20250514",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "The codebase has src/, tests/, and docs/ directories.",
                    }
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 100, "output_tokens": 40},
            },
            "timestamp": "2026-01-31T10:00:05.000Z",
        },
        # Main session: tool result with agentId
        {
            "uuid": "main-003",
            "parentUuid": "main-002",
            "isSidechain": False,
            "sessionId": "main-session-001",
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_task_001",
                        "content": [
                            {
                                "type": "text",
                                "text": "The codebase has src/, tests/, and docs/.",
                            },
                            {
                                "type": "text",
                                "text": '{"agentId": "subagent-session-001"}',
                            },
                        ],
                    }
                ],
            },
            "toolUseResult": {
                "status": "completed",
                "agentId": "subagent-session-001",
                "totalTokens": 250,
            },
            "timestamp": "2026-01-31T10:00:06.000Z",
        },
        # Main session: final response
        {
            "uuid": "main-004",
            "parentUuid": "main-003",
            "isSidechain": False,
            "sessionId": "main-session-001",
            "type": "assistant",
            "message": {
                "id": "msg_002",
                "model": "claude-opus-4-5-20251101",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "The exploration found three main directories.",
                    }
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 150, "output_tokens": 30},
            },
            "timestamp": "2026-01-31T10:00:07.000Z",
        },
    ]


@pytest.mark.asyncio
async def test_simple_conversation(fixtures_dir: Path) -> None:
    """Test importing a simple user/assistant conversation."""
    from inspect_scout import Transcript
    from inspect_scout.sources import claude_code
    from inspect_scout.sources._claude_code.client import CLAUDE_CODE_SOURCE_TYPE

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code(path=session_file):
        transcripts.append(transcript)

    assert len(transcripts) == 1
    transcript = transcripts[0]

    assert isinstance(transcript, Transcript)
    assert transcript.source_type == CLAUDE_CODE_SOURCE_TYPE
    assert transcript.transcript_id == "test-session-001"

    # Should have 4 messages: 2 user + 2 assistant
    assert transcript.message_count == 4

    # Check message content
    assert len(transcript.messages) == 4
    assert transcript.messages[0].role == "user"
    assert transcript.messages[1].role == "assistant"
    assert transcript.messages[2].role == "user"
    assert transcript.messages[3].role == "assistant"


@pytest.mark.asyncio
async def test_tool_call_conversation(fixtures_dir: Path) -> None:
    """Test importing a conversation with tool calls."""
    from inspect_ai.model import ContentReasoning
    from inspect_ai.model._chat_message import ChatMessageAssistant
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "tool_call_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code(path=session_file):
        transcripts.append(transcript)

    assert len(transcripts) == 1
    transcript = transcripts[0]

    # Should have messages including tool messages
    assert transcript.message_count is not None
    assert transcript.message_count >= 3

    # Find assistant message with tool call
    assistant_msgs = [m for m in transcript.messages if m.role == "assistant"]
    assert len(assistant_msgs) >= 1

    # First assistant message should have tool call
    first_assistant = assistant_msgs[0]
    assert isinstance(first_assistant, ChatMessageAssistant)
    assert first_assistant.tool_calls is not None
    assert len(first_assistant.tool_calls) == 1
    assert first_assistant.tool_calls[0].function == "Read"

    # Should have ContentReasoning (thinking block)
    content = first_assistant.content
    if isinstance(content, list):
        reasoning_blocks = [c for c in content if isinstance(c, ContentReasoning)]
        assert len(reasoning_blocks) == 1
        assert reasoning_blocks[0].signature == "sig_abc123"


@pytest.mark.asyncio
async def test_clear_split_session(fixtures_dir: Path) -> None:
    """Test that /clear command splits session into multiple transcripts."""
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "clear_split_session.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code(path=session_file):
        transcripts.append(transcript)

    # Should produce 2 transcripts (split on /clear)
    assert len(transcripts) == 2

    # First transcript should have segment index 0
    assert transcripts[0].transcript_id == "test-session-003-0"
    # Second transcript should have segment index 1
    assert transcripts[1].transcript_id == "test-session-003-1"

    # Each should have messages
    assert transcripts[0].message_count == 2  # user + assistant before clear
    assert transcripts[1].message_count == 2  # user + assistant after clear


@pytest.mark.asyncio
async def test_agent_session(fixtures_dir: Path) -> None:
    """Test importing a session with Task agent spawn."""
    from inspect_ai.model._chat_message import ChatMessageAssistant
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "agent_session.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code(path=session_file):
        transcripts.append(transcript)

    assert len(transcripts) == 1
    transcript = transcripts[0]

    # Should have messages
    assert transcript.message_count is not None
    assert transcript.message_count >= 2

    # Check for Task tool call in assistant message
    assistant_msgs = [m for m in transcript.messages if m.role == "assistant"]
    task_call_found = False
    for msg in assistant_msgs:
        if isinstance(msg, ChatMessageAssistant) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.function == "Task":
                    task_call_found = True
                    assert tc.arguments.get("subagent_type") == "Explore"
    assert task_call_found, "Should have Task tool call"


@pytest.mark.asyncio
async def test_compaction_session(fixtures_dir: Path) -> None:
    """Test importing a session with compaction boundary."""
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "compaction_session.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code(path=session_file):
        transcripts.append(transcript)

    assert len(transcripts) == 1
    transcript = transcripts[0]

    # Should have messages including compaction summary
    assert transcript.message_count is not None
    assert transcript.message_count >= 3

    # Check that compaction summary is included in messages
    messages_content = [m.content for m in transcript.messages if hasattr(m, "content")]
    found_summary = False
    for content in messages_content:
        if isinstance(content, str) and "Summary of previous conversation" in content:
            found_summary = True
    assert found_summary, "Compaction summary should be in messages"


@pytest.mark.asyncio
async def test_import_from_directory(fixtures_dir: Path) -> None:
    """Test importing from a directory of session files."""
    from inspect_scout.sources import claude_code

    if not fixtures_dir.exists():
        pytest.skip("Test fixtures directory not available")

    count = 0
    async for transcript in claude_code(path=fixtures_dir, limit=10):
        assert transcript.transcript_id is not None
        count += 1

    # Should find multiple transcripts from the fixtures
    # We have 5 fixture files, but clear_split produces 2 transcripts
    assert count >= 5


@pytest.mark.asyncio
async def test_import_with_limit(fixtures_dir: Path) -> None:
    """Test that limit parameter works."""
    from inspect_scout.sources import claude_code

    if not fixtures_dir.exists():
        pytest.skip("Test fixtures directory not available")

    count = 0
    async for _transcript in claude_code(path=fixtures_dir, limit=2):
        count += 1

    # Should respect limit
    assert count == 2


@pytest.mark.asyncio
async def test_model_extraction(fixtures_dir: Path) -> None:
    """Test that model name is correctly extracted."""
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    async for transcript in claude_code(path=session_file):
        assert transcript.model == "claude-opus-4-5-20251101"
        break


@pytest.mark.asyncio
async def test_token_counting(fixtures_dir: Path) -> None:
    """Test that tokens are correctly counted."""
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    async for transcript in claude_code(path=session_file):
        # Should have token counts
        assert transcript.total_tokens is not None
        assert transcript.total_tokens > 0
        # 100+20+150+30 = 300 from the fixture
        assert transcript.total_tokens == 300
        break


@pytest.mark.asyncio
async def test_token_counting_includes_subagents(
    streaming_events_with_subagent: list[dict[str, Any]],
) -> None:
    """Token counts include both main and subagent ModelEvent usage.

    The streaming_events_with_subagent fixture has:
    - Main assistant (main-002): input=100, output=50 → 150
    - Subagent assistant (sub-002): input=80, output=30 → 110
    - Subagent assistant (sub-004): input=100, output=40 → 140
    - Main assistant (main-004): input=150, output=30 → 180
    Total: 580
    """
    from inspect_ai.event import Event, ModelEvent
    from inspect_scout.sources._claude_code.events import claude_code_events
    from inspect_scout.sources._claude_code.extraction import sum_scout_tokens

    scout_events: list[Event] = []
    async for event in claude_code_events(streaming_events_with_subagent):
        scout_events.append(event)

    model_events = [e for e in scout_events if isinstance(e, ModelEvent)]
    # Should have model events from both main and subagent sessions
    assert len(model_events) >= 3

    total = sum_scout_tokens(scout_events)
    # Main: 150 + 180 = 330, Subagent: 110 + 140 = 250, Total: 580
    assert total == 580


@pytest.mark.asyncio
async def test_claude_code_events_streaming(
    streaming_events_with_subagent: list[dict[str, Any]],
) -> None:
    """Test claude_code_events with subagent events interleaved in the stream.

    This simulates headless mode where events from subagents come inline
    with different sessionIds.
    """
    from inspect_ai.event import ModelEvent, SpanBeginEvent, SpanEndEvent, ToolEvent
    from inspect_scout.sources._claude_code.events import claude_code_events

    events: list[Any] = []
    async for event in claude_code_events(streaming_events_with_subagent):
        events.append(event)

    # Should have events from main session
    assert len(events) > 0

    # First event should be ModelEvent for the main assistant
    model_events = [e for e in events if isinstance(e, ModelEvent)]
    assert len(model_events) >= 2  # At least 2: one with Task call, one final

    # Check first model event has Task tool call
    first_model = model_events[0]
    assert first_model.output is not None
    assert first_model.output.message is not None
    assert first_model.output.message.tool_calls is not None
    assert len(first_model.output.message.tool_calls) == 1
    assert first_model.output.message.tool_calls[0].function == "Task"

    # Should have tool spans
    span_begins = [e for e in events if isinstance(e, SpanBeginEvent)]
    span_ends = [e for e in events if isinstance(e, SpanEndEvent)]
    assert len(span_begins) > 0
    assert len(span_begins) == len(span_ends)

    # Should have Tool span with type="tool"
    tool_spans = [e for e in span_begins if e.type == "tool"]
    assert len(tool_spans) >= 1

    # Should have agent span with type="agent" for the Task
    agent_spans = [e for e in span_begins if e.type == "agent"]
    assert len(agent_spans) >= 1
    assert agent_spans[0].name == "Explore"

    # Should have ToolEvents
    tool_events = [e for e in events if isinstance(e, ToolEvent)]
    assert len(tool_events) > 0

    # The Task tool event should exist
    task_tool_events = [e for e in tool_events if e.function == "Task"]
    assert len(task_tool_events) == 1

    # Subagent events should be nested: check for Bash tool from subagent
    bash_tool_events = [e for e in tool_events if e.function == "Bash"]
    assert len(bash_tool_events) == 1


@pytest.mark.asyncio
async def test_claude_code_events_async_iterable(
    streaming_events_with_subagent: list[dict[str, Any]],
) -> None:
    """Test that claude_code_events works with async iterables."""
    from collections.abc import AsyncIterator

    from inspect_ai.event import ModelEvent
    from inspect_scout.sources._claude_code.events import claude_code_events

    async def async_event_stream() -> AsyncIterator[dict[str, Any]]:
        for event in streaming_events_with_subagent:
            yield event

    events: list[Any] = []
    async for event in claude_code_events(async_event_stream()):
        events.append(event)

    # Should work the same as sync iterable
    model_events = [e for e in events if isinstance(e, ModelEvent)]
    assert len(model_events) >= 2


@pytest.mark.asyncio
async def test_claude_code_events_no_subagent_events() -> None:
    """Test claude_code_events with simple events (no subagents)."""
    from inspect_ai.event import ModelEvent
    from inspect_scout.sources._claude_code.events import claude_code_events

    simple_events = [
        {
            "uuid": "001",
            "sessionId": "session-001",
            "type": "user",
            "message": {"role": "user", "content": "Hello"},
            "timestamp": "2026-01-31T10:00:00.000Z",
        },
        {
            "uuid": "002",
            "parentUuid": "001",
            "sessionId": "session-001",
            "type": "assistant",
            "message": {
                "id": "msg_001",
                "model": "claude-opus-4-5-20251101",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi there!"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            "timestamp": "2026-01-31T10:00:01.000Z",
        },
    ]

    events: list[Any] = []
    async for event in claude_code_events(simple_events):
        events.append(event)

    # Should have one ModelEvent
    model_events = [e for e in events if isinstance(e, ModelEvent)]
    assert len(model_events) == 1
    assert model_events[0].model == "claude-opus-4-5-20251101"


def _make_main_user(
    uuid: str, content: str | list[dict[str, Any]], ts: str
) -> dict[str, Any]:
    """Helper to build a main-session user event."""
    msg: dict[str, Any] = {"role": "user", "content": content}
    return {
        "uuid": uuid,
        "parentUuid": None,
        "isSidechain": False,
        "sessionId": "main",
        "type": "user",
        "message": msg,
        "timestamp": ts,
    }


def _make_main_assistant(
    uuid: str,
    parent: str,
    content: list[dict[str, Any]],
    ts: str,
    *,
    stop_reason: str = "tool_use",
) -> dict[str, Any]:
    """Helper to build a main-session assistant event."""
    return {
        "uuid": uuid,
        "parentUuid": parent,
        "isSidechain": False,
        "sessionId": "main",
        "type": "assistant",
        "message": {
            "id": f"msg_{uuid}",
            "model": "claude-opus-4-5-20251101",
            "role": "assistant",
            "content": content,
            "stop_reason": stop_reason,
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
        "timestamp": ts,
    }


def _make_subagent_event(
    uuid: str,
    session_id: str,
    event_type: str,
    message: dict[str, Any],
    ts: str,
) -> dict[str, Any]:
    """Helper to build a subagent (sidechain) event."""
    return {
        "uuid": uuid,
        "parentUuid": None,
        "isSidechain": True,
        "sessionId": session_id,
        "type": event_type,
        "message": message,
        "timestamp": ts,
    }


def _task_tool_use(tool_id: str) -> dict[str, Any]:
    """Build a Task tool_use content block."""
    return {
        "type": "tool_use",
        "id": tool_id,
        "name": "Task",
        "input": {
            "description": "do work",
            "prompt": "do the work",
            "subagent_type": "Explore",
        },
    }


def _tool_result_block(tool_id: str, text: str = "done") -> dict[str, Any]:
    """Build a tool_result content block."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_id,
        "content": text,
    }


@pytest.mark.asyncio
async def test_claude_code_events_subagent_arrives_first() -> None:
    """Subagent events arriving before their Task tool_use are buffered, not dropped."""
    from inspect_ai.event import SpanBeginEvent, ToolEvent
    from inspect_scout.sources._claude_code.events import claude_code_events

    raw: list[dict[str, Any]] = [
        # Subagent events arrive BEFORE the main assistant emits the Task tool_use
        _make_subagent_event(
            "s1",
            "sub-sess-1",
            "user",
            {"role": "user", "content": "explore"},
            "2026-01-31T10:00:00.000Z",
        ),
        _make_subagent_event(
            "s2",
            "sub-sess-1",
            "assistant",
            {
                "id": "msg_s2",
                "model": "claude-sonnet-4-20250514",
                "role": "assistant",
                "content": [{"type": "text", "text": "Found stuff."}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            "2026-01-31T10:00:01.000Z",
        ),
        # Now main session: user, then assistant with Task tool
        _make_main_user("m1", "Hello", "2026-01-31T10:00:02.000Z"),
        _make_main_assistant(
            "m2",
            "m1",
            [
                {"type": "text", "text": "Let me explore."},
                _task_tool_use("toolu_task_1"),
            ],
            "2026-01-31T10:00:03.000Z",
        ),
        # Tool result for the Task
        _make_main_user(
            "m3",
            [_tool_result_block("toolu_task_1", "explored")],
            "2026-01-31T10:00:04.000Z",
        ),
    ]

    events: list[Any] = []
    async for event in claude_code_events(raw):
        events.append(event)

    # The subagent events should be buffered and matched to the Task tool
    agent_spans = [
        e for e in events if isinstance(e, SpanBeginEvent) and e.type == "agent"
    ]
    assert len(agent_spans) == 1, "Early subagent events should be matched to Task tool"

    task_tools = [
        e for e in events if isinstance(e, ToolEvent) and e.function == "Task"
    ]
    assert len(task_tools) == 1


@pytest.mark.asyncio
async def test_claude_code_events_parallel_subagents() -> None:
    """Two Task tools in one assistant message get correct FIFO subagent assignment."""
    from inspect_ai.event import SpanBeginEvent
    from inspect_scout.sources._claude_code.events import claude_code_events

    raw: list[dict[str, Any]] = [
        _make_main_user("m1", "Do two things", "2026-01-31T10:00:00.000Z"),
        # Assistant emits two Task tool_use blocks
        _make_main_assistant(
            "m2",
            "m1",
            [
                {"type": "text", "text": "I'll do both."},
                _task_tool_use("toolu_A"),
                _task_tool_use("toolu_B"),
            ],
            "2026-01-31T10:00:01.000Z",
        ),
        # First subagent session arrives — should bind to toolu_A (FIFO)
        _make_subagent_event(
            "sa1",
            "sub-A",
            "user",
            {"role": "user", "content": "task A prompt"},
            "2026-01-31T10:00:02.000Z",
        ),
        _make_subagent_event(
            "sa2",
            "sub-A",
            "assistant",
            {
                "id": "msg_sa2",
                "model": "claude-sonnet-4-20250514",
                "role": "assistant",
                "content": [{"type": "text", "text": "A done."}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            "2026-01-31T10:00:03.000Z",
        ),
        # Second subagent session arrives — should bind to toolu_B (FIFO)
        _make_subagent_event(
            "sb1",
            "sub-B",
            "user",
            {"role": "user", "content": "task B prompt"},
            "2026-01-31T10:00:04.000Z",
        ),
        _make_subagent_event(
            "sb2",
            "sub-B",
            "assistant",
            {
                "id": "msg_sb2",
                "model": "claude-sonnet-4-20250514",
                "role": "assistant",
                "content": [{"type": "text", "text": "B done."}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
            "2026-01-31T10:00:05.000Z",
        ),
        # Tool results
        _make_main_user(
            "m3",
            [
                _tool_result_block("toolu_A", "result A"),
                _tool_result_block("toolu_B", "result B"),
            ],
            "2026-01-31T10:00:06.000Z",
        ),
    ]

    events: list[Any] = []
    async for event in claude_code_events(raw):
        events.append(event)

    agent_spans = [
        e for e in events if isinstance(e, SpanBeginEvent) and e.type == "agent"
    ]
    assert len(agent_spans) == 2, "Both Task tools should get agent spans"


@pytest.mark.asyncio
async def test_claude_code_events_isSidechain_routing() -> None:
    """IsSidechain flag is used for routing — first event being subagent doesn't corrupt main."""
    from inspect_ai.event import ModelEvent
    from inspect_scout.sources._claude_code.events import claude_code_events

    raw: list[dict[str, Any]] = [
        # Very first event in the stream is a subagent event
        _make_subagent_event(
            "s1",
            "sub-sess",
            "user",
            {"role": "user", "content": "subagent prompt"},
            "2026-01-31T10:00:00.000Z",
        ),
        # Main session events follow
        _make_main_user("m1", "Hello", "2026-01-31T10:00:01.000Z"),
        _make_main_assistant(
            "m2",
            "m1",
            [{"type": "text", "text": "Hi there!"}],
            "2026-01-31T10:00:02.000Z",
            stop_reason="end_turn",
        ),
    ]

    events: list[Any] = []
    async for event in claude_code_events(raw):
        events.append(event)

    # Main session should NOT be corrupted by the subagent arriving first
    model_events = [e for e in events if isinstance(e, ModelEvent)]
    assert len(model_events) == 1, "Main session ModelEvent should still be produced"
    assert model_events[0].model == "claude-opus-4-5-20251101"


# =========================================================================
# Slug merging tests
# =========================================================================


class TestPeekSlug:
    """Tests for peek_slug()."""

    def test_extracts_slug_from_first_line(self, tmp_path: Path) -> None:
        """Reads slug from a JSONL file's first event."""
        from inspect_scout.sources._claude_code.client import peek_slug

        f = tmp_path / "session.jsonl"
        f.write_text(
            json.dumps(
                {
                    "uuid": "1",
                    "type": "user",
                    "sessionId": "s1",
                    "slug": "my-slug",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "message": {"content": "hi"},
                }
            )
            + "\n"
        )
        assert peek_slug(f) == "my-slug"

    def test_returns_none_when_no_slug(self, tmp_path: Path) -> None:
        """Returns None when no slug field is present."""
        from inspect_scout.sources._claude_code.client import peek_slug

        f = tmp_path / "session.jsonl"
        f.write_text(
            json.dumps(
                {
                    "uuid": "1",
                    "type": "user",
                    "sessionId": "s1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "message": {"content": "hi"},
                }
            )
            + "\n"
        )
        assert peek_slug(f) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Returns None for a non-existent file."""
        from inspect_scout.sources._claude_code.client import peek_slug

        assert peek_slug(tmp_path / "nonexistent.jsonl") is None

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        """Skips blank lines to find slug."""
        from inspect_scout.sources._claude_code.client import peek_slug

        f = tmp_path / "session.jsonl"
        lines = [
            "",
            "",
            json.dumps(
                {
                    "uuid": "1",
                    "type": "user",
                    "sessionId": "s1",
                    "slug": "found-it",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "message": {"content": "hi"},
                }
            ),
        ]
        f.write_text("\n".join(lines) + "\n")
        assert peek_slug(f) == "found-it"


@pytest.mark.asyncio
async def test_slug_merge_combines_sessions(slug_fixtures_dir: Path) -> None:
    """Two session files with same slug produce one merged transcript."""
    from inspect_ai.event import InfoEvent
    from inspect_scout.sources import claude_code

    transcripts = []
    async for transcript in claude_code(path=slug_fixtures_dir):
        transcripts.append(transcript)

    # Should merge into a single transcript
    assert len(transcripts) == 1
    merged = transcripts[0]

    # transcript_id should be from the first session (chronologically)
    assert merged.transcript_id == "session-aaa"

    # task_id should be the slug
    assert merged.task_id == "merged-slug-test"

    # Messages from both sessions should be combined
    assert merged.message_count == 4  # 2 from each session

    # Events should include an InfoEvent boundary separator
    info_events = [e for e in merged.events if isinstance(e, InfoEvent)]
    assert len(info_events) >= 1
    assert "Context reset" in str(info_events[0].data)

    # Tokens should be summed (100+50 + 200+100 = 450)
    assert merged.total_tokens == 450

    # Metadata should contain session_ids
    assert "session_ids" in merged.metadata
    assert "session-aaa" in merged.metadata["session_ids"]
    assert "session-bbb" in merged.metadata["session_ids"]


@pytest.mark.asyncio
async def test_single_session_slug_unchanged(fixtures_dir: Path) -> None:
    """A single session file with a slug produces unchanged output."""
    from inspect_scout.sources import claude_code

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code(path=session_file):
        transcripts.append(transcript)

    # Single file should produce one transcript as before
    assert len(transcripts) == 1
    transcript = transcripts[0]

    # Should preserve existing behavior
    assert transcript.transcript_id == "test-session-001"
    assert transcript.task_id == "simple-conv-slug"
    assert transcript.message_count == 4
    # No session_ids metadata for single sessions
    assert "session_ids" not in transcript.metadata


@pytest.mark.asyncio
async def test_slug_backfill_from_single_file(slug_fixtures_dir: Path) -> None:
    """Passing a single slug file as path backfills its partner from siblings."""
    from inspect_scout.sources import claude_code

    # Pass only one of the two slug partner files
    single_file = slug_fixtures_dir / "slug_session_1.jsonl"

    transcripts = []
    async for transcript in claude_code(path=single_file):
        transcripts.append(transcript)

    # Backfill should find the partner, producing one merged transcript
    assert len(transcripts) == 1
    merged = transcripts[0]
    assert merged.task_id == "merged-slug-test"
    assert merged.message_count == 4  # 2 from each session
    assert "session_ids" in merged.metadata
    assert len(merged.metadata["session_ids"]) == 2


@pytest.mark.asyncio
async def test_slug_backfill_with_time_filter(slug_fixtures_dir: Path) -> None:
    """Time filter that excludes one slug partner still produces merged result."""
    from datetime import datetime, timezone

    from inspect_scout.sources import claude_code

    # slug_session_1 timestamps are at 10:00:00, slug_session_2 at 10:01:00
    # Use a from_time that excludes session_1 but includes session_2
    from_time = datetime(2026, 1, 31, 10, 0, 30, tzinfo=timezone.utc)

    # Set the mtime of session_1 to be before from_time so it gets excluded
    import os
    import time

    session_1 = slug_fixtures_dir / "slug_session_1.jsonl"
    session_2 = slug_fixtures_dir / "slug_session_2.jsonl"

    # Set session_1 mtime to the past (before from_time)
    old_time = time.mktime(datetime(2026, 1, 31, 9, 0, 0).timetuple())
    os.utime(session_1, (old_time, old_time))

    # Set session_2 mtime to after from_time
    new_time = time.mktime(datetime(2026, 1, 31, 11, 0, 0).timetuple())
    os.utime(session_2, (new_time, new_time))

    transcripts = []
    async for transcript in claude_code(
        path=slug_fixtures_dir, from_time=from_time.replace(tzinfo=None)
    ):
        transcripts.append(transcript)

    # Only session_2 passes the time filter, but backfill should find session_1
    assert len(transcripts) == 1
    merged = transcripts[0]
    assert merged.task_id == "merged-slug-test"
    assert merged.message_count == 4  # both sessions merged
