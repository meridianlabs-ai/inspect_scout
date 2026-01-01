import re
from dataclasses import dataclass
from typing import Iterator, Literal

from inspect_ai.event import Event
from inspect_ai.model import ChatMessage

from .._scanner.extract import message_as_str
from .._scanner.util import _event_id, _message_id
from ._event import event_as_str

MAX_CONTEXT = 50


@dataclass(frozen=True)
class Match:
    """A single pattern match with location information."""

    source: Literal["message", "event"]
    index: int
    id: str
    position: int
    match_text: str
    context: str


class PatternError(ValueError):
    """Error raised when a pattern is invalid."""

    pass


def compile_pattern(
    pattern: str,
    regex: bool,
    ignore_case: bool,
    word_boundary: bool,
) -> re.Pattern[str]:
    """Compile a pattern into a regex object.

    Args:
        pattern: The pattern string to compile.
        regex: If True, treat as regex; if False, escape special chars.
        ignore_case: If True, compile with case-insensitive flag.
        word_boundary: If True, wrap pattern with word boundary anchors.

    Returns:
        Compiled regex pattern.

    Raises:
        PatternError: If the pattern is an invalid regular expression.
    """
    if not regex:
        pattern = re.escape(pattern)  # Escape special chars for literal matching

    if word_boundary:
        pattern = rf"\b{pattern}\b"

    flags = re.IGNORECASE if ignore_case else 0

    try:
        return re.compile(pattern, flags)
    except re.error as e:
        raise PatternError(f"Invalid regex pattern '{pattern}': {e}") from e


def find_matches_in_messages(
    messages: list[ChatMessage],
    patterns: list[re.Pattern[str]],
) -> Iterator[Match]:
    """Find all matches across all messages for any of the patterns."""
    for index, message in enumerate(messages, start=1):
        text = message_as_str(message) or ""
        msg_id = _message_id(message)

        for compiled in patterns:
            for match in compiled.finditer(text):
                yield Match(
                    source="message",
                    index=index,
                    id=msg_id,
                    position=match.start(),
                    match_text=match.group(0),
                    context=_extract_context(text, match.start(), len(match.group(0))),
                )


def find_matches_in_events(
    events: list[Event],
    patterns: list[re.Pattern[str]],
) -> Iterator[Match]:
    """Find all matches across all events for any of the patterns."""
    for index, event in enumerate(events, start=1):
        text = event_as_str(event) or ""
        evt_id = _event_id(event)

        for compiled in patterns:
            for match in compiled.finditer(text):
                yield Match(
                    source="event",
                    index=index,
                    id=evt_id,
                    position=match.start(),
                    match_text=match.group(0),
                    context=_extract_context(text, match.start(), len(match.group(0))),
                )


def _extract_context(text: str, pos: int, match_len: int) -> str:
    """Extract context around a match position.

    Shows up to MAX_CONTEXT chars before and after the match,
    with the match text highlighted in bold.
    """
    start = max(0, pos - MAX_CONTEXT)
    end = min(len(text), pos + match_len + MAX_CONTEXT)

    before = text[start:pos]
    match_text = text[pos : pos + match_len]
    after = text[pos + match_len : end]

    # Strip newlines and build context with bold match
    context = (
        before.replace("\n", " ")
        + "**"
        + match_text.replace("\n", " ")
        + "**"
        + after.replace("\n", " ")
    )

    # Add ellipsis if truncated
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."

    return context
