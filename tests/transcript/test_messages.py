"""Tests for message extraction with compaction boundary handling."""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from inspect_ai.event import CompactionEvent, Event, ModelEvent, ToolEvent
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    ModelOutput,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model_output import ChatCompletionChoice
from inspect_scout._transcript.messages import messages_by_compaction


def _make_model_event(
    input: Sequence[ChatMessage],
    output_content: str = "response",
    uuid: str | None = None,
) -> ModelEvent:
    """Create a ModelEvent with the given input and output."""
    return ModelEvent(
        event="model",
        timestamp=datetime(2024, 1, 1),
        model="test-model",
        input=list(input),
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(
            model="test-model",
            choices=[
                ChatCompletionChoice(
                    message=ChatMessageAssistant(content=output_content),
                    stop_reason="stop",
                )
            ],
        ),
        uuid=uuid,
    )


def _make_compaction_event(
    type: Literal["summary", "trim", "edit"] = "summary",
) -> CompactionEvent:
    """Create a CompactionEvent with the given type."""
    return CompactionEvent(
        event="compaction",
        timestamp=datetime(2024, 1, 1),
        type=type,
    )


def _make_tool_event() -> ToolEvent:
    """Create a ToolEvent for testing that non-model events are ignored."""
    return ToolEvent(
        event="tool",
        timestamp=datetime(2024, 1, 1),
        id="tool-call-id",
        function="test_func",
        arguments={"arg": "value"},
        result="result",
    )


# -- Shared messages for tests --

_sys = ChatMessageSystem(content="You are an assistant", id="sys-1")
_user1 = ChatMessageUser(content="Hello", id="u-1")
_user2 = ChatMessageUser(content="Continue", id="u-2")
_user3 = ChatMessageUser(content="Elaborate", id="u-3")
_asst1 = ChatMessageAssistant(content="Hi there", id="a-1")
_asst2 = ChatMessageAssistant(content="Here is more", id="a-2")


def test_no_compaction() -> None:
    """Events with no compaction produce a single segment from the last ModelEvent."""
    events: list[Event] = [
        _make_model_event(
            input=[_sys, _user1],
            output_content="First response",
        ),
        _make_model_event(
            input=[_sys, _user1, _asst1, _user2],
            output_content="Second response",
        ),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 1
    segment = result[0]
    # Last ModelEvent's input + output
    assert len(segment) == 5  # sys, user1, asst1, user2, output
    assert segment[0].role == "system"
    assert segment[1] is _user1
    assert segment[3] is _user2
    assert segment[4].role == "assistant"
    assert segment[4].text == "Second response"


def test_summary_compaction() -> None:
    """Summary compaction produces two segments, each from its last ModelEvent."""
    events: list[Event] = [
        _make_model_event(
            input=[_sys, _user1],
            output_content="Pre-compaction answer",
        ),
        _make_model_event(
            input=[_sys, _user1, _asst1, _user2],
            output_content="More pre-compaction",
        ),
        _make_compaction_event(type="summary"),
        _make_model_event(
            input=[_sys, ChatMessageUser(content="Summary of prior", id="u-sum")],
            output_content="Post-compaction answer",
        ),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 2

    # Segment 0: last pre-compaction ModelEvent (the second one)
    seg0 = result[0]
    assert seg0[-1].text == "More pre-compaction"
    assert seg0[0].role == "system"

    # Segment 1: post-compaction ModelEvent
    seg1 = result[1]
    assert seg1[-1].text == "Post-compaction answer"


def test_trim_compaction() -> None:
    """Trim compaction produces a prefix segment + post-compaction segment."""
    # Pre-compaction: [sys, u1, a1, u2] — full conversation
    # Post-compaction: [a1, u2, u3] — sys and u1 were trimmed
    pre_msgs: list[ChatMessage] = [_sys, _user1, _asst1, _user2]
    post_msgs: list[ChatMessage] = [_asst1, _user2, _user3]

    events: list[Event] = [
        _make_model_event(input=pre_msgs, output_content="Before trim"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=post_msgs, output_content="After trim"),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 2

    # Segment 0: trimmed prefix — messages dropped by trim
    prefix = result[0]
    assert len(prefix) == 2  # sys, u1
    assert prefix[0] is _sys
    assert prefix[1] is _user1

    # Segment 1: post-compaction ModelEvent's input + output
    seg1 = result[1]
    assert seg1[0] is _asst1
    assert seg1[-1].text == "After trim"


def test_edit_compaction() -> None:
    """Edit compaction produces no split — single segment."""
    events: list[Event] = [
        _make_model_event(input=[_sys, _user1], output_content="Before edit"),
        _make_compaction_event(type="edit"),
        _make_model_event(
            input=[_sys, _user1, _asst1, _user2],
            output_content="After edit",
        ),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 1
    seg = result[0]
    assert seg[-1].text == "After edit"
    assert len(seg) == 5  # sys, u1, a1, u2, output


def test_multiple_compactions() -> None:
    """Two summary compactions produce three segments."""
    events: list[Event] = [
        _make_model_event(input=[_user1], output_content="Seg 0"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user2], output_content="Seg 1"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user3], output_content="Seg 2"),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 3
    assert result[0][-1].text == "Seg 0"
    assert result[1][-1].text == "Seg 1"
    assert result[2][-1].text == "Seg 2"


def test_empty_segment_omitted() -> None:
    """No ModelEvents before a compaction boundary → segment omitted."""
    events: list[Event] = [
        # Compaction with no preceding ModelEvents
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user1], output_content="Only segment"),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 1
    assert result[0][-1].text == "Only segment"


def test_non_model_events_ignored() -> None:
    """ToolEvents and other events are ignored."""
    events: list[Event] = [
        _make_tool_event(),
        _make_model_event(input=[_user1], output_content="Response"),
        _make_tool_event(),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 1
    assert result[0][-1].text == "Response"


def test_trim_empty_prefix() -> None:
    """Trim where all messages survive produces no prefix segment."""
    # Same messages in pre and post — nothing was trimmed
    msgs: list[ChatMessage] = [_sys, _user1]

    events: list[Event] = [
        _make_model_event(input=msgs, output_content="Before trim"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=msgs + [_user2], output_content="After trim"),
    ]

    result = messages_by_compaction(events)

    # No prefix segment, just the post-compaction segment
    assert len(result) == 1
    assert result[0][-1].text == "After trim"


def test_trim_prefix_id_matching() -> None:
    """Trim prefix is found via message id matching."""
    # Create messages with explicit IDs
    a = ChatMessageUser(content="Message A", id="id-a")
    b = ChatMessageUser(content="Message B", id="id-b")
    c = ChatMessageUser(content="Message C", id="id-c")
    d = ChatMessageUser(content="Message D", id="id-d")

    # Pre: [a, b, c, d], Post: [c, d, e] — a and b were trimmed
    e = ChatMessageUser(content="Message E", id="id-e")
    pre_msgs = [a, b, c, d]
    post_msgs = [c, d, e]

    events: list[Event] = [
        _make_model_event(input=pre_msgs, output_content="Before"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=post_msgs, output_content="After"),
    ]

    result = messages_by_compaction(events)

    assert len(result) == 2
    prefix = result[0]
    assert len(prefix) == 2
    assert prefix[0] is a
    assert prefix[1] is b


def test_no_events() -> None:
    """Empty event list produces empty result."""
    assert messages_by_compaction([]) == []


def test_no_model_events() -> None:
    """Only compaction events produce empty result."""
    events: list[Event] = [
        _make_compaction_event(type="summary"),
        _make_compaction_event(type="trim"),
    ]

    assert messages_by_compaction(events) == []
