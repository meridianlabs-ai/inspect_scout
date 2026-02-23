"""Tests for Claude Code import source."""

from typing import Any

from inspect_scout.sources._claude_code.client import (
    CLAUDE_CODE_SOURCE_TYPE,
    decode_project_path,
    encode_project_path,
)
from inspect_scout.sources._claude_code.detection import (
    _get_command_name,
    get_event_type,
    get_model_name,
    get_task_agent_info,
    get_timestamp,
    is_assistant_event,
    is_clear_command,
    is_compact_boundary,
    is_compact_summary,
    is_skill_command,
    is_user_event,
    should_skip_event,
)
from inspect_scout.sources._claude_code.extraction import (
    extract_assistant_content,
    extract_compaction_info,
    extract_tool_result_messages,
    extract_usage,
    extract_user_message,
    sum_tokens,
)
from inspect_scout.sources._claude_code.models import (
    AssistantEvent,
    AssistantMessage,
    BaseEvent,
    CompactMetadata,
    ContentToolUse,
    SystemEvent,
    Usage,
    UserEvent,
    UserMessage,
    consolidate_assistant_events,
    parse_event,
)
from inspect_scout.sources._claude_code.tree import (
    build_event_tree,
    find_clear_indices,
    flatten_tree_chronological,
    split_on_clear,
)


def _parse(raw: dict[str, Any]) -> BaseEvent:
    """Parse a raw event dict, asserting it succeeds."""
    result = parse_event(raw)
    assert result is not None
    return result


class TestPathEncoding:
    """Tests for path encoding/decoding."""

    def test_decode_project_path(self) -> None:
        """Test decoding Claude Code project paths."""
        # With validate=False, uses naive replacement
        assert (
            decode_project_path("-Users-jjallaire-dev-project", validate=False)
            == "/Users/jjallaire/dev/project"
        )
        assert decode_project_path("-Users-foo-bar", validate=False) == "/Users/foo/bar"

    def test_decode_project_path_with_validation(self) -> None:
        """Test decoding with filesystem validation."""
        # With validate=True (default), falls back to naive if path doesn't exist
        # Since /Users/jjallaire/dev/project likely doesn't exist in test env,
        # it should fall back to naive replacement
        assert (
            decode_project_path("-Users-jjallaire-dev-project")
            == "/Users/jjallaire/dev/project"
        )

    def test_decode_project_path_real_paths(self) -> None:
        """Test that validation finds real paths on the filesystem."""
        import shutil
        from pathlib import Path

        # Create a temporary directory with hyphens in the name
        tmp_base = Path("/tmp/test-claude-code-paths")
        hyphenated_dir = tmp_base / "my-project"
        nested_dir = hyphenated_dir / "src"

        try:
            nested_dir.mkdir(parents=True, exist_ok=True)

            # Encode the path: /tmp/test-claude-code-paths/my-project/src
            # becomes: -tmp-test-claude-code-paths-my-project-src
            encoded = "-tmp-test-claude-code-paths-my-project-src"

            # Without validation, would incorrectly decode to:
            # /tmp/test/claude/code/paths/my/project/src
            assert (
                decode_project_path(encoded, validate=False)
                == "/tmp/test/claude/code/paths/my/project/src"
            )

            # With validation (default), should find the correct path
            decoded = decode_project_path(encoded, validate=True)
            assert decoded == "/tmp/test-claude-code-paths/my-project/src"

        finally:
            # Cleanup
            if tmp_base.exists():
                shutil.rmtree(tmp_base)

    def test_encode_project_path(self) -> None:
        """Test encoding file system paths."""
        assert (
            encode_project_path("/Users/jjallaire/dev/project")
            == "-Users-jjallaire-dev-project"
        )
        assert encode_project_path("/Users/foo/bar") == "-Users-foo-bar"

    def test_roundtrip(self) -> None:
        """Test that encoding and decoding are inverses.

        Note: This is a lossy encoding - hyphens in directory names cannot
        be distinguished from path separators without filesystem validation.
        This test uses a path without hyphens in directory names.
        """
        original = "/Users/jjallaire/dev/project"
        encoded = encode_project_path(original)
        decoded = decode_project_path(encoded, validate=False)
        assert decoded == original


