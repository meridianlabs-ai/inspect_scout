"""Integration tests for Claude Code import source."""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory."""
    return Path(__file__).parent / "fixtures"


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
    from inspect_scout._transcript.types import Transcript
    from inspect_scout.sources import claude_code_transcripts
    from inspect_scout.sources._claude_code.client import CLAUDE_CODE_SOURCE_TYPE

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code_transcripts(path=session_file):
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
    from inspect_scout.sources import claude_code_transcripts

    session_file = fixtures_dir / "tool_call_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code_transcripts(path=session_file):
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
    from inspect_scout.sources import claude_code_transcripts

    session_file = fixtures_dir / "clear_split_session.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code_transcripts(path=session_file):
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
    from inspect_scout.sources import claude_code_transcripts

    session_file = fixtures_dir / "agent_session.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code_transcripts(path=session_file):
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
    from inspect_scout.sources import claude_code_transcripts

    session_file = fixtures_dir / "compaction_session.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    transcripts = []
    async for transcript in claude_code_transcripts(path=session_file):
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
    from inspect_scout.sources import claude_code_transcripts

    if not fixtures_dir.exists():
        pytest.skip("Test fixtures directory not available")

    count = 0
    async for transcript in claude_code_transcripts(path=fixtures_dir, limit=10):
        assert transcript.transcript_id is not None
        count += 1

    # Should find multiple transcripts from the fixtures
    # We have 5 fixture files, but clear_split produces 2 transcripts
    assert count >= 5


@pytest.mark.asyncio
async def test_import_with_limit(fixtures_dir: Path) -> None:
    """Test that limit parameter works."""
    from inspect_scout.sources import claude_code_transcripts

    if not fixtures_dir.exists():
        pytest.skip("Test fixtures directory not available")

    count = 0
    async for _transcript in claude_code_transcripts(path=fixtures_dir, limit=2):
        count += 1

    # Should respect limit
    assert count == 2


@pytest.mark.asyncio
async def test_model_extraction(fixtures_dir: Path) -> None:
    """Test that model name is correctly extracted."""
    from inspect_scout.sources import claude_code_transcripts

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    async for transcript in claude_code_transcripts(path=session_file):
        assert transcript.model == "claude-opus-4-5-20251101"
        break


@pytest.mark.asyncio
async def test_token_counting(fixtures_dir: Path) -> None:
    """Test that tokens are correctly counted."""
    from inspect_scout.sources import claude_code_transcripts

    session_file = fixtures_dir / "simple_conversation.jsonl"
    if not session_file.exists():
        pytest.skip("Test fixture not available")

    async for transcript in claude_code_transcripts(path=session_file):
        # Should have token counts
        assert transcript.total_tokens is not None
        assert transcript.total_tokens > 0
        # 100+20+150+30 = 300 from the fixture
        assert transcript.total_tokens == 300
        break


@pytest.mark.asyncio
async def test_claude_code_events_streaming(
    streaming_events_with_subagent: list[dict[str, Any]],
) -> None:
    """Test claude_code_events with subagent events interleaved in the stream.

    This simulates headless mode where events from subagents come inline
    with different sessionIds.
    """
    from inspect_ai.event import ModelEvent, SpanBeginEvent, SpanEndEvent, ToolEvent
    from inspect_scout.sources import claude_code_events

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
    from inspect_scout.sources import claude_code_events

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
async def test_extract_messages_from_scout_events() -> None:
    """Test extracting messages from Scout events."""
    from inspect_ai.event import ModelEvent
    from inspect_ai.model import ModelOutput
    from inspect_ai.model._chat_message import ChatMessageAssistant, ChatMessageUser
    from inspect_ai.model._generate_config import GenerateConfig
    from inspect_ai.model._model_output import ChatCompletionChoice
    from inspect_scout.sources._claude_code.extraction import (
        extract_messages_from_scout_events,
    )

    # Create mock events
    user_msg = ChatMessageUser(content="Hello")
    assistant_msg = ChatMessageAssistant(content="Hi there")

    model_event = ModelEvent(
        model="test-model",
        input=[user_msg],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(
            model="test-model",
            choices=[
                ChatCompletionChoice(message=assistant_msg, stop_reason="stop"),
            ],
        ),
    )

    events: list[Any] = [model_event]
    messages = extract_messages_from_scout_events(events)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there"


@pytest.mark.asyncio
async def test_claude_code_events_no_subagent_events() -> None:
    """Test claude_code_events with simple events (no subagents)."""
    from inspect_ai.event import ModelEvent
    from inspect_scout.sources import claude_code_events

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
