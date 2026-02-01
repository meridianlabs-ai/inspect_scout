"""Integration tests for Claude Code import source."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory."""
    return Path(__file__).parent / "fixtures"


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
