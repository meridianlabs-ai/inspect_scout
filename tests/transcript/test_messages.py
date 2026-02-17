"""Tests for message extraction with compaction boundary handling."""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal

import pytest
from inspect_ai.event import CompactionEvent, Event, ModelEvent, ToolEvent
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    ModelOutput,
    get_model,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.model._model_output import ChatCompletionChoice
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.messages import (
    MessagesSegment,
    segment_messages,
    span_messages,
    transcript_messages,
)
from inspect_scout._transcript.timeline import (
    Timeline,
    TimelineEvent,
    TimelineMessages,
    TimelineSpan,
    timeline_messages,
)
from inspect_scout._transcript.types import Transcript


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


def _make_timeline_span(
    name: str,
    events: list[Event] | None = None,
    children: list[TimelineSpan] | None = None,
    *,
    utility: bool = False,
    span_id: str | None = None,
) -> TimelineSpan:
    """Helper to build a TimelineSpan with events and/or child spans."""
    content: list[TimelineEvent | TimelineSpan] = []
    if events:
        content.extend(TimelineEvent(event=e) for e in events)
    if children:
        content.extend(children)
    return TimelineSpan(
        id=span_id or f"span-{name}",
        name=name,
        span_type=None,
        content=content,
        utility=utility,
    )


# -- Shared messages for tests --

_sys = ChatMessageSystem(content="You are an assistant", id="sys-1")
_user1 = ChatMessageUser(content="Hello", id="u-1")
_user2 = ChatMessageUser(content="Continue", id="u-2")
_user3 = ChatMessageUser(content="Elaborate", id="u-3")
_asst1 = ChatMessageAssistant(content="Hi there", id="a-1")
_asst2 = ChatMessageAssistant(content="Here is more", id="a-2")


# -- span_messages tests --


def test_no_compaction() -> None:
    """Events with no compaction return messages from the last ModelEvent."""
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

    result = span_messages(events)

    # Last ModelEvent's input + output
    assert len(result) == 5  # sys, user1, asst1, user2, output
    assert result[0].role == "system"
    assert result[1] is _user1
    assert result[3] is _user2
    assert result[4].role == "assistant"
    assert result[4].text == "Second response"


def test_summary_compaction() -> None:
    """Summary compaction grafts pre + post messages into one merged list."""
    _u_sum = ChatMessageUser(content="Summary of prior", id="u-sum")
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
            input=[_sys, _u_sum],
            output_content="Post-compaction answer",
        ),
    ]

    result = span_messages(events)

    # Pre-compaction (last pre-compaction ModelEvent's input + output)
    # + post-compaction (input + output), all merged
    assert result[0].role == "system"
    assert result[1] is _user1
    assert result[2] is _asst1
    assert result[3] is _user2
    assert result[4].text == "More pre-compaction"  # pre output
    # Post-compaction segment grafted on
    assert result[5].role == "system"
    assert result[6] is _u_sum
    assert result[-1].text == "Post-compaction answer"  # post output


def test_trim_compaction() -> None:
    """Trim compaction merges trimmed prefix + post-compaction messages."""
    # Pre-compaction: [sys, u1, a1, u2] — full conversation
    # Post-compaction: [a1, u2, u3] — sys and u1 were trimmed
    pre_msgs: list[ChatMessage] = [_sys, _user1, _asst1, _user2]
    post_msgs: list[ChatMessage] = [_asst1, _user2, _user3]

    events: list[Event] = [
        _make_model_event(input=pre_msgs, output_content="Before trim"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=post_msgs, output_content="After trim"),
    ]

    result = span_messages(events)

    # Trimmed prefix [sys, u1] + post-compaction input [a1, u2, u3] + output
    assert result[0] is _sys
    assert result[1] is _user1
    assert result[2] is _asst1
    assert result[3] is _user2
    assert result[4] is _user3
    assert result[-1].text == "After trim"
    assert len(result) == 6  # prefix(2) + post input(3) + post output(1)


def test_edit_compaction() -> None:
    """Edit compaction is transparent — returns last ModelEvent's messages."""
    events: list[Event] = [
        _make_model_event(input=[_sys, _user1], output_content="Before edit"),
        _make_compaction_event(type="edit"),
        _make_model_event(
            input=[_sys, _user1, _asst1, _user2],
            output_content="After edit",
        ),
    ]

    result = span_messages(events)

    assert result[-1].text == "After edit"
    assert len(result) == 5  # sys, u1, a1, u2, output


