"""Segment, scan, and aggregate a transcript: the pipeline shared by `llm_scanner` and `jev_scanner`.

A scanner supplies a per-segment ``scan_segment`` callable (rendered messages
in, ``Result`` out); this module handles transcript handles (streaming vs.
materialized), message extraction (timelines, events, or raw messages),
context-window segmentation, bounded segment concurrency, and aggregation.
"""

from logging import getLogger
from typing import AsyncIterator, Awaitable, Callable, Literal, NamedTuple

import anyio
from inspect_ai.model import Model

from .._scanner.extract import MessagesAsStr
from .._scanner.result import Result
from .._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
    TranscriptHandle,
)
from .._transcript.messages import (
    MessagesSegment,
    stream_segment_messages,
    transcript_messages,
)
from .._transcript.timeline import TimelineMessages
from .._transcript.timeline_stream import (
    _StubSkeletonUnsupported,
    stream_timeline_messages,
)
from .._transcript.types import Transcript
from ._reducer import aggregate_results
from .types import AnswerSpec

logger = getLogger(__name__)

# Bounds memory (one rendered segment string per slot), not connections:
# inspect_ai's own per-model semaphore gates the real generate calls, so a
# surplus admitted task costs a string and nothing else.
_SEGMENT_WINDOW_CAP = 16


class ScanSource(NamedTuple):
    """The transcript to scan, resolved from a scanner's input.

    Attributes:
        transcript: The full transcript, or (on the streaming path) a
            content-empty ``Transcript`` carrying only ``TranscriptInfo``
            fields, for template rendering and metadata.
        handle: The handle to stream segments from, or ``None`` to scan
            ``transcript`` directly.
    """

    transcript: Transcript
    handle: TranscriptHandle | None


async def resolve_scan_source(
    transcript: Transcript | TranscriptHandle,
    *,
    full_transcript_needed: bool,
    scanner_name: str,
) -> ScanSource:
    """Resolve a scanner input into a transcript and an optional streaming handle.

    Args:
        transcript: The scanner input.
        full_transcript_needed: Whether the scanner needs the whole transcript
            (e.g. callable template inputs or timeline extraction), which forces
            a handle to be loaded rather than streamed.
        scanner_name: Scanner name, for the error raised on unsupported input.

    Raises:
        TypeError: If ``transcript`` is not a ``Transcript`` or a concrete
            transcript handle.
    """
    # Match the concrete handle classes: TranscriptHandle is a plain
    # Protocol, and making it runtime-checkable would only test method
    # presence.
    handle: TranscriptHandle | None = (
        transcript
        if isinstance(
            transcript,
            (MaterializedTranscriptHandle, SpooledTranscriptHandle),
        )
        else None
    )

    if handle is not None and _must_materialize(handle, full_transcript_needed):
        transcript = await handle.load()
        handle = None

    # On the streaming path, template rendering only needs TranscriptInfo
    # fields, so pass a content-empty Transcript where one is required.
    if handle is not None:
        # Transcript subclasses TranscriptInfo, so a handle whose info
        # *is* a Transcript would collide with the empties below.
        return ScanSource(
            transcript=Transcript.model_construct(
                **handle.info.model_dump(exclude={"messages", "events", "timelines"}),
                messages=[],
                events=[],
                timelines=[],
            ),
            handle=handle,
        )
    elif isinstance(transcript, Transcript):
        return ScanSource(transcript=transcript, handle=None)
    else:
        raise TypeError(
            f"{scanner_name} cannot scan {type(transcript).__name__}: expected a "
            "Transcript, a MaterializedTranscriptHandle or a "
            "SpooledTranscriptHandle."
        )


