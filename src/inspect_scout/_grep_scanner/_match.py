import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from inspect_ai._util.textsearch import Fold, FoldedText, compile_query
from inspect_ai._view.find import MessageRow, project_event, project_row
from inspect_ai.event import Event
from inspect_ai.model import ChatMessage

from .._scanner.util import _event_id, _message_id

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
) -> re.Pattern[str] | None:
    """Compile a pattern the same way inspect_ai Find/grep matching does.

    Args:
        pattern: The pattern string to compile.
        regex: If True, treat as regex; if False, escape special chars.
        ignore_case: Casefold the text and a literal query.
        word_boundary: Match whole words only (wraps the whole pattern).

    Returns:
        Compiled regex to run over ``FoldedText.folded``, or None when
        ``pattern`` is empty (no matches).

    Raises:
        PatternError: If regex=True and pattern is an invalid regular expression.
    """
    try:
        return compile_query(
            pattern,
            mode="regex" if regex else "literal",
            fold=_fold(ignore_case),
            word_boundary=word_boundary,
        )
    except re.error as e:
        raise PatternError(f"Invalid regex pattern '{pattern}': {e}") from e


def find_matches_in_messages(
    messages: list[ChatMessage],
    patterns: list[re.Pattern[str] | None],
    fold: Fold,
) -> Iterator[Match]:
    """Find all matches across all messages for any of the patterns."""
    for index, message in enumerate(messages, start=1):
        text = _message_text(message)
        yield from _scan(text, patterns, fold, "message", index, _message_id(message))


def find_matches_in_events(
    events: list[Event],
    patterns: list[re.Pattern[str] | None],
    fold: Fold,
) -> Iterator[Match]:
    """Find all matches across all events for any of the patterns."""
    for index, event in enumerate(events, start=1):
        text = _event_text(event)
        yield from _scan(text, patterns, fold, "event", index, _event_id(event))


def _fold(ignore_case: bool) -> Fold:
    return "case" if ignore_case else "none"


def _message_text(message: ChatMessage) -> str:
    # grep has never searched system prompts (message_as_str skipped them)
    if message.role == "system":
        return ""
    return "\n".join(project_row(MessageRow(message), include_chrome=False))


def _event_text(event: Event) -> str:
    return "\n".join(project_event(event, include_chrome=False))


def _scan(
    text: str,
    patterns: list[re.Pattern[str] | None],
    fold: Fold,
    source: Literal["message", "event"],
    index: int,
    item_id: str,
) -> Iterator[Match]:
    if not text:
        return
    folded = FoldedText(text, fold)
    for compiled in patterns:
        for start, end in folded.find_all(compiled):
            yield Match(
                source=source,
                index=index,
                id=item_id,
                position=start,
                match_text=text[start:end],
                context=_extract_context(text, start, end - start),
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
