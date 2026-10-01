"""Streamed-vs-materialized rendering harness for timeline message tests."""

from __future__ import annotations

from typing import Literal, NamedTuple

from inspect_ai.event import Event
from inspect_ai.model import get_model
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.interleave import EventsSpec
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import TimelineMessages
from inspect_scout._transcript.timeline_stream import stream_timeline_messages
from inspect_scout._transcript.types import Transcript, TranscriptInfo


class BothPaths(NamedTuple):
    """`(span.id, messages_str)` segments rendered by each path."""

    streamed: list[tuple[str, str]]
    materialized: list[tuple[str, str]]


async def both_paths(
    events: list[Event],
    *,
    events_spec: EventsSpec = "all",
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    include_scorers: bool = False,
) -> BothPaths:
    """Render `events` via `stream_timeline_messages` and `transcript_messages`.

    Each side gets its own fresh message numbering, so `[M#]`/`[E#]`
    ordinals are comparable.
    """
    transcript = Transcript(transcript_id="t-both", events=list(events))

    async def load() -> Transcript:
        return transcript

    model = get_model("mockllm/model")
    handle = MaterializedTranscriptHandle(load, TranscriptInfo(transcript_id="t-both"))
    streamed_numbering, _ = message_numbering()
    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=streamed_numbering,
            model=model,
            context_window=100_000,
            compaction=compaction,
            depth=depth,
            include_scorers=include_scorers,
            events=events_spec,
        )
    ]
    materialized_numbering, _ = message_numbering()
    materialized: list[tuple[str, str]] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=materialized_numbering,
        model=model,
        context_window=100_000,
        compaction=compaction,
        depth=depth,
        include_scorers=include_scorers,
        events=events_spec,
    ):
        assert isinstance(seg, TimelineMessages)
        materialized.append((seg.span.id, seg.messages_str))
    return BothPaths(streamed, materialized)
