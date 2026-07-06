"""Memory regression: streamed reads stay bounded on large synthetic samples."""

from __future__ import annotations

import io
import json
import tracemalloc
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.model import get_model
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.handle import SpooledTranscriptHandle
from inspect_scout._transcript.json.stream_parse import (
    StreamParseResult,
    stream_parse_to_spool,
)
from inspect_scout._transcript.timeline_stream import stream_timeline_messages
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from .fixtures_agentic import agentic_events, agentic_transcript


def _build_sample() -> bytes:
    """Build a synthetic transcript with large events and small messages."""
    # ~50 MB of events, ~100 KB of messages: a scan requesting messages only
    # must not pay for the events.
    n_events = 5_000
    event_payload = "x" * 10_000

    sample = {
        "id": "big",
        "messages": [
            {"id": f"m{i}", "role": "user", "content": f"msg {i}"} for i in range(100)
        ],
        "events": [
            {"event": "info", "timestamp": float(i), "data": event_payload}
            for i in range(n_events)
        ],
        "attachments": {},
    }
    return json.dumps(sample).encode()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_streamed_messages_read_bounded(tmp_path: Path) -> None:
    """Streamed message reads stay within a 6 MB budget on a large-events sample.

    The sample has ~50 MB of events and ~100 KB of messages; reading messages
    only must not scale with the discarded events' size.
    """
    data = _build_sample()
    assert len(data) > 45 * 1024 * 1024

    tracemalloc.start()
    result = await stream_parse_to_spool(io.BytesIO(data), "all", None, tmp_path)
    try:
        from inspect_scout._transcript.json.stream_parse import replay_messages

        count = sum(1 for _ in replay_messages(result))
        assert count == 100
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        result.close()

    # Materializing this sample costs > len(data) (~50 MB) in dicts alone.
    # The streamed path must stay far below. Measured peak is ~0.66 MB; a
    # 6 MB budget stays comfortably above the real cost while still failing
    # loudly if the events ever get accumulated in memory again.
    assert peak < 6 * 1024 * 1024, f"peak {peak / 1024 / 1024:.1f} MB"


def _build_message_heavy_sample() -> bytes:
    """Build a transcript whose bulk lives in MESSAGES, not events.

    ~80 messages of ~500 KB each => ~40 MB of message content. A read that
    accumulates validated messages in a list would pay all of it; single-item
    streaming replay must stay far below.
    """
    n_messages = 80
    message_payload = "y" * 500_000

    sample = {
        "id": "big-messages",
        "messages": [
            {"id": f"m{i}", "role": "user", "content": f"{message_payload}{i}"}
            for i in range(n_messages)
        ],
        "events": [],
        "attachments": {},
    }
    return json.dumps(sample).encode()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_streamed_messages_no_accumulation_bounded(tmp_path: Path) -> None:
    """Symmetric case: message-heavy sample stays bounded when not retained.

    Catches a validated-message accumulation regression. The bulk (~40 MB)
    is in messages; consuming replay one item at a time without retaining
    (``sum(1 for _)``) must stay under a budget that list-accumulation of the
    validated messages would blow.
    """
    from inspect_scout._transcript.json.stream_parse import replay_messages

    data = _build_message_heavy_sample()
    assert len(data) > 35 * 1024 * 1024

    result = await stream_parse_to_spool(io.BytesIO(data), "all", None, tmp_path)
    try:
        # Measure ONLY the consume path. The parse phase transiently
        # accumulates ijson ObjectBuilder reference-cycle garbage (closures
        # over the in-progress dict) until a gc pass reclaims it -- a
        # pre-existing ijson behavior that scales with message count/size
        # and is orthogonal to the accumulation regression this guards.
        # Consume one at a time WITHOUT retaining any message.
        tracemalloc.start()
        count = sum(1 for _ in replay_messages(result))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert count == 80
    finally:
        result.close()

    # Accumulating the 80 validated messages (~40 MB, measured) would blow this
    # budget; single-item streaming replay peaks at roughly one message
    # (~2.5 MB, measured) plus overhead. 8 MB cleanly separates the two.
    assert peak < 8 * 1024 * 1024, f"peak {peak / 1024 / 1024:.1f} MB"


def _build_agentic_sample(big_payload: str, bulk_model_turns: int) -> bytes:
    """Serialize `agentic_events(...)` the way a real transcript store would.

    `bulk_model_turns` non-selected `ModelEvent`s each carry `big_payload` in
    a user message; with `compaction="last"` only the span's closing turn is
    selected, so the bulk conversations must never survive into pass 2's
    substituted output.
    """
    events = agentic_events(big_payload=big_payload, bulk_model_turns=bulk_model_turns)
    transcript: Transcript = agentic_transcript(events)
    sample: dict[str, Any] = {
        "id": transcript.transcript_id,
        "messages": [],
        "events": [event.model_dump(mode="json") for event in transcript.events],
        "attachments": {},
    }
    # Round-trip through json.dumps to confirm the events serialize cleanly
    # (datetimes etc. are handled by `model_dump(mode="json")`).
    return json.dumps(sample).encode()