def test_multiple_compactions() -> None:
    """Two summary compactions graft all three segments together."""
    events: list[Event] = [
        _make_model_event(input=[_user1], output_content="Seg 0"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user2], output_content="Seg 1"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user3], output_content="Seg 2"),
    ]

    result = span_messages(events)

    # All grafted: [u1, "Seg 0", u2, "Seg 1", u3, "Seg 2"]
    assert result[0] is _user1
    assert result[1].text == "Seg 0"
    assert result[2] is _user2
    assert result[3].text == "Seg 1"
    assert result[4] is _user3
    assert result[5].text == "Seg 2"
    assert len(result) == 6


def test_empty_segment_omitted() -> None:
    """No ModelEvents before a compaction boundary — nothing grafted."""
    events: list[Event] = [
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user1], output_content="Only segment"),
    ]

    result = span_messages(events)

    assert result[-1].text == "Only segment"
    assert len(result) == 2  # u1 + output


def test_non_model_events_ignored() -> None:
    """ToolEvents and other events are ignored."""
    events: list[Event] = [
        _make_tool_event(),
        _make_model_event(input=[_user1], output_content="Response"),
        _make_tool_event(),
    ]

    result = span_messages(events)

    assert result[-1].text == "Response"
    assert len(result) == 2


def test_trim_empty_prefix() -> None:
    """Trim where all messages survive — no prefix prepended."""
    msgs: list[ChatMessage] = [_sys, _user1]

    events: list[Event] = [
        _make_model_event(input=msgs, output_content="Before trim"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=msgs + [_user2], output_content="After trim"),
    ]

    result = span_messages(events)

    # No prefix, just the post-compaction messages
    assert result[-1].text == "After trim"
    assert result[0] is _sys
    assert result[1] is _user1
    assert result[2] is _user2


def test_trim_prefix_id_matching() -> None:
    """Trim prefix is found via message id matching."""
    a = ChatMessageUser(content="Message A", id="id-a")
    b = ChatMessageUser(content="Message B", id="id-b")
    c = ChatMessageUser(content="Message C", id="id-c")
    d = ChatMessageUser(content="Message D", id="id-d")
    e = ChatMessageUser(content="Message E", id="id-e")

    # Pre: [a, b, c, d], Post: [c, d, e] — a and b were trimmed
    events: list[Event] = [
        _make_model_event(input=[a, b, c, d], output_content="Before"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=[c, d, e], output_content="After"),
    ]

    result = span_messages(events)

    # prefix [a, b] + post [c, d, e] + output
    assert result[0] is a
    assert result[1] is b
    assert result[2] is c
    assert result[3] is d
    assert result[4] is e
    assert result[-1].text == "After"
    assert len(result) == 6


def test_no_events() -> None:
    """Empty event list produces empty result."""
    assert span_messages([]) == []


def test_no_model_events() -> None:
    """Only compaction events produce empty result."""
    events: list[Event] = [
        _make_compaction_event(type="summary"),
        _make_compaction_event(type="trim"),
    ]

    assert span_messages(events) == []


def test_span_messages_from_timeline_span() -> None:
    """Accepts TimelineSpan and extracts events from its content."""
    span = _make_timeline_span(
        "Agent",
        events=[
            _make_model_event(input=[_user1], output_content="From span"),
        ],
    )

    result = span_messages(span)

    assert result[0] is _user1
    assert result[-1].text == "From span"
    assert len(result) == 2


def test_span_messages_compaction_last() -> None:
    """compaction="last" returns only the last ModelEvent's messages."""
    events: list[Event] = [
        _make_model_event(input=[_user1], output_content="Seg 0"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user2], output_content="Seg 1"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user3], output_content="Final"),
    ]

    result = span_messages(events, compaction="last")

    # Only the last ModelEvent's input + output
    assert result[0] is _user3
    assert result[-1].text == "Final"
    assert len(result) == 2


