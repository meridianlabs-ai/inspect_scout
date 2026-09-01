"""Pruning, remapping, and envelope assembly for the pooled passthrough."""

from __future__ import annotations

import json
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from inspect_scout._transcript.json.passthrough import pooled_passthrough
from inspect_scout._transcript.json.pool import slice_positions
from inspect_scout._transcript.json.spool import BlobSpool, ByteSpool, ItemSpool
from inspect_scout._transcript.json.stream_parse import StreamParseResult
from inspect_scout._transcript.types import TranscriptInfo
from inspect_scout._util._json import to_json_bytes_compact


def _result(tmp_path: Path, events: list[dict[str, Any]]) -> StreamParseResult:
    """Build a StreamParseResult with a 3-entry message pool, no messages."""
    messages = ItemSpool(tmp_path)
    event_spool = ItemSpool(tmp_path)
    blobs = BlobSpool(tmp_path)
    for i in range(3):
        blobs.put(("message_pool", i), json.dumps({"role": "user", "content": f"m{i}"}))
    for event in events:
        event_spool.append(event)
    return StreamParseResult(
        messages, event_spool, blobs, ByteSpool(tmp_path), tmp_path
    )


@pytest.mark.parametrize(
    ("input_refs", "expected_pool", "expected_refs"),
    [
        pytest.param([[2, 3]], ["m2"], [[0, 1]], id="prunes-and-remaps"),
        # A range running past the spooled pool (0-2 exist, the event asks for
        # 1-3). The materialized path expands refs by slicing and silently
        # drops position 3, so this must too -- looking the unspooled position
        # up would raise KeyError, which `_transcript_for_record` would swallow
        # and record an empty transcript for the whole scan.
        pytest.param([[1, 4]], ["m1", "m2"], [[0, 2]], id="past-the-pool"),
        # Bounds follow Python slicing, because that is what the materialized
        # path does.
        pytest.param([[-1, 3]], ["m2"], [[0, 1]], id="negative-start"),
        pytest.param([[-3, -1]], ["m0", "m1"], [[0, 2]], id="negative-both"),
        pytest.param([[1, 10**9]], ["m1", "m2"], [[0, 2]], id="huge-end"),
        pytest.param([[2, 1]], [], [], id="inverted-empty"),
    ],
)
def test_pool_refs_are_pruned_and_remapped(
    input_refs: list[list[int]],
    expected_pool: list[str],
    expected_refs: list[list[int]],
    tmp_path: Path,
) -> None:
    result = _result(tmp_path, [{"event": "model", "input_refs": input_refs}])
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is not None
    assert json.loads(input_data_json)["messages"] == [
        {"role": "user", "content": content} for content in expected_pool
    ]
    assert json.loads(input_json)["events"][0]["input_refs"] == expected_refs


def test_empty_pools_still_emit_input_data(tmp_path: Path) -> None:
    """Empty pools emit `{"messages":[],"calls":[]}`, not None.

    The materialized path runs `condense_events` unconditionally for a
    transcript input, so it emits empty pools rather than omitting the column.
    Returning None here would make the recorded row differ from the
    materialized one for any transcript with no pooled content.
    """
    result = _result(tmp_path, [])
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert input_data_json is not None
    assert json.loads(input_data_json) == {"messages": [], "calls": []}
    assert json.loads(input_json)["events"] == []


def test_envelope_omits_unset_and_subclass_fields(tmp_path: Path) -> None:
    """The envelope carries exactly the field set the materialized path emits.

    `to_json_safe` passes exclude_none=True and the materialized path builds a
    `Transcript`, so unset fields are omitted and subclass-only fields (a
    parquet index row carries `filename`) are dropped.
    """

    class _IndexRow(TranscriptInfo):
        filename: str = "shard-0.parquet"

    result = _result(tmp_path, [])
    try:
        input_json, _ = pooled_passthrough(_IndexRow(transcript_id="t1"), result)
    finally:
        result.close()

    envelope = json.loads(input_json)
    assert "filename" not in envelope
    assert not [k for k, v in envelope.items() if v is None]
    assert envelope["transcript_id"] == "t1"


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
    result = StreamParseResult(messages, events, blobs, ByteSpool(tmp_path), tmp_path)
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
    result = StreamParseResult(messages, events, blobs, ByteSpool(tmp_path), tmp_path)
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
    result = StreamParseResult(messages, events, blobs, ByteSpool(tmp_path), tmp_path)
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


