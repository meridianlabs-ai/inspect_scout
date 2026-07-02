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
        # multi-shot: second replay identical (re-iterable, not just replay_messages)
        again = [e for e in replay_events(result) if e.event == "model"]
        assert len(again) == len(model_events)
        assert again[0].input[1].content == "pool-attachment-resolved"
    finally:
        result.close()


@pytest.mark.asyncio
async def test_replay_events_expands_call_pool(tmp_path: Path) -> None:
    """call_refs/call_key on a model event's `call` are expanded from call_pool.

    Mirrors test_call_pool_resolution in tests/scanner/test_load_filtered.py.
    """
    from inspect_scout._transcript.json.stream_parse import replay_events

    sample: dict[str, Any] = {
        "id": "test-pool-call",
        "target": "expected",
        "messages": [],
        "scores": {},
        "metadata": {},
        "events": [
            {
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "event": "model",
                "model": "test-model",
                "input": [{"role": "user", "content": "hi"}],
                "output": {"model": "test-model", "choices": []},
                "call": {
                    "request": {"model": "test-model"},
                    "response": {},
                    "call_refs": [[0, 1]],
                    "call_key": "messages",
                },
                "tools": [],
                "tool_choice": "auto",
                "config": {},
            },
        ],
        "attachments": {},
        "message_pool": [],
        "call_pool": [
            {"role": "user", "content": "pooled call msg"},
        ],
    }
    result = await stream_parse_to_spool(_stream(sample), "all", "all", tmp_path)
    try:
        events = list(replay_events(result))
        assert len(events) == 1
        model_event = events[0]
        assert model_event.call is not None
        assert model_event.call.request["messages"] == [
            {"role": "user", "content": "pooled call msg"}
        ]
    finally:
        result.close()


@pytest.mark.asyncio
async def test_resolve_item_dict_removes_call_refs_and_call_key(
    tmp_path: Path,
) -> None:
    """resolve_item_dict pops call_refs/call_key after expanding the pool range."""
    from inspect_scout._transcript.json.stream_parse import resolve_item_dict

    sample: dict[str, Any] = {
        "id": "test-pool-call-2",
        "target": None,
        "messages": [],
        "scores": {},
        "metadata": {},
        "events": [
            {
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "event": "model",
                "model": "test-model",
                "input": [],
                "output": {"model": "test-model", "choices": []},
                "call": {
                    "request": {},
                    "response": {},
                    "call_refs": [[0, 1]],
                    "call_key": "messages",
                },
                "tools": [],
                "tool_choice": "auto",
                "config": {},
            },
        ],
        "attachments": {},
        "message_pool": [],
        "call_pool": [
            {"role": "user", "content": "pooled call msg"},
        ],
    }
    result = await stream_parse_to_spool(_stream(sample), None, "all", tmp_path)
    try:
        raw_events = list(result.events.items())
        assert len(raw_events) == 1
        resolved = resolve_item_dict(raw_events[0], result.blobs)
        assert resolved["call"]["request"]["messages"] == [
            {"role": "user", "content": "pooled call msg"}
        ]
        assert "call_refs" not in resolved["call"]
        assert "call_key" not in resolved["call"]
    finally:
        result.close()


@pytest.mark.asyncio
async def test_resolve_strings_empty_string_attachment_not_treated_as_missing(
    tmp_path: Path,
) -> None:
    """An attachment resolving to "" must substitute "", not leave the ref text.

    Regression test: `blobs.get(...) or m.group(0)` treats an empty-string
    attachment value as falsy/missing; the fix must use an `is not None` check.
    """
    from inspect_scout._transcript.json.stream_parse import replay_messages

    empty_id = "c" * 32
    sample: dict[str, Any] = {
        "id": "s-empty-attachment",
        "metadata": {},
        "target": None,
        "messages": [
            {"id": "m1", "role": "user", "content": "attachment://" + empty_id},
        ],
        "scores": {},
        "events": [],
        "attachments": {empty_id: ""},
    }
    result = await stream_parse_to_spool(_stream(sample), "all", None, tmp_path)
    try:
        messages = list(replay_messages(result))
        assert messages[0].content == ""
    finally:
        result.close()