def _spooled_agentic_handle(result: StreamParseResult) -> SpooledTranscriptHandle:
    """Wrap an already-spooled parse result the way `_spooled_handle` does."""

    async def parse() -> StreamParseResult:
        return result

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    info = TranscriptInfo(transcript_id="agentic-1")
    return SpooledTranscriptHandle(info, parse, fallback)


async def _stream_agentic_peak(
    big_payload: str, bulk_model_turns: int, spool_dir: Path
) -> tuple[int, int]:
    """Spool an agentic sample and return (sample bytes, streaming peak bytes).

    Measures ONLY the `stream_timeline_messages` consumption (pass 1 stub
    build + classification, pass 2 substitution, segmentation) -- not the
    initial `stream_parse_to_spool` call. Same rationale as the message-heavy
    test above: the parse phase transiently accumulates ijson ObjectBuilder
    reference-cycle garbage that a gc pass eventually reclaims, which would
    contaminate a measurement of the two-pass skeleton itself.
    """
    data = _build_agentic_sample(big_payload, bulk_model_turns)
    result = await stream_parse_to_spool(io.BytesIO(data), "all", "all", spool_dir)
    handle = _spooled_agentic_handle(result)
    # Warm up the mockllm model/tokenizer OUTSIDE the tracemalloc window: the
    # first call in a process pays a one-time tiktoken-encoder-load cost
    # (tens of MB) that has nothing to do with the two-pass skeleton being
    # measured here.
    await get_model("mockllm/model").count_tokens("warmup")
    try:
        tracemalloc.start()
        segments = [
            seg
            async for seg in stream_timeline_messages(
                handle,
                messages_as_str=message_numbering()[0],
                model="mockllm/model",
                compaction="last",
            )
        ]
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert segments  # non-vacuous: the fixture must yield >=1 segment
    finally:
        await handle.aclose()
    return len(data), peak


@pytest.mark.slow
@pytest.mark.asyncio
async def test_streamed_events_scan_bounded(tmp_path: Path) -> None:
    """Agentic events-heavy sample: two-pass skeleton stays far below materialization.

    Bulk lives in 60 non-selected `ModelEvent` conversations (~33 MB); with
    `compaction="last"` only the small closing turn per span is selected.
    """
    # "word " repeated (rather than a single repeated character) avoids a
    # tiktoken regex-backtracking pathology on very long runs of one
    # character; it hits the same byte-size targets.
    big_payload = "word " * 100_000  # ~500 KB per bulk turn

    nbytes, peak = await _stream_agentic_peak(big_payload, 60, tmp_path)
    assert nbytes > 30 * 1024 * 1024

    # Materializing the 60 bulk conversations (~33 MB sample) would cost
    # tens of MB if retained. Measured peak is ~6.7-8.0 MB across repeated
    # runs; 12 MB stays comfortably above the real cost while still failing
    # loudly if the stub skeleton ever stops discarding non-selected bulk
    # content.
    assert peak < 12 * 1024 * 1024, f"peak {peak / 1024 / 1024:.1f} MB"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_streamed_events_scan_scales_with_structure_not_payload(
    tmp_path: Path,
) -> None:
    """Pass-1 stub retention tracks turn count, not per-turn payload size.

    Doubling the number of non-selected bulk turns (60 -> 120, ~33 MB -> ~62
    MB sample) must NOT roughly double peak memory: the stub skeleton drops
    each bulk turn's conversation regardless of how many there are. Measured
    peak: 60 turns ~6.7-8.0 MB, 120 turns ~7.3 MB -- effectively flat, so a
    1.5x budget leaves generous headroom while still catching a regression
    where bulk turns start accumulating per-turn.

    (Doubling `big_payload` itself is not used as the scaling axis: a single
    JSON line containing one bulk `ModelEvent` is transiently materialized in
    full during that line's `json.loads`, so its peak legitimately scales
    with payload size regardless of stubbing -- an inherent decoding cost,
    not a stub-retention regression. Scaling turn count instead isolates
    "stub retention scales with structure, not payload".)
    """
    big_payload = "word " * 100_000  # fixed; only turn count changes below

    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, peak_60 = await _stream_agentic_peak(big_payload, 60, tmp_path / "a")
    _, peak_120 = await _stream_agentic_peak(big_payload, 120, tmp_path / "b")

    assert peak_120 < peak_60 * 1.5, (
        f"peak_60={peak_60 / 1024 / 1024:.1f} MB "
        f"peak_120={peak_120 / 1024 / 1024:.1f} MB"
    )
