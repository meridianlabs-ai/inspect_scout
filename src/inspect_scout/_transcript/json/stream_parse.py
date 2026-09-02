"""Single-pass spool-building parse and replay for large transcripts.

Parses the sample JSON once, spooling filtered messages/events (unresolved)
to JSONL and every attachment (plus, when events are collected, the pool
items they can reference) to an offset-indexed blob spool. Replay (see
``replay_*``) resolves ``attachment://`` refs and pool ranges per item,
validates via TypeAdapter, and yields -- O(one item) memory.

Every attachment must be spooled: refs inside events_data pool items arrive
after the attachments section, so they cannot be filtered during the parse.
"""

from __future__ import annotations

import contextlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, AsyncIterable, Iterator

import ijson  # type: ignore[import-untyped]  # no published stubs
from inspect_ai._util.async_bytes_reader import adapt_to_reader
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from pydantic import TypeAdapter, ValidationError

from ..types import EventFilter, MessageFilter
from .pool import slice_positions
from .reducer import (
    ATTACHMENT_PREFIX,
    ATTACHMENT_PREFIX_LEN,
    ATTACHMENT_REF_LEN,
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
    _coroutine,
    _item_coroutine,
    _unfiltered_item_coroutine,
    scores_coroutine,
    spooling_metadata_coroutine,
    target_coroutine,
)
from .spool import BlobSpool, ByteSpool, ItemSpool

# Section constants for prefix classification. Mirrors the `_SECTION_*` block
# in load_filtered.py minus _SECTION_TIMELINES (streaming skips timelines --
# see the note on `elif prefix[0] == "t":` below). Keep both constant blocks
# and both classify/dispatch loops (the HOT PATH comment below, and the one in
# load_filtered.py's `_parse_and_filter`) in sync when either changes.
#
# One deliberate asymmetry: load_filtered.py sets `state.events_seen` in its
# events branch, to decide how much of the attachment table to retain. This
# path retains all of it unconditionally, so there is nothing to gate -- do
# not add it here for parity.
_SECTION_OTHER = 0
_SECTION_MESSAGES = 1
_SECTION_EVENTS = 2
_SECTION_ATTACHMENTS = 3
_SECTION_METADATA = 4
# 5 is load_filtered.py's _SECTION_TIMELINES, skipped here. The gap is
# deliberate: matching numbers keep the two blocks diffable.
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


class _PoolSink:
    """ItemSink whose append writes positional pool entries to a BlobSpool."""

    def __init__(self, blobs: BlobSpool, pool_name: str) -> None:
        self._blobs = blobs
        self._pool_name = pool_name
        self._i = 0

    def append(self, item: dict[str, Any]) -> None:
        self._blobs.put(
            (self._pool_name, self._i),
            json.dumps(item, ensure_ascii=False, separators=(",", ":")),
        )
        self._i += 1


class _ChunkReader(io.RawIOBase):
    """Read-only file over an iterator of byte chunks.

    Tracks a cursor into the current chunk rather than re-slicing it: a
    consumer reading a 1 MB chunk in small reads would otherwise recopy the
    remainder on every one.
    """

    def __init__(self, chunks: Iterator[bytes | bytearray]) -> None:
        self._chunks = chunks
        self._buffer: bytes | bytearray = b""
        self._pos = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int:
        while self._pos >= len(self._buffer):
            try:
                self._buffer = next(self._chunks)
            except StopIteration:
                return 0
            self._pos = 0
        count = min(len(buffer), len(self._buffer) - self._pos)
        buffer[:count] = self._buffer[self._pos : self._pos + count]
        self._pos += count
        return count


