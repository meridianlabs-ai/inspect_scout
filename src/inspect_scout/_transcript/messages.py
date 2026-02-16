"""Message extraction from events, with compaction boundary handling."""

from inspect_ai.event import CompactionEvent, Event, ModelEvent
from inspect_ai.model import ChatMessage


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
