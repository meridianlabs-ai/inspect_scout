"""Tests for grep_scanner."""

import pytest
from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageUser
from inspect_scout import grep_scanner
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