class TestEventDetection:
    """Tests for event type detection."""

    def test_get_event_type(self) -> None:
        """Test getting event type."""
        user_event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert get_event_type(user_event) == "user"

        assistant_event = AssistantEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert get_event_type(assistant_event) == "assistant"

    def test_is_user_event(self) -> None:
        """Test user event detection."""
        user_event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert is_user_event(user_event)

        assistant_event = AssistantEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert not is_user_event(assistant_event)

    def test_is_assistant_event(self) -> None:
        """Test assistant event detection."""
        assistant_event = AssistantEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert is_assistant_event(assistant_event)

        user_event = UserEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert not is_assistant_event(user_event)

    def test_is_clear_command(self) -> None:
        """Test /clear command detection."""
        clear_event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content="<command-name>/clear</command-name>\n<command-args></command-args>"
            ),
        )
        assert is_clear_command(clear_event)

        regular_user = UserEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello there"),
        )
        assert not is_clear_command(regular_user)

        assistant = AssistantEvent(
            uuid="3",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert not is_clear_command(assistant)

    def test_is_compact_boundary(self) -> None:
        """Test compaction boundary detection."""
        compact_event = SystemEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="system",
            subtype="compact_boundary",
            compactMetadata=CompactMetadata(trigger="auto", preTokens=155660),
        )
        assert is_compact_boundary(compact_event)

        other_system = SystemEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="system",
            subtype="turn_duration",
        )
        assert not is_compact_boundary(other_system)

    def test_is_compact_summary(self) -> None:
        """Test compaction summary detection."""
        summary_event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            isCompactSummary=True,
            message=UserMessage(content="Summary of previous conversation..."),
        )
        assert is_compact_summary(summary_event)

        regular_user = UserEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert not is_compact_summary(regular_user)

    def test_should_skip_event(self) -> None:
        """Test event skip detection."""
        turn_duration = SystemEvent(
            uuid="4",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="system",
            subtype="turn_duration",
        )
        assert should_skip_event(turn_duration)

        # /clear should be skipped
        clear_event = UserEvent(
            uuid="5",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="<command-name>/clear</command-name>"),
        )
        assert should_skip_event(clear_event)

        # Regular user/assistant should not be skipped
        regular_user = UserEvent(
            uuid="6",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert not should_skip_event(regular_user)

        assistant = AssistantEvent(
            uuid="7",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert not should_skip_event(assistant)

    def test_get_model_name(self) -> None:
        """Test model name extraction."""
        event = AssistantEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(model="claude-opus-4-5-20251101", content=[]),
        )
        assert get_model_name(event) == "claude-opus-4-5-20251101"

        no_model = AssistantEvent(
            uuid="2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert get_model_name(no_model) is None

        user_event = UserEvent(
            uuid="3",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert get_model_name(user_event) is None

    def test_get_timestamp(self) -> None:
        """Test timestamp extraction."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-31T21:46:52.807Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert get_timestamp(event) == "2026-01-31T21:46:52.807Z"


class TestTreeBuilding:
    """Tests for conversation tree building."""

    def test_build_simple_tree(self) -> None:
        """Test building a simple conversation tree."""
        events = [
            _parse(
                {
                    "uuid": "1",
                    "parentUuid": None,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            _parse(
                {
                    "uuid": "2",
                    "parentUuid": "1",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            _parse(
                {
                    "uuid": "3",
                    "parentUuid": "2",
                    "timestamp": "2026-01-01T00:02:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Thanks"},
                }
            ),
        ]

        roots = build_event_tree(events)
        assert len(roots) == 1
        assert roots[0].uuid == "1"
        assert len(roots[0].children) == 1
        assert roots[0].children[0].uuid == "2"
        assert len(roots[0].children[0].children) == 1
        assert roots[0].children[0].children[0].uuid == "3"

    def test_flatten_tree_chronological(self) -> None:
        """Test flattening tree to chronological order."""
        events = [
            _parse(
                {
                    "uuid": "1",
                    "parentUuid": None,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            _parse(
                {
                    "uuid": "2",
                    "parentUuid": "1",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            _parse(
                {
                    "uuid": "3",
                    "parentUuid": "2",
                    "timestamp": "2026-01-01T00:02:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Thanks"},
                }
            ),
        ]

        roots = build_event_tree(events)
        flat = flatten_tree_chronological(roots)

        assert len(flat) == 3
        assert flat[0].uuid == "1"
        assert flat[1].uuid == "2"
        assert flat[2].uuid == "3"

    def test_find_clear_indices(self) -> None:
        """Test finding /clear command indices."""
        events = [
            _parse(
                {
                    "uuid": "1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            _parse(
                {
                    "uuid": "2",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            _parse(
                {
                    "uuid": "3",
                    "timestamp": "2026-01-01T00:02:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "<command-name>/clear</command-name>"},
                }
            ),
            _parse(
                {
                    "uuid": "4",
                    "timestamp": "2026-01-01T00:03:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "New conversation"},
                }
            ),
        ]

        indices = find_clear_indices(events)
        assert indices == [2]

    def test_split_on_clear(self) -> None:
        """Test splitting events on /clear boundaries."""
        events = [
            _parse(
                {
                    "uuid": "1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            _parse(
                {
                    "uuid": "2",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            _parse(
                {
                    "uuid": "3",
                    "timestamp": "2026-01-01T00:02:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "<command-name>/clear</command-name>"},
                }
            ),
            _parse(
                {
                    "uuid": "4",
                    "timestamp": "2026-01-01T00:03:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "New conversation"},
                }
            ),
            _parse(
                {
                    "uuid": "5",
                    "timestamp": "2026-01-01T00:04:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
        ]

        segments = split_on_clear(events)
        assert len(segments) == 2
        assert len(segments[0]) == 2  # First conversation
        assert len(segments[1]) == 2  # Second conversation

    def test_split_on_clear_no_splits(self) -> None:
        """Test that no splits returns single segment."""
        events = [
            _parse(
                {
                    "uuid": "1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            _parse(
                {
                    "uuid": "2",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
        ]

        segments = split_on_clear(events)
        assert len(segments) == 1
        assert segments[0] == events


class TestMessageExtraction:
    """Tests for message extraction."""

    def test_extract_user_message(self) -> None:
        """Test extracting user messages."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello, how are you?"),
        )

        msg = extract_user_message(event)
        assert msg is not None
        assert msg.role == "user"
        assert msg.content == "Hello, how are you?"

    def test_extract_user_message_skips_commands(self) -> None:
        """Test that command messages are skipped."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="<command-name>/clear</command-name>"),
        )

        msg = extract_user_message(event)
        assert msg is None

    def test_extract_assistant_content(self) -> None:
        """Test extracting assistant content blocks."""
        content: list[dict[str, Any]] = [
            {"type": "text", "text": "Here's my response."},
            {
                "type": "thinking",
                "thinking": "Let me think about this...",
                "signature": "test_sig",
            },
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "Read",
                "input": {"file_path": "/test.py"},
            },
        ]

        extracted_content, tool_calls = extract_assistant_content(content)

        assert len(extracted_content) == 2  # text and thinking
        assert len(tool_calls) == 1

        # Check tool call
        assert tool_calls[0].id == "tool_1"
        assert tool_calls[0].function == "Read"
        assert tool_calls[0].arguments == {"file_path": "/test.py"}


class TestUsageExtraction:
    """Tests for token usage extraction."""

    def test_extract_usage(self) -> None:
        """Test extracting token usage."""
        event = AssistantEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(
                content=[],
                usage=Usage(
                    input_tokens=1000,
                    output_tokens=500,
                    cache_creation_input_tokens=200,
                    cache_read_input_tokens=100,
                ),
            ),
        )

        usage = extract_usage(event)
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500
        assert usage["cache_creation_input_tokens"] == 200
        assert usage["cache_read_input_tokens"] == 100

    def test_sum_tokens(self) -> None:
        """Test summing tokens across events."""
        events = [
            AssistantEvent(
                uuid="1",
                timestamp="2026-01-01T00:00:00Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    content=[], usage=Usage(input_tokens=100, output_tokens=50)
                ),
            ),
            AssistantEvent(
                uuid="2",
                timestamp="2026-01-01T00:01:00Z",
                sessionId="test",
                type="assistant",
                message=AssistantMessage(
                    content=[], usage=Usage(input_tokens=200, output_tokens=100)
                ),
            ),
            UserEvent(
                uuid="3",
                timestamp="2026-01-01T00:02:00Z",
                sessionId="test",
                type="user",
                message=UserMessage(content="Hello"),
            ),  # No usage
        ]

        total = sum_tokens(events)
        assert total == 450  # 100+50+200+100


class TestSourceType:
    """Tests for source type constant."""

    def test_source_type(self) -> None:
        """Test source type is set correctly."""
        assert CLAUDE_CODE_SOURCE_TYPE == "claude_code"


class TestCommandDetection:
    """Tests for _get_command_name() and is_skill_command()."""

    def test_builtin_command(self) -> None:
        """User event with /clear → _get_command_name returns 'clear', is_skill_command returns None."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content="<command-name>/clear</command-name>\n<command-args></command-args>"
            ),
        )
        assert _get_command_name(event) == "clear"
        assert is_skill_command(event) is None

    def test_skill_command(self) -> None:
        """User event with skill command → returns skill name."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content="<command-name>/feature-dev:feature-dev</command-name>"
            ),
        )
        assert _get_command_name(event) == "feature-dev:feature-dev"
        assert is_skill_command(event) == "feature-dev:feature-dev"

    def test_plain_text_no_command(self) -> None:
        """User event with plain text → both return None."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello there"),
        )
        assert _get_command_name(event) is None
        assert is_skill_command(event) is None

    def test_non_user_event(self) -> None:
        """Non-UserEvent → both return None."""
        event = AssistantEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert _get_command_name(event) is None
        assert is_skill_command(event) is None

    def test_list_content_no_command(self) -> None:
        """User event with list content → returns None (only string content has command tags)."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content=[{"type": "text", "text": "Hello"}]),
        )
        assert _get_command_name(event) is None
        assert is_skill_command(event) is None


class TestTaskAgentInfo:
    """Tests for get_task_agent_info()."""

    def test_task_tool_use(self) -> None:
        """ContentToolUse with name='Task' and valid input → returns TaskAgentInfo."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_abc",
            name="Task",
            input={
                "subagent_type": "Explore",
                "description": "Find config files",
                "prompt": "Search for all config files in the repo",
            },
        )
        info = get_task_agent_info(block)
        assert info is not None
        assert info.subagent_type == "Explore"
        assert info.description == "Find config files"
        assert info.prompt == "Search for all config files in the repo"
        assert info.tool_use_id == "tool_abc"

    def test_non_task_tool(self) -> None:
        """ContentToolUse with name='Bash' → returns None."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_xyz",
            name="Bash",
            input={"command": "ls"},
        )
        assert get_task_agent_info(block) is None

    def test_missing_optional_fields(self) -> None:
        """Task tool_use with missing optional fields → returns TaskAgentInfo with defaults."""
        block = ContentToolUse(
            type="tool_use",
            id="tool_def",
            name="Task",
            input={},
        )
        info = get_task_agent_info(block)
        assert info is not None
        assert info.subagent_type == "unknown"
        assert info.description == ""
        assert info.prompt == ""
        assert info.tool_use_id == "tool_def"


class TestCompactionExtraction:
    """Tests for extract_compaction_info()."""

    def test_compact_boundary_with_metadata(self) -> None:
        """SystemEvent with compact_boundary and compactMetadata → returns dict."""
        event = SystemEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="system",
            subtype="compact_boundary",
            content="Conversation compacted",
            compactMetadata=CompactMetadata(trigger="auto", preTokens=155660),
        )
        result = extract_compaction_info(event)
        assert result is not None
        assert result["trigger"] == "auto"
        assert result["preTokens"] == 155660
        assert result["content"] == "Conversation compacted"

    def test_compact_boundary_no_metadata(self) -> None:
        """SystemEvent with compact_boundary but no metadata → returns dict with defaults."""
        event = SystemEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="system",
            subtype="compact_boundary",
        )
        result = extract_compaction_info(event)
        assert result is not None
        assert result["trigger"] == "auto"
        assert result["content"] == "Conversation compacted"
        assert "preTokens" not in result

    def test_different_subtype(self) -> None:
        """SystemEvent with different subtype → returns None."""
        event = SystemEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="system",
            subtype="turn_duration",
        )
        assert extract_compaction_info(event) is None

    def test_non_system_event(self) -> None:
        """Non-SystemEvent → returns None."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert extract_compaction_info(event) is None


