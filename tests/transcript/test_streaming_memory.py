"""Memory regression: streamed reads stay bounded on large synthetic samples."""

from __future__ import annotations

import io
import json
import tracemalloc
from pathlib import Path

import pytest
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool


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
    """Verify streamed message reads stay within 16 MB budget."""
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
