"""Chronological interleaving of non-message events into the message list."""

from collections import defaultdict

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import ChatMessage, ChatMessageUser

from .._scanner.extract import EVENT_MARKER_KEY
from .._scanner.util import _event_id, _message_id
from .._transcript.event_text import event_as_str
from .._transcript.types import Transcript

# Events that already appear in the message thread (model, tool) or are pure
# structure are never rendered as [E#] entries.
_NON_INTERLEAVED: frozenset[str] = frozenset(
    {"model", "tool", "compaction", "span_begin", "span_end"}
)


def _is_interleavable(event: Event) -> bool:
    return event.event not in _NON_INTERLEAVED and event_as_str(event) is not None


def _event_message(event: Event) -> ChatMessage:
    return ChatMessageUser(
        id=_event_id(event),
        content=event_as_str(event) or "",
        metadata={EVENT_MARKER_KEY: True},
    )


def has_interleavable_events(transcript: Transcript) -> bool:
    return any(_is_interleavable(e) for e in transcript.events)


def interleave_events(transcript: Transcript) -> list[ChatMessage]:
    """Splice loaded non-message events into ``transcript.messages``.

    Each event is anchored after the most recent preceding assistant message
    (the output of the most recent ``ModelEvent`` whose message is present in
    ``transcript.messages``). Events with no preceding turn are prepended.
    """
    messages = list(transcript.messages)
    if not messages or not transcript.events:
        return messages

    # Anchoring assumes a ModelEvent's output message id matches the same
    # message in transcript.messages (the invariant Inspect logs satisfy). If
    # those ids ever diverge, the event finds no anchor and is prepended
    # (leading) rather than misplaced mid-thread.
    rendered_ids = {_message_id(m) for m in messages}

    leading: list[Event] = []
    anchors: dict[str, list[Event]] = defaultdict(list)
    last_anchor: str | None = None
    for event in transcript.events:
        if isinstance(event, ModelEvent):
            out = event.output
            if out and out.choices and out.choices[0].message is not None:
                mid = _message_id(out.choices[0].message)
                if mid in rendered_ids:
                    last_anchor = mid
            continue
        if not _is_interleavable(event):
            continue
        if last_anchor is None:
            leading.append(event)
        else:
            anchors[last_anchor].append(event)

    result: list[ChatMessage] = [_event_message(e) for e in leading]
    for message in messages:
        result.append(message)
        for event in anchors.get(_message_id(message), []):
            result.append(_event_message(event))
    return result
