"""Tests for single-pass spool-building stream parse."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Callable

import ijson  # type: ignore[import-untyped]  # no published stubs
import pytest
from inspect_ai.event import ModelEvent, ToolEvent
from inspect_scout._transcript.json import spool as spool_mod
from inspect_scout._transcript.json import stream_parse
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.json.pool import slice_positions
from inspect_scout._transcript.json.spool import ItemSpool, SpoolKey
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
    result = await stream_parse_to_spool(_stream(SAMPLE), None, "all", tmp_path)
    try:
        # attachments spooled even though no kept item references this one
        assert result.blobs.get("a" * 32) == "resolved-text"
        # pool items positionally addressable
        assert result.blobs.pool_len("message_pool") == 2
        pooled = json.loads(result.blobs.get(("message_pool", 1)) or "")
        assert pooled["content"] == "attachment://" + "b" * 32
    finally:
        result.close()


@pytest.mark.asyncio
async def test_parse_nan_raises_and_closes_every_spool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed JSON must not leak the spool fds it had already opened.

    Asserted on the files rather than on ``tmp_path.iterdir()``: the spool
    files are unlinked at creation on POSIX, so the directory is empty
    whether or not the unwind ever runs.
    """
    opened: list[Any] = []
    real_open = spool_mod._open_spool_file

    def spy_open(dir: Path, suffix: str) -> Any:
        spool_file = real_open(dir, suffix)
        opened.append(spool_file)
        return spool_file

    monkeypatch.setattr(spool_mod, "_open_spool_file", spy_open)

    bad = io.BytesIO(b'{"id": "s", "messages": [], "x": NaN}')
    with pytest.raises(ijson.JSONError):
        await stream_parse_to_spool(bad, "all", "all", tmp_path)

    assert len(opened) == 4  # messages, events, blobs, metadata
    assert all(spool_file.closed for spool_file in opened)


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


