"""Pruning, remapping, and envelope assembly for the pooled passthrough."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspect_scout._transcript.json.passthrough import pooled_passthrough
from inspect_scout._transcript.json.spool import BlobSpool, ItemSpool
from inspect_scout._transcript.json.stream_parse import StreamParseResult
from inspect_scout._transcript.types import TranscriptInfo


def _result(tmp_path: Path, events: list[dict[str, Any]]) -> StreamParseResult:
    """Build a StreamParseResult with a 3-entry message pool, no messages."""
    messages = ItemSpool(tmp_path)
    event_spool = ItemSpool(tmp_path)
    blobs = BlobSpool(tmp_path)
    for i in range(3):
        blobs.put(("message_pool", i), json.dumps({"role": "user", "content": f"m{i}"}))
    for event in events:
        event_spool.append(event)
    return StreamParseResult(messages, event_spool, blobs)


def test_prunes_pool_to_referenced_entries_and_remaps(tmp_path: Path) -> None:
    # One event referencing only pool positions [2,3) -- entries 0 and 1 are
    # unreferenced and must be dropped, leaving the survivor at position 0.
    result = _result(tmp_path, [{"event": "model", "input_refs": [[2, 3]]}])
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is not None
    data = json.loads(input_data_json)
    assert data["messages"] == [{"role": "user", "content": "m2"}]
    events = json.loads(input_json)["events"]
    assert events[0]["input_refs"] == [[0, 1]]


def test_refs_past_the_pool_are_dropped_not_raised(tmp_path: Path) -> None:
    # A ref range that runs past the spooled pool (positions 0-2 exist, the
    # event asks for 1-3). The materialized path expands refs by slicing and
    # silently drops position 3, so the passthrough must too -- looking the
    # unspooled position up would raise KeyError, and `_transcript_for_record`
    # would swallow it and record an empty transcript for the whole scan.
    result = _result(tmp_path, [{"event": "model", "input_refs": [[1, 4]]}])
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is not None
    assert json.loads(input_data_json)["messages"] == [
        {"role": "user", "content": "m1"},
        {"role": "user", "content": "m2"},
    ]
    assert json.loads(input_json)["events"][0]["input_refs"] == [[0, 2]]


def test_empty_pools_and_no_attachments_yield_no_input_data(tmp_path: Path) -> None:
    result = _result(tmp_path, [])
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is None
    assert json.loads(input_json)["events"] == []


def test_collects_attachments_referenced_from_pool_entries(tmp_path: Path) -> None:
    # The ref lives inside a POOL entry, not the event -- a naive scan of
    # events alone would miss it and emit a dangling attachment:// ref.
    att = "a" * 32
    messages = ItemSpool(tmp_path)
    events = ItemSpool(tmp_path)
    blobs = BlobSpool(tmp_path)
    blobs.put(
        ("message_pool", 0),
        json.dumps({"role": "user", "content": f"attachment://{att}"}),
    )
    blobs.put(att, "the real content")
    events.append({"event": "model", "input_refs": [[0, 1]]})
    result = StreamParseResult(messages, events, blobs)
    try:
        _, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is not None
    assert json.loads(input_data_json)["attachments"] == {att: "the real content"}


def test_prunes_and_remaps_call_pool_via_call_refs(tmp_path: Path) -> None:
    # message_pool and call_pool are seeded with disjoint referenced position
    # sets ({3,4} vs {1,2}) and disjoint content ("kind": "message"/"call").
    # If the message/call position maps were swapped when calling
    # `remap_pool_refs`, the message positions (3,4) would be looked up in
    # the call map (keyed 1,2) and vice versa -- a KeyError, not a silent
    # pass. `input_refs`/`call_refs` alone (as in the other tests) can't
    # detect this because they only ever populate one of the two maps.
    messages = ItemSpool(tmp_path)
    events = ItemSpool(tmp_path)
    blobs = BlobSpool(tmp_path)
    for i in range(5):
        blobs.put(("message_pool", i), json.dumps({"kind": "message", "idx": i}))
    for i in range(4):
        blobs.put(("call_pool", i), json.dumps({"kind": "call", "idx": i}))
    events.append(
        {
            "event": "tool",
            "input_refs": [[3, 5]],
            "call": {"call_refs": [[1, 3]], "call_key": "arguments"},
        }
    )
    result = StreamParseResult(messages, events, blobs)
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is not None
    data = json.loads(input_data_json)
    assert data["messages"] == [
        {"kind": "message", "idx": 3},
        {"kind": "message", "idx": 4},
    ]
    assert data["calls"] == [{"kind": "call", "idx": 1}, {"kind": "call", "idx": 2}]

    event = json.loads(input_json)["events"][0]
    assert event["input_refs"] == [[0, 2]]
    assert event["call"]["call_refs"] == [[0, 2]]


def test_envelope_carries_info_and_messages(tmp_path: Path) -> None:
    messages = ItemSpool(tmp_path)
    events = ItemSpool(tmp_path)
    blobs = BlobSpool(tmp_path)
    messages.append({"id": "m1", "role": "user", "content": "hello"})
    result = StreamParseResult(messages, events, blobs)
    try:
        input_json, _ = pooled_passthrough(
            TranscriptInfo(transcript_id="t1", source_id="e1"), result
        )
    finally:
        result.close()

    envelope = json.loads(input_json)
    assert envelope["transcript_id"] == "t1"
    assert envelope["source_id"] == "e1"
    assert envelope["messages"] == [{"id": "m1", "role": "user", "content": "hello"}]
    assert envelope["timelines"] == []
