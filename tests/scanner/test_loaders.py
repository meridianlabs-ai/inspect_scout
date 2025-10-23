"""Tests for create_loader_for_scanner functionality."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import pytest
from inspect_ai._util.registry import (
    registry_unqualified_name,
)
from inspect_ai.event import Event, ModelEvent, ToolEvent
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_scout._scanner._loaders import (
    create_implicit_loader,
)
from inspect_scout._transcript.types import Transcript, TranscriptContent


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


async def _no_hint(input) -> Any:  # type:ignore
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


does_not_matter_filter = TranscriptContent(["tool"], None)
user_filter = TranscriptContent(["user"], None)
assistant_filter = TranscriptContent(["assistant"], None)
model_event_filter = TranscriptContent(None, ["model"])
tool_event_filter = TranscriptContent(None, ["tool"])
all_filter = TranscriptContent("all", "all")


@pytest.mark.parametrize(
    "scanner_fn,expected_loader_type",
    [
        (_transcript, "IdentityLoader"),
        (_no_hint, "IdentityLoader"),
        (_message, "ListItemLoader"),
        (_specific_message, "ListItemLoader"),
        (_union_message, "ListItemLoader"),
        (_list_message, "ListLoader"),
        (_list_specific_message, "ListLoader"),
        (_list_union_message, "ListLoader"),
        (_event, "ListItemLoader"),
        (_specific_event, "ListItemLoader"),
        (_union_event, "ListItemLoader"),
        (_list_event, "ListLoader"),
        (_list_specific_event, "ListLoader"),
        (_list_union_event, "ListLoader"),
    ],
)
def test_create_loader_returns_correct_type(
    scanner_fn: Any, expected_loader_type: str
) -> None:
    """create_loader_for_scanner returns correct loader type for each input annotation."""
    loader = create_implicit_loader(scanner_fn, does_not_matter_filter)
    assert registry_unqualified_name(loader) == expected_loader_type


@pytest.mark.asyncio
async def test_identity_loader_yields_transcript() -> None:
    """IdentityLoader returns transcript unchanged."""
    loader = create_implicit_loader(_transcript, all_filter)
    transcript = create_test_transcript()

    results = [item async for item in loader(transcript)]

    assert len(results) == 1
    assert isinstance(results[0], Transcript)


@pytest.mark.asyncio
async def test_list_loader_yields_entire_message_list() -> None:
    """ListLoader for messages yields entire message list."""
    loader = create_implicit_loader(_list_message, user_filter)
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
    loader = create_implicit_loader(_list_event, tool_event_filter)
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
    loader = create_implicit_loader(_message, user_filter)
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

    loader = create_implicit_loader(_event, model_event_filter)
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
    loader = create_implicit_loader(_union_message, does_not_matter_filter)

    # Should create a ListItemLoader
    assert registry_unqualified_name(loader) == "ListItemLoader"


@pytest.mark.asyncio
async def test_union_message_list_should_be_detected_as_message() -> None:
    """Union message list type should be detected as message type."""
    loader = create_implicit_loader(_list_union_message, does_not_matter_filter)

    # Should create a ListLoader
    assert registry_unqualified_name(loader) == "ListLoader"


@pytest.mark.asyncio
async def test_loaders_handle_empty_transcript() -> None:
    """All loaders handle empty transcript correctly."""
    empty_transcript = create_test_transcript()

    # IdentityLoader should yield the empty transcript
    identity_loader = create_implicit_loader(_transcript, all_filter)
    identity_results = [item async for item in identity_loader(empty_transcript)]
    assert len(identity_results) == 1
    assert isinstance(identity_results[0], Transcript)
    assert not identity_results[0].messages
    assert not identity_results[0].events

    # List loaders should yield empty lists
    message_list_loader = create_implicit_loader(_list_message, all_filter)
    message_list_results = [
        item async for item in message_list_loader(empty_transcript)
    ]
    assert len(message_list_results) == 1
    assert message_list_results[0] == []

    event_list_loader = create_implicit_loader(_list_event, all_filter)
    event_list_results = [item async for item in event_list_loader(empty_transcript)]
    assert len(event_list_results) == 1
    assert event_list_results[0] == []

    # Item loaders should yield nothing
    message_item_loader = create_implicit_loader(_message, all_filter)
    message_item_results = [
        item async for item in message_item_loader(empty_transcript)
    ]
    assert len(message_item_results) == 0

    event_item_loader = create_implicit_loader(_event, all_filter)
    event_item_results = [item async for item in event_item_loader(empty_transcript)]
    assert len(event_item_results) == 0


def test_bare_list_type_should_raise_error() -> None:
    """Scanner with bare list type (no type parameters) should raise RuntimeError."""

    async def _bare_list(input: list[Any]) -> Any:
        """Scanner with bare list type - ambiguous whether messages or events."""
        pass

    # Should raise RuntimeError because element_type cannot be determined
    with pytest.raises(RuntimeError):
        create_implicit_loader(_bare_list, does_not_matter_filter)
