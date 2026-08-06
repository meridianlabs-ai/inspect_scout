"""Emit recorder column values straight from a transcript spool.

The spool already holds the compact form the recorder wants: events with
range-encoded pool refs and `attachment://` refs intact, plus the pool
entries and attachments in a `BlobSpool`. This module copies that form
through -- pruned to what is actually referenced -- instead of expanding it
into a `Transcript` and re-condensing it with `condense_events`.

Attachment refs are NOT resolved: resolving inlines every duplicate, and the
attachments table travels inside `input_data` instead.
"""

from __future__ import annotations

import json
from typing import Any

from inspect_ai.event._pool import (
    POOL_REF_FIELDS,
    collect_pool_ref_positions,
    remap_pool_refs,
)
from pydantic import JsonValue

from ..._util._json import to_json_bytes_compact
from ..types import TranscriptInfo
from .reducer import ATTACHMENT_REF_BYTES, ATTACHMENT_REF_PATTERN
from .stream_parse import StreamParseResult

_POOLS = ("message_pool", "call_pool")

# Stand-in for the sample metadata, which is copied from its spool rather than
# parsed; see `_merged_metadata`.
_SPOOLED_SAMPLE_METADATA = object()

# Longest an `attachment://<32 hex>` ref can be, less one: how much of the
# previous chunk a scan must revisit so a ref split across chunks is still found.
_REF_OVERLAP = len("attachment://") + 32 - 1


def pooled_passthrough(
    info: TranscriptInfo, result: StreamParseResult
) -> tuple[bytes, bytes | None]:
    """Build `(input_json, input_data_json)` from a spooled parse.

    The envelope is emitted incrementally: each message and event is
    serialized as the spool replays it and appended to a list of chunks, so
    the full set of items never exists as Python objects at once and no
    ``json.dumps`` ever runs over the whole envelope.

    Args:
        info: Transcript metadata for the envelope.
        result: The spooled parse to copy from.

    Returns:
        The `input` column value, and the `input_data` column value or None
        when nothing is pooled and no attachments are referenced. UTF-8 bytes
        rather than ``str``: these go straight into a parquet column, and
        decoding would double a non-ASCII value in memory for nothing.
    """
    # Pass 1: which pool positions and attachments do the events reference?
    # `collect_pool_ref_positions` walks inspect_ai's POOL_REF_FIELDS registry
    # so this stays correct when upstream adds a new *_refs field.
    positions = collect_pool_ref_positions(result.events.items())
    referenced = {
        "message_pool": positions.message_positions,
        "call_pool": positions.call_positions,
    }

    # Fetch the surviving pool entries and build old -> new position maps.
    # Both come from one fetched list so they cannot disagree about which
    # entries survived -- a mismatch would silently point refs at the wrong
    # pool entry. Ascending order keeps pool ordering stable.
    pool_entries: dict[str, list[Any]] = {}
    pos_maps: dict[str, dict[int, int]] = {}
    dropped = False
    for pool in _POOLS:
        fetched = [
            (position, raw)
            for position in sorted(referenced[pool])
            if (raw := result.blobs.get((pool, position))) is not None
        ]
        pos_maps[pool] = {old: new for new, (old, _) in enumerate(fetched)}
        pool_entries[pool] = [json.loads(raw) for _, raw in fetched]
        dropped = dropped or len(fetched) != len(referenced[pool])

    # Pass 2: re-emit events with refs remapped onto the pruned pools.
    #
    # Attachment ids may be referenced from messages, from events, or from
    # inside a pool entry -- scan all three or refs dangle. Each chunk is
    # scanned as it is emitted: an id cannot straddle two chunks because every
    # item is serialized whole, so this sees exactly what a scan of the
    # finished envelope would.
    chunks: list[bytes | memoryview] = []
    attachment_ids: set[str] = set()

    def emit_bytes(data: bytes | memoryview) -> None:
        attachment_ids.update(
            match.decode("ascii") for match in ATTACHMENT_REF_BYTES.findall(data)
        )
        chunks.append(data)

    def emit(text: str) -> None:
        emit_bytes(text.encode("utf-8"))

    # Everything up to "messages", written key by key rather than dumped whole
    # -- and sample metadata, which for a metadata-dominated transcript is most
    # of the envelope, is copied straight from its spool without ever becoming
    # objects or a `str`.
    #
    # These values (unlike the spooled items below) originate from index rows
    # rather than from parsed transcript JSON, so they can hold types stdlib
    # `json` refuses -- a parquet TIMESTAMP column arrives as a `datetime`.
    # `to_json_bytes_compact` is what the materialized path uses, so coercion
    # of those, of NaN/Infinity, and of anything unserializable matches it
    # exactly. Values here are small: the large one is spooled.
    emit("{")
    for key, value in info.model_dump(exclude={"metadata"}).items():
        emit(_dumps(key) + ":")
        emit_bytes(to_json_bytes_compact(value))
        emit(",")
    emit('"metadata":{')
    for index, (key, value) in enumerate(_merged_metadata(info, result).items()):
        emit(("," if index else "") + _dumps(key) + ":")
        if value is _SPOOLED_SAMPLE_METADATA:
            # Scan with an overlap: unlike whole items, these chunks are
            # arbitrary byte slices, so a ref can straddle two of them.
            tail = b""
            for chunk in result.metadata_json.chunks():
                chunks.append(chunk)
                attachment_ids.update(
                    match.decode("ascii")
                    for match in ATTACHMENT_REF_BYTES.findall(tail + chunk)
                )
                tail = chunk[-(_REF_OVERLAP):]
        else:
            emit_bytes(to_json_bytes_compact(value))
    emit('},"messages":[')
    for index, message in enumerate(result.messages.items()):
        if index:
            emit(",")
        emit(_dumps(message))
    emit('],"events":[')
    for index, event in enumerate(result.events.items()):
        if index:
            emit(",")
        emit(
            _dumps(
                remap_pool_refs(
                    _drop_unmapped_refs(event, pos_maps) if dropped else event,
                    pos_maps["message_pool"],
                    pos_maps["call_pool"],
                )
            )
        )
    emit('],"timelines":[]}')

    envelope_json = b"".join(chunks)
    chunks.clear()

    pools_json = _dumps(
        {
            "messages": pool_entries["message_pool"],
            "calls": pool_entries["call_pool"],
        }
    )
    attachment_ids.update(ATTACHMENT_REF_PATTERN.findall(pools_json))
    attachments = {
        att_id: content
        for att_id in sorted(attachment_ids)
        if (content := result.blobs.get(att_id)) is not None
    }

    if not (pool_entries["message_pool"] or pool_entries["call_pool"] or attachments):
        return envelope_json, None

    input_data: dict[str, Any] = {
        "messages": pool_entries["message_pool"],
        "calls": pool_entries["call_pool"],
    }
    if attachments:
        input_data["attachments"] = attachments
    return envelope_json, _dumps(input_data).encode("utf-8")