def _fail_item_spool_append(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the second `ItemSpool.append` fail (the filtered-item coroutine)."""
    real_append = spool_mod.ItemSpool.append
    calls = {"n": 0}

    def failing_append(self: spool_mod.ItemSpool, item: dict[str, Any]) -> None:
        calls["n"] += 1
        if calls["n"] == 2:  # fail mid-parse, not on the first item
            raise OSError(28, "No space left on device")
        real_append(self, item)

    monkeypatch.setattr(spool_mod.ItemSpool, "append", failing_append)


def _fail_pool_blob_put(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the first pool `BlobSpool.put` fail (the unfiltered coroutine).

    Keyed on the tuple form so attachment writes, which share `put`, still
    succeed -- the pool sinks are the only users of positional keys.
    """
    real_put = spool_mod.BlobSpool.put

    def failing_put(self: spool_mod.BlobSpool, key: SpoolKey, value: str) -> None:
        if isinstance(key, tuple):
            raise OSError(28, "No space left on device")
        real_put(self, key, value)

    monkeypatch.setattr(spool_mod.BlobSpool, "put", failing_put)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "break_sink",
    [_fail_item_spool_append, _fail_pool_blob_put],
    ids=["filtered-items", "pool-items"],
)
async def test_spool_write_failure_surfaces_instead_of_dropping_items(
    break_sink: Callable[[pytest.MonkeyPatch], None],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing spool write must raise, not silently drop the item.

    Both item coroutines tolerate a malformed item by design, but that guard
    used to wrap the sink append too -- so a full disk or a closed fd dropped
    a message, event or pool entry while the parse went on to report success.
    Data loss that a caller cannot see is worse than a crash.
    """
    break_sink(monkeypatch)

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


@pytest.mark.parametrize(
    ("start", "end", "pool_len"),
    [
        (0, 3, 3),
        (1, 4, 3),
        (-1, 3, 3),
        (-3, -1, 3),
        (1, 10**9, 3),
        (-99, 99, 3),
        (2, 1, 3),
        (0, 1, 0),
        (-1, 10**9, 5),
    ],
)
def test_slice_positions_matches_python_slicing(
    start: int, end: int, pool_len: int
) -> None:
    """Divergence from slicing here is a silent divergence in replayed events."""
    pool = list(range(pool_len))
    assert [pool[i] for i in slice_positions(start, end, pool_len)] == pool[start:end]


@pytest.mark.asyncio
async def test_both_pool_shapes_share_one_positional_index(tmp_path: Path) -> None:
    """Legacy `message_pool` and `events_data.messages` are one pool, in order.

    Two sinks over the same pool name each start their own counter, so the
    later shape overwrites the earlier one's entries while `pool_len` still
    counts both -- entries silently vanish and refs address the wrong ones.
    The materialized path appends both shapes into one list.
    """
    sample: dict[str, Any] = {
        "id": "s-both-pool-shapes",
        "messages": [],
        "message_pool": [
            {"role": "user", "content": "legacy-0"},
            {"role": "user", "content": "legacy-1"},
        ],
        "events": [
            {
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "event": "model",
                "model": "test-model",
                "input": [],
                "input_refs": [[0, 3]],
                "output": {"model": "test-model", "choices": []},
                "tools": [],
                "tool_choice": "auto",
                "config": {},
            }
        ],
        "attachments": {},
        "events_data": {"messages": [{"role": "user", "content": "new-0"}]},
    }
    result = await stream_parse_to_spool(_stream(sample), None, "all", tmp_path)
    try:
        assert result.blobs.pool_len("message_pool") == 3
        event = list(replay_events(result))[0]
        assert isinstance(event, ModelEvent)
        assert [m.content for m in event.input] == ["legacy-0", "legacy-1", "new-0"]
    finally:
        result.close()


@pytest.mark.asyncio
async def test_pools_are_not_spooled_when_events_are_not_collected(
    tmp_path: Path,
) -> None:
    """Only events carry pool refs, so a messages-only read must skip the pool.

    Spooling it writes the whole `events_data` section to disk for data
    nothing can fetch.
    """
    result = await stream_parse_to_spool(_stream(SAMPLE), "all", None, tmp_path)
    try:
        assert result.blobs.pool_len("message_pool") == 0
        assert result.blobs.get("a" * 32) == "resolved-text"  # attachments still kept
    finally:
        result.close()


@pytest.mark.asyncio
async def test_pooled_attachment_body_is_not_rescanned_for_refs(
    tmp_path: Path,
) -> None:
    """A ref inside a resolved attachment body must survive, as when materialized.

    The materialized path substitutes with one `re.sub`, which never rescans
    what it just wrote. Resolving pool entries on fetch *and* again with the
    rest of the item would expand the inner ref on the streamed path only.
    """
    outer, inner = "e" * 32, "f" * 32
    sample: dict[str, Any] = {
        "id": "s-nested-ref",
        "messages": [],
        "events": [
            {
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "event": "model",
                "model": "test-model",
                "input": [],
                "input_refs": [[0, 1]],
                "output": {"model": "test-model", "choices": []},
                "tools": [],
                "tool_choice": "auto",
                "config": {},
            }
        ],
        "attachments": {
            outer: f"body mentioning attachment://{inner} verbatim",
            inner: "INNER",
        },
        "events_data": {
            "messages": [{"role": "user", "content": f"attachment://{outer}"}]
        },
    }

    result = await stream_parse_to_spool(_stream(sample), None, "all", tmp_path)
    try:
        streamed_event = list(replay_events(result))[0]
        assert isinstance(streamed_event, ModelEvent)
        streamed = streamed_event.input[0].content
    finally:
        result.close()

    materialized = await load_filtered_transcript(
        _stream(sample),
        TranscriptInfo(
            transcript_id="s-nested-ref",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )
    materialized_event = materialized.events[0]
    assert isinstance(materialized_event, ModelEvent)
    expected = f"body mentioning attachment://{inner} verbatim"
    assert streamed == expected
    assert materialized_event.input[0].content == expected


def _tool_event_with_nested(nested: list[Any]) -> dict[str, Any]:
    return {
        "event": "tool",
        "span_id": "s1",
        "timestamp": "2022-01-01T00:00:00+00:00",
        "working_start": 0,
        "id": "call-1",
        "function": "f",
        "arguments": {},
        "events": nested,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nested",
    [
        pytest.param(["a string", 42], id="non-dict"),
        pytest.param([{"event": "future_thing", "timestamp": 1.0}], id="unknown-event"),
        pytest.param([{"hello": "world"}], id="not-an-event"),
    ],
)
async def test_nested_tool_events_that_are_not_events_pass_through(
    nested: list[Any], tmp_path: Path
) -> None:
    """`ToolEvent.events` is `list[Any]`; hydration must not crash or invent.

    The materialized path leaves these entries as-is. Validating them instead
    raises out of the whole `events()` stream for an unknown event type, and
    silently fabricates a `BranchEvent` from any other dict.
    """
    sample: dict[str, Any] = {
        "id": "s-nested-tolerance",
        "messages": [],
        "events": [_tool_event_with_nested(nested)],
        "attachments": {},
    }
    result = await stream_parse_to_spool(_stream(sample), None, "all", tmp_path)
    try:
        event = list(replay_events(result))[0]
        assert isinstance(event, ToolEvent)
        assert event.events == nested
    finally:
        result.close()
