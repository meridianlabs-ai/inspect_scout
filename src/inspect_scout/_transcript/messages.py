"""Message extraction from events, with compaction boundary handling."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from inspect_ai._util._async import tg_collect
from inspect_ai.event import CompactionEvent, Event, ModelEvent
from inspect_ai.model import ChatMessage, Model
from inspect_ai.model._chat_message import ChatMessageBase
from inspect_ai.model._model_info import get_model_info

from inspect_scout._scanner.extract import MessagesAsStr
from inspect_scout._transcript.timeline import TimelineEvent, TimelineSpan

if TYPE_CHECKING:
    from inspect_scout._transcript.types import Transcript

DEFAULT_CONTEXT_WINDOW = 128_000
_BUDGET_DISCOUNT = 0.8


@dataclass(frozen=True)
class MessagesSegment:
    """A segment of rendered messages that fits within a token budget.

    Attributes:
        messages: The original ChatMessage objects in this segment.
        text: Pre-rendered string from messages_as_str.
        segment: 0-based segment index, auto-increments across yields.
    """

    messages: list[ChatMessage]
    text: str
    segment: int


async def segment_messages(
    source: list[ChatMessage] | list[Event] | TimelineSpan,
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
    compaction: Literal["all", "last"] = "all",
) -> AsyncIterator[MessagesSegment]:
    """Render messages and split them into segments that fit within a token budget.

    Renders each message individually via ``messages_as_str``, counts
    tokens in parallel via ``tg_collect``, then accumulates segments that
    fit within the effective budget (context window * 80%).

    When given events or a ``TimelineSpan``, delegates to
    ``span_messages()`` to extract and merge messages (handling
    compaction boundaries), then segments the result.

    Args:
        source: A list of ChatMessage, a list of Event, or a
            TimelineSpan. Events and spans are processed via
            ``span_messages()`` first.
        messages_as_str: Rendering function from ``message_numbering()``.
            Must be called sequentially to preserve counter ordering.
        model: Model used for token counting.
        context_window: Override for context window size. If None,
            looked up via ``get_model_info(model)``.
        compaction: How to handle compaction boundaries when source
            contains events. Passed through to ``span_messages()``.

    Yields:
        MessagesSegment instances, each fitting within the token budget.
        Segment counter increments across all yields.
    """
    # Resolve source to a flat message list
    if isinstance(source, TimelineSpan):
        messages = span_messages(source, compaction=compaction)
    elif source and isinstance(source[0], ChatMessageBase):
        messages = list(source)  # type: ignore[arg-type]
    elif source:
        messages = span_messages(source, compaction=compaction)  # type: ignore[arg-type]
    else:
        messages = []

    if not messages:
        return

    # Compute effective budget
    if context_window is not None:
        budget = context_window
    else:
        model_info = get_model_info(model)
        budget = (
            model_info.input_tokens
            if model_info is not None and model_info.input_tokens is not None
            else DEFAULT_CONTEXT_WINDOW
        )
    effective_budget = int(budget * _BUDGET_DISCOUNT)

    # Pass 1: Render each message sequentially (counter ordering matters)
    rendered: list[tuple[ChatMessage, str]] = []
    for msg in messages:
        text = await messages_as_str([msg])
        if text:  # Skip empty renders (e.g. filtered system messages)
            rendered.append((msg, text))

    if not rendered:
        return

    # Pass 2: Count tokens in parallel
    token_counts = await tg_collect(
        [lambda t=text: model.count_tokens(t) for _, text in rendered]  # type: ignore[misc]
    )

    # Pass 3: Segment based on accumulated token counts
    segment_counter = 0
    current_messages: list[ChatMessage] = []
    current_texts: list[str] = []
    running_tokens = 0

    for (msg, text), tokens in zip(rendered, token_counts, strict=False):
        if current_messages and running_tokens + tokens > effective_budget:
            yield MessagesSegment(
                messages=current_messages,
                text="\n".join(current_texts),
                segment=segment_counter,
            )
            segment_counter += 1
            current_messages = []
            current_texts = []
            running_tokens = 0

        current_messages.append(msg)
        current_texts.append(text)
        running_tokens += tokens

    # Yield remaining segment
    if current_messages:
        yield MessagesSegment(
            messages=current_messages,
            text="\n".join(current_texts),
            segment=segment_counter,
        )


async def transcript_messages(
    transcript: "Transcript",
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
    compaction: Literal["all", "last"] = "all",
    depth: int | None = None,
) -> AsyncIterator[MessagesSegment]:
    """Yield pre-rendered message segments from a transcript.

    Automatically selects the best extraction strategy based on
    what data is available on the transcript:

    - If timelines are present, delegates to ``timeline_messages()``
    - If events are present (no timelines), delegates to
      ``segment_messages()`` with compaction handling
    - If only messages are present, delegates to ``segment_messages()``
      for context window segmentation only

    Since ``TimelineMessages`` is structurally compatible with
    ``MessagesSegment``, callers get a uniform interface. Those needing
    span context can isinstance-check for ``TimelineMessages``.

    Args:
        transcript: The transcript to extract messages from.
        messages_as_str: Rendering function from ``message_numbering()``.
        model: The model used for scanning.
        context_window: Override for the model's context window size.
        compaction: How to handle compaction boundaries when extracting
            messages from events.
        depth: Maximum depth of the span tree to process when timelines
            are present. Ignored for events-only or messages-only paths.

    Yields:
        ``MessagesSegment`` (or ``TimelineMessages``) for each segment.
    """
    if transcript.timelines:
        from inspect_scout._transcript.timeline import timeline_messages

        async for timeline_seg in timeline_messages(
            transcript.timelines[0],
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            compaction=compaction,
            depth=depth,
        ):
            yield timeline_seg  # type: ignore[misc]
    elif transcript.events:
        async for seg in segment_messages(
            transcript.events,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            compaction=compaction,
        ):
            yield seg
    else:
        async for seg in segment_messages(
            transcript.messages,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
        ):
            yield seg


def span_messages(
    source: TimelineSpan | list[Event],
    *,
    compaction: Literal["all", "last"] = "all",
) -> list[ChatMessage]:
    """Extract messages from a span or event list, handling compaction.

    Filters for ``ModelEvent`` and ``CompactionEvent``, then merges
    messages into a single list based on the ``compaction`` strategy.

    Args:
        source: A ``TimelineSpan`` (events extracted from its content)
            or a raw list of events. Non-Model/Compaction events are
            ignored.
        compaction: How to handle compaction boundaries:
            - ``"all"``: merge across boundaries for full coverage.
              Summary grafts pre + post messages. Trim prepends the
              trimmed prefix. Edit is transparent.
            - ``"last"``: ignore compaction history, return only the
              last ``ModelEvent``'s input + output.

    Returns:
        Merged message list. Empty if no ``ModelEvent`` is found.
    """
    # Extract events from TimelineSpan if needed
    if isinstance(source, TimelineSpan):
        events = [
            item.event for item in source.content if isinstance(item, TimelineEvent)
        ]
    else:
        events = source

    # Filter to ModelEvents and CompactionEvents
    model_events: list[ModelEvent] = []
    for event in events:
        if isinstance(event, ModelEvent):
            model_events.append(event)

    if not model_events:
        return []

    # "last" mode: just return the final ModelEvent's messages
    if compaction == "last":
        return _segment_messages(model_events[-1])

    # "all" mode: merge across compaction boundaries
    merged: list[ChatMessage] = []
    current_model_events: list[ModelEvent] = []
    pending_trim_pre_input: list[ChatMessage] | None = None

    for event in events:
        if isinstance(event, ModelEvent):
            # If we have a pending trim, compute prefix now that we have
            # the first post-compaction ModelEvent
            if pending_trim_pre_input is not None:
                prefix = _trim_prefix(pending_trim_pre_input, list(event.input))
                merged.extend(prefix)
                pending_trim_pre_input = None

            current_model_events.append(event)

        elif isinstance(event, CompactionEvent):
            if event.type == "summary":
                # Graft pre-compaction messages onto the merged list
                if current_model_events:
                    merged.extend(_segment_messages(current_model_events[-1]))
                current_model_events = []

            elif event.type == "trim":
                # Save pre-compaction input for prefix extraction
                if current_model_events:
                    pending_trim_pre_input = list(current_model_events[-1].input)
                current_model_events = []

            # Edit: no action, continue accumulating

    # Append final segment
    if current_model_events:
        merged.extend(_segment_messages(current_model_events[-1]))

    return merged


def _segment_messages(model_event: ModelEvent) -> list[ChatMessage]:
    """Extract the conversation from a ModelEvent.

    Returns the model's input messages plus its output message
    (the assistant's response).

    Args:
        model_event: The ModelEvent to extract messages from.

    Returns:
        List of messages: input + output assistant message.
        Returns just the input if output is unavailable.
    """
    messages = list(model_event.input)
    if (
        model_event.output is not None
        and model_event.output.choices
        and model_event.output.choices[0].message is not None
    ):
        messages.append(model_event.output.choices[0].message)
    return messages


def _trim_prefix(
    pre_input: list[ChatMessage],
    post_input: list[ChatMessage],
) -> list[ChatMessage]:
    """Compute the messages trimmed by a trim compaction.

    Finds the overlap point between pre-compaction and post-compaction
    inputs, returning the prefix of pre-compaction messages that were
    dropped.

    Uses message ``id`` fields for matching. Falls back to content
    equality (``message.text``) when IDs don't match.

    Args:
        pre_input: Full conversation before trim compaction.
        post_input: Trimmed conversation after trim compaction.

    Returns:
        Messages from pre_input that were dropped by the trim.
        Empty list if no prefix was trimmed or inputs can't be aligned.
    """
    if not post_input or not pre_input:
        return []

    # Try matching by message id
    first_post_id = post_input[0].id
    if first_post_id is not None:
        for i, msg in enumerate(pre_input):
            if msg.id == first_post_id:
                return pre_input[:i]

    # Fall back to content equality: find the first message in pre_input
    # whose text matches the first post_input message
    first_post_text = post_input[0].text
    for i, msg in enumerate(pre_input):
        if msg.text == first_post_text and msg.role == post_input[0].role:
            return pre_input[:i]

    return []