_POOL_FOR_FIELD = {"message": "message_pool", "call": "call_pool"}


def _drop_unmapped_refs(
    event: dict[str, Any], pos_maps: dict[str, dict[int, int]]
) -> dict[str, Any]:
    """Copy of `event` with refs to positions the spool doesn't have removed.

    `remap_pool_refs` looks every referenced position up in the map and would
    raise `KeyError` for one that was never spooled. The materialized path
    expands refs by slicing, which silently drops such positions, so drop
    them here too: the two paths must not diverge on the same input.

    Walks `POOL_REF_FIELDS` for the same reason `collect_pool_ref_positions`
    does -- it stays correct when upstream adds a new `*_refs` field.
    """
    pruned = event
    for field in POOL_REF_FIELDS:
        pruned = _drop_unmapped_refs_at_path(
            pruned, field.path, pos_maps[_POOL_FOR_FIELD[field.pool]]
        )
    return pruned


def _drop_unmapped_refs_at_path(
    node: dict[str, Any], path: tuple[str, ...], pos_map: dict[int, int]
) -> dict[str, Any]:
    """`node` with unmapped positions removed from the refs list at `path`."""
    key, rest = path[0], path[1:]
    child = node.get(key)
    if rest:
        if not isinstance(child, dict):
            return node
        new_child = _drop_unmapped_refs_at_path(child, rest, pos_map)
        return node if new_child is child else {**node, key: new_child}
    if not isinstance(child, list):
        return node
    # Emit one single-position range per surviving position; `remap_pool_refs`
    # re-compresses them into contiguous ranges.
    kept: list[JsonValue] = [
        [position, position + 1]
        for ref in child
        if isinstance(ref, (list, tuple))
        and len(ref) == 2
        and isinstance(ref[0], int)
        and isinstance(ref[1], int)
        for position in range(ref[0], ref[1])
        if position in pos_map
    ]
    return {**node, key: kept}


def _dumps(value: Any) -> str:
    """Compact JSON, matching the recorder's existing column encoding."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _merged_metadata(info: TranscriptInfo, result: StreamParseResult) -> dict[str, Any]:
    """Transcript metadata plus unthinned fields, mirroring handle.load().

    `sample_metadata` maps to `_SPOOLED_SAMPLE_METADATA`, a stand-in the
    caller replaces by copying the value out of the spool: parsing it back
    into objects is exactly what the spool exists to avoid. Key order still
    matches the merge `handle.load()` performs, so the emitted object is
    identical either way.
    """
    overrides: dict[str, Any] = {}
    if result.has_metadata:
        overrides["sample_metadata"] = _SPOOLED_SAMPLE_METADATA
    if result.target is not None:
        overrides["target"] = result.target
    if result.scores:
        overrides["scores"] = result.scores
    return info.metadata.copy() | overrides if overrides else info.metadata