@dataclass
class StreamParseResult:
    """Result of a single-pass spool-building parse."""

    messages: ItemSpool
    events: ItemSpool
    blobs: BlobSpool
    metadata_json: ByteSpool
    spool_dir: Path
    """Where these spools live, so consumers can open their own alongside."""
    target: str | list[str] | None = None
    scores: dict[str, Any] = field(default_factory=dict)

    @property
    def has_metadata(self) -> bool:
        """Whether sample metadata is present and non-empty.

        Mirrors the truthiness of the dict this used to be: an absent section
        spools nothing, and an empty object spools exactly ``{}``.
        """
        return len(self.metadata_json) > 2

    def metadata(self) -> dict[str, Any]:
        """Sample metadata as objects, parsed from the spool on each call.

        A method rather than a field because this is the expensive thing the
        spool exists to avoid: for a metadata-heavy transcript the result can
        be gigabytes. Deliberately not cached -- holding it would reinstate
        the retention this spool removes. Call it once and keep the result if
        you need it repeatedly.
        """
        if not self.has_metadata:
            return {}
        # Parsed from the spool's chunks rather than from one contiguous
        # `read()`: for a metadata-dominated transcript that buffer is itself
        # gigabytes, and it would sit alongside the object graph being built
        # from it. `use_float` matches stdlib `json` (ijson yields `Decimal`
        # otherwise), so the objects -- and anything reserialized from them --
        # are identical either way.
        parsed: dict[str, Any] = next(
            ijson.items(_ChunkReader(self.metadata_json.chunks()), "", use_float=True)
        )
        return parsed

    def close(self) -> None:
        """Close all spools (idempotent)."""
        self.messages.close()
        self.events.close()
        self.blobs.close()
        self.metadata_json.close()


