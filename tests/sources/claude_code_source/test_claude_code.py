"""Tests for Claude Code import source."""

from typing import Any

from inspect_scout.sources._claude_code.client import (
    CLAUDE_CODE_SOURCE_TYPE,
    decode_project_path,
    encode_project_path,
)
from inspect_scout.sources._claude_code.detection import (
    get_event_type,
    get_model_name,
    get_timestamp,
    is_assistant_event,
    is_clear_command,
    is_compact_boundary,
    is_compact_summary,
    is_user_event,
    should_skip_event,
)
from inspect_scout.sources._claude_code.extraction import (
    extract_assistant_content,
    extract_usage,
    extract_user_message,
    sum_tokens,
)
from inspect_scout.sources._claude_code.models import (
    AssistantEvent,
    AssistantMessage,
    CompactMetadata,
    SystemEvent,
    Usage,
    UserEvent,
    UserMessage,
    parse_event,
)
from inspect_scout.sources._claude_code.tree import (
    build_event_tree,
    find_clear_indices,
    flatten_tree_chronological,
    split_on_clear,
)


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
            parse_event(
                {
                    "uuid": "1",
                    "parentUuid": None,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            parse_event(
                {
                    "uuid": "2",
                    "parentUuid": "1",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            parse_event(
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
            parse_event(
                {
                    "uuid": "1",
                    "parentUuid": None,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            parse_event(
                {
                    "uuid": "2",
                    "parentUuid": "1",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            parse_event(
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
            parse_event(
                {
                    "uuid": "1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            parse_event(
                {
                    "uuid": "2",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            parse_event(
                {
                    "uuid": "3",
                    "timestamp": "2026-01-01T00:02:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "<command-name>/clear</command-name>"},
                }
            ),
            parse_event(
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
            parse_event(
                {
                    "uuid": "1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            parse_event(
                {
                    "uuid": "2",
                    "timestamp": "2026-01-01T00:01:00Z",
                    "sessionId": "test",
                    "type": "assistant",
                    "message": {"content": []},
                }
            ),
            parse_event(
                {
                    "uuid": "3",
                    "timestamp": "2026-01-01T00:02:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "<command-name>/clear</command-name>"},
                }
            ),
            parse_event(
                {
                    "uuid": "4",
                    "timestamp": "2026-01-01T00:03:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "New conversation"},
                }
            ),
            parse_event(
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
            parse_event(
                {
                    "uuid": "1",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "sessionId": "test",
                    "type": "user",
                    "message": {"content": "Hello"},
                }
            ),
            parse_event(
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
