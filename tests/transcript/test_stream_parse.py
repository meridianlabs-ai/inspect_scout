"""Tests for single-pass spool-building stream parse."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import ijson  # type: ignore[import-untyped]  # no published stubs
import pytest
from inspect_ai.event import ModelEvent
from inspect_scout._transcript.json import spool as spool_mod
from inspect_scout._transcript.json import stream_parse
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.json.spool import ItemSpool
from inspect_scout._transcript.json.stream_parse import (
    replay_events,
    replay_messages,
    stream_parse_to_spool,
)
from inspect_scout._transcript.types import EventFilter, MessageFilter, TranscriptInfo


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
@pytest.mark.parametrize(
    "messages_filter,events_filter,expected_message_ids,expected_event_kinds",
    [
        pytest.param("all", ["model"], ["m1", "m2"], ["model"], id="all-and-model"),
        pytest.param(["user"], None, ["m1"], [], id="user-only"),
        pytest.param(None, "all", [], ["model", "info"], id="events-only"),
    ],
)
async def test_parse_spools_filtered_items(
    messages_filter: MessageFilter,
    events_filter: EventFilter,
    expected_message_ids: list[str],
    expected_event_kinds: list[str],
    tmp_path: Path,
) -> None:
    result = await stream_parse_to_spool(
        _stream(SAMPLE), messages_filter, events_filter, tmp_path
    )
    try:
        messages = list(result.messages.items())
        assert [m["id"] for m in messages] == expected_message_ids
        events = list(result.events.items())
        assert [e["event"] for e in events] == expected_event_kinds
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_captures_scalar_fields(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), "all", ["model"], tmp_path)
    try:
        assert result.metadata() == {"k": "v"}
        assert result.has_metadata
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
async def test_parse_nan_raises(tmp_path: Path) -> None:
    bad = io.BytesIO(b'{"id": "s", "messages": [], "x": NaN}')
    with pytest.raises(ijson.JSONError):
        await stream_parse_to_spool(bad, "all", "all", tmp_path)
    assert list(tmp_path.iterdir()) == []  # spools closed/unlinked on error


@pytest.mark.asyncio
async def test_partial_spool_construction_failure_closes_opened_spools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A constructor failing mid-construction must close the earlier spools.

    The item spools open before the blob spool; if the blob spool's open
    fails (e.g. EMFILE/ENOSPC), the already-opened fds must not leak. Spy on
    close() of every ItemSpool created and fail BlobSpool construction.
    """
    created: list[ItemSpool] = []
    closed: list[ItemSpool] = []

    class SpyItemSpool(ItemSpool):
        def __init__(self, dir: Path) -> None:
            super().__init__(dir)
            created.append(self)

        def close(self) -> None:
            closed.append(self)
            super().close()

    class FailingBlobSpool:
        def __init__(self, dir: Path) -> None:
            raise OSError("out of file descriptors")

    monkeypatch.setattr(stream_parse, "ItemSpool", SpyItemSpool)
    monkeypatch.setattr(stream_parse, "BlobSpool", FailingBlobSpool)

    with pytest.raises(OSError, match="file descriptors"):
        await stream_parse_to_spool(_stream(SAMPLE), "all", "all", tmp_path)

    assert len(created) == 2  # messages + events spools opened before failure
    assert set(closed) == set(created)  # ...both closed on (LIFO) unwind


@pytest.mark.asyncio
async def test_replay_messages_resolves_attachments(tmp_path: Path) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), "all", None, tmp_path)
    try:
        messages = list(replay_messages(result))
        assert messages[1].content == "resolved-text"  # attachment resolved
        assert messages[0].role == "user"
    finally:
        result.close()


@pytest.mark.asyncio
async def test_replay_events_expands_pools_and_pool_attachments(
    tmp_path: Path,
) -> None:
    result = await stream_parse_to_spool(_stream(SAMPLE), None, "all", tmp_path)
    try:
        events = list(replay_events(result))
        model_events = [e for e in events if e.event == "model"]
        assert len(model_events) == 1
        inputs = model_events[0].input
        assert len(inputs) == 2  # input_refs [[0, 2]] expanded from pool
        # attachment ref inside a pool item is resolved
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
        assert isinstance(model_event, ModelEvent)
        assert model_event.call is not None
        assert model_event.call.request["messages"] == [
            {"role": "user", "content": "pooled call msg"}
        ]
        # call_refs/call_key are popped after expanding the pool range.
        assert model_event.call.call_refs is None
        assert model_event.call.call_key is None
    finally:
        result.close()


