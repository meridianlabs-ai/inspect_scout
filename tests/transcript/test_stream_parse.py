"""Tests for single-pass spool-building stream parse."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool


def _stream(data: dict[str, Any]) -> io.BytesIO:
    return io.BytesIO(json.dumps(data).encode())


SAMPLE: dict[str, Any] = {
    "id": "s1",
    "metadata": {"k": "v"},
    "target": "the-target",
    "messages": [
        {"id": "m1", "role": "user", "content": "hello"},
        {"id": "m2", "role": "assistant", "content": "attachment://" + "a" * 32},
    ],
    "scores": {"scorer": {"value": 1}},
    "events": [
        {
            "span_id": "s1",
            "timestamp": "2022-01-01T00:00:00+00:00",
            "event": "model",
            "model": "test-model",
            "input": [],
            "input_refs": [[0, 2]],
            "output": {"model": "test-model", "choices": []},
            "tools": [],
            "tool_choice": "auto",
            "config": {},
        },
        {"event": "info", "timestamp": 2.0, "data": "x"},
    ],
    "attachments": {
        "a" * 32: "resolved-text",
        "b" * 32: "pool-attachment-resolved",
    },
    "events_data": {
        "messages": [
            {"role": "user", "content": "pooled-1"},
            {"role": "assistant", "content": "attachment://" + "b" * 32},
        ],
        "calls": [],
    },
}


@pytest.mark.asyncio
async def test_parse_spools_filtered_items(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), "all", ["model"], tmp_path)
    try:
        messages = list(result.messages.items())
        assert [m["id"] for m in messages] == ["m1", "m2"]
        events = list(result.events.items())
        assert len(events) == 1 and events[0]["event"] == "model"
        assert result.metadata == {"k": "v"}
        assert result.target == "the-target"
        assert result.scores == {"scorer": {"value": 1}}
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_spools_all_attachments_and_pools(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), None, None, tmp_path)
    try:
        # attachments spooled even when no kept item references them
        assert result.blobs.get("a" * 32) == "resolved-text"
        # pool items positionally addressable
        assert result.blobs.pool_len("message_pool") == 2
        pooled = json.loads(result.blobs.get(("message_pool", 1)) or "")
        assert pooled["content"] == "attachment://" + "b" * 32
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_message_filter(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), ["user"], None, tmp_path)
    try:
        messages = list(result.messages.items())
        assert [m["role"] for m in messages] == ["user"]
        assert len(result.events) == 0
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_nan_raises(tmp_path: Path) -> None:
    import ijson

    bad = io.BytesIO(b'{"id": "s", "messages": [], "x": NaN}')
    with pytest.raises(ijson.JSONError):
        await stream_parse_to_spool(bad, "all", "all", tmp_path)
    assert list(tmp_path.iterdir()) == []  # spools closed/unlinked on error


@pytest.mark.asyncio
async def test_replay_messages_resolves_attachments(tmp_path: Path) -> None:
    from inspect_scout._transcript.json.stream_parse import replay_messages

    result = await stream_parse_to_spool(_stream(SAMPLE), "all", None, tmp_path)
    try:
        messages = list(replay_messages(result))
        assert messages[1].content == "resolved-text"  # attachment resolved
        assert messages[0].role == "user"
        # multi-shot: second replay identical
        again = list(replay_messages(result))
        assert [m.id for m in again] == [m.id for m in messages]
    finally:
        result.close()


@pytest.mark.asyncio
async def test_replay_events_expands_pools_and_pool_attachments(
    tmp_path: Path,
) -> None:
    from inspect_scout._transcript.json.stream_parse import replay_events

    result = await stream_parse_to_spool(_stream(SAMPLE), None, "all", tmp_path)
    try:
        events = list(replay_events(result))
        model_events = [e for e in events if e.event == "model"]
        assert len(model_events) == 1
        inputs = model_events[0].input
        assert len(inputs) == 2  # input_refs [[0, 2]] expanded from pool
        # THE BUG FIX: attachment ref inside a pool item is resolved.
        # (Requires "b"*32 in SAMPLE attachments — extend SAMPLE first.)
        assert inputs[1].content == "pool-attachment-resolved"
    finally:
        result.close()
