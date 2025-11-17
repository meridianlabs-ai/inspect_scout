"""Tests for utility functions in the scanner module."""

from datetime import datetime

import pytest
from inspect_ai.event import ModelEvent, ToolEvent
from inspect_ai.model import ChatMessageAssistant, ChatMessageUser, ModelOutput
from inspect_ai.model._generate_config import GenerateConfig
from inspect_scout._scanner.util import get_input_type_and_ids
from inspect_scout._transcript.types import Transcript


@pytest.mark.parametrize(
    "input_value,expected_type,expected_ids",
    [
        # Single items with explicit IDs
        (
            Transcript(
                id="t1", source_type="test", source_id="s1", source_uri="uri://1"
            ),
            "transcript",
            ["t1"],
        ),
        (ChatMessageUser(content="hello", id="m1"), "message", ["m1"]),
        (ChatMessageAssistant(content="response", id="m2"), "message", ["m2"]),
        (
            ToolEvent(
                event="tool",
                timestamp=datetime.now(),
                id="tool1",
                function="fn",
                arguments={},
                uuid="e1",
            ),
            "event",
            ["e1"],
        ),
        (
            ModelEvent(
                event="model",
                timestamp=datetime.now(),
                model="gpt-4",
                input=[],
                tools=[],
                tool_choice="auto",
                config=GenerateConfig(),
                output=ModelOutput(model="gpt-4", choices=[]),
                uuid="e2",
            ),
            "event",
            ["e2"],
        ),
    ],
)
def test_single_items_return_correct_type_and_id(
    input_value: Transcript
    | ChatMessageUser
    | ChatMessageAssistant
    | ToolEvent
    | ModelEvent,
    expected_type: str,
    expected_ids: list[str],
) -> None:
    """Single items return (type_name, [id])."""
    result = get_input_type_and_ids(input_value)

    assert result == (expected_type, expected_ids)


@pytest.mark.parametrize(
    "input_value,expected_type",
    [
        (ChatMessageUser(content="test"), "message"),
        (
            ToolEvent(
                event="tool",
                timestamp=datetime.now(),
                id="tool1",
                function="fn",
                arguments={},
            ),
            "event",
        ),
    ],
)
def test_single_items_without_id_generate_auto_id(
    input_value: ChatMessageUser | ToolEvent,
    expected_type: str,
) -> None:
    """Single items without IDs generate non-empty auto IDs."""
    result = get_input_type_and_ids(input_value)

    assert result is not None
    assert result[0] == expected_type
    assert isinstance(result[1], list)
    assert len(result[1]) == 1
    assert isinstance(result[1][0], str)
    assert len(result[1][0]) > 0


@pytest.mark.parametrize(
    "input_list",
    [
        [],
        [ChatMessageUser(content="m1", id="id1")],
        [
            ChatMessageUser(content="m1", id="id1"),
            ChatMessageAssistant(content="m2", id="id2"),
        ],
    ],
)
def test_message_sequences(
    input_list: list[ChatMessageUser | ChatMessageAssistant],
) -> None:
    """Message sequences return ('messages', [ids]) or None for empty."""
    result = get_input_type_and_ids(input_list)

    if not input_list:
        assert result is None
    else:
        assert result is not None
        assert result[0] == "messages"
        assert result[1] == [msg.id for msg in input_list]


@pytest.mark.parametrize(
    "input_list",
    [
        [],
        [
            ToolEvent(
                event="tool",
                timestamp=datetime.now(),
                id="t1",
                function="fn",
                arguments={},
                uuid="e1",
            )
        ],
        [
            ToolEvent(
                event="tool",
                timestamp=datetime.now(),
                id="t1",
                function="fn",
                arguments={},
                uuid="e1",
            ),
            ModelEvent(
                event="model",
                timestamp=datetime.now(),
                model="gpt-4",
                input=[],
                tools=[],
                tool_choice="auto",
                config=GenerateConfig(),
                output=ModelOutput(model="gpt-4", choices=[]),
                uuid="e2",
            ),
        ],
    ],
)
def test_event_sequences(
    input_list: list[ToolEvent | ModelEvent],
) -> None:
    """Event sequences return ('events', [ids]) or None for empty."""
    result = get_input_type_and_ids(input_list)

    if not input_list:
        assert result is None
    else:
        assert result is not None
        assert result[0] == "events"
        assert result[1] == [evt.uuid for evt in input_list]


def test_heterogeneous_sequence_returns_based_on_first_item() -> None:
    """Sequence with mixed types returns type based on first item."""
    message = ChatMessageUser(content="msg", id="m1")
    event = ToolEvent(
        event="tool",
        timestamp=datetime.now(),
        id="t1",
        function="fn",
        arguments={},
        uuid="e1",
    )
    heterogeneous = [message, event]

    result = get_input_type_and_ids(heterogeneous)  # type: ignore[arg-type]

    # Returns type based on first item (message) and attempts to get IDs from all items
    assert result is not None
    assert result[0] == "messages"
    assert isinstance(result[1], list)
