"""Tests for grep_scanner."""

from datetime import datetime
from typing import Any, Literal

import pytest
from inspect_ai.event import Event, ToolEvent
from inspect_ai.event._approval import ApprovalEvent
from inspect_ai.event._error import ErrorEvent
from inspect_ai.event._info import InfoEvent
from inspect_ai.event._logger import LoggerEvent, LoggingMessage
from inspect_ai.event._model import ModelEvent
from inspect_ai.log import EvalError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
    ModelOutput,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool import ToolCall
from inspect_scout import grep_scanner
from inspect_scout._grep_scanner import PatternError
from inspect_scout._scanner.result import Result
from inspect_scout._transcript.types import Transcript


def make_transcript(
    messages: list[tuple[str, str]], transcript_id: str = "test-123"
) -> Transcript:
    """Helper to create test transcripts.

    Args:
        messages: List of (role, content) tuples
        transcript_id: ID for the transcript
    """
    chat_messages: list[ChatMessage] = []
    for i, (role, content) in enumerate(messages):
        msg_id = f"msg-{i}"
        if role == "user":
            chat_messages.append(ChatMessageUser(content=content, id=msg_id))
        elif role == "assistant":
            chat_messages.append(ChatMessageAssistant(content=content, id=msg_id))
    return Transcript(
        transcript_id=transcript_id,
        source_id="test-source",
        source_type="test",
        source_uri="test://uri",
        messages=chat_messages,
    )


