"""Tests for runtime type validation in the scanner module."""

from collections.abc import Callable
from typing import Any, AsyncGenerator

import pytest
from inspect_ai._util.registry import registry_info
from inspect_ai.event._event import Event
from inspect_ai.event._model import ModelEvent
from inspect_ai.event._tool import ToolEvent
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import SCANNER_CONFIG, Scanner, scanner
from inspect_scout._transcript.types import Transcript

# Valid scanner tests


def test_base_type_with_filter() -> None:
    """Base ChatMessage type should work with any message filter."""

    @scanner(messages=["system", "user"])
    def test_scanner() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    # Should not raise
    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[
        SCANNER_CONFIG
    ].content.messages == ["system", "user"]


def test_exact_union_match() -> None:
    """Union type matching filter should work."""

    @scanner(messages=["system", "user"])
    def test_scanner() -> Scanner[ChatMessageSystem | ChatMessageUser]:
        async def scan(message: ChatMessageSystem | ChatMessageUser) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_single_type_single_filter() -> None:
    """Single type with matching single filter should work."""

    @scanner(messages=["assistant"])
    def test_scanner() -> Scanner[ChatMessageAssistant]:
        async def scan(message: ChatMessageAssistant) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_list_of_base_type() -> None:
    """List of base type should work."""

    @scanner(messages=["system", "user"])
    def test_scanner() -> Scanner[list[ChatMessage]]:
        async def scan(messages: list[ChatMessage]) -> Result:
            return Result(value={"count": len(messages)})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_list_of_specific_type() -> None:
    """List of specific type with matching filter should work."""

    @scanner(messages=["assistant"])  # type: ignore[type-var]
    def test_scanner() -> Scanner[list[ChatMessageAssistant]]:
        async def scan(messages: list[ChatMessageAssistant]) -> Result:
            return Result(value={"count": len(messages)})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_list_of_union_type() -> None:
    """List of union types should work."""

    @scanner(messages=["system", "user"])  # type: ignore[type-var]
    def test_scanner() -> Scanner[list[ChatMessageSystem | ChatMessageUser]]:
        async def scan(
            messages: list[ChatMessageSystem | ChatMessageUser],
        ) -> Result:
            return Result(value={"count": len(messages)})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_messages_all_with_base_type() -> None:
    """messages='all' should work with ChatMessage."""

    @scanner(messages="all")
    def test_scanner() -> Scanner[ChatMessage]:
        async def scan(message: ChatMessage) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert (
        registry_info(scanner_instance).metadata[SCANNER_CONFIG].content.messages
        == "all"
    )


def test_events_all_with_base_type() -> None:
    """events='all' should work with Event."""

    @scanner(events="all")
    def test_scanner() -> Scanner[Event]:
        async def scan(event: Event) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert (
        registry_info(scanner_instance).metadata[SCANNER_CONFIG].content.events == "all"
    )


def test_event_union_types() -> None:
    """Event union types should work."""

    @scanner(events=["model", "tool"])
    def test_scanner() -> Scanner[ModelEvent | ToolEvent]:
        async def scan(event: ModelEvent | ToolEvent) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_transcript_with_both_filters() -> None:
    """Both message and event filters should require Transcript."""

    @scanner(messages=["user"], events=["model"])
    def test_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value={"id": transcript.id})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_all_message_types_union() -> None:
    """Union of all message types should work with 'all'."""

    @scanner(messages="all")
    def test_scanner() -> Scanner[
        ChatMessageSystem | ChatMessageUser | ChatMessageAssistant | ChatMessageTool
    ]:
        async def scan(
            message: ChatMessageSystem
            | ChatMessageUser
            | ChatMessageAssistant
            | ChatMessageTool,
        ) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


# Invalid scanner tests


def test_subset_type_error() -> None:
    """Single type can't handle multiple filter types."""
    with pytest.raises(TypeError, match="must be able to handle all types"):

        @scanner(messages=["system", "user"])
        def test_scanner() -> Scanner[ChatMessageSystem]:
            async def scan(message: ChatMessageSystem) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()  # Validation happens here


def test_wrong_type_error() -> None:
    """Type not in filter should fail."""
    with pytest.raises(TypeError, match="must be able to handle all types"):

        @scanner(messages=["user"])
        def test_scanner() -> Scanner[ChatMessageAssistant]:
            async def scan(message: ChatMessageAssistant) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_partial_union_error() -> None:
    """Union missing required types should fail."""
    with pytest.raises(TypeError, match="must be able to handle all types"):

        @scanner(messages=["system", "user", "assistant"])
        def test_scanner() -> Scanner[ChatMessageSystem | ChatMessageUser]:
            async def scan(
                message: ChatMessageSystem | ChatMessageUser,
            ) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_all_filter_with_specific_type() -> None:
    """messages='all' with specific type should fail."""
    with pytest.raises(TypeError, match="must accept ChatMessage"):

        @scanner(messages="all")
        def test_scanner() -> Scanner[ChatMessageAssistant]:
            async def scan(message: ChatMessageAssistant) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_events_all_with_specific_type() -> None:
    """events='all' with specific type should fail."""
    with pytest.raises(TypeError, match="must accept Event"):

        @scanner(events="all")
        def test_scanner() -> Scanner[ModelEvent]:
            async def scan(event: ModelEvent) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_both_filters_without_transcript() -> None:
    """Both filters present but not accepting Transcript should fail."""
    with pytest.raises(TypeError, match="must accept Transcript"):

        @scanner(messages=["user"], events=["model"])  # type: ignore[arg-type]
        def test_scanner() -> Scanner[ChatMessage]:
            async def scan(message: ChatMessage) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_list_of_wrong_type() -> None:
    """List of wrong type should fail."""
    with pytest.raises(TypeError, match="must be able to handle all types"):

        @scanner(messages=["user"])  # type: ignore[type-var]
        def test_scanner() -> Scanner[list[ChatMessageAssistant]]:
            async def scan(messages: list[ChatMessageAssistant]) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


