"""Sample scanner implementations for testing."""

from collections.abc import Callable

from inspect_ai.event._model import ModelEvent
from inspect_ai.event._tool import (
    ToolEvent,
)
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
)
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, scanner
from inspect_scout._transcript.types import Transcript

# Valid scanners for testing


@scanner(messages=["system"])
def valid_system_scanner() -> Scanner[ChatMessageSystem]:
    """Scanner that correctly handles only system messages."""

    async def scan(message: ChatMessageSystem) -> Result:
        return Result(value={"type": "system", "content": message.text})

    return scan


@scanner(messages=["system", "user"])
def valid_union_scanner() -> Scanner[ChatMessageSystem | ChatMessageUser]:
    """Scanner that correctly handles a union of message types."""

    async def scan(message: ChatMessageSystem | ChatMessageUser) -> Result:
        return Result(value={"role": message.role})

    return scan


@scanner(messages=["assistant"])
def valid_assistant_scanner() -> Scanner[ChatMessageAssistant]:
    """Scanner that correctly handles assistant messages."""

    async def scan(message: ChatMessageAssistant) -> Result:
        return Result(value={"model": message.model})

    return scan


@scanner(messages="all")
def valid_all_messages_scanner() -> Scanner[ChatMessage]:
    """Scanner that accepts all message types."""

    async def scan(message: ChatMessage) -> Result:
        return Result(value={"role": message.role})

    return scan


@scanner(events=["model", "tool"])
def valid_event_union_scanner() -> Scanner[ModelEvent | ToolEvent]:
    """Scanner that handles specific event types."""

    async def scan(event: ModelEvent | ToolEvent) -> Result:
        return Result(value={"event": event.event})

    return scan


@scanner(messages=["user"], events=["model"])
def valid_transcript_scanner() -> Scanner[Transcript]:
    """Scanner that requires both messages and events."""

    async def scan(transcript: Transcript) -> Result:
        return Result(value={"id": transcript.transcript_id})

    return scan


@scanner(messages=["system", "user"])
def valid_base_type_scanner() -> Scanner[ChatMessage]:
    """Scanner using base type with specific filter."""

    async def scan(message: ChatMessage) -> Result:
        return Result(value={"text": message.text})

    return scan


@scanner(messages=["assistant"])  # type: ignore[type-var]
def valid_list_scanner() -> Scanner[list[ChatMessageAssistant]]:
    """Scanner that handles lists of messages."""

    async def scan(messages: list[ChatMessageAssistant]) -> Result:
        return Result(value={"count": len(messages)})

    return scan


# Invalid scanners for testing (will be created dynamically in tests)


def create_invalid_subset_scanner() -> Callable[[], Scanner[ChatMessageSystem]]:
    """Create scanner with subset type error."""

    @scanner(messages=["system", "user"])
    def invalid_scanner() -> Scanner[ChatMessageSystem]:
        async def scan(message: ChatMessageSystem) -> Result:
            return Result(value={"error": "invalid"})

        return scan

    return invalid_scanner


def create_invalid_wrong_type_scanner() -> Callable[[], Scanner[ChatMessageAssistant]]:
    """Create scanner with wrong type error."""

    @scanner(messages=["user"])
    def invalid_scanner() -> Scanner[ChatMessageAssistant]:
        async def scan(message: ChatMessageAssistant) -> Result:
            return Result(value={"error": "wrong type"})

        return scan

    return invalid_scanner


def create_invalid_all_filter_scanner() -> Callable[[], Scanner[ChatMessageAssistant]]:
    """Create scanner with invalid 'all' filter usage."""

    @scanner(messages="all")
    def invalid_scanner() -> Scanner[ChatMessageAssistant]:
        async def scan(message: ChatMessageAssistant) -> Result:
            return Result(value={"error": "all filter"})

        return scan

    return invalid_scanner
