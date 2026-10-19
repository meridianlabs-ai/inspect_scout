"""Pruning, remapping, and envelope assembly for the pooled passthrough."""

from __future__ import annotations

import json
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from inspect_scout._transcript.json.passthrough import pooled_passthrough
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

    cell = len(input_data_json)
    assert cell > 15 * 1024 * 1024, "fixture should be big enough to be meaningful"
    # The read-back is unavoidable, and measures 1.03x here; 1.5x leaves
    # headroom while still failing the likeliest regression -- building the
    # value as an object graph and dumping it whole, measured at 2.0x.
    assert peak < cell * 1.5, f"peak {peak} exceeds 1.5x the {cell}-byte cell"


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


def _embedded(attachment_id: str) -> str:
    return f"see attachment://{attachment_id} for details"


def test_envelope_collects_only_whole_value_attachment_refs(tmp_path: Path) -> None:
    """An id inside author-written text is not a ref, so its body is not shipped.

    Over-collection is not cosmetic here: attachment bodies are large by
    construction, so one mention would bloat the public `input_data` column by
    the whole body of an attachment nothing will ever resolve.
    """
    embedded_id, quoted_id, whole_id = "a" * 32, "e" * 32, "b" * 32
    messages = ItemSpool(tmp_path)
    messages.append({"role": "user", "content": _embedded(embedded_id)})
    # Text opening with a quote character: JSON escapes it, so the serialized
    # bytes read `\"attachment://<id>"` and the value's own closing delimiter
    # would otherwise complete a match.
    messages.append({"role": "user", "content": f'"attachment://{quoted_id}'})
    messages.append({"role": "assistant", "content": f"attachment://{whole_id}"})
    blobs = BlobSpool(tmp_path)
    blobs.put(embedded_id, "MENTIONED")
    blobs.put(quoted_id, "QUOTED")
    blobs.put(whole_id, "REFERENCED")
    result = StreamParseResult(
        messages, ItemSpool(tmp_path), blobs, ByteSpool(tmp_path), tmp_path
    )
    try:
        input_json, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    assert json.loads(input_data_json)["attachments"] == {whole_id: "REFERENCED"}
    assert json.loads(input_json)["messages"][0]["content"] == _embedded(embedded_id)


def test_pool_entries_collect_only_whole_value_attachment_refs(
    tmp_path: Path,
) -> None:
    """The same rule on the second scan site: refs reached through a pool ref.

    The event carries positions, not text, so nothing here is collectable from
    the envelope -- only from the pool entries `_emit_input_data` re-serializes.
    """
    embedded_id, whole_id = "c" * 32, "d" * 32
    blobs = BlobSpool(tmp_path)
    blobs.put(
        ("message_pool", 0),
        json.dumps({"role": "user", "content": _embedded(embedded_id)}),
    )
    blobs.put(
        ("message_pool", 1),
        json.dumps({"role": "user", "content": f"attachment://{whole_id}"}),
    )
    blobs.put(embedded_id, "MENTIONED")
    blobs.put(whole_id, "REFERENCED")
    events = ItemSpool(tmp_path)
    events.append({"event": "model", "input_refs": [[0, 2]]})
    result = StreamParseResult(
        ItemSpool(tmp_path), events, blobs, ByteSpool(tmp_path), tmp_path
    )
    try:
        _, input_data_json = pooled_passthrough(
            TranscriptInfo(transcript_id="t1"), result
        )
    finally:
        result.close()

    data = json.loads(input_data_json)
    assert data["attachments"] == {whole_id: "REFERENCED"}
    assert data["messages"][0]["content"] == _embedded(embedded_id)
