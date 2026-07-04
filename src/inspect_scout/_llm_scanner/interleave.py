"""Chronological interleaving of non-message events into the message list."""

from typing import AsyncIterator

from inspect_ai.event import CompactionEvent, Event, ModelEvent
from inspect_ai.model import ChatMessage

from .._scanner.util import _event_id, _message_id
from .._transcript.handle import TranscriptHandle
from .._transcript.interleave import (
    _NON_INTERLEAVED,
    Compaction,
    EventsSpec,
    _AnchorWalk,
    _event_message,
    _interleavable_text,
    _model_output_id,
    _scorers_model_event_ids,
)
from .._transcript.messages import span_messages
from .._transcript.types import Transcript

__all__ = [
    "EventsSpec",
    "Compaction",
    "_NON_INTERLEAVED",
    "_interleavable_text",
    "_event_message",
    "_model_output_id",
    "_AnchorWalk",
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

    Each event is anchored after the most recent preceding assistant message
    (the output of the most recent ``ModelEvent`` whose message is present in
    ``transcript.messages``). Events with no preceding turn are prepended.
    A ``ModelEvent`` whose output never joined the thread (a fork/branch
    experiment, or a retry) is off-thread and renders instead as an always-on
    ``[E#] MODEL (BRANCH):`` entry, anchored at the current position -- see
    ``_AnchorWalk``/``_off_thread_model_text`` (``_transcript/interleave.py``).

    When the transcript carries no top-level messages (events-only loads),
    the message thread is reconstructed from model events via
    ``span_messages`` (honoring ``compaction``) and events are spliced into
    the reconstructed thread.

    Grader model calls (``ModelEvent``s nested under a top-level ``scorers``
    span, if the event list carries span structure) are excluded from the
    walk entirely -- they neither render as branch entries nor advance the
    anchor -- preserving the invariant that scorer/grader activity never
    surfaces in scanned content (see ``_scorers_model_event_ids``).

    Warning:
        The events-only reconstruction (``span_messages``) assumes a single
        linear conversation: it keeps only the region-last ``ModelEvent``
        per compaction region, and nested ``ToolEvent.events`` subagents are
        not walked. With multiple parallel agents (or tool-spawned
        subagents), this silently drops every agent but the last from the
        reconstructed thread -- though each off-thread agent's model
        outputs still surface individually as ``[E#] MODEL (BRANCH):``
        entries rather than vanishing, their original conversational
        context is not recovered. Such transcripts must go through the
        timeline machinery instead (see ``inspect_scout._transcript.timeline``
        / ``timeline_stream``), which reconstructs per-span segments so
        every agent is visible with its own context. ``llm_scanner`` routes
        events-only transcripts there automatically and never reaches this
        fallback for multi-agent input.

    Args:
        transcript: Transcript providing messages and events.
        events: Which event types to interleave (``"all"`` or a list).
        compaction: Compaction handling for events-only thread reconstruction.
    """
    messages = list(transcript.messages)
    if not transcript.events:
        return messages
    if not messages:
        messages = span_messages(transcript.events, compaction=compaction)

    excluded = _scorers_model_event_ids(transcript.events)
    walk = _AnchorWalk([_message_id(m) for m in messages], events)
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

    Yields the same message sequence ``interleave_events`` would produce for
    the materialized transcript, without holding messages and event payloads
    in memory at once.

    Messages-present transcripts take three passes over the handle
    (multi-shot contract): collect message ids, run the anchor walk
    (retaining just id + rendered text per selected event), then re-stream
    messages splicing anchored entries. Retained memory is one id per
    message plus the rendered text of selected events.

    Events-only transcripts (empty ``messages()``) reconstruct the thread
    from model events in a single events pass: only the most recent
    ``ModelEvent`` per compaction region is retained (that event's input
    already carries the region's conversation — the thread itself), plus a
    small op log of output-message ids and rendered entries so anchors
    resolve against the reconstructed thread in event order.

    Warning:
        The events-only reconstruction above assumes a single linear
        conversation: keeping only the region-last ``ModelEvent`` per
        compaction region silently drops every agent but the last when
        multiple parallel agents are present, and nested
        ``ToolEvent.events`` subagents are never walked. Such transcripts
        must go through the timeline machinery instead (see
        ``inspect_scout._transcript.timeline_stream.stream_timeline_messages``),
        which reconstructs per-span segments so every agent is visible.
        ``llm_scanner`` routes events-only transcripts there automatically
        and never reaches this fallback for multi-agent input.
    """
    message_ids = [_message_id(m) async for m in handle.messages()]
    types = None if events == "all" else ["model", "compaction", *events]

    if message_ids:
        walk = _AnchorWalk(message_ids, events)
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

    # Events-only: reconstruct the thread from model events. `skeleton`
    # keeps compaction events plus the most recent ModelEvent per region
    # (span_messages only reads the region-last event); `ops` records the
    # anchor walk's inputs in event order for replay once the thread exists.
    # Each op is (kind, a, b): ("m", output_message_id, "") for a model
    # event, ("e", event_id, rendered_text) for an interleavable event.
    skeleton: list[Event] = []
    ops: list[tuple[str, str, str]] = []
    async for event in handle.events(types=types):
        if isinstance(event, ModelEvent):
            mid = _model_output_id(event)
            if mid is not None:
                ops.append(("m", mid, ""))
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
    walk = _AnchorWalk([_message_id(m) for m in thread], events)
    for kind, a, b in ops:
        if kind == "m":
            walk.add_model_output(a)
        else:
            walk.add_rendered(a, b)

    for event_id, text in walk.leading:
        yield _event_message(event_id, text)
    for index, message in enumerate(thread):
        yield message
        for event_id, text in walk.anchored.get(index, []):
            yield _event_message(event_id, text)