def test_span_messages_compaction_last_with_trim() -> None:
    """compaction="last" ignores trim boundaries too."""
    pre_msgs: list[ChatMessage] = [_sys, _user1, _asst1, _user2]
    post_msgs: list[ChatMessage] = [_asst1, _user2, _user3]

    events: list[Event] = [
        _make_model_event(input=pre_msgs, output_content="Before"),
        _make_compaction_event(type="trim"),
        _make_model_event(input=post_msgs, output_content="After"),
    ]

    result = span_messages(events, compaction="last")

    # Only the last ModelEvent: post input + output
    assert result[0] is _asst1
    assert result[-1].text == "After"
    assert len(result) == 4  # a1, u2, u3, output


# -- segment_messages tests --


async def _collect(
    source: list[ChatMessage] | list[Event],
    *,
    context_window: int | None = None,
) -> list[MessagesSegment]:
    """Helper to collect all MessagesSegment from segment_messages."""
    model = get_model("mockllm/model")
    msgs_as_str, _ = message_numbering()
    results: list[MessagesSegment] = []
    async for seg in segment_messages(
        source,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=context_window,
    ):
        results.append(seg)
    return results


@pytest.mark.anyio
async def test_segment_messages_single_segment() -> None:
    """Small message list fits in budget → single MessagesSegment."""
    msgs: list[ChatMessage] = [_user1, _asst1, _user2]
    results = await _collect(msgs, context_window=10_000)

    assert len(results) == 1
    assert results[0].segment == 0
    assert len(results[0].messages) == 3
    assert results[0].messages[0] is _user1
    assert results[0].messages[1] is _asst1
    assert results[0].messages[2] is _user2


@pytest.mark.anyio
async def test_segment_messages_renders_text() -> None:
    """Rendered text contains [M1], [M2] etc. from message_numbering()."""
    msgs: list[ChatMessage] = [_user1, _asst1]
    results = await _collect(msgs, context_window=10_000)

    assert len(results) == 1
    text = results[0].text
    assert "[M1]" in text
    assert "[M2]" in text


@pytest.mark.anyio
async def test_segment_messages_with_events() -> None:
    """Events with compaction → merged via span_messages, then chunked."""
    events: list[Event] = [
        _make_model_event(input=[_user1], output_content="Seg 0"),
        _make_compaction_event(type="summary"),
        _make_model_event(input=[_user2], output_content="Seg 1"),
    ]
    results = await _collect(events, context_window=10_000)

    # Now produces a single merged segment (not two separate segments)
    assert len(results) == 1
    assert results[0].segment == 0
    # Contains messages from both pre and post compaction
    texts = [m.text for m in results[0].messages]
    assert "Hello" in texts  # _user1
    assert "Continue" in texts  # _user2


@pytest.mark.anyio
async def test_segment_messages_chunking() -> None:
    """Large messages exceeding budget → multiple chunks."""
    long_text = "word " * 100  # ~100 tokens
    msgs: list[ChatMessage] = [
        ChatMessageUser(content=long_text, id="long-1"),
        ChatMessageUser(content=long_text, id="long-2"),
        ChatMessageUser(content=long_text, id="long-3"),
    ]
    # Set budget so each message is its own segment (budget < single message tokens)
    # 80% of 50 = 40 tokens, each message is ~100+ tokens
    results = await _collect(msgs, context_window=50)

    assert len(results) == 3
    assert results[0].segment == 0
    assert results[1].segment == 1
    assert results[2].segment == 2
    assert len(results[0].messages) == 1
    assert len(results[1].messages) == 1
    assert len(results[2].messages) == 1


@pytest.mark.anyio
async def test_segment_messages_continuous_numbering() -> None:
    """Message numbering is continuous across chunks."""
    long_text = "word " * 100
    msgs: list[ChatMessage] = [
        ChatMessageUser(content=long_text, id="long-1"),
        ChatMessageUser(content=long_text, id="long-2"),
    ]
    results = await _collect(msgs, context_window=50)

    assert len(results) == 2
    assert "[M1]" in results[0].text
    assert "[M2]" in results[1].text