@pytest.mark.asyncio
async def test_streamed_and_materialized_resolve_embedded_ref_the_same(
    tmp_path: Path,
) -> None:
    """Streamed and materialized paths resolve an embedded attachment ref identically.

    Both must resolve a ref embedded inside a larger string (e.g. "prefix
    attachment://<id> suffix"), not just on an exact-match string.
    """
    attachment_id = "d" * 32
    sample: dict[str, Any] = {
        "id": "s-embedded-ref",
        "metadata": {},
        "target": None,
        "messages": [
            {
                "id": "m1",
                "role": "user",
                "content": f"prefix attachment://{attachment_id} suffix",
            },
        ],
        "scores": {},
        "events": [],
        "attachments": {attachment_id: "VALUE"},
    }

    streamed_result = await stream_parse_to_spool(
        _stream(sample), "all", None, tmp_path
    )
    try:
        streamed_content = list(replay_messages(streamed_result))[0].content
    finally:
        streamed_result.close()

    materialized = await load_filtered_transcript(
        _stream(sample),
        TranscriptInfo(
            transcript_id="s-embedded-ref",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )
    materialized_content = materialized.messages[0].content

    assert streamed_content == "prefix VALUE suffix"
    assert materialized_content == "prefix VALUE suffix"
    assert streamed_content == materialized_content


@pytest.mark.asyncio
async def test_resolve_strings_empty_string_attachment_not_treated_as_missing(
    tmp_path: Path,
) -> None:
    """An attachment resolving to "" must substitute "", not leave the ref text.

    An empty-string attachment value is not the same as a missing one.
    """
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


@pytest.mark.parametrize(
    "metadata,expected_present",
    [
        pytest.param({"k": "v"}, True, id="present"),
        pytest.param({}, False, id="empty-object"),
        pytest.param(None, False, id="absent"),
        pytest.param({"nested": {"a": [1, 2, {"b": None}]}}, True, id="nested"),
        pytest.param({"unicode": "héllo 你好"}, True, id="unicode"),
    ],
)
@pytest.mark.asyncio
async def test_metadata_spools_instead_of_building_objects(
    metadata: dict[str, Any] | None, expected_present: bool, tmp_path: Path
) -> None:
    """Metadata is spooled as text and only becomes objects when asked for.

    `has_metadata` must match the truthiness of the dict the parse used to
    expose, since callers gate the `sample_metadata` key on it.
    """
    sample = {key: value for key, value in SAMPLE.items() if key != "metadata"}
    if metadata is not None:
        sample["metadata"] = metadata

    result = await stream_parse_to_spool(_stream(sample), "all", "all", tmp_path)
    try:
        assert result.has_metadata is expected_present
        assert result.metadata() == (metadata if expected_present else {})
    finally:
        result.close()


@pytest.mark.asyncio
async def test_metadata_is_not_cached_between_calls(tmp_path: Path) -> None:
    """Each call reparses: caching would restore the retention being avoided."""
    result = await stream_parse_to_spool(_stream(SAMPLE), "all", "all", tmp_path)
    try:
        first = result.metadata()
        second = result.metadata()
        assert first == second
        assert first is not second
    finally:
        result.close()


@pytest.mark.asyncio
async def test_spool_write_failure_surfaces_instead_of_dropping_items(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing spool write must raise, not silently drop the item.

    The item coroutines tolerate a malformed item by design, but that guard
    used to wrap the sink append too -- so a full disk or a closed fd dropped
    a message or event while the parse went on to report success. Data loss
    that a caller cannot see is worse than a crash.
    """
    real_append = spool_mod.ItemSpool.append
    calls = {"n": 0}

    def failing_append(self: spool_mod.ItemSpool, item: dict[str, Any]) -> None:
        calls["n"] += 1
        if calls["n"] == 2:  # fail mid-parse, not on the first item
            raise OSError(28, "No space left on device")
        real_append(self, item)

    monkeypatch.setattr(spool_mod.ItemSpool, "append", failing_append)

    with pytest.raises(OSError, match="No space left on device"):
        await stream_parse_to_spool(_stream(SAMPLE), "all", "all", tmp_path)


@pytest.mark.asyncio
async def test_timelines_are_not_spooled(tmp_path: Path) -> None:
    """A timelines section is parsed past, not retained.

    Not a classifier guard: every reducer coroutine re-checks the prefix it is
    handed, so a misrouted section is ignored rather than misread. `target` is
    asserted because it is the section timelines could be confused with.
    """
    timelines = [
        {"id": f"tl{i}", "name": "solve", "events": [{"event": "info"}]}
        for i in range(3)
    ]
    sample: dict[str, Any] = {"id": SAMPLE["id"], "timelines": timelines}
    sample.update({k: v for k, v in SAMPLE.items() if k != "id"})

    result = await stream_parse_to_spool(_stream(sample), "all", "all", tmp_path)
    try:
        assert not hasattr(result, "timelines")
        assert result.target == "the-target"
    finally:
        result.close()
