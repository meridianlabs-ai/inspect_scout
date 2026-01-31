"""Tests for Claude Code import source."""

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
        assert (
            decode_project_path("-Users-jjallaire-dev-project")
            == "/Users/jjallaire/dev/project"
        )
        assert decode_project_path("-Users-foo-bar") == "/Users/foo/bar"

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
        be distinguished from path separators. This test uses a path without
        hyphens in directory names.
        """
        original = "/Users/jjallaire/dev/project"
        encoded = encode_project_path(original)
        decoded = decode_project_path(encoded)
        assert decoded == original


class TestEventDetection:
    """Tests for event type detection."""

    def test_get_event_type(self) -> None:
        """Test getting event type."""
        assert get_event_type({"type": "user"}) == "user"
        assert get_event_type({"type": "assistant"}) == "assistant"
        assert get_event_type({"type": "progress"}) == "progress"
        assert get_event_type({}) == "unknown"

    def test_is_user_event(self) -> None:
        """Test user event detection."""
        assert is_user_event({"type": "user"})
        assert not is_user_event({"type": "assistant"})

    def test_is_assistant_event(self) -> None:
        """Test assistant event detection."""
        assert is_assistant_event({"type": "assistant"})
        assert not is_assistant_event({"type": "user"})

    def test_is_clear_command(self) -> None:
        """Test /clear command detection."""
        clear_event = {
            "type": "user",
            "message": {
                "role": "user",
                "content": "<command-name>/clear</command-name>\n<command-args></command-args>",
            },
        }
        assert is_clear_command(clear_event)

        regular_user = {
            "type": "user",
            "message": {"role": "user", "content": "Hello there"},
        }
        assert not is_clear_command(regular_user)

        assistant = {"type": "assistant"}
        assert not is_clear_command(assistant)

    def test_is_compact_boundary(self) -> None:
        """Test compaction boundary detection."""
        compact_event = {
            "type": "system",
            "subtype": "compact_boundary",
            "compactMetadata": {"trigger": "auto", "preTokens": 155660},
        }
        assert is_compact_boundary(compact_event)

        other_system = {"type": "system", "subtype": "turn_duration"}
        assert not is_compact_boundary(other_system)

    def test_is_compact_summary(self) -> None:
        """Test compaction summary detection."""
        summary_event = {
            "type": "user",
            "isCompactSummary": True,
            "message": {
                "role": "user",
                "content": "Summary of previous conversation...",
            },
        }
        assert is_compact_summary(summary_event)

        regular_user = {"type": "user", "message": {"role": "user", "content": "Hello"}}
        assert not is_compact_summary(regular_user)

    def test_should_skip_event(self) -> None:
        """Test event skip detection."""
        assert should_skip_event({"type": "progress"})
        assert should_skip_event({"type": "queue-operation"})
        assert should_skip_event({"type": "file-history-snapshot"})
        assert should_skip_event({"type": "system", "subtype": "turn_duration"})

        # /clear should be skipped
        clear_event = {
            "type": "user",
            "message": {"content": "<command-name>/clear</command-name>"},
        }
        assert should_skip_event(clear_event)

        # Regular user/assistant should not be skipped
        assert not should_skip_event({"type": "user", "message": {"content": "Hello"}})
        assert not should_skip_event({"type": "assistant"})

    def test_get_model_name(self) -> None:
        """Test model name extraction."""
        event = {
            "type": "assistant",
            "message": {"model": "claude-opus-4-5-20251101"},
        }
        assert get_model_name(event) == "claude-opus-4-5-20251101"

        no_model = {"type": "assistant", "message": {}}
        assert get_model_name(no_model) is None

        user_event = {"type": "user"}
        assert get_model_name(user_event) is None

    def test_get_timestamp(self) -> None:
        """Test timestamp extraction."""
        event = {"timestamp": "2026-01-31T21:46:52.807Z"}
        assert get_timestamp(event) == "2026-01-31T21:46:52.807Z"

        no_ts = {}
        assert get_timestamp(no_ts) is None


class TestTreeBuilding:
    """Tests for conversation tree building."""

    def test_build_simple_tree(self) -> None:
        """Test building a simple conversation tree."""
        events = [
            {"uuid": "1", "parentUuid": None, "timestamp": "2026-01-01T00:00:00Z"},
            {"uuid": "2", "parentUuid": "1", "timestamp": "2026-01-01T00:01:00Z"},
            {"uuid": "3", "parentUuid": "2", "timestamp": "2026-01-01T00:02:00Z"},
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
            {"uuid": "1", "parentUuid": None, "timestamp": "2026-01-01T00:00:00Z"},
            {"uuid": "2", "parentUuid": "1", "timestamp": "2026-01-01T00:01:00Z"},
            {"uuid": "3", "parentUuid": "2", "timestamp": "2026-01-01T00:02:00Z"},
        ]

        roots = build_event_tree(events)
        flat = flatten_tree_chronological(roots)

        assert len(flat) == 3
        assert flat[0]["uuid"] == "1"
        assert flat[1]["uuid"] == "2"
        assert flat[2]["uuid"] == "3"

    def test_find_clear_indices(self) -> None:
        """Test finding /clear command indices."""
        events = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant"},
            {
                "type": "user",
                "message": {"content": "<command-name>/clear</command-name>"},
            },
            {"type": "user", "message": {"content": "New conversation"}},
        ]

        indices = find_clear_indices(events)
        assert indices == [2]

    def test_split_on_clear(self) -> None:
        """Test splitting events on /clear boundaries."""
        events = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant"},
            {
                "type": "user",
                "message": {"content": "<command-name>/clear</command-name>"},
            },
            {"type": "user", "message": {"content": "New conversation"}},
            {"type": "assistant"},
        ]

        segments = split_on_clear(events)
        assert len(segments) == 2
        assert len(segments[0]) == 2  # First conversation
        assert len(segments[1]) == 2  # Second conversation

    def test_split_on_clear_no_splits(self) -> None:
        """Test that no splits returns single segment."""
        events = [
            {"type": "user", "message": {"content": "Hello"}},
            {"type": "assistant"},
        ]

        segments = split_on_clear(events)
        assert len(segments) == 1
        assert segments[0] == events


class TestMessageExtraction:
    """Tests for message extraction."""

    def test_extract_user_message(self) -> None:
        """Test extracting user messages."""
        event = {
            "type": "user",
            "message": {"role": "user", "content": "Hello, how are you?"},
        }

        msg = extract_user_message(event)
        assert msg is not None
        assert msg.role == "user"
        assert msg.content == "Hello, how are you?"

    def test_extract_user_message_skips_commands(self) -> None:
        """Test that command messages are skipped."""
        event = {
            "type": "user",
            "message": {"content": "<command-name>/clear</command-name>"},
        }

        msg = extract_user_message(event)
        assert msg is None

    def test_extract_assistant_content(self) -> None:
        """Test extracting assistant content blocks."""
        content = [
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
        event = {
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cache_creation_input_tokens": 200,
                    "cache_read_input_tokens": 100,
                }
            },
        }

        usage = extract_usage(event)
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500
        assert usage["cache_creation_input_tokens"] == 200
        assert usage["cache_read_input_tokens"] == 100

    def test_sum_tokens(self) -> None:
        """Test summing tokens across events."""
        events = [
            {
                "type": "assistant",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}},
            },
            {
                "type": "assistant",
                "message": {"usage": {"input_tokens": 200, "output_tokens": 100}},
            },
            {"type": "user"},  # No usage
        ]

        total = sum_tokens(events)
        assert total == 450  # 100+50+200+100


class TestSourceType:
    """Tests for source type constant."""

    def test_source_type(self) -> None:
        """Test source type is set correctly."""
        assert CLAUDE_CODE_SOURCE_TYPE == "claude_code"
