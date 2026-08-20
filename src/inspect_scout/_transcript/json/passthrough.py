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
from typing import Any, Iterable, Iterator

from inspect_ai.event._pool import (
    POOL_REF_FIELDS,
    remap_pool_refs,
)
from pydantic import JsonValue

from ..._util._json import to_json_bytes_compact
from ..types import Transcript, TranscriptInfo
from .pool import slice_positions
from .reducer import ATTACHMENT_REF_BYTES
from .spool import ByteSpool
from .stream_parse import StreamParseResult

_POOLS = ("message_pool", "call_pool")

# Stand-in for the sample metadata, which is copied from its spool rather than
# parsed; see `_merged_metadata`.
_SPOOLED_SAMPLE_METADATA = object()


def pooled_passthrough(
    info: TranscriptInfo, result: StreamParseResult
) -> tuple[bytes, bytes | None]:
    """Build `(input_json, input_data_json)` from a spooled parse.

    The envelope is emitted incrementally: each message and event is
    serialized as the spool replays it and written to a scratch spool, so
    the full set of items never exists as Python objects at once and no
    ``json.dumps`` ever runs over the whole envelope. Only the finished
    value is read back whole, because a parquet cell is a single value --
    that read is the floor this cannot go below.

    Args:
        info: Transcript metadata for the envelope.
        result: The spooled parse to copy from.

    Returns:
        The `input` and `input_data` column values, as UTF-8 bytes rather
        than ``str``: these go straight into a parquet column, and decoding
        would double a non-ASCII value in memory for nothing.
    """
    # Pass 1: which pool positions and attachments do the events reference?
    pool_lens = {pool: result.blobs.pool_len(pool) for pool in _POOLS}
    referenced = _referenced_positions(result.events.items(), pool_lens)

    # Position maps and the emitted pools both derive from `surviving`, so
    # they cannot disagree about which entries exist -- a mismatch would
    # silently point refs at the wrong entry. Ascending order keeps pool
    # ordering stable. The entries themselves are fetched later, one at a
    # time, rather than held as an object graph.
    surviving: dict[str, list[int]] = {}
    pos_maps: dict[str, dict[int, int]] = {}
    for pool in _POOLS:
        surviving[pool] = [
            position
            for position in sorted(referenced[pool])
            if result.blobs.has((pool, position))
        ]
        pos_maps[pool] = {old: new for new, old in enumerate(surviving[pool])}

    # Pass 2: re-emit events with refs remapped onto the pruned pools.
    #
    # Attachment ids may be referenced from messages, from events, or from
    # inside a pool entry -- scan all three or refs dangle. Each chunk is
    # scanned as it is emitted: an id cannot straddle two chunks because every
    # item is serialized whole, so this sees exactly what a scan of the
    # finished envelope would.
    #
    # Chunks accumulate on a spool, not in memory: only the finished envelope
    # has to exist contiguously, and holding the pieces as well would double
    # the peak on a multi-GB transcript.
    envelope = ByteSpool(result.spool_dir)
    try:
        attachment_ids: set[str] = set()

        def emit_bytes(data: bytes | memoryview) -> None:
            attachment_ids.update(
                match.decode("ascii") for match in ATTACHMENT_REF_BYTES.findall(data)
            )
            envelope.write(data)

        def emit(text: str) -> None:
            emit_bytes(text.encode("utf-8"))

        # Everything up to "messages", written key by key rather than dumped
        # whole -- and sample metadata, most of the envelope on a
        # metadata-dominated transcript, is copied straight from its spool
        # without ever becoming objects or a `str`.
        #
        # These values come from index rows rather than parsed transcript JSON,
        # so they can hold types stdlib `json` refuses -- a parquet TIMESTAMP
        # column arrives as a `datetime`. `to_json_bytes_compact` is what the
        # materialized path uses, so coercion of those, of NaN/Infinity, and of
        # anything unserializable matches it exactly.
        #
        # The field set must match that path too: it builds a `Transcript`, so
        # subclass-only fields (an index row carries `filename`) are dropped,
        # and `to_json_safe` passes exclude_none=True, so unset fields are
        # omitted rather than emitted as null.
        emit("{")
        for key, value in info.model_dump(exclude={"metadata"}).items():
            if value is None or key not in Transcript.model_fields:
                continue
            emit(_dumps(key) + ":")
            emit_bytes(to_json_bytes_compact(value))
            emit(",")
        emit('"metadata":{')
        for index, (key, value) in enumerate(_merged_metadata(info, result).items()):
            emit(("," if index else "") + _dumps(key) + ":")
            if value is _SPOOLED_SAMPLE_METADATA:
                # Copied through without scanning for attachment refs: inspect_ai
                # never writes one here. `condense_sample` updates only input,
                # messages, events, error_retries, attachments and events_data --
                # metadata is not walked -- and scanning it would mean a regex
                # pass over the largest section of a metadata-heavy transcript.
                for chunk in result.metadata_json.chunks():
                    envelope.write(chunk)
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
                        _normalize_pool_refs(event, pos_maps, pool_lens),
                        pos_maps["message_pool"],
                        pos_maps["call_pool"],
                    )
                )
            )
        emit('],"timelines":[]}')

        envelope_json = envelope.read()
    finally:
        envelope.close()

    return envelope_json, _emit_input_data(result, surviving, attachment_ids)