def test_index_metadata_values_json_stdlib_refuses_are_coerced(
    tmp_path: Path,
) -> None:
    """Non-JSON-native metadata values must not abort the record.

    Unlike the spooled items, `TranscriptInfo` fields come from index rows, so
    a parquet TIMESTAMP column arrives as a `datetime`. Encoding it with stdlib
    `json` raises, and the caller turns any exception here into an empty
    placeholder transcript -- losing the whole recorded input for every
    transcript in the scan, with only a log line to show for it. Coercion must
    match the materialized path, which serializes these with pydantic.
    """
    info = TranscriptInfo(
        transcript_id="t1",
        metadata={"created": datetime(2026, 8, 6, 12, 30, tzinfo=timezone.utc)},
    )

    input_json, _ = pooled_passthrough(info, _result(tmp_path, []))

    envelope = json.loads(input_json)
    assert envelope["metadata"]["created"].startswith("2026-08-06T12:30:00")
    # ...and identical to how the materialized path renders the same value.
    assert json.dumps(
        envelope["metadata"]["created"]
    ).encode() == to_json_bytes_compact(info.metadata["created"])


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
    """Divergence from slicing here is a silent divergence in recorded output."""
    pool = list(range(pool_len))
    assert [pool[i] for i in slice_positions(start, end, pool_len)] == pool[start:end]


def test_input_data_streams_pool_entries_without_holding_them(
    tmp_path: Path,
) -> None:
    """`input_data` must stay near the cell size, like the envelope does."""
    entry = "x" * (512 * 1024)
    blobs = BlobSpool(tmp_path)
    for i in range(40):  # ~20 MB of pool
        blobs.put(("message_pool", i), json.dumps({"role": "user", "content": entry}))
    result = StreamParseResult(
        ItemSpool(tmp_path),
        ItemSpool(tmp_path),
        blobs,
        ByteSpool(tmp_path),
        tmp_path,
    )
    result.events.append({"event": "model", "input_refs": [[0, 40]]})

    tracemalloc.start()
    try:
        _, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        result.close()

    assert input_data_json is not None
    cell = len(input_data_json)
    assert cell > 15 * 1024 * 1024, "fixture should be big enough to be meaningful"
    # The read-back is unavoidable; 2.5x leaves headroom while still failing
    # if the value is built as an object graph and dumped whole (~5x).
    assert peak < cell * 2.5, f"peak {peak} exceeds 2.5x the {cell}-byte cell"


def test_merged_metadata_prefers_spooled_values_over_the_stale_index_copies(
    tmp_path: Path,
) -> None:
    """Spooled `sample_metadata`/`target`/`scores` win over the index row's.

    Real eval-log index rows carry their own stale `sample_metadata` (observed:
    the literal string `"{}"`) inside `TranscriptInfo.metadata`, alongside
    whatever the spool actually holds. `_merged_metadata` has to merge the
    spooled values in as overrides -- `info.metadata.copy() | overrides` --
    not the reverse; swapping that precedence would silently record the
    stale index value into a public column instead of the real one.
    """
    metadata_json = ByteSpool(tmp_path)
    metadata_json.write(json.dumps({"foo": "bar"}).encode())
    result = StreamParseResult(
        ItemSpool(tmp_path),
        ItemSpool(tmp_path),
        BlobSpool(tmp_path),
        metadata_json,
        tmp_path,
        target="t",
        scores={"accuracy": 1.0},
    )
    try:
        info = TranscriptInfo(
            transcript_id="t1",
            metadata={"sample_metadata": "{}", "other": "kept"},
        )
        input_json, _ = pooled_passthrough(info, result)
    finally:
        result.close()

    assert json.loads(input_json)["metadata"] == {
        "other": "kept",
        "sample_metadata": {"foo": "bar"},
        "target": "t",
        "scores": {"accuracy": 1.0},
    }
