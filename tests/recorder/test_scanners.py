"""Scanner definitions for DuckDB tests."""

from inspect_scout import Result, Scanner, scanner
from inspect_scout._transcript.types import Transcript


@scanner(messages=["assistant"])
def word_counter(target_word: str) -> Scanner[Transcript]:
    """Count occurrences of a target word in assistant messages."""
    target_word = target_word.lower()

    async def execute(transcript: Transcript) -> Result:
        count = sum(
            msg.text.lower().count(target_word)
            for msg in transcript.messages
            if msg.role == "assistant"
        )
        return Result(
            value=count,
            explanation=f"Found '{target_word}' {count} times in assistant messages",
        )

    return execute


@scanner(messages=["user"])
def message_length() -> Scanner[Transcript]:
    """Calculate total length of user messages."""

    async def execute(transcript: Transcript) -> Result:
        total_length = sum(
            len(msg.text) for msg in transcript.messages if msg.role == "user"
        )
        return Result(
            value=total_length,
            explanation=f"Total user message length: {total_length}",
        )

    return execute