def _emit_input_data(
    result: StreamParseResult,
    surviving: dict[str, list[int]],
    attachment_ids: set[str],
) -> bytes:
    """Serialize the `input_data` column through a scratch spool.

    Holds one pool entry or attachment at a time, leaving the single
    read-back a parquet cell requires as the only whole-value copy -- the
    bound the envelope keeps, and for the same reason: on a pool-dominated
    transcript this value is the largest thing in the process.
    """
    # Entries are parsed and re-serialized individually rather than spliced
    # verbatim, so the bytes match a dump of the whole structure. Attachments
    # come last because their ids are only complete once every pool entry has
    # been scanned.
    spool = ByteSpool(result.spool_dir)
    try:

        def emit(text: str) -> None:
            data = text.encode("utf-8")
            attachment_ids.update(
                match.decode("ascii") for match in ATTACHMENT_REF_BYTES.findall(data)
            )
            spool.write(data)

        for prefix, pool in (
            ('{"messages":[', "message_pool"),
            ('],"calls":[', "call_pool"),
        ):
            emit(prefix)
            for index, position in enumerate(surviving[pool]):
                raw = result.blobs.get((pool, position))
                # `surviving` was built from has(), so a miss here means the
                # spool changed underneath us. Dropping the entry would shift
                # every later position out from under the maps built above.
                assert raw is not None, f"{pool} lost position {position}"
                emit(("," if index else "") + _dumps(json.loads(raw)))
        spool.write(b"]")

        # Ids with nothing spooled are dangling refs; skipping them matches
        # what the materialized path ships.
        written = False
        for att_id in sorted(attachment_ids):
            content = result.blobs.get(att_id)
            if content is None:
                continue
            spool.write(b',"attachments":{' if not written else b",")
            written = True
            spool.write((_dumps(att_id) + ":" + _dumps(content)).encode("utf-8"))
        if written:
            spool.write(b"}")

        spool.write(b"}")
        return spool.read()
    finally:
        spool.close()


_POOL_FOR_FIELD = {"message": "message_pool", "call": "call_pool"}


def _ref_positions(refs: Any, pool_len: int) -> Iterator[int]:
    """Pool positions a raw `*_refs` list selects, under slicing semantics."""
    if not isinstance(refs, list):
        return
    for ref in refs:
        if (
            isinstance(ref, (list, tuple))
            and len(ref) == 2
            and isinstance(ref[0], int)
            and isinstance(ref[1], int)
        ):
            yield from slice_positions(ref[0], ref[1], pool_len)


def _referenced_positions(
    events: Iterable[dict[str, Any]], pool_lens: dict[str, int]
) -> dict[str, set[int]]:
    """Pool positions the events reference.

    Replaces upstream `collect_pool_ref_positions`, which enumerates each
    range verbatim: a negative bound there counts from zero rather than the
    end, and a huge one walks the whole span that slicing would truncate.
    """
    # Walks POOL_REF_FIELDS so a new upstream `*_refs` field is picked up.
    referenced: dict[str, set[int]] = {pool: set() for pool in _POOLS}
    for event in events:
        for field in POOL_REF_FIELDS:
            value: Any = event
            for key in field.path:
                value = value.get(key) if isinstance(value, dict) else None
            pool = _POOL_FOR_FIELD[field.pool]
            referenced[pool].update(_ref_positions(value, pool_lens[pool]))
    return referenced


def _normalize_pool_refs(
    event: dict[str, Any],
    pos_maps: dict[str, dict[int, int]],
    pool_lens: dict[str, int],
) -> dict[str, Any]:
    """Copy of `event` with refs rewritten to the positions slicing selects.

    Both corrections are needed before `remap_pool_refs`, which enumerates
    each range verbatim and looks every position up in the map: bounds are
    resolved by slicing, and positions the spool never held are dropped --
    silent under slicing, a `KeyError` under a map lookup.
    """
    pruned = event
    for field in POOL_REF_FIELDS:
        pool = _POOL_FOR_FIELD[field.pool]
        pruned = _normalize_pool_refs_at_path(
            pruned, field.path, pos_maps[pool], pool_lens[pool]
        )
    return pruned


def _normalize_pool_refs_at_path(
    node: dict[str, Any],
    path: tuple[str, ...],
    pos_map: dict[int, int],
    pool_len: int,
) -> dict[str, Any]:
    """`node` with the refs list at `path` rewritten to surviving positions."""
    key, rest = path[0], path[1:]
    child = node.get(key)
    if rest:
        if not isinstance(child, dict):
            return node
        new_child = _normalize_pool_refs_at_path(child, rest, pos_map, pool_len)
        return node if new_child is child else {**node, key: new_child}
    if not isinstance(child, list):
        return node
    # Emit one single-position range per surviving position; `remap_pool_refs`
    # re-compresses them into contiguous ranges.
    kept: list[JsonValue] = [
        [position, position + 1]
        for position in _ref_positions(child, pool_len)
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