async def stream_parse_to_spool(
    sample_bytes: IO[bytes] | AsyncIterable[bytes],
    messages_filter: MessageFilter,
    events_filter: EventFilter,
    spool_dir: Path,
) -> StreamParseResult:
    """Parse sample JSON in a single ijson pass, spooling to disk.

    Filtered messages/events are appended (as raw, unresolved dicts) to JSONL
    item spools. ALL attachments are spooled regardless of filters: refs
    inside pool items are only known during replay, so filtering attachments
    here would be unsound. Pool items are spooled only when events are
    collected, since only an event can carry a pool ref.

    Args:
        sample_bytes: Byte stream of JSON sample data.
        messages_filter: Filter for message roles (None=exclude all,
            "all"=include all, list=include matching).
        events_filter: Filter for event types (None=exclude all, "all"=include
            all, list=include matching).
        spool_dir: Directory in which to create spool files.

    Returns:
        StreamParseResult with spools populated; ``target`` and ``scores``
        are small enough to hold in memory, metadata is spooled. The sample's
        ``timelines`` section is neither spooled nor returned --
        ``StreamParseResult`` has no field for it, so a transcript
        materialized from this parse has ``timelines == []`` even when the
        sample carried some. See the note on the ``"t"`` branch below.

    Raises:
        ijson.JSONError: On malformed JSON (e.g. NaN/Inf without use_float
            support); spools are closed before re-raising.
    """
    messages_config = (
        ListProcessingConfig(
            array_item_prefix="messages.item",
            filter_field="role",
            filter_list=messages_filter,
        )
        if messages_filter is not None
        else None
    )

    events_config = (
        ListProcessingConfig(
            array_item_prefix="events.item",
            filter_field="event",
            filter_list=events_filter,
        )
        if events_filter is not None
        else None
    )

    state = ParseState()

    # Unwind already-opened spools if a later constructor fails (e.g. EMFILE /
    # ENOSPC): until `result` exists, nothing else can close them. Disarmed
    # via pop_all() once all four are open; from then on the
    # `except BaseException: result.close()` below owns cleanup.
    with contextlib.ExitStack() as unwind:
        messages_spool = ItemSpool(spool_dir)
        unwind.callback(messages_spool.close)
        events_spool = ItemSpool(spool_dir)
        unwind.callback(events_spool.close)
        blobs = BlobSpool(spool_dir)
        unwind.callback(blobs.close)
        metadata_spool = ByteSpool(spool_dir)
        unwind.pop_all()
    result = StreamParseResult(
        messages_spool, events_spool, blobs, metadata_spool, spool_dir
    )

    messages_coro = (
        _item_coroutine(messages_spool, set(), messages_config)
        if messages_config
        else None
    )
    events_coro = (
        _item_coroutine(events_spool, set(), events_config) if events_config else None
    )
    attachments_coro = _spool_attachments_coroutine(blobs)
    metadata_coro = spooling_metadata_coroutine(metadata_spool.write)
    target_coro: CoroutineGen | None = target_coroutine(state)
    scores_coro = scores_coroutine(state)
    # One sink per pool, shared by both on-disk shapes: they carry the same
    # pool, so a second sink would restart the positional counter and overwrite
    # the first shape's entries. Only built when events are collected -- pool
    # refs live on events, so nothing else can fetch them (load_filtered.py
    # gates its own pool coroutines the same way).
    message_pool_coros: list[CoroutineGen] = []
    call_pool_coros: list[CoroutineGen] = []
    if events_config:
        message_sink = _PoolSink(blobs, "message_pool")
        message_pool_coros = [
            _unfiltered_item_coroutine(message_sink, MESSAGE_POOL_ITEM_PREFIX),
            _unfiltered_item_coroutine(message_sink, EVENTS_DATA_MESSAGES_ITEM_PREFIX),
        ]
        call_sink = _PoolSink(blobs, "call_pool")
        call_pool_coros = [
            _unfiltered_item_coroutine(call_sink, CALL_POOL_ITEM_PREFIX),
            _unfiltered_item_coroutine(call_sink, EVENTS_DATA_CALLS_ITEM_PREFIX),
        ]

    last_prefix = ""
    current_section = _SECTION_OTHER

    try:
        async with adapt_to_reader(sample_bytes) as reader:
            async for prefix, event, value in ijson.parse_async(reader, use_float=True):
                # HOT PATH: this classification runs 56M+ times per large parse.
                # Avoid string slicing, startswith, or any allocation in common
                # paths. Profile before changing. Mirrored in
                # load_filtered.py's `_parse_and_filter` (which also handles
                # _SECTION_TIMELINES -- streaming has no such branch, see
                # below). A change to this decision tree needs the same
                # change there.
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
                        # "messages" vs "metadata": both start "me", discriminate
                        # on 3rd char.
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
                        # events array, or an events_data.* pool sub-array.
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
                        # "target" vs "timelines", on the 2nd char. Timelines
                        # are skipped: spooling them would retain the whole
                        # section for the parse's lifetime, and a caller that
                        # *requests* a timeline never reaches this parse --
                        # `EvalLogTranscriptsView.open` routes
                        # `content.timeline is not None` to the materialized
                        # path. That is a constraint on callers, not a fact
                        # about them: the guard looks only at the requested
                        # content, never at whether the sample stores
                        # timelines, so anything reading a spooled transcript's
                        # `.timelines` sees [] regardless. Pinned by
                        # test_handle_equivalence.py::
                        # test_materialized_preserves_timelines_spooled_drops_them.
                        current_section = (
                            _SECTION_TARGET
                            if prefix[1] == _TARGET_CHAR1
                            else _SECTION_OTHER
                        )
                    elif (
                        prefix[0] == "s"
                        and prefix[:_SCORES_PREFIX_LEN] == SCORES_PREFIX
                    ):
                        current_section = _SECTION_SCORES
                    else:
                        current_section = _SECTION_OTHER

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
                elif current_section == _SECTION_SCORES:
                    scores_coro.send((prefix, event, value))
                elif current_section == _SECTION_MESSAGE_POOL and message_pool_coros:
                    for coro in message_pool_coros:
                        coro.send((prefix, event, value))
                elif current_section == _SECTION_CALL_POOL and call_pool_coros:
                    for coro in call_pool_coros:
                        coro.send((prefix, event, value))

        result.target = state.target
        result.scores = state.scores
        return result
    except BaseException:
        result.close()
        raise


