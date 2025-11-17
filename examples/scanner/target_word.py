from functools import reduce
from typing import NamedTuple

from inspect_ai.model import ChatMessage, ChatMessageAssistant
from inspect_scout import Result, Scanner, scanner
from inspect_scout._scanner.extract import message_as_str
from inspect_scout._scanner.result import Reference
from inspect_scout._scanner.util import _message_id
from inspect_scout._transcript.types import Transcript

MAX_CONTEXT = 50


@scanner(messages=["assistant"])
def target_word_message(target: str) -> Scanner[ChatMessageAssistant]:
    """Count target word occurrences in an assistant message.

    Searches an assistant message for the target word (case-insensitive), returning
    the occurrence count with contextual snippets.

    Args:
        target: The word or phrase to search for.

    Returns:
        Scanner that produces Result with:
            - value: Occurrence count
            - explanation: Contextual snippets showing each match with MAX_CONTEXT chars before/after
    """
    target = target.lower()
    target_length = len(target)

    async def execute(message: ChatMessageAssistant) -> Result:
        text = message_as_str(message) or ""
        positions = _find_positions(text.lower(), target)

        explanation = (
            "\n".join(_extract_context(text, pos, target_length) for pos in positions)
            if positions
            else None
        )

        return Result(value=len(positions), explanation=explanation)

    return execute


@scanner(messages=["assistant"])
def target_word_transcript(
    target: str,
) -> Scanner[Transcript]:
    """Count target word occurrences across transcript with context.

    Searches all assistant messages in the transcript for the target word (case-insensitive),
    returning total count, contextual snippets for each match, and message references.

    Args:
        target: The word or phrase to search for.

    Returns:
        Scanner that produces Result with:
            - value: Total occurrence count across all messages
            - explanation: Contextual snippets showing each match with 50 chars before/after
            - references: Message citations for each match location
    """
    target = target.lower()
    target_length = len(target)

    class _Accum(NamedTuple):
        total: int
        explanation_parts: list[str]
        references: list[Reference]

    def _reduce_message(acc: _Accum, item: tuple[int, ChatMessage]) -> _Accum:
        index, message = item
        text = message_as_str(message) or ""

        if not (positions := _find_positions(text.lower(), target)):
            return acc

        new_explanations = [
            f"[Z{index}]: {_extract_context(text, pos, target_length)}"
            for pos in positions
        ]

        new_reference = [
            Reference(type="message", cite=f"[Z{index}]", id=_message_id(message))
        ]

        return _Accum(
            total=acc.total + len(positions),
            explanation_parts=acc.explanation_parts + new_explanations,
            references=acc.references + new_reference,
        )

    async def execute(transcript: Transcript) -> Result:
        total, explanation_parts, references = reduce(
            _reduce_message,
            enumerate(transcript.messages, start=1),
            _Accum(total=0, explanation_parts=[], references=[]),
        )
        return Result(
            value=total,
            explanation="\n".join(explanation_parts) if total else None,
            references=references,
        )

    return execute


def _find_positions(text: str, target: str) -> list[int]:
    positions = []
    start = 0
    while (pos := text.find(target, start)) != -1:
        positions.append(pos)
        start = pos + len(target)
    return positions


def _extract_context(text: str, pos: int, match_len: int) -> str:
    """Extract up to MAX_CONTEXT chars before and after the match."""
    start = max(0, pos - MAX_CONTEXT)
    end = min(len(text), pos + match_len + MAX_CONTEXT)

    # Extract parts: before, match, after
    before = text[start:pos]
    match = text[pos : pos + match_len]
    after = text[pos + match_len : end]

    # Strip newlines and build context with bold match
    context = (
        before.replace("\n", " ")
        + "**"
        + match.replace("\n", " ")
        + "**"
        + after.replace("\n", " ")
    )

    # Add ellipsis if truncated
    if start > 0:
        context = "..." + context
    if end < len(text):
        context = context + "..."

    return context