async def scan_transcript_segments(
    source: ScanSource,
    *,
    scan_segment: Callable[[str], Awaitable[Result]],
    messages_as_str: MessagesAsStr,
    model: Model,
    context_window: int | None,
    timeline: str | None,
    compaction: Literal["all", "last"] | int,
    depth: int | None,
    prompt_reserve: int,
    content_has_events: bool,
    answer: AnswerSpec,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None,
) -> Result:
    """Segment a transcript, scan each segment, and aggregate the results.

    Args:
        source: The transcript (and optional streaming handle) to scan.
        scan_segment: Scans one rendered segment of messages.
        messages_as_str: Rendering function from ``message_numbering()``.
        model: Model whose tokenizer and context window size segments.
        context_window: Context window override for segmentation.
        timeline: Name of the timeline to extract messages from.
        compaction: How to handle compaction boundaries.
        depth: Maximum nesting level of scannable timeline spans.
        prompt_reserve: Tokens reserved for scaffolding around the messages.
        content_has_events: Whether the scanner's content filter requests
            events (selects timeline streaming on the handle path).
        answer: Answer spec, used to pick the default reducer.
        reducer: Optional reducer for multi-segment results.
    """

    async def scan_materialized(source_transcript: Transcript) -> Result:
        materialized_results = await _scan_segments_bounded(
            transcript_messages(
                source_transcript,
                messages_as_str=messages_as_str,
                model=model,
                context_window=context_window,
                timeline=timeline,
                compaction=compaction,
                depth=depth,
                prompt_reserve=prompt_reserve,
            ),
            scan_segment,
        )
        return await aggregate_results(
            results=materialized_results,
            timeline=bool(source_transcript.timelines),
            answer=answer,
            reducer=reducer,
        )

    handle = source.handle
    if handle is None:
        return await scan_materialized(source.transcript)

    # The source is picked from the *requested* filter, so it can come
    # up empty on a transcript the materialized path would still scan
    # (events="all" over a transcript carrying none). Reducing over
    # zero segments would answer the question with no transcript
    # content, so fall back instead.
    segments: AsyncIterator[MessagesSegment | TimelineMessages]
    if content_has_events:
        segments = stream_timeline_messages(
            handle,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            compaction=compaction,
            depth=depth,
            prompt_reserve=prompt_reserve,
        )
    else:
        segments = stream_segment_messages(
            handle.messages(),
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            prompt_reserve=prompt_reserve,
        )
    try:
        results = await _scan_segments_bounded(segments, scan_segment)
    except _StubSkeletonUnsupported as ex:
        # Raised while building the pass-1 stub skeleton, before any
        # segment is yielded and thus before any model call, so the
        # fallback re-runs from scratch with no duplicated scan work.
        logger.info(
            "Streaming events skeleton unsupported for transcript %s "
            "(%s); falling back to materialized scan.",
            handle.info.transcript_id,
            ex,
        )
        results = []
    if not results:
        return await scan_materialized(await handle.load())
    # A handle carries events, not named timelines.
    return await aggregate_results(
        results=results,
        timeline=False,
        answer=answer,
        reducer=reducer,
    )


async def _scan_segments_bounded(
    segments: AsyncIterator[MessagesSegment | TimelineMessages],
    scan_segment: Callable[[str], Awaitable[Result]],
) -> list[tuple[str | None, Result]]:
    """Scan lazily-yielded segments with bounded concurrency, in segment order.

    Each result is paired with its originating span id (None on non-timeline
    paths) so ``aggregate_results`` can group timeline chunks by span.

    A failing segment aborts the scan and raises its own exception, unwrapped
    from the task group's ``ExceptionGroup``.
    """
    window = anyio.Semaphore(_SEGMENT_WINDOW_CAP)
    indexed: list[tuple[int, str | None, Result]] = []

    async def scan_bounded(index: int, span_id: str | None, messages_str: str) -> None:
        try:
            indexed.append((index, span_id, await scan_segment(messages_str)))
        finally:
            window.release()

    try:
        async with anyio.create_task_group() as tg:
            index = 0
            while True:
                # Admit before pulling: `async for` renders the next segment
                # while the window is full, holding one string over the cap.
                await window.acquire()
                seg = await anext(segments, None)
                if seg is None:
                    window.release()
                    break
                tg.start_soon(
                    scan_bounded,
                    index,
                    seg.span.id if isinstance(seg, TimelineMessages) else None,
                    seg.messages_str,
                )
                index += 1
    except ExceptionGroup as ex:
        # Deliberately not inspect_ai's `inner_exception`: it also walks
        # `__context__`, and picks from an unordered set -- so an unrelated
        # chained exception can win over the segment's actual failure.
        raise ex.exceptions[0] from None

    # Reduction is order-sensitive, so undo the completion-order interleaving.
    return [(span_id, r) for _, span_id, r in sorted(indexed, key=lambda t: t[0])]


def _must_materialize(handle: TranscriptHandle, full_transcript_needed: bool) -> bool:
    """Whether to load() the handle and take the batch path instead of streaming it.

    Streaming a `MaterializedTranscriptHandle` buys nothing -- it loads the whole
    transcript on first use -- and costs the serialised per-segment token
    counting of the streaming path, so only a spooled handle is streamed.
    """
    return full_transcript_needed or isinstance(handle, MaterializedTranscriptHandle)