@pytest.mark.anyio
async def test_segment_messages_events_with_chunking() -> None:
    """Events with compaction merged then chunked by token budget."""
    long_text = "word " * 100
    events: list[Event] = [
        _make_model_event(
            input=[ChatMessageUser(content=long_text, id="a")],
            output_content=long_text,
        ),
        _make_compaction_event(type="summary"),
        _make_model_event(
            input=[ChatMessageUser(content=long_text, id="b")],
            output_content=long_text,
        ),
    ]
    results = await _collect(events, context_window=50)

    # Messages are merged then chunked — segment counter should be
    # monotonically increasing
    segments = [r.segment for r in results]
    assert segments == sorted(segments)
    assert len(set(segments)) == len(segments)  # All unique
    assert len(results) >= 2  # Merged messages should still exceed budget


@pytest.mark.anyio
async def test_segment_messages_empty_input() -> None:
    """Empty list yields nothing."""
    results = await _collect([], context_window=10_000)
    assert results == []


@pytest.mark.anyio
async def test_segment_messages_skips_empty_renders() -> None:
    """System messages excluded by default preprocessor are skipped."""
    msgs: list[ChatMessage] = [_sys, _user1]
    results = await _collect(msgs, context_window=10_000)

    assert len(results) == 1
    assert len(results[0].messages) == 1
    assert results[0].messages[0] is _user1
    assert "[M1]" in results[0].text


# -- timeline_messages tests --


async def _collect_timeline(
    timeline: Timeline | TimelineSpan,
    *,
    context_window: int = 10_000,
    include: object = None,
    depth: int | None = None,
) -> list[TimelineMessages]:
    """Helper to collect all TimelineMessages from timeline_messages."""
    model = get_model("mockllm/model")
    msgs_as_str, _ = message_numbering()
    results: list[TimelineMessages] = []
    async for seg in timeline_messages(
        timeline,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=context_window,
        include=include,  # type: ignore[arg-type]
        depth=depth,
    ):
        results.append(seg)
    return results


@pytest.mark.anyio
async def test_timeline_messages_single_span() -> None:
    """Single span with events → yields TimelineMessages with correct span."""
    span = _make_timeline_span(
        "Agent",
        events=[
            _make_model_event(input=[_user1], output_content="Response"),
        ],
    )
    results = await _collect_timeline(span)

    assert len(results) == 1
    assert isinstance(results[0], TimelineMessages)
    assert results[0].span is span
    assert "[M1]" in results[0].text


@pytest.mark.anyio
async def test_timeline_messages_nested_spans() -> None:
    """Child spans visited recursively in depth-first order."""
    child1 = _make_timeline_span(
        "Child1",
        events=[_make_model_event(input=[_user1], output_content="From child1")],
    )
    child2 = _make_timeline_span(
        "Child2",
        events=[_make_model_event(input=[_user2], output_content="From child2")],
    )
    root = _make_timeline_span("Root", children=[child1, child2])

    results = await _collect_timeline(root)

    assert len(results) == 2
    assert results[0].span is child1
    assert results[1].span is child2


@pytest.mark.anyio
async def test_timeline_messages_include_none_skips_utility() -> None:
    """Default filter skips utility spans."""
    utility_span = _make_timeline_span(
        "Helper",
        events=[_make_model_event(input=[_user1], output_content="Utility response")],
        utility=True,
    )
    normal_span = _make_timeline_span(
        "Agent",
        events=[_make_model_event(input=[_user2], output_content="Normal response")],
    )
    root = _make_timeline_span("Root", children=[utility_span, normal_span])

    results = await _collect_timeline(root)

    assert len(results) == 1
    assert results[0].span is normal_span


@pytest.mark.anyio
async def test_timeline_messages_include_none_skips_empty() -> None:
    """Default filter skips container spans with no direct ModelEvents."""
    child = _make_timeline_span(
        "Child",
        events=[_make_model_event(input=[_user1], output_content="Response")],
    )
    container = _make_timeline_span("Container", children=[child])

    results = await _collect_timeline(container)

    assert len(results) == 1
    assert results[0].span is child


@pytest.mark.anyio
async def test_timeline_messages_include_name() -> None:
    """String filter matches span name case-insensitively."""
    build_span = _make_timeline_span(
        "Build",
        events=[_make_model_event(input=[_user1], output_content="Building")],
    )
    test_span = _make_timeline_span(
        "Test",
        events=[_make_model_event(input=[_user2], output_content="Testing")],
    )
    root = _make_timeline_span("Root", children=[build_span, test_span])

    results = await _collect_timeline(root, include="build")

    assert len(results) == 1
    assert results[0].span is build_span