class TestToolResultExtraction:
    """Tests for extract_tool_result_messages()."""

    def test_tool_result_blocks(self) -> None:
        """User event with tool_result blocks → returns ChatMessageTool list."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_1",
                        "content": "file contents here",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_2",
                        "content": "another result",
                    },
                ]
            ),
        )
        results = extract_tool_result_messages(event)
        assert len(results) == 2
        assert results[0].tool_call_id == "tool_1"
        assert results[0].content == "file contents here"
        assert results[1].tool_call_id == "tool_2"

    def test_mixed_content_extracts_only_tool_results(self) -> None:
        """User event with mixed text + tool_result → extracts only tool results."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content=[
                    {"type": "text", "text": "some context"},
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_1",
                        "content": "result text",
                    },
                ]
            ),
        )
        results = extract_tool_result_messages(event)
        assert len(results) == 1
        assert results[0].tool_call_id == "tool_1"

    def test_string_content_returns_empty(self) -> None:
        """User event with string content → returns empty list."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        assert extract_tool_result_messages(event) == []

    def test_list_content_in_tool_result(self) -> None:
        """Tool result with list content (nested text blocks) → content is joined text."""
        event = UserEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_1",
                        "content": [
                            {"type": "text", "text": "line one"},
                            {"type": "text", "text": "line two"},
                        ],
                    }
                ]
            ),
        )
        results = extract_tool_result_messages(event)
        assert len(results) == 1
        assert results[0].content == "line one\nline two"

    def test_non_user_event_returns_empty(self) -> None:
        """Non-UserEvent → returns empty list."""
        event = AssistantEvent(
            uuid="1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="assistant",
            message=AssistantMessage(content=[]),
        )
        assert extract_tool_result_messages(event) == []


def _make_assistant(
    uuid: str,
    message_id: str | None,
    content: list[dict[str, Any]],
    *,
    usage: Usage | None = None,
    stop_reason: str | None = None,
) -> AssistantEvent:
    """Helper to create an AssistantEvent for consolidation tests."""
    return AssistantEvent(
        uuid=uuid,
        timestamp="2026-01-01T00:00:00Z",
        sessionId="test",
        type="assistant",
        message=AssistantMessage(
            id=message_id,
            content=content,
            usage=usage,
            stop_reason=stop_reason,
        ),
    )


class TestConsolidateAssistantEvents:
    """Tests for consolidate_assistant_events()."""

    def test_merges_fragments(self) -> None:
        """3 assistant events with same message.id → 1 event with combined content."""
        events: list[BaseEvent] = [
            _make_assistant(
                "u1",
                "msg_123",
                [{"type": "thinking", "thinking": "hmm"}],
            ),
            _make_assistant(
                "u2",
                "msg_123",
                [{"type": "text", "text": "Hello"}],
            ),
            _make_assistant(
                "u3",
                "msg_123",
                [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}],
                usage=Usage(input_tokens=100, output_tokens=50),
                stop_reason="tool_use",
            ),
        ]

        result = consolidate_assistant_events(events)
        assert len(result) == 1
        merged = result[0]
        assert isinstance(merged, AssistantEvent)
        assert len(merged.message.content) == 3
        assert merged.message.content[0]["type"] == "thinking"
        assert merged.message.content[1]["type"] == "text"
        assert merged.message.content[2]["type"] == "tool_use"
        assert merged.message.usage is not None
        assert merged.message.usage.input_tokens == 100
        assert merged.message.stop_reason == "tool_use"

    def test_preserves_non_assistant(self) -> None:
        """User events pass through unchanged."""
        user = UserEvent(
            uuid="u1",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Hello"),
        )
        events: list[BaseEvent] = [user]
        result = consolidate_assistant_events(events)
        assert len(result) == 1
        assert result[0] is user

    def test_no_message_id(self) -> None:
        """Assistant events with id=None are not merged."""
        events: list[BaseEvent] = [
            _make_assistant("u1", None, [{"type": "text", "text": "A"}]),
            _make_assistant("u2", None, [{"type": "text", "text": "B"}]),
        ]
        result = consolidate_assistant_events(events)
        assert len(result) == 2

    def test_different_message_ids(self) -> None:
        """Different message.id values stay separate."""
        events: list[BaseEvent] = [
            _make_assistant("u1", "msg_1", [{"type": "text", "text": "A"}]),
            _make_assistant("u2", "msg_2", [{"type": "text", "text": "B"}]),
        ]
        result = consolidate_assistant_events(events)
        assert len(result) == 2
        assert isinstance(result[0], AssistantEvent)
        assert result[0].message.content == [{"type": "text", "text": "A"}]
        assert isinstance(result[1], AssistantEvent)
        assert result[1].message.content == [{"type": "text", "text": "B"}]

    def test_interleaved(self) -> None:
        """Assistant-user-assistant pattern flushes correctly."""
        user = UserEvent(
            uuid="u2",
            timestamp="2026-01-01T00:00:00Z",
            sessionId="test",
            type="user",
            message=UserMessage(content="Reply"),
        )
        events: list[BaseEvent] = [
            _make_assistant("u1", "msg_1", [{"type": "text", "text": "First"}]),
            user,
            _make_assistant("u3", "msg_2", [{"type": "text", "text": "Second"}]),
        ]
        result = consolidate_assistant_events(events)
        assert len(result) == 3
        assert isinstance(result[0], AssistantEvent)
        assert result[0].message.id == "msg_1"
        assert isinstance(result[1], UserEvent)
        assert isinstance(result[2], AssistantEvent)
        assert result[2].message.id == "msg_2"

    def test_empty_input(self) -> None:
        """Empty list returns empty list."""
        assert consolidate_assistant_events([]) == []

    def test_single_assistant_no_merge_needed(self) -> None:
        """Single assistant event passes through without copying."""
        events: list[BaseEvent] = [
            _make_assistant("u1", "msg_1", [{"type": "text", "text": "Solo"}]),
        ]
        result = consolidate_assistant_events(events)
        assert len(result) == 1
        assert result[0] is events[0]
