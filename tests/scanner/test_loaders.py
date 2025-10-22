"""Tests for create_loader_for_scanner functionality."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import pytest
from inspect_ai.event import Event, ModelEvent, ToolEvent
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_scout._scanner._loaders import (
    IdentityLoader,
    _ListItemLoader,
    _ListLoader,
    create_loader_for_scanner,
)
from inspect_scout._transcript.types import Transcript


def create_test_transcript(
    messages: Sequence[ChatMessage] | None = None,
    events: Sequence[Event] | None = None,
) -> Transcript:
    """Create a test transcript with required fields."""
    return Transcript(
        id="test_id",
        source_id="test_source",
        source_uri="test://uri",
        messages=list(messages) if messages else [],
        events=list(events) if events else [],
    )


# Test scanner functions with different input type annotations
async def _transcript(input: Transcript) -> Any:
    pass


async def _no_hint(input) -> Any:
    pass


async def _message(input: ChatMessage) -> Any:
    pass


async def _specific_message(input: ChatMessageAssistant) -> Any:
    pass


async def _union_message(
    input: ChatMessageAssistant | ChatMessageUser,
) -> Any:
    pass


async def _list_message(input: list[ChatMessage]) -> Any:
    pass


async def _list_specific_message(input: list[ChatMessageAssistant]) -> Any:
    pass


async def _list_union_message(
    input: list[ChatMessageAssistant | ChatMessageUser],
) -> Any:
    pass


async def _event(input: Event) -> Any:
    pass


async def _specific_event(input: ToolEvent) -> Any:
    pass


async def _union_event(
    input: ModelEvent | ToolEvent,
) -> Any:
    pass


async def _list_event(input: list[Event]) -> Any:
    pass


async def _list_specific_event(input: list[ToolEvent]) -> Any:
    pass


async def _list_union_event(
    input: list[ModelEvent | ToolEvent],
) -> Any:
    pass


@pytest.mark.parametrize(
    "scanner_fn,expected_loader_type",
    [
        (_transcript, IdentityLoader),
        (_no_hint, IdentityLoader),
        (_message, _ListItemLoader),
        (_specific_message, _ListItemLoader),
        (_union_message, _ListItemLoader),
        (_list_message, _ListLoader),
        (_list_specific_message, _ListLoader),
        (_list_union_message, _ListLoader),
        (_event, _ListItemLoader),
        (_specific_event, _ListItemLoader),
        (_union_event, _ListItemLoader),
        (_list_event, _ListLoader),
        (_list_specific_event, _ListLoader),
        (_list_union_event, _ListLoader),
    ],
)
def test_create_loader_returns_correct_type(
    scanner_fn: Any, expected_loader_type: type
) -> None:
    """create_loader_for_scanner returns correct loader type for each input annotation."""
    loader = create_loader_for_scanner(scanner_fn)
    assert isinstance(loader, expected_loader_type)


@pytest.mark.asyncio
async def test_identity_loader_yields_transcript() -> None:
    """IdentityLoader returns transcript unchanged."""
    loader = create_loader_for_scanner(_transcript)
    transcript = create_test_transcript()

    results = [item async for item in loader(transcript)]

    assert len(results) == 1
    assert results[0] is transcript


@pytest.mark.asyncio
async def test_list_loader_yields_entire_message_list() -> None:
    """ListLoader for messages yields entire message list."""
    loader = create_loader_for_scanner(_list_message)
    messages: list[ChatMessage] = [
        ChatMessageUser(content="msg1"),
        ChatMessageUser(content="msg2"),
    ]
    transcript = create_test_transcript(messages=messages)

    results = [item async for item in loader(transcript)]

    assert len(results) == 1
    assert results[0] == messages


@pytest.mark.asyncio
async def test_list_loader_yields_entire_event_list() -> None:
    """ListLoader for events yields entire event list."""
    loader = create_loader_for_scanner(_list_event)
    events: list[Event] = [
        ToolEvent(
            event="tool",
            timestamp=datetime.now(),
            id="tool1",
            function="test_tool",
            arguments={},
        ),
        ToolEvent(
            event="tool",
            timestamp=datetime.now(),
            id="tool2",
            function="test_tool2",
            arguments={},
        ),
    ]
    transcript = create_test_transcript(events=events)

    results = [item async for item in loader(transcript)]

    assert len(results) == 1
    assert results[0] == events


@pytest.mark.asyncio
async def test_list_item_loader_yields_individual_messages() -> None:
    """ListItemLoader for messages yields messages one at a time."""
    loader = create_loader_for_scanner(_message)
    messages: list[ChatMessage] = [
        ChatMessageUser(content="msg1"),
        ChatMessageUser(content="msg2"),
        ChatMessageUser(content="msg3"),
    ]
    transcript = create_test_transcript(messages=messages)

    results = [item async for item in loader(transcript)]

    assert len(results) == 3
    assert results == messages


@pytest.mark.asyncio
async def test_list_item_loader_yields_individual_events() -> None:
    """ListItemLoader for events yields events one at a time."""
    from inspect_ai.model import ModelOutput

    loader = create_loader_for_scanner(_event)
    events: list[Event] = [
        ModelEvent(
            event="model",
            timestamp=datetime.now(),
            model="gpt-4",
            input=[],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput(model="gpt-4", choices=[]),
        ),
        ModelEvent(
            event="model",
            timestamp=datetime.now(),
            model="gpt-3.5",
            input=[],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput(model="gpt-3.5", choices=[]),
        ),
        ModelEvent(
            event="model",
            timestamp=datetime.now(),
            model="claude",
            input=[],
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput(model="claude", choices=[]),
        ),
    ]
    transcript = create_test_transcript(events=events)

    results = [item async for item in loader(transcript)]

    assert len(results) == 3
    assert results == events


@pytest.mark.asyncio
async def test_union_message_type_should_be_detected_as_message() -> None:
    """Union message type (ChatMessageAssistant | ChatMessageUser) should be detected as message type."""
    loader = create_loader_for_scanner(_union_message)

    # Should create a ListItemLoader
    assert isinstance(loader, _ListItemLoader)

    # Union of message types should be detected as a message type
    assert loader.is_message is True


@pytest.mark.asyncio
async def test_union_message_list_should_be_detected_as_message() -> None:
    """Union message list type should be detected as message type."""
    loader = create_loader_for_scanner(_list_union_message)

    # Should create a ListLoader
    assert isinstance(loader, _ListLoader)

    # Union of message types should be detected as a message type
    assert loader.is_message is True


@pytest.mark.asyncio
async def test_loaders_handle_empty_transcript() -> None:
    """All loaders handle empty transcript correctly."""
    empty_transcript = create_test_transcript()

    # IdentityLoader should yield the empty transcript
    identity_loader = create_loader_for_scanner(_transcript)
    identity_results = [item async for item in identity_loader(empty_transcript)]
    assert len(identity_results) == 1
    assert identity_results[0] is empty_transcript

    # List loaders should yield empty lists
    message_list_loader = create_loader_for_scanner(_list_message)
    message_list_results = [
        item async for item in message_list_loader(empty_transcript)
    ]
    assert len(message_list_results) == 1
    assert message_list_results[0] == []

    event_list_loader = create_loader_for_scanner(_list_event)
    event_list_results = [item async for item in event_list_loader(empty_transcript)]
    assert len(event_list_results) == 1
    assert event_list_results[0] == []

    # Item loaders should yield nothing
    message_item_loader = create_loader_for_scanner(_message)
    message_item_results = [
        item async for item in message_item_loader(empty_transcript)
    ]
    assert len(message_item_results) == 0

    event_item_loader = create_loader_for_scanner(_event)
    event_item_results = [item async for item in event_item_loader(empty_transcript)]
    assert len(event_item_results) == 0


def test_bare_list_type_should_raise_error() -> None:
    """Scanner with bare list type (no type parameters) should raise RuntimeError."""

    async def _bare_list(input: list) -> Any:
        """Scanner with bare list type - ambiguous whether messages or events."""
        pass

    # Should raise RuntimeError because element_type cannot be determined
    with pytest.raises(RuntimeError):
        create_loader_for_scanner(_bare_list)