@_coroutine
def _spool_attachments_coroutine(blobs: BlobSpool) -> CoroutineGen:  # pragma: no cover
    """Spool ALL attachments, without an ``attachment_refs`` membership check.

    Refs inside pool items only become known during replay, after the parse
    has moved past the attachments section, so every attachment must be kept.
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


_CHAT_MESSAGE_ADAPTER: TypeAdapter[ChatMessage] = TypeAdapter(ChatMessage)
_EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)


def _resolve_strings(obj: Any, blobs: BlobSpool) -> Any:
    """Recursively resolve ``attachment://<id>`` refs against ``blobs``.

    Like ``_resolve_dict_attachments`` in load_filtered.py, including its
    whole-value rule -- a ref inside a longer string is not a ref -- but looks
    ids up in the on-disk BlobSpool, mutating dict/list containers in place.
    """
    if isinstance(obj, str):
        if len(obj) != ATTACHMENT_REF_LEN or not obj.startswith(ATTACHMENT_PREFIX):
            return obj
        resolved = blobs.get(obj[ATTACHMENT_PREFIX_LEN:])
        return obj if resolved is None else resolved
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

    Entries come back unresolved: the caller's trailing ``_resolve_strings``
    walks them along with the rest of the item. Resolving here as well would
    rescan a just-substituted attachment body for refs, which the
    materialized path (a single ``re.sub``) never does.
    """
    result: list[Any] = []
    pool_len = blobs.pool_len(pool_name)
    for start, end_exclusive in refs:
        for i in slice_positions(start, end_exclusive, pool_len):
            raw = blobs.get((pool_name, i))
            if raw is not None:
                result.append(json.loads(raw))
    return result


def resolve_item_dict(item: dict[str, Any], blobs: BlobSpool) -> dict[str, Any]:
    """Resolve attachment refs and pool ranges on a spooled item, in place.

    Expands ``input_refs``/``call_refs`` positional ranges (same semantics as
    ``_resolve_events_pools`` in pool.py) by fetching pool entries from
    ``blobs`` and resolving attachment refs inside them, then resolves
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


def _hydrate_nested_tool_events(item: dict[str, Any], blobs: BlobSpool) -> None:
    """Recursively resolve and validate a `ToolEvent` item's nested `events`.

    `ToolEvent.events` is typed `list[Any]` (a legacy field for tool-spawned
    agents), so `TypeAdapter(Event)` leaves its entries as raw dicts.
    Consumers that walk nested events expect real `Event` instances, so each
    nested dict is resolved and validated the same way top-level events are
    (recursively, in place).

    Anything that does not validate is passed through unchanged, matching the
    materialized path, which leaves the whole list alone. The field is legacy
    and loosely shaped: a non-dict entry, or a dict from a future/unknown
    event type, must not take down the surrounding `events()` stream -- and a
    dict that is not an event at all must not be coerced into an invented one
    (`TypeAdapter(Event)` happily turns `{"hello": "world"}` into a
    `BranchEvent`).

    Known limitation: the materialized read path never runs this hydration,
    so for legacy tool-spawned-agent transcripts the streaming path surfaces
    nested `ModelEvent`s while the materialized path does not -- scan results
    can differ between the two paths on such transcripts.
    """
    nested = item.get("events")
    if not nested:
        return
    hydrated: list[Any] = []
    for nested_item in nested:
        if not isinstance(nested_item, dict):
            hydrated.append(nested_item)
            continue
        resolved = resolve_item_dict(nested_item, blobs)
        _hydrate_nested_tool_events(resolved, blobs)
        if "event" not in resolved:
            hydrated.append(resolved)  # not an event: validating would invent one
            continue
        try:
            hydrated.append(_EVENT_ADAPTER.validate_python(resolved))
        except ValidationError:
            hydrated.append(resolved)  # unknown or future event type
    item["events"] = hydrated


def replay_events(result: StreamParseResult) -> Iterator[Event]:
    """Replay spooled events, resolving attachments/pools and validating each."""
    for item in result.events.items():
        resolved = resolve_item_dict(item, result.blobs)
        _hydrate_nested_tool_events(resolved, result.blobs)
        yield _EVENT_ADAPTER.validate_python(resolved)
