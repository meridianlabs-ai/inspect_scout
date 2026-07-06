"""Chronological interleaving of non-message events into the message list."""

from typing import AsyncIterator

from inspect_ai.event import CompactionEvent, Event, ModelEvent
from inspect_ai.model import ChatMessage

from .._scanner.util import _event_id, _message_id
from .._transcript.handle import TranscriptHandle
from .._transcript.interleave import (
    Compaction,
    EventsSpec,
    _AnchorWalk,
    _compaction_excluded_ids,
    _event_message,
    _interleavable_text,
    _model_output_id,
    _off_thread_model_text,
    _scorers_model_event_ids,
)
from .._transcript.messages import span_messages
from .._transcript.types import Transcript

__all__ = [
    "EventsSpec",
    "Compaction",
    "has_interleavable_events",
    "interleave_events",
    "stream_interleave_events",
]


def has_interleavable_events(
    transcript: Transcript, events: EventsSpec = "all"
) -> bool:
    return any(_interleavable_text(e, events) is not None for e in transcript.events)


def interleave_events(
    transcript: Transcript,
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> list[ChatMessage]:
    """Splice loaded non-message events into ``transcript.messages``.

    Each event is anchored after the most recent preceding assistant turn;
    events with no preceding turn are prepended. A ``ModelEvent`` whose
    output never joined the thread renders as a ``[E#] MODEL (BRANCH):``
    entry unless the turn was compaction-pruned, in which case it stays
    hidden (see ``_AnchorWalk``). Grader model calls under a ``scorers``
    span are excluded from the walk entirely.

    When the transcript has no top-level messages (events-only loads), the
    thread is reconstructed from model events via ``span_messages``
    (honoring ``compaction``).

    Warning:
        The events-only reconstruction assumes a single linear
        conversation; with multiple parallel agents it drops every agent
        but the last from the thread (their outputs surface only as branch
        entries). Multi-agent transcripts must use the timeline machinery
        instead; ``llm_scanner`` routes them there automatically.

    Args:
        transcript: Transcript providing messages and events.
        events: Which event types to interleave (``"all"`` or a list).
        compaction: Compaction handling for events-only thread reconstruction.
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages
    excluded_ids: frozenset[str] = frozenset()
    if messages:
        # `messages` is the transcript's own live thread, already shaped by
        # the original run's compaction (the `compaction` argument only
        # governs events-only reconstruction below). The "last" sentinel
        # forces `_compaction_excluded_ids` past its `"all"` fast path.
        if any(isinstance(e, CompactionEvent) for e in transcript.events):
            excluded_ids = _compaction_excluded_ids(
                transcript.events,
                (_message_id(m) for m in messages),
                compaction="last",
            )
    else:
        messages = span_messages(transcript.events, compaction=compaction)
        excluded_ids = _compaction_excluded_ids(
            transcript.events, (_message_id(m) for m in messages), compaction
        )

    excluded = _scorers_model_event_ids(transcript.events)
    walk = _AnchorWalk(
        [_message_id(m) for m in messages], events, excluded_ids=excluded_ids
    )
    for event in transcript.events:
        if excluded and _event_id(event) in excluded:
            continue
        walk.add(event)

    result: list[ChatMessage] = [
        _event_message(event_id, text) for event_id, text in walk.leading
    ]
    for index, message in enumerate(messages):
        result.append(message)
        for event_id, text in walk.anchored.get(index, []):
            result.append(_event_message(event_id, text))
    return result


async def stream_interleave_events(
    handle: TranscriptHandle,
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> AsyncIterator[ChatMessage]:
    """Streaming counterpart to ``interleave_events`` over a handle.

    Yields the same message sequence ``interleave_events`` would produce,
    without holding messages and event payloads in memory at once.

    Messages-present transcripts take four passes over the handle: collect
    message ids; derive compaction-pruned ``excluded_ids`` from a
    region-last-``ModelEvent`` skeleton (cheap no-op when there is no
    ``CompactionEvent``); the anchor walk (retaining just id + rendered
    text per selected event); then re-stream messages splicing anchored
    entries.

    Events-only transcripts reconstruct the thread in a single events pass,
    retaining only the region-last ``ModelEvent`` (whose input carries the
    region's conversation) plus an op log of output-message ids and
    pre-rendered branch text, replayed against the reconstructed thread.

    Warning:
        The events-only reconstruction assumes a single linear
        conversation; multi-agent transcripts must use
        ``stream_timeline_messages`` instead (``llm_scanner`` routes them
        there automatically).
    """
    message_ids = [_message_id(m) async for m in handle.messages()]
    types = None if events == "all" else ["model", "compaction", *events]

    if message_ids:
        # Build a region-last-ModelEvent skeleton (as in the events-only
        # branch below) solely to derive compaction-pruned `excluded_ids`.
        # Without a CompactionEvent this pass costs only the filtered scan.
        excluded_ids: frozenset[str] = frozenset()
        compaction_skeleton: list[Event] = []
        saw_compaction = False
        async for event in handle.events(types=["model", "compaction"]):
            if isinstance(event, CompactionEvent):
                saw_compaction = True
                compaction_skeleton.append(event)
            elif compaction_skeleton and isinstance(
                compaction_skeleton[-1], ModelEvent
            ):
                compaction_skeleton[-1] = event
            else:
                compaction_skeleton.append(event)
        if saw_compaction:
            excluded_ids = _compaction_excluded_ids(
                compaction_skeleton, message_ids, compaction="last"
            )

        walk = _AnchorWalk(message_ids, events, excluded_ids=excluded_ids)
        async for event in handle.events(types=types):
            walk.add(event)

        for event_id, text in walk.leading:
            yield _event_message(event_id, text)
        index = 0
        async for message in handle.messages():
            yield message
            for event_id, text in walk.anchored.get(index, []):
                yield _event_message(event_id, text)
            index += 1
        return

    # Events-only: `skeleton` keeps compaction events plus the region-last
    # ModelEvent (all span_messages reads); `ops` records the anchor walk's
    # inputs for replay once the thread exists: ("m", output_message_id,
    # rendered_branch_text_or_"") or ("e", event_id, rendered_text).
    skeleton: list[Event] = []
    ops: list[tuple[str, str, str]] = []
    async for event in handle.events(types=types):
        if isinstance(event, ModelEvent):
            mid = _model_output_id(event)
            if mid is not None:
                ops.append(("m", mid, _off_thread_model_text(event) or ""))
            if skeleton and isinstance(skeleton[-1], ModelEvent):
                skeleton[-1] = event
            else:
                skeleton.append(event)
        elif isinstance(event, CompactionEvent):
            skeleton.append(event)
        else:
            rendered = _interleavable_text(event, events)
            if rendered is not None:
                ops.append(("e", _event_id(event), rendered))

    thread = span_messages(skeleton, compaction=compaction)
    excluded_ids = _compaction_excluded_ids(
        skeleton, (_message_id(m) for m in thread), compaction
    )

    walk = _AnchorWalk(
        [_message_id(m) for m in thread], events, excluded_ids=excluded_ids
    )
    for kind, a, b in ops:
        if kind == "m":
            consumed = walk.add_model_output(a)
            if not consumed and a not in excluded_ids and b:
                walk.add_rendered(a, b)
        else:
            walk.add_rendered(a, b)

    for event_id, text in walk.leading:
        yield _event_message(event_id, text)
    for index, message in enumerate(thread):
        yield message
        for event_id, text in walk.anchored.get(index, []):
            yield _event_message(event_id, text)
