"""Tests for single-pass spool-building stream parse."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import IO, Any, Callable

import ijson  # type: ignore[import-untyped]  # no published stubs
import pytest
from inspect_ai.event import ToolEvent
from inspect_scout._transcript.json import spool as spool_mod
from inspect_scout._transcript.json.spool import SpoolKey
from inspect_scout._transcript.json.stream_parse import (
    replay_events,
    replay_messages,
    stream_parse_to_spool,
)


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
async def test_parse_nan_raises_and_closes_every_spool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed JSON must not leak the spool fds it had already opened.

    Asserted on the files rather than on ``tmp_path.iterdir()``: the spool
    files are unlinked at creation on POSIX, so the directory is empty
    whether or not the unwind ever runs.
    """
    opened: list[IO[bytes]] = []
    real_open = spool_mod._open_spool_file

    def spy_open(dir: Path, suffix: str) -> IO[bytes]:
        spool_file = real_open(dir, suffix)
        opened.append(spool_file)
        return spool_file

    monkeypatch.setattr(spool_mod, "_open_spool_file", spy_open)

    bad = io.BytesIO(b'{"id": "s", "messages": [], "x": NaN}')
    with pytest.raises(ijson.JSONError):
        await stream_parse_to_spool(bad, "all", "all", tmp_path)

    assert len(opened) == 4  # messages, events, blobs, metadata
    assert all(spool_file.closed for spool_file in opened)


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

    Both item coroutines tolerate a malformed item by design; that tolerance
    must not extend to the sink append, or a full disk or a closed fd drops a
    message, event or pool entry while the parse reports success.
    """
    break_sink(monkeypatch)

    with pytest.raises(OSError, match="No space left on device"):
        await stream_parse_to_spool(_stream(SAMPLE), "all", "all", tmp_path)


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


@pytest.mark.asyncio
async def test_embedded_attachment_ref_is_not_a_ref(tmp_path: Path) -> None:
    """Mid-string ids are left alone, as on the materialized path.

    The spool keeps every attachment, so the resolution rule is the only thing
    standing between an id that appears inside author-written text and the
    attachment body being pasted over it.
    """
    attachment_id = "a" * 32
    embedded = f"see attachment://{attachment_id} for details"
    sample: dict[str, Any] = {
        "id": "s-embedded",
        "messages": [
            {"id": "m1", "role": "user", "content": embedded},
            {
                "id": "m2",
                "role": "assistant",
                "content": f"attachment://{attachment_id}",
            },
        ],
        "attachments": {attachment_id: "SECRET"},
    }
    result = await stream_parse_to_spool(_stream(sample), "all", None, tmp_path)
    try:
        messages = list(replay_messages(result))
    finally:
        result.close()
    assert messages[0].content == embedded
    assert messages[1].content == "SECRET"