@pytest.mark.anyio
async def test_timeline_messages_include_callable() -> None:
    """Callable predicate filters spans."""
    agent_span = _make_timeline_span(
        "Agent",
        events=[_make_model_event(input=[_user1], output_content="Agent response")],
    )
    agent_span.span_type = "agent"
    other_span = _make_timeline_span(
        "Other",
        events=[_make_model_event(input=[_user2], output_content="Other response")],
    )
    root = _make_timeline_span("Root", children=[agent_span, other_span])

    results = await _collect_timeline(root, include=lambda s: s.span_type == "agent")

    assert len(results) == 1
    assert results[0].span is agent_span


@pytest.mark.anyio
async def test_timeline_messages_from_timeline_object() -> None:
    """Accepts Timeline (extracts .root)."""
    span = _make_timeline_span(
        "Agent",
        events=[_make_model_event(input=[_user1], output_content="Response")],
    )
    tl = Timeline(name="Default", description="", root=span)

    results = await _collect_timeline(tl)

    assert len(results) == 1
    assert results[0].span is span


@pytest.mark.anyio
async def test_timeline_messages_depth_1() -> None:
    """depth=1 processes only the root span, not children."""
    child = _make_timeline_span(
        "Child",
        events=[_make_model_event(input=[_user2], output_content="From child")],
    )
    root = _make_timeline_span(
        "Root",
        events=[_make_model_event(input=[_user1], output_content="From root")],
        children=[child],
    )

    results = await _collect_timeline(root, depth=1)

    assert len(results) == 1
    assert results[0].span is root


@pytest.mark.anyio
async def test_timeline_messages_depth_2() -> None:
    """depth=2 processes root + immediate children, not grandchildren."""
    grandchild = _make_timeline_span(
        "Grandchild",
        events=[_make_model_event(input=[_user3], output_content="From grandchild")],
    )
    child = _make_timeline_span(
        "Child",
        events=[_make_model_event(input=[_user2], output_content="From child")],
        children=[grandchild],
    )
    root = _make_timeline_span(
        "Root",
        events=[_make_model_event(input=[_user1], output_content="From root")],
        children=[child],
    )

    results = await _collect_timeline(root, depth=2)

    assert len(results) == 2
    assert results[0].span is root
    assert results[1].span is child


# -- transcript_messages tests --


@pytest.mark.anyio
async def test_transcript_messages_with_timelines() -> None:
    """Dispatches to timeline_messages when timelines present."""
    span = _make_timeline_span(
        "Agent",
        events=[_make_model_event(input=[_user1], output_content="Response")],
    )
    tl = Timeline(name="Default", description="", root=span)
    transcript = Transcript(
        transcript_id="t1",
        messages=[_user1],
        timelines=[tl],
    )

    model = get_model("mockllm/model")
    msgs_as_str, _ = message_numbering()
    results: list[MessagesSegment] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=10_000,
    ):
        results.append(seg)

    assert len(results) == 1
    assert isinstance(results[0], TimelineMessages)


@pytest.mark.anyio
async def test_transcript_messages_with_events() -> None:
    """Dispatches to segment_messages with events."""
    events: list[Event] = [
        _make_model_event(input=[_user1], output_content="Response"),
    ]
    transcript = Transcript(
        transcript_id="t2",
        messages=[_user1],
        events=events,
    )

    model = get_model("mockllm/model")
    msgs_as_str, _ = message_numbering()
    results: list[MessagesSegment] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=10_000,
    ):
        results.append(seg)

    assert len(results) == 1
    assert not isinstance(results[0], TimelineMessages)


@pytest.mark.anyio
async def test_transcript_messages_with_messages_only() -> None:
    """Dispatches to segment_messages with messages."""
    transcript = Transcript(
        transcript_id="t3",
        messages=[_user1, _asst1],
    )

    model = get_model("mockllm/model")
    msgs_as_str, _ = message_numbering()
    results: list[MessagesSegment] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=10_000,
    ):
        results.append(seg)

    assert len(results) == 1
    assert not isinstance(results[0], TimelineMessages)