class TestSinglePattern:
    """Tests for single pattern matching."""

    @pytest.mark.asyncio
    async def test_simple_match(self) -> None:
        """Simple string pattern finds matches."""
        transcript = make_transcript(
            [
                ("user", "Hello world"),
                ("assistant", "There was an error processing your request"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1
        assert result.explanation is not None
        assert "**error**" in result.explanation
        assert len(result.references) == 1

    @pytest.mark.asyncio
    async def test_multiple_matches_same_message(self) -> None:
        """Multiple matches in same message are all counted."""
        transcript = make_transcript(
            [
                ("assistant", "error: first error occurred, then another error"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 3  # "error" appears 3 times

    @pytest.mark.asyncio
    async def test_no_matches(self) -> None:
        """No matches returns value=0."""
        transcript = make_transcript(
            [
                ("user", "Hello world"),
                ("assistant", "Everything is fine"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 0
        assert result.explanation is None
        assert len(result.references) == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_default(self) -> None:
        """Case insensitive matching is default."""
        transcript = make_transcript(
            [
                ("assistant", "ERROR occurred"),
                ("assistant", "error occurred"),
                ("assistant", "Error occurred"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 3

    @pytest.mark.asyncio
    async def test_case_sensitive(self) -> None:
        """Case sensitive matching when ignore_case=False."""
        transcript = make_transcript(
            [
                ("assistant", "ERROR occurred"),
                ("assistant", "error occurred"),
                ("assistant", "Error occurred"),
            ]
        )
        scanner = grep_scanner("error", ignore_case=False)
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1  # Only lowercase "error"


class TestMultiplePatterns:
    """Tests for multiple pattern matching (list input)."""

    @pytest.mark.asyncio
    async def test_multiple_patterns_or_logic(self) -> None:
        """Multiple patterns match with OR logic."""
        transcript = make_transcript(
            [
                ("assistant", "There was an error"),
                ("assistant", "The operation failed"),
                ("assistant", "Everything is fine"),
            ]
        )
        scanner = grep_scanner(["error", "failed"])
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 2  # "error" and "failed"

    @pytest.mark.asyncio
    async def test_multiple_patterns_same_message(self) -> None:
        """Multiple different patterns in same message are all counted."""
        transcript = make_transcript(
            [
                ("assistant", "error occurred and operation failed"),
            ]
        )
        scanner = grep_scanner(["error", "failed"])
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 2


class TestLabeledPatterns:
    """Tests for labeled patterns (dict input)."""

    @pytest.mark.asyncio
    async def test_labeled_patterns_basic(self) -> None:
        """Labeled patterns return multiple results."""
        transcript = make_transcript(
            [
                ("assistant", "error occurred"),
                ("assistant", "warning: check this"),
            ]
        )
        scanner = grep_scanner(
            {
                "errors": "error",
                "warnings": "warning",
            }
        )
        results = await scanner(transcript)

        assert isinstance(results, list)
        assert len(results) == 2

        errors_result = next(r for r in results if r.label == "errors")
        warnings_result = next(r for r in results if r.label == "warnings")

        assert errors_result.value == 1
        assert warnings_result.value == 1

    @pytest.mark.asyncio
    async def test_labeled_patterns_with_lists(self) -> None:
        """Labeled patterns can have list values."""
        transcript = make_transcript(
            [
                ("assistant", "error occurred"),
                ("assistant", "operation failed"),
                ("assistant", "exception raised"),
                ("assistant", "warning issued"),
            ]
        )
        scanner = grep_scanner(
            {
                "errors": ["error", "failed", "exception"],
                "warnings": ["warning", "caution"],
            }
        )
        results = await scanner(transcript)

        assert isinstance(results, list)
        errors_result = next(r for r in results if r.label == "errors")
        warnings_result = next(r for r in results if r.label == "warnings")

        assert errors_result.value == 3  # error, failed, exception
        assert warnings_result.value == 1  # warning

    @pytest.mark.asyncio
    async def test_labeled_patterns_zero_matches(self) -> None:
        """Labels with no matches still return Result with value=0."""
        transcript = make_transcript(
            [
                ("assistant", "everything is fine"),
            ]
        )
        scanner = grep_scanner(
            {
                "errors": "error",
                "warnings": "warning",
            }
        )
        results = await scanner(transcript)

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(r.value == 0 for r in results)


class TestRegexMode:
    """Tests for regex pattern matching."""

    @pytest.mark.asyncio
    async def test_regex_pattern(self) -> None:
        """Regex patterns match correctly."""
        transcript = make_transcript(
            [
                ("assistant", "Visit https://example.com for more info"),
                ("assistant", "Or check http://test.org"),
            ]
        )
        scanner = grep_scanner(r"https?://\S+", regex=True)
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 2

    @pytest.mark.asyncio
    async def test_regex_special_chars_escaped_when_not_regex(self) -> None:
        """Special regex chars are escaped when regex=False."""
        transcript = make_transcript(
            [
                ("assistant", "The file is at /path/to/file.txt"),
                ("assistant", "Use regex pattern .*"),
            ]
        )
        # This should match literal ".*" not regex "any char"
        scanner = grep_scanner(".*", regex=False)
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1  # Only the literal ".*"


class TestWordBoundary:
    """Tests for word boundary matching."""

    @pytest.mark.asyncio
    async def test_word_boundary_excludes_partial(self) -> None:
        """Word boundary excludes partial matches."""
        transcript = make_transcript(
            [
                ("assistant", "error occurred"),
                ("assistant", "errorCode is 500"),  # "error" is part of "errorCode"
            ]
        )
        scanner = grep_scanner("error", word_boundary=True)
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1  # Only standalone "error"

    @pytest.mark.asyncio
    async def test_word_boundary_with_regex(self) -> None:
        """Word boundary works with regex patterns."""
        transcript = make_transcript(
            [
                ("assistant", "the cat sat"),
                ("assistant", "category is pets"),  # "cat" is part of "category"
            ]
        )
        scanner = grep_scanner("cat", regex=True, word_boundary=True)
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1


class TestContextExtraction:
    """Tests for context extraction in explanations."""

    @pytest.mark.asyncio
    async def test_context_shows_surrounding_text(self) -> None:
        """Explanation shows text around matches."""
        transcript = make_transcript(
            [
                ("assistant", "Before the error occurred after"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.explanation is not None
        assert "Before" in result.explanation
        assert "**error**" in result.explanation
        assert "after" in result.explanation

    @pytest.mark.asyncio
    async def test_context_truncated_for_long_text(self) -> None:
        """Long context is truncated with ellipsis."""
        long_before = "x" * 100
        long_after = "y" * 100
        transcript = make_transcript(
            [
                ("assistant", f"{long_before}error{long_after}"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.explanation is not None
        assert "..." in result.explanation


class TestReferences:
    """Tests for message references."""

    @pytest.mark.asyncio
    async def test_references_point_to_correct_messages(self) -> None:
        """References have correct message IDs."""
        transcript = make_transcript(
            [
                ("user", "no match here"),
                ("assistant", "error occurred"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert len(result.references) == 1
        assert result.references[0].type == "message"
        assert result.references[0].id == "msg-1"  # Second message (0-indexed)
        assert result.references[0].cite == "[M2]"  # 1-indexed citation

    @pytest.mark.asyncio
    async def test_references_unique_per_message(self) -> None:
        """Multiple matches in same message yield single reference."""
        transcript = make_transcript(
            [
                ("assistant", "error error error"),
            ]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 3  # 3 matches
        assert len(result.references) == 1  # But only 1 message reference


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_transcript(self) -> None:
        """Empty transcript returns 0 matches."""
        transcript = make_transcript([])
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 0

    @pytest.mark.asyncio
    async def test_empty_pattern(self) -> None:
        """Empty pattern matches everywhere (regex behavior)."""
        transcript = make_transcript(
            [
                ("assistant", "hello"),
            ]
        )
        scanner = grep_scanner("")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        # Empty pattern matches at every position
        assert isinstance(result.value, int) and result.value > 0

    @pytest.mark.asyncio
    async def test_unicode_patterns(self) -> None:
        """Unicode patterns work correctly."""
        transcript = make_transcript(
            [
                ("assistant", "The café serves great espresso"),
            ]
        )
        scanner = grep_scanner("café")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1


def make_transcript_with_events(
    events: list[Event], transcript_id: str = "test-123"
) -> Transcript:
    """Helper to create test transcripts with events only."""
    return Transcript(
        transcript_id=transcript_id,
        source_id="test-source",
        source_type="test",
        source_uri="test://uri",
        messages=[],
        events=events,
    )


def make_tool_event(function: str, result: str, uuid: str) -> ToolEvent:
    """Helper to create ToolEvent for testing."""
    return ToolEvent(
        event="tool",
        timestamp=datetime.now(),
        id="tool-call-id",
        function=function,
        arguments={"arg": "value"},
        result=result,
        uuid=uuid,
    )


def make_error_event(message: str, uuid: str) -> ErrorEvent:
    """Helper to create ErrorEvent for testing."""
    return ErrorEvent(
        event="error",
        timestamp=datetime.now(),
        error=EvalError(message=message, traceback="", traceback_ansi=""),
        uuid=uuid,
    )


def make_info_event(data: Any, uuid: str) -> InfoEvent:
    """Helper to create InfoEvent for testing."""
    return InfoEvent(
        event="info",
        timestamp=datetime.now(),
        data=data,
        uuid=uuid,
    )


def make_logger_event(
    message: str,
    level: Literal[
        "debug", "trace", "http", "sandbox", "info", "warning", "error", "critical"
    ],
    uuid: str,
) -> LoggerEvent:
    """Helper to create LoggerEvent for testing."""
    return LoggerEvent(
        event="logger",
        timestamp=datetime.now(),
        message=LoggingMessage(message=message, level=level, created=0.0),
        uuid=uuid,
    )


class TestEventMatching:
    """Tests for event matching."""

    @pytest.mark.asyncio
    async def test_tool_event_match(self) -> None:
        """Pattern matches tool event content."""
        transcript = make_transcript_with_events(
            [make_tool_event("search_files", "Found error in file.py", "e1")]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1
        assert result.explanation is not None
        assert "**error**" in result.explanation
        assert len(result.references) == 1
        assert result.references[0].type == "event"
        assert result.references[0].cite == "[E1]"

    @pytest.mark.asyncio
    async def test_error_event_match(self) -> None:
        """Pattern matches error event message."""
        transcript = make_transcript_with_events(
            [make_error_event("Connection timeout occurred", "e1")]
        )
        scanner = grep_scanner("timeout")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1
        assert result.references[0].type == "event"

    @pytest.mark.asyncio
    async def test_info_event_string_match(self) -> None:
        """Pattern matches info event string data."""
        transcript = make_transcript_with_events(
            [make_info_event("Processing completed successfully", "e1")]
        )
        scanner = grep_scanner("successfully")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1

    @pytest.mark.asyncio
    async def test_info_event_dict_match(self) -> None:
        """Pattern matches info event dict data (JSON dumped)."""
        transcript = make_transcript_with_events(
            [make_info_event({"status": "error", "code": "500"}, "e1")]
        )
        scanner = grep_scanner("500")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1

    @pytest.mark.asyncio
    async def test_logger_event_match(self) -> None:
        """Pattern matches logger event message."""
        transcript = make_transcript_with_events(
            [make_logger_event("Warning: memory usage high", "warning", "e1")]
        )
        scanner = grep_scanner("memory")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1

    @pytest.mark.asyncio
    async def test_multiple_event_matches(self) -> None:
        """Multiple events with matches are all counted."""
        transcript = make_transcript_with_events(
            [
                make_tool_event("fn1", "timeout in step 1", "e1"),
                make_tool_event("fn2", "success", "e2"),
                make_error_event("timeout occurred", "e3"),
            ]
        )
        scanner = grep_scanner("timeout")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 2  # "timeout" in tool result and error message
        assert len(result.references) == 2

    @pytest.mark.asyncio
    async def test_event_references_unique_per_event(self) -> None:
        """Multiple matches in same event yield single reference."""
        transcript = make_transcript_with_events(
            [make_tool_event("fn", "error error error", "e1")]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 3  # 3 matches
        assert len(result.references) == 1  # But only 1 event reference


class TestMixedMessagesAndEvents:
    """Tests for searching both messages and events."""

    @pytest.mark.asyncio
    async def test_mixed_transcript(self) -> None:
        """Pattern matches in both messages and events."""
        messages: list[ChatMessage] = [
            ChatMessageAssistant(content="Found an error in the code", id="m1"),
        ]
        events: list[Event] = [
            make_tool_event("analyze", "error detected", "e1"),
        ]
        transcript = Transcript(
            transcript_id="test-123",
            source_id="test-source",
            source_type="test",
            source_uri="test://uri",
            messages=messages,
            events=events,
        )

        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 2  # One in message, one in event

        # Check we have both message and event references
        ref_types = {r.type for r in result.references}
        assert ref_types == {"message", "event"}

    @pytest.mark.asyncio
    async def test_mixed_labeled_patterns(self) -> None:
        """Labeled patterns work with mixed messages and events."""
        messages: list[ChatMessage] = [
            ChatMessageAssistant(content="Operation failed", id="m1"),
        ]
        events: list[Event] = [
            make_error_event("connection lost", "e1"),
        ]
        transcript = Transcript(
            transcript_id="test-123",
            source_id="test-source",
            source_type="test",
            source_uri="test://uri",
            messages=messages,
            events=events,
        )

        scanner = grep_scanner(
            {
                "failures": "failed",
                "connections": "connection",
            }
        )
        results = await scanner(transcript)

        assert isinstance(results, list)
        failures = next(r for r in results if r.label == "failures")
        connections = next(r for r in results if r.label == "connections")

        assert failures.value == 1  # "failed" in message
        assert connections.value == 1  # "connection" in event


def make_model_event(completion: str, uuid: str) -> ModelEvent:
    """Helper to create ModelEvent for testing."""
    return ModelEvent(
        event="model",
        timestamp=datetime.now(),
        model="gpt-4",
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(model="gpt-4", choices=[], completion=completion),
        uuid=uuid,
    )


def make_approval_event(
    message: str,
    function: str,
    decision: Literal["approve", "modify", "reject", "escalate", "terminate"],
    uuid: str,
) -> ApprovalEvent:
    """Helper to create ApprovalEvent for testing."""
    return ApprovalEvent(
        event="approval",
        timestamp=datetime.now(),
        message=message,
        call=ToolCall(id="call-1", function=function, arguments={"arg": "value"}),
        approver="test-approver",
        decision=decision,
        uuid=uuid,
    )


class TestAdditionalEventTypes:
    """Tests for ModelEvent and ApprovalEvent matching."""

    @pytest.mark.asyncio
    async def test_model_event_match(self) -> None:
        """Pattern matches model event completion."""
        transcript = make_transcript_with_events(
            [make_model_event("The answer contains an error in the logic", "e1")]
        )
        scanner = grep_scanner("error")
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1
        assert result.references[0].type == "event"

    @pytest.mark.asyncio
    async def test_approval_event_match(self) -> None:
        """Pattern matches approval event content."""
        transcript = make_transcript_with_events(
            [
                make_approval_event(
                    "Dangerous operation detected", "rm_rf", "reject", "e1"
                )
            ]
        )
        scanner = grep_scanner("dangerous", ignore_case=True)
        result = await scanner(transcript)

        assert isinstance(result, Result)
        assert result.value == 1


class TestErrorHandling:
    """Tests for error handling."""

    def test_empty_pattern_list_raises(self) -> None:
        """Empty pattern list raises ValueError."""
        with pytest.raises(ValueError, match="Pattern list cannot be empty"):
            grep_scanner([])

    def test_empty_pattern_dict_raises(self) -> None:
        """Empty pattern dict raises ValueError."""
        with pytest.raises(ValueError, match="Pattern dict cannot be empty"):
            grep_scanner({})

    @pytest.mark.asyncio
    async def test_invalid_regex_raises(self) -> None:
        """Invalid regex pattern raises PatternError."""
        transcript = make_transcript([("assistant", "test")])
        scanner = grep_scanner("[invalid(", regex=True)

        with pytest.raises(PatternError, match="Invalid regex pattern"):
            await scanner(transcript)

    @pytest.mark.asyncio
    async def test_invalid_regex_in_list_raises(self) -> None:
        """Invalid regex in pattern list raises PatternError."""
        transcript = make_transcript([("assistant", "test")])
        scanner = grep_scanner(["valid", "[invalid("], regex=True)

        with pytest.raises(PatternError):
            await scanner(transcript)
