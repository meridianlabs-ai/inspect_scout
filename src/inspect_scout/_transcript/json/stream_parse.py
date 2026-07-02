"""Single-pass spool-building parse and replay for large transcripts.

Parses the sample JSON once, spooling filtered messages/events (unresolved)
to JSONL and ALL attachments + pool items to an offset-indexed blob spool.
Replay (see replay_* functions) resolves attachment:// refs and pool ranges
per item, validates via TypeAdapter, and yields -- O(one item) memory.

Spooling all attachments is required (refs inside events_data pool items
arrive after the attachments section) and fixes the pool-attachment
resolution bug in the in-memory path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, AsyncIterable, Iterator

import ijson  # type: ignore
from ijson.utils import coroutine as _ijson_coroutine  # type: ignore
from inspect_ai._util.async_bytes_reader import adapt_to_reader
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from pydantic import TypeAdapter

from ..types import EventFilter, MessageFilter
from .reducer import (
    ATTACHMENTS_PREFIX,
    CALL_POOL_ITEM_PREFIX,
    EVENTS_DATA_CALLS_ITEM_PREFIX,
    EVENTS_DATA_MESSAGES_ITEM_PREFIX,
    EVENTS_ITEM_PREFIX,
    MESSAGE_POOL_ITEM_PREFIX,
    MESSAGES_ITEM_PREFIX,
    METADATA_PREFIX,
    SCORES_PREFIX,
    TARGET_PREFIX,
    TIMELINES_ITEM_PREFIX,
    CoroutineGen,
    ListProcessingConfig,
    ParseState,
    _item_coroutine,
    _unfiltered_item_coroutine,
    metadata_coroutine,
    scores_coroutine,
    target_coroutine,
    timeline_item_coroutine,
)
from .spool import BlobSpool, ItemSpool

# Section constants for prefix classification (mirrors load_filtered.py)
_SECTION_OTHER = 0
_SECTION_MESSAGES = 1
_SECTION_EVENTS = 2
_SECTION_ATTACHMENTS = 3
_SECTION_METADATA = 4
_SECTION_TIMELINES = 5
_SECTION_TARGET = 6
_SECTION_SCORES = 7
_SECTION_MESSAGE_POOL = 8
_SECTION_CALL_POOL = 9

_MESSAGES_ITEM_PREFIX_LEN = len(MESSAGES_ITEM_PREFIX)
_EVENTS_ITEM_PREFIX_LEN = len(EVENTS_ITEM_PREFIX)
_ATTACHMENTS_PREFIX_LEN = len(ATTACHMENTS_PREFIX)
_METADATA_PREFIX_LEN = len(METADATA_PREFIX)
_TIMELINES_ITEM_PREFIX_LEN = len(TIMELINES_ITEM_PREFIX)
_SCORES_PREFIX_LEN = len(SCORES_PREFIX)
_TARGET_PREFIX_LEN = len(TARGET_PREFIX)
_MESSAGE_POOL_ITEM_PREFIX_LEN = len(MESSAGE_POOL_ITEM_PREFIX)
_CALL_POOL_ITEM_PREFIX_LEN = len(CALL_POOL_ITEM_PREFIX)
_EVENTS_DATA_MESSAGES_ITEM_PREFIX_LEN = len(EVENTS_DATA_MESSAGES_ITEM_PREFIX)
_EVENTS_DATA_CALLS_ITEM_PREFIX_LEN = len(EVENTS_DATA_CALLS_ITEM_PREFIX)
# "target" vs "timelines" — discriminate on 2nd char (derived from constant)
_TARGET_CHAR1 = TARGET_PREFIX[1]
_MIN_SECTION_PREFIX_LEN = min(
    _MESSAGES_ITEM_PREFIX_LEN,
    _EVENTS_ITEM_PREFIX_LEN,
    _ATTACHMENTS_PREFIX_LEN,
    _METADATA_PREFIX_LEN,
    _TIMELINES_ITEM_PREFIX_LEN,
    _SCORES_PREFIX_LEN,
    _TARGET_PREFIX_LEN,
    _MESSAGE_POOL_ITEM_PREFIX_LEN,
    _CALL_POOL_ITEM_PREFIX_LEN,
    _EVENTS_DATA_MESSAGES_ITEM_PREFIX_LEN,
    _EVENTS_DATA_CALLS_ITEM_PREFIX_LEN,
)


class _SpoolSink(list):  # type: ignore[type-arg]
    """List stand-in whose append writes to an ItemSpool."""

    def __init__(self, spool: ItemSpool) -> None:
        super().__init__()
        self._spool = spool

    def append(self, item: Any) -> None:
        self._spool.append(item)


class _PoolSink(list):  # type: ignore[type-arg]
    """List stand-in whose append writes positional pool entries to a BlobSpool."""

    def __init__(self, blobs: BlobSpool, pool_name: str) -> None:
        super().__init__()
        self._blobs = blobs
        self._pool_name = pool_name
        self._i = 0

    def append(self, item: Any) -> None:
        self._blobs.put(
            (self._pool_name, self._i),
            json.dumps(item, ensure_ascii=False, separators=(",", ":")),
        )
        self._i += 1


@dataclass
class StreamParseResult:
    """Result of a single-pass spool-building parse."""

    messages: ItemSpool
    events: ItemSpool
    blobs: BlobSpool
    metadata: dict[str, Any] = field(default_factory=dict)
    target: str | list[str] | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    timelines: list[dict[str, Any]] = field(default_factory=list)

    def close(self) -> None:
        """Close all spools (idempotent)."""
        self.messages.close()
        self.events.close()
        self.blobs.close()


async def stream_parse_to_spool(
    sample_bytes: IO[bytes] | AsyncIterable[bytes],
    messages_filter: MessageFilter,
    events_filter: EventFilter,
    spool_dir: Path,
) -> StreamParseResult:
    """Parse sample JSON in a single ijson pass, spooling to disk.

    Filtered messages/events are appended (as raw, unresolved dicts) to
    JSONL item spools. ALL attachments and ALL pool items (message_pool /
    call_pool, in either on-disk shape) are spooled to an offset-indexed
    blob spool, regardless of filters -- attachment refs inside pool items
    are only known after later replay, so filtering pools/attachments here
    would be unsound.

    Args:
        sample_bytes: Byte stream of JSON sample data.
        messages_filter: Filter for message roles (None=exclude all,
            "all"=include all, list=include matching).
        events_filter: Filter for event types (None=exclude all, "all"=include
            all, list=include matching).
        spool_dir: Directory in which to create spool files.

    Returns:
        StreamParseResult with spools populated and small fields
        (metadata/target/scores/timelines) resolved in memory.

    Raises:
        ijson.JSONError: On malformed JSON (e.g. NaN/Inf without use_float
            support); spools are closed before re-raising.
    """
    messages_config = (
        ListProcessingConfig(
            array_item_prefix="messages.item",
            filter_field="role",
            filter_list=messages_filter,  # type:ignore
        )
        if messages_filter is not None
        else None
    )

    events_config = (
        ListProcessingConfig(
            array_item_prefix="events.item",
            filter_field="event",
            filter_list=events_filter,  # type:ignore
        )
        if events_filter is not None
        else None
    )

    state = ParseState()

    messages_spool = ItemSpool(spool_dir)
    events_spool = ItemSpool(spool_dir)
    blobs = BlobSpool(spool_dir)
    result = StreamParseResult(messages_spool, events_spool, blobs)

    messages_coro = (
        _item_coroutine(_SpoolSink(messages_spool), set(), messages_config)
        if messages_config
        else None
    )
    events_coro = (
        _item_coroutine(_SpoolSink(events_spool), set(), events_config)
        if events_config
        else None
    )
    timelines_coro = timeline_item_coroutine(state)
    attachments_coro = _spool_attachments_coroutine(blobs)
    metadata_coro = metadata_coroutine(state)
    target_coro: Any = target_coroutine(state)
    scores_coro = scores_coroutine(state)
    # Pools are spooled unconditionally (cost is negligible; keeps one path).
    message_pool_coros = [
        _unfiltered_item_coroutine(
            _PoolSink(blobs, "message_pool"), MESSAGE_POOL_ITEM_PREFIX
        ),
        _unfiltered_item_coroutine(
            _PoolSink(blobs, "message_pool"), EVENTS_DATA_MESSAGES_ITEM_PREFIX
        ),
    ]
    call_pool_coros = [
        _unfiltered_item_coroutine(
            _PoolSink(blobs, "call_pool"), CALL_POOL_ITEM_PREFIX
        ),
        _unfiltered_item_coroutine(
            _PoolSink(blobs, "call_pool"), EVENTS_DATA_CALLS_ITEM_PREFIX
        ),
    ]

    last_prefix = ""
    current_section = _SECTION_OTHER

    try:
        async with adapt_to_reader(sample_bytes) as reader:
            async for prefix, event, value in ijson.parse_async(reader, use_float=True):
                # Inline prefix classification for performance (56M+ calls in
                # hot path). WARNING: every operation here can run millions of
                # times per parse. Avoid string slicing, startswith, or any
                # allocation in common paths. Profile before changing.
                if prefix != last_prefix:
                    last_prefix = prefix
                    p_len = len(prefix)
                    if p_len == 0 or prefix[0] not in ("m", "e", "a", "t", "s", "c"):
                        current_section = _SECTION_OTHER
                    elif p_len < _MIN_SECTION_PREFIX_LEN:
                        # Short prefixes: "scores" (6), "target" (6)
                        if prefix == "scores":
                            current_section = _SECTION_SCORES
                        elif prefix == "target":
                            current_section = _SECTION_TARGET
                        else:
                            current_section = _SECTION_OTHER
                    elif prefix[0] == "m":
                        # Both "messages" and "metadata" start with "me", check
                        # 3rd char (safe because we already checked p_len >=
                        # _MIN_SECTION_PREFIX_LEN)
                        if (
                            p_len >= _MESSAGES_ITEM_PREFIX_LEN
                            and prefix[2] == "s"
                            and prefix[:_MESSAGES_ITEM_PREFIX_LEN]
                            == MESSAGES_ITEM_PREFIX
                        ):
                            current_section = _SECTION_MESSAGES
                        elif prefix[2] == "t" and (
                            prefix == "metadata" or prefix.startswith(METADATA_PREFIX)
                        ):
                            current_section = _SECTION_METADATA
                        elif (
                            p_len >= _MESSAGE_POOL_ITEM_PREFIX_LEN
                            and prefix[:_MESSAGE_POOL_ITEM_PREFIX_LEN]
                            == MESSAGE_POOL_ITEM_PREFIX
                        ):
                            current_section = _SECTION_MESSAGE_POOL
                        else:
                            current_section = _SECTION_OTHER
                    elif prefix[0] == "e":
                        # events array, or one of the events_data.* pool
                        # sub-arrays.
                        if (
                            p_len >= _EVENTS_ITEM_PREFIX_LEN
                            and prefix[:_EVENTS_ITEM_PREFIX_LEN] == EVENTS_ITEM_PREFIX
                        ):
                            current_section = _SECTION_EVENTS
                        elif (
                            p_len >= _EVENTS_DATA_MESSAGES_ITEM_PREFIX_LEN
                            and prefix[:_EVENTS_DATA_MESSAGES_ITEM_PREFIX_LEN]
                            == EVENTS_DATA_MESSAGES_ITEM_PREFIX
                        ):
                            current_section = _SECTION_MESSAGE_POOL
                        elif (
                            p_len >= _EVENTS_DATA_CALLS_ITEM_PREFIX_LEN
                            and prefix[:_EVENTS_DATA_CALLS_ITEM_PREFIX_LEN]
                            == EVENTS_DATA_CALLS_ITEM_PREFIX
                        ):
                            current_section = _SECTION_CALL_POOL
                        else:
                            current_section = _SECTION_OTHER
                    elif (
                        prefix[0] == "a"
                        and p_len >= _ATTACHMENTS_PREFIX_LEN
                        and prefix[:_ATTACHMENTS_PREFIX_LEN] == ATTACHMENTS_PREFIX
                    ):
                        current_section = _SECTION_ATTACHMENTS
                    elif (
                        prefix[0] == "c"
                        and p_len >= _CALL_POOL_ITEM_PREFIX_LEN
                        and prefix[:_CALL_POOL_ITEM_PREFIX_LEN] == CALL_POOL_ITEM_PREFIX
                    ):
                        current_section = _SECTION_CALL_POOL
                    elif prefix[0] == "t":
                        if prefix[1] == _TARGET_CHAR1:
                            current_section = _SECTION_TARGET
                        elif (
                            p_len >= _TIMELINES_ITEM_PREFIX_LEN
                            and prefix[:_TIMELINES_ITEM_PREFIX_LEN]
                            == TIMELINES_ITEM_PREFIX
                        ):
                            current_section = _SECTION_TIMELINES
                        else:
                            current_section = _SECTION_OTHER
                    elif (
                        prefix[0] == "s"
                        and prefix[:_SCORES_PREFIX_LEN] == SCORES_PREFIX
                    ):
                        current_section = _SECTION_SCORES
                    else:
                        current_section = _SECTION_OTHER

                # Dispatch to coroutines (optimized to avoid redundant None
                # checks)
                if current_section == _SECTION_MESSAGES and messages_coro:
                    messages_coro.send((prefix, event, value))
                elif current_section == _SECTION_EVENTS and events_coro:
                    events_coro.send((prefix, event, value))
                elif current_section == _SECTION_ATTACHMENTS:
                    attachments_coro.send((prefix, event, value))
                elif current_section == _SECTION_METADATA:
                    metadata_coro.send((prefix, event, value))
                elif current_section == _SECTION_TARGET and target_coro is not None:
                    try:
                        target_coro.send((prefix, event, value))
                    except StopIteration:
                        target_coro = None
                elif current_section == _SECTION_TIMELINES:
                    timelines_coro.send((prefix, event, value))
                elif current_section == _SECTION_SCORES:
                    scores_coro.send((prefix, event, value))
                elif current_section == _SECTION_MESSAGE_POOL:
                    for coro in message_pool_coros:
                        coro.send((prefix, event, value))
                elif current_section == _SECTION_CALL_POOL:
                    for coro in call_pool_coros:
                        coro.send((prefix, event, value))

        result.metadata = state.metadata
        result.target = state.target
        result.scores = state.scores
        result.timelines = state.timelines
        return result
    except BaseException:
        result.close()
        raise


@_ijson_coroutine  # type: ignore
def _spool_attachments_coroutine(blobs: BlobSpool) -> CoroutineGen:  # pragma: no cover
    """Coroutine that spools ALL attachments, unconditionally (no ref check).

    Modeled on ``attachments_coroutine`` (reducer.py) minus the
    ``attachment_refs`` membership check: refs inside pool items only
    become known during replay, after this parse has already moved past
    the attachments section, so every attachment must be kept.
    """
    attachments_prefix_len = len(ATTACHMENTS_PREFIX)
    while True:
        prefix, event, value = yield
        if event != "string":
            continue
        if not prefix.startswith(ATTACHMENTS_PREFIX):
            continue
        end = prefix.find(".", attachments_prefix_len)
        attachment_id = (
            prefix[attachments_prefix_len:]
            if end == -1
            else prefix[attachments_prefix_len:end]
        )
        blobs.put(attachment_id, value)


_ATTACHMENT_PATTERN = re.compile(r"attachment://([a-f0-9]{32})")
_CHAT_MESSAGE_ADAPTER: TypeAdapter[ChatMessage] = TypeAdapter(ChatMessage)
_EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)


def _resolve_strings(obj: Any, blobs: BlobSpool) -> Any:
    """Recursively resolve ``attachment://<id>`` refs against ``blobs``.

    Mirrors ``_resolve_dict_attachments`` in load_filtered.py but looks
    up attachment ids in the on-disk BlobSpool rather than an in-memory
    dict, mutating dict/list containers in place.
    """
    if isinstance(obj, str):
        if "attachment://" not in obj:
            return obj
        return _ATTACHMENT_PATTERN.sub(
            lambda m: blobs.get(m.group(1)) or m.group(0), obj
        )
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _resolve_strings(v, blobs)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _resolve_strings(v, blobs)
        return obj
    return obj


def _expand_pool_range(
    refs: list[list[int]], pool_name: str, blobs: BlobSpool
) -> list[Any]:
    """Expand range-encoded pool refs by fetching items from ``blobs``.

    Each fetched pool item is resolved for attachment refs before being
    returned -- pool items are spooled unresolved (attachments arrive
    after pools in the JSON), so this fetch-then-resolve step is where
    the pool-attachment bug fix lives.
    """
    result: list[Any] = []
    for start, end_exclusive in refs:
        for i in range(start, end_exclusive):
            raw = blobs.get((pool_name, i))
            if raw is not None:
                result.append(_resolve_strings(json.loads(raw), blobs))
    return result


def resolve_item_dict(item: dict[str, Any], blobs: BlobSpool) -> dict[str, Any]:
    """Resolve attachment refs and pool ranges on a spooled item, in place.

    Expands ``input_refs``/``call_refs`` positional ranges (same semantics
    as ``_resolve_events_pools`` in pool.py) by fetching pool entries from
    ``blobs`` and resolving attachment refs inside them -- fixing the bug
    where pool-item attachments were never resolved -- then resolves
    ``attachment://`` refs throughout the rest of the item.
    """
    input_refs = item.get("input_refs")
    if input_refs and blobs.pool_len("message_pool"):
        item["input"] = _expand_pool_range(input_refs, "message_pool", blobs)
        item.pop("input_refs", None)
    call = item.get("call")
    if call and call.get("call_refs") is not None and blobs.pool_len("call_pool"):
        key = call.get("call_key", "messages")
        call.setdefault("request", {})[key] = _expand_pool_range(
            call["call_refs"], "call_pool", blobs
        )
        call.pop("call_refs", None)
        call.pop("call_key", None)
    _resolve_strings(item, blobs)
    return item


def replay_messages(result: StreamParseResult) -> Iterator[ChatMessage]:
    """Replay spooled messages, resolving attachments and validating each."""
    for item in result.messages.items():
        yield _CHAT_MESSAGE_ADAPTER.validate_python(
            resolve_item_dict(item, result.blobs)
        )


def replay_events(result: StreamParseResult) -> Iterator[Event]:
    """Replay spooled events, resolving attachments/pools and validating each."""
    for item in result.events.items():
        yield _EVENT_ADAPTER.validate_python(resolve_item_dict(item, result.blobs))
