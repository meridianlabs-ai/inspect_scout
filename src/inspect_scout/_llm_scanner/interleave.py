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

    Each event is anchored after the most recent preceding assistant message
    (the output of the most recent ``ModelEvent`` whose message is present in
    ``transcript.messages``). Events with no preceding turn are prepended.
    A ``ModelEvent`` whose output never joined the thread splits into two
    cases (see ``_AnchorWalk``'s ``excluded_ids`` discriminator,
    ``_transcript/interleave.py``): a genuine fork/branch experiment (or a
    retry whose output never joined any thread) renders as an always-on
    ``[E#] MODEL (BRANCH):`` entry, anchored at the current position; a
    turn that ``compaction`` deliberately pruned (present in the
    untruncated ``compaction="all"`` thread but not the current one) stays
    hidden instead, honoring the caller's compaction request rather than
    resurrecting it as a fork.

    When the transcript carries top-level messages, those messages ARE the
    current thread; the untruncated ``compaction="all"`` reconstruction
    (from ``transcript.events``) needed to derive the excluded-ids set above
    is only computed when ``transcript.events`` actually contains a
    ``CompactionEvent`` (a cheap check) -- transcripts with no compaction
    history pay no extra cost and get an empty excluded-ids set, exactly as
    before this discriminator existed.

    When the transcript carries no top-level messages (events-only loads),
    the message thread is reconstructed from model events via
    ``span_messages`` (honoring ``compaction``); when ``compaction`` is not
    ``"all"``, the untruncated ``compaction="all"`` reconstruction is also
    computed to derive the excluded-ids set above. Events are then spliced
    into the (possibly truncated) reconstructed thread.

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
    excluded_ids: frozenset[str] = frozenset()
    if messages:
        # `compaction` doesn't apply here -- `messages` is the transcript's
        # own live thread, already shaped by whatever compaction the
        # original run applied, independent of this function's `compaction`
        # argument (which only governs events-only reconstruction below).
        # Compute the exclusion set unconditionally whenever the events
        # actually contain a CompactionEvent (cheap presence check); a
        # `compaction="last"` sentinel (rather than the real, irrelevant
        # `compaction` argument) forces `_compaction_excluded_ids` past its
        # own `compaction == "all"` fast path so the computation actually
        # runs -- see that function's docstring.
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

    Yields the same message sequence ``interleave_events`` would produce for
    the materialized transcript, without holding messages and event payloads
    in memory at once.

    Messages-present transcripts take four passes over the handle
    (multi-shot contract): collect message ids; a dedicated pass filtered to
    ``model``/``compaction`` events that builds a region-last-``ModelEvent``
    skeleton (mirroring the events-only branch below) to derive the
    compaction-pruned ``excluded_ids`` set (see ``_compaction_excluded_ids``)
    -- skipped past the cheap type-filtered scan itself whenever no
    ``CompactionEvent`` is present; the anchor walk (retaining just id +
    rendered text per selected event); then re-stream messages splicing
    anchored entries. Retained memory is one id per message, the rendered
    text of selected events, plus (only while a ``CompactionEvent`` is
    present) one full ``ModelEvent`` per compaction region for the extra
    pass, discarded once ``excluded_ids`` is computed.

    Events-only transcripts (empty ``messages()``) reconstruct the thread
    from model events in a single events pass: only the most recent
    ``ModelEvent`` per compaction region is retained (that event's input
    already carries the region's conversation — the thread itself), plus a
    small op log of output-message ids, each paired with that same
    ``ModelEvent``'s rendered off-thread text (or ``""`` if it has none), so
    anchors resolve against the reconstructed thread in event order and any
    op whose model output does not anchor can still render as a branch
    entry without re-visiting the (already discarded) original event.
    Because ``skeleton`` always retains every compaction region's *last*
    ``ModelEvent`` in full (never stubbed), it carries enough content to
    also reconstruct the untruncated ``compaction="all"`` thread -- used to
    compute the excluded-ids set that keeps compaction-pruned turns hidden
    (see ``_AnchorWalk``). Memory: one rendered output string per
    ``ModelEvent``, which is bounded and is exactly the content that would
    be rendered anyway for genuine forks.

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
        # A dedicated fourth pass, filtered to just "model"/"compaction",
        # builds the same region-last-ModelEvent `skeleton` as the
        # events-only branch below -- solely to reconstruct the untruncated
        # `compaction="all"` thread and derive `excluded_ids` (see
        # `_compaction_excluded_ids`), so a compaction-pruned turn stays
        # hidden here exactly as it does on the materialized path
        # (`interleave_events`). `message_ids` (not full `ChatMessage`s) is
        # already all that's retained of the current thread, so the diff is
        # taken directly against it. Skipped whenever the transcript has no
        # `CompactionEvent` at all: `excluded_ids` stays empty and this
        # pass's only cost is the (typically small) scan for compaction
        # events itself.
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

    # Events-only: reconstruct the thread from model events. `skeleton`
    # keeps compaction events plus the most recent ModelEvent per region
    # (span_messages only reads the region-last event); `ops` records the
    # anchor walk's inputs in event order for replay once the thread exists.
    # Each op is (kind, a, b): ("m", output_message_id, rendered_text_or_"")
    # for a model event -- the rendered text is precomputed since the full
    # event itself is not retained past this loop -- or ("e", event_id,
    # rendered_text) for an interleavable event.
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