def test_list_of_partial_union() -> None:
    """List of partial union should fail."""
    with pytest.raises(TypeError, match="must be able to handle all types"):

        @scanner(messages=["system", "user", "assistant"])  # type: ignore[type-var]
        def test_scanner() -> Scanner[list[ChatMessageSystem | ChatMessageUser]]:
            async def scan(
                messages: list[ChatMessageSystem | ChatMessageUser],
            ) -> Result:
                return Result(value={"bad": True})

            return scan

        test_scanner()


# Edge case tests


def test_no_type_hints() -> None:
    """Scanner without type hints should not raise."""

    @scanner(messages=["system"])
    def test_scanner() -> Callable[[Any], Any]:
        async def scan(message):  # type: ignore[no-untyped-def]
            return Result(value={"ok": True})

        return scan

    # Should not raise even without type hints
    scanner_instance = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]


def test_scanner_without_filters_but_with_loader() -> None:
    """Scanner with only a custom loader should work."""
    from inspect_scout._scanner.loader import loader

    @loader(name="test_loader", messages="all")  # type: ignore[arg-type]
    def test_loader() -> Callable[[Transcript], AsyncGenerator[Transcript, None]]:
        async def load(transcripts: Transcript) -> AsyncGenerator[Transcript, None]:
            yield transcripts

        return load

    @scanner(loader=test_loader())
    def test_scanner() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value={"id": transcript.id})

        return scan

    scanner_instance: Any = test_scanner()
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]
    assert registry_info(scanner_instance).metadata[SCANNER_CONFIG].loader


def test_non_async_scanner() -> None:
    """Non-async scanner should raise TypeError."""
    with pytest.raises(TypeError, match="not declared as an async callable"):

        @scanner(messages=["system"])
        def test_scanner() -> Scanner[ChatMessage]:
            def scan(message: ChatMessage) -> Result:  # Not async!
                return Result(value={"bad": True})

            return scan  # type: ignore[return-value]

        test_scanner()


def test_multiple_event_types() -> None:
    """Multiple event types should work correctly."""

    @scanner(events=["model", "tool", "error", "sample_init"])  # type: ignore[list-item]
    def test_scanner() -> Scanner[Event]:
        async def scan(event: Event) -> Result:
            return Result(value={"event": event.event})

        return scan

    scanner_instance = test_scanner()
    assert (
        len(registry_info(scanner_instance).metadata[SCANNER_CONFIG].content.events)
        == 4
    )


def test_all_supported_event_types() -> None:
    """Test all currently supported event types."""
    all_events = [
        "model",
        "tool",
        "sample_init",
        "sample_limit",
        "sandbox",
        "state",
        "store",
        "approval",
        "input",
        "score",
        "error",
        "logger",
        "info",
        "span_begin",
        "span_end",
    ]

    @scanner(events=all_events)  # type: ignore[arg-type]
    def test_scanner() -> Scanner[Event]:
        async def scan(event: Event) -> Result:
            return Result(value={"ok": True})

        return scan

    scanner_instance = test_scanner()
    assert len(
        registry_info(scanner_instance).metadata[SCANNER_CONFIG].content.events
    ) == len(all_events)


# Parametrized tests


@pytest.mark.parametrize(
    "filter_types,scanner_type,should_pass",
    [
        # Valid cases
        (["system"], ChatMessageSystem, True),
        (["system"], ChatMessage, True),
        (["system", "user"], ChatMessage, True),
        (["assistant"], ChatMessageAssistant, True),
        ("all", ChatMessage, True),
        # Invalid cases
        (["system", "user"], ChatMessageSystem, False),
        (["user"], ChatMessageAssistant, False),
        (["system", "user", "assistant"], ChatMessageSystem | ChatMessageUser, False),
        ("all", ChatMessageAssistant, False),
    ],
)
def test_message_validation_matrix(
    filter_types: Any, scanner_type: Any, should_pass: bool
) -> None:
    """Test various combinations of filters and types."""
    if should_pass:

        @scanner(messages=filter_types)
        def test_scanner() -> Scanner[scanner_type]:  # pyright: ignore[reportInvalidTypeForm]
            async def scan(message: scanner_type) -> Result:
                return Result(value={"ok": True})

            return scan

        scanner_instance = test_scanner()
        assert registry_info(scanner_instance).metadata[SCANNER_CONFIG]
    else:
        with pytest.raises(TypeError):

            @scanner(messages=filter_types)
            def test_scanner() -> Scanner[scanner_type]:  # pyright: ignore[reportInvalidTypeForm]
                async def scan(message: scanner_type) -> Result:
                    return Result(value={"bad": True})

                return scan

            test_scanner()
