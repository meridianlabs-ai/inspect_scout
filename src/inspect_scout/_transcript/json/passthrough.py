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

from inspect_ai.event._pool import collect_pool_ref_positions, remap_pool_refs

from ..types import TranscriptInfo
from .reducer import ATTACHMENT_REF_PATTERN
from .stream_parse import StreamParseResult

_POOLS = ("message_pool", "call_pool")


def pooled_passthrough(
    info: TranscriptInfo, result: StreamParseResult
) -> tuple[str, str | None]:
    """Build `(input_json, input_data_json)` from a spooled parse.

    Args:
        info: Transcript metadata for the envelope.
        result: The spooled parse to copy from.

    Returns:
        The `input` column value, and the `input_data` column value or None
        when nothing is pooled and no attachments are referenced.
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
    # Ascending order keeps pool ordering stable.
    pool_entries: dict[str, list[Any]] = {}
    pos_maps: dict[str, dict[int, int]] = {}
    for pool in _POOLS:
        kept = sorted(p for p in referenced[pool] if p < result.blobs.pool_len(pool))
        pos_maps[pool] = {old: new for new, old in enumerate(kept)}
        pool_entries[pool] = [
            json.loads(raw)
            for raw in (result.blobs.get((pool, old)) for old in kept)
            if raw is not None
        ]

    # Pass 2: re-emit events with refs remapped onto the pruned pools.
    events = [
        remap_pool_refs(event, pos_maps["message_pool"], pos_maps["call_pool"])
        for event in result.events.items()
    ]

    envelope: dict[str, Any] = {
        **info.model_dump(exclude={"metadata"}),
        "metadata": _merged_metadata(info, result),
        "messages": list(result.messages.items()),
        "events": events,
        "timelines": [],
    }
    envelope_json = _dumps(envelope)
    pools_json = _dumps(
        {
            "messages": pool_entries["message_pool"],
            "calls": pool_entries["call_pool"],
        }
    )

    # Attachment ids may be referenced from messages, from events, or from
    # inside a pool entry -- scan all three or refs dangle. Scanning the two
    # serialized forms we already have to produce avoids serializing every
    # item a second time just to search it.
    attachment_ids = set(ATTACHMENT_REF_PATTERN.findall(envelope_json)) | set(
        ATTACHMENT_REF_PATTERN.findall(pools_json)
    )
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
    return envelope_json, _dumps(input_data)


def _dumps(value: Any) -> str:
    """Compact JSON, matching the recorder's existing column encoding."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _merged_metadata(info: TranscriptInfo, result: StreamParseResult) -> dict[str, Any]:
    """Transcript metadata plus unthinned fields, mirroring handle.load()."""
    overrides: dict[str, Any] = {}
    if result.metadata:
        overrides["sample_metadata"] = result.metadata
    if result.target is not None:
        overrides["target"] = result.target
    if result.scores:
        overrides["scores"] = result.scores
    return info.metadata.copy() | overrides if overrides else info.metadata
