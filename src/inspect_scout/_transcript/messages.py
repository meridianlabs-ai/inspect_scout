"""Message extraction from events, with compaction boundary handling."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from inspect_ai._util._async import tg_collect
from inspect_ai.event import CompactionEvent, Event, ModelEvent
from inspect_ai.model import ChatMessage, Model
from inspect_ai.model._chat_message import ChatMessageBase
from inspect_ai.model._model_info import get_model_info

from inspect_scout._scanner.extract import MessagesAsStr

DEFAULT_CONTEXT_WINDOW = 128_000
_BUDGET_DISCOUNT = 0.8


@dataclass(frozen=True)
class MessagesChunk:
    """A chunk of rendered messages that fits within a token budget.

    Attributes:
        messages: The original ChatMessage objects in this chunk.
        text: Pre-rendered string from messages_as_str.
        segment: 0-based segment index, auto-increments across yields.
    """

    messages: list[ChatMessage]
    text: str
    segment: int


async def chunked_messages(
    source: list[ChatMessage] | list[Event],
    *,
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None = None,
) -> AsyncIterator[MessagesChunk]:
    """Render messages and chunk them to fit within a token budget.

    Renders each message individually via ``messages_as_str``, counts
    tokens in parallel via ``tg_collect``, then accumulates chunks that
    fit within the effective budget (context window * 80%).

    When given events, delegates to ``messages_by_compaction()`` first
    to split at compaction boundaries, then chunks each segment
    independently.

    Args:
        source: Either a list of ChatMessage or a list of Event.
            Events are split via ``messages_by_compaction()`` first.
        messages_as_str: Rendering function from ``message_numbering()``.
            Must be called sequentially to preserve counter ordering.
        model: Model used for token counting.
        context_window: Override for context window size. If None,
            looked up via ``get_model_info(model)``.

    Yields:
        MessagesChunk chunks, each fitting within the token budget.
        Segment counter increments across all yields.
    """
    # Determine segments
    if source and isinstance(source[0], ChatMessageBase):
        segments: list[list[ChatMessage]] = [source]  # type: ignore[list-item]
    elif source:
        segments = messages_by_compaction(source)  # type: ignore[arg-type]
    else:
        segments = []

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

    segment_counter = 0

    for segment in segments:
        if not segment:
            continue

        # Pass 1: Render each message sequentially (counter ordering matters)
        rendered: list[tuple[ChatMessage, str]] = []
        for msg in segment:
            text = await messages_as_str([msg])
            if text:  # Skip empty renders (e.g. filtered system messages)
                rendered.append((msg, text))

        if not rendered:
            continue

        # Pass 2: Count tokens in parallel
        token_counts = await tg_collect(
            [lambda t=text: model.count_tokens(t) for _, text in rendered]  # type: ignore[misc]
        )

        # Pass 3: Chunk based on accumulated token counts
        chunk_messages: list[ChatMessage] = []
        chunk_texts: list[str] = []
        running_tokens = 0

        for (msg, text), tokens in zip(rendered, token_counts, strict=False):
            if chunk_messages and running_tokens + tokens > effective_budget:
                # Yield current chunk
                yield MessagesChunk(
                    messages=chunk_messages,
                    text="\n".join(chunk_texts),
                    segment=segment_counter,
                )
                segment_counter += 1
                chunk_messages = []
                chunk_texts = []
                running_tokens = 0

            chunk_messages.append(msg)
            chunk_texts.append(text)
            running_tokens += tokens

        # Yield remaining chunk
        if chunk_messages:
            yield MessagesChunk(
                messages=chunk_messages,
                text="\n".join(chunk_texts),
                segment=segment_counter,
            )
            segment_counter += 1


def messages_by_compaction(events: list[Event]) -> list[list[ChatMessage]]:
    """Split events into message lists at compaction boundaries.

    Filters for ModelEvent and CompactionEvent, then splits based on
    compaction type:
    - Summary: full split — each segment uses its last ModelEvent's
      input + output
    - Trim: prefix split — yields trimmed prefix (dropped messages)
      as a separate segment, followed by the post-compaction segment
    - Edit: ignored — no split

    Each segment's messages come from the **last** ModelEvent in that
    segment: ``input + [output.choices[0].message]``.

    Args:
        events: Events to process (non-Model/Compaction events are
            ignored).

    Returns:
        List of message lists, one per segment. Empty segments
        (no ModelEvents before a compaction boundary, or empty trim
        prefix) are omitted.
    """
    segments: list[list[ChatMessage]] = []
    current_model_events: list[ModelEvent] = []
    # For trim compaction, we need to know the first post-compaction ModelEvent
    pending_trim_pre_input: list[ChatMessage] | None = None

    for event in events:
        if isinstance(event, ModelEvent):
            # If we have a pending trim, compute prefix now that we have
            # the first post-compaction ModelEvent
            if pending_trim_pre_input is not None:
                prefix = _trim_prefix(pending_trim_pre_input, list(event.input))
                if prefix:
                    segments.append(prefix)
                pending_trim_pre_input = None

            current_model_events.append(event)

        elif isinstance(event, CompactionEvent):
            if event.type == "summary":
                # Full split: flush current segment, start fresh
                if current_model_events:
                    messages = _segment_messages(current_model_events[-1])
                    if messages:
                        segments.append(messages)
                current_model_events = []

            elif event.type == "trim":
                # Prefix split: save pre-compaction input for comparison
                # with the first post-compaction ModelEvent
                if current_model_events:
                    pending_trim_pre_input = list(current_model_events[-1].input)
                current_model_events = []

            # Edit: no split, continue accumulating

    # Flush final segment
    if current_model_events:
        messages = _segment_messages(current_model_events[-1])
        if messages:
            segments.append(messages)

    return segments


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
