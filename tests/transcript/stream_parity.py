"""Streamed-vs-materialized rendering harness for timeline message tests."""

from __future__ import annotations

import json
from typing import Any, Literal, NamedTuple, Sequence

from inspect_ai.event import Event
from inspect_ai.log import condense_events
from inspect_ai.model import ChatMessage, get_model
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


def sample_json(
    events: Sequence[Event],
    *,
    messages: Sequence[ChatMessage] = (),
    attachments: dict[str, str] | None = None,
    pooled: bool = False,
) -> bytes:
    """A sample's JSON as a log stores it, for `stream_parse_to_spool`.

    ``pooled`` moves ModelEvent inputs and calls into an ``events_data`` pool,
    as inspect_ai's log writer does, so a replay reads them through refs.
    """
    sample: dict[str, Any] = {
        "id": "s",
        "messages": [m.model_dump(mode="json") for m in messages],
        "attachments": attachments or {},
    }
    if pooled:
        events, data = condense_events(events)
        sample["events_data"] = {
            "messages": [m.model_dump(mode="json") for m in data["messages"]],
            "calls": data["calls"],
        }
    sample["events"] = [e.model_dump(mode="json") for e in events]
    return json.dumps(sample).encode()
