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
    # The streamed path must stay far below: budget 16 MB.
    assert peak < 16 * 1024 * 1024, f"peak {peak / 1024 / 1024:.1f} MB"
