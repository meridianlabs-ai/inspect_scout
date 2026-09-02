from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Generator, Literal, ParamSpec, Protocol

from ijson import ObjectBuilder  # type: ignore[import-untyped]  # no published stubs
from ijson.utils import (  # type: ignore[import-untyped]  # no published stubs
    coroutine as _ijson_coroutine,
)

# Public constants / prefixes
ATTACHMENT_PREFIX = "attachment://"
ATTACHMENT_PREFIX_LEN = len(ATTACHMENT_PREFIX)
ATTACHMENT_REF_JSON_BYTES = re.compile(rb'(?<!\\)"attachment://([a-f0-9]{32})"')
"""A whole-value ref as serialized JSON spells it, delimiters included.

Scans serialized JSON without decoding it first (refs are ASCII). The quotes
are load-bearing: a ref is only a ref when it is the entire string value, and
JSON writes a value's own delimiters unescaped, so requiring them is what
separates a ref from an id mentioned inside author-written text.

The lookbehind rejects `\\"attachment://<id>"`, which is text whose content
opens with a quote character, not a value. It can never reject a real ref: a
value's opening delimiter follows `:`, `,` or `[`, never a backslash."""
# A ref is the prefix plus a 32-char hex id, and nothing else.
ATTACHMENT_REF_LEN = ATTACHMENT_PREFIX_LEN + 32
ATTACHMENTS_PREFIX = "attachments."
MESSAGES_ITEM_PREFIX = "messages.item"
EVENTS_ITEM_PREFIX = "events.item"
TIMELINES_ITEM_PREFIX = "timelines.item"
# Pool prefixes for deduplicated ChatMessage / call payloads. Two on-disk
# shapes carry identical data: legacy top-level arrays, and the post-PR-#3519
# nesting under events_data. Both resolve to the same state.{message,call}_pool.
MESSAGE_POOL_ITEM_PREFIX = "message_pool.item"  # legacy
CALL_POOL_ITEM_PREFIX = "call_pool.item"  # legacy
EVENTS_DATA_MESSAGES_ITEM_PREFIX = "events_data.messages.item"
EVENTS_DATA_CALLS_ITEM_PREFIX = "events_data.calls.item"
METADATA_PREFIX = "metadata."


def _should_skip(
    filter_field_value: str, filter_list: None | Literal["all"] | Sequence[str]
) -> bool:
    if filter_list is None:
        return True
    if filter_list == "all":
        return False
    return filter_field_value not in filter_list


@dataclass(frozen=True, slots=True)
class ListProcessingConfig:
    array_item_prefix: str
    filter_field: str
    filter_list: None | Literal["all"] | Sequence[str]
    filter_prefix: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "filter_prefix", f"{self.array_item_prefix}.{self.filter_field}"
        )


@dataclass(slots=True)
class ParseState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    timelines: list[dict[str, Any]] = field(default_factory=list)
    attachment_refs: set[str] = field(default_factory=set)
    attachments: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    target: str | list[str] | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    message_pool: list[dict[str, Any]] = field(default_factory=list)
    call_pool: list[dict[str, Any]] = field(default_factory=list)
    # Set once the events section starts streaming (see attachments_coroutine).
    events_seen: bool = False


# ---------------------------------------------------------------------------
# Coroutine-based object processors (idiomatic style with early filtering)
# ---------------------------------------------------------------------------

EventTuple = tuple[str, str, Any]
CoroutineGen = Generator[None, EventTuple, None]
_P = ParamSpec("_P")


def _coroutine(fn: Callable[_P, CoroutineGen]) -> Callable[_P, CoroutineGen]:
    """``ijson.utils.coroutine`` with the decorated signature preserved.

    The upstream decorator is untyped, so applying it directly erases the
    function to ``Any`` -- which silently switches off argument checking on
    every coroutine here, including the ``ItemSink`` protocol below.
    """
    decorated: Callable[_P, CoroutineGen] = _ijson_coroutine(fn)
    return decorated


class ItemSink(Protocol):
    """Structural target for parsed items: anything with a list-like `append`.

    `list[dict[str, Any]]` (used by `ParseState` fields) satisfies this
    structurally; spooling sinks (see stream_parse.py) can implement it
    directly without inheriting from `list`.
    """

    def append(self, item: dict[str, Any], /) -> None: ...


@_coroutine
def _item_coroutine(
    target_list: ItemSink,
    attachment_refs: set[str],
    config: ListProcessingConfig,
) -> CoroutineGen:  # pragma: no cover
    builder: ObjectBuilder | None = None
    attachments: set[str] = set()
    skip = False
    item_prefix = config.array_item_prefix
    filter_prefix = config.filter_prefix
    while True:
        prefix, event, value = yield
        if prefix == item_prefix and event == "start_map":
            builder = ObjectBuilder()
            builder.event(event, value)
            attachments.clear()
            skip = False
            continue
        if builder is None:
            continue
        if prefix == filter_prefix and event == "string":
            if _should_skip(value, config.filter_list):
                builder = None
                skip = True
                attachments.clear()
                continue
        if prefix == item_prefix and event == "end_map":
            if not skip and builder is not None:
                try:
                    builder.event(event, value)
                    item = builder.value
                except Exception:
                    pass  # malformed item: drop it and keep parsing
                else:
                    # Deliberately outside the guard. `target_list` is a spool
                    # sink, so an append failure means ENOSPC or a closed fd --
                    # data loss, not a malformed item. Swallowing it would drop
                    # the item while the parse went on to report success.
                    target_list.append(item)
                    attachment_refs.update(attachments)
            builder = None
            skip = False
            attachments.clear()
            continue
        if skip:
            continue
        try:
            builder.event(event, value)
        except Exception:
            builder = None
            continue
        if event == "string" and isinstance(value, str):
            # A ref is the whole value, never a substring -- inspect_ai's
            # create_attachment replaces the entire field. Length-first keeps
            # this cheap in a loop that runs per ijson event.
            if len(value) == ATTACHMENT_REF_LEN and value.startswith(ATTACHMENT_PREFIX):
                attachments.add(value[ATTACHMENT_PREFIX_LEN:])


def message_item_coroutine(
    state: ParseState, config: ListProcessingConfig
) -> CoroutineGen:
    return _item_coroutine(state.messages, state.attachment_refs, config)


def event_item_coroutine(
    state: ParseState, config: ListProcessingConfig
) -> CoroutineGen:
    return _item_coroutine(state.events, state.attachment_refs, config)


@_coroutine
def _unfiltered_item_coroutine(
    target_list: ItemSink,
    item_prefix: str,
) -> CoroutineGen:  # pragma: no cover
    """Collect items from the JSON stream without filtering."""
    builder: ObjectBuilder | None = None
    while True:
        prefix, event, value = yield
        if prefix == item_prefix and event == "start_map":
            builder = ObjectBuilder()
            builder.event(event, value)
            continue
        if builder is None:
            continue
        if prefix == item_prefix and event == "end_map":
            try:
                builder.event(event, value)
                item = builder.value
            except Exception:
                pass  # malformed item: drop it and keep parsing
            else:
                # Outside the guard: see `_item_coroutine` -- an append failure
                # is a spool write failure, and must not be silently dropped.
                target_list.append(item)
            builder = None
            continue
        try:
            builder.event(event, value)
        except Exception:
            builder = None
            continue


def timeline_item_coroutine(state: ParseState) -> CoroutineGen:
    return _unfiltered_item_coroutine(state.timelines, TIMELINES_ITEM_PREFIX)


def message_pool_item_coroutine(state: ParseState, item_prefix: str) -> CoroutineGen:
    return _unfiltered_item_coroutine(state.message_pool, item_prefix)


def call_pool_item_coroutine(state: ParseState, item_prefix: str) -> CoroutineGen:
    return _unfiltered_item_coroutine(state.call_pool, item_prefix)


def _event_has_pool_refs(event_dict: dict[str, Any]) -> bool:
    """Does this event dict carry an unresolved message/call pool ref?

    Must stay in step with the conditions `pool.py`'s `_resolve_events_pools`
    checks before expanding a ref.
    """
    if event_dict.get("input_refs"):
        return True
    call = event_dict.get("call")
    return isinstance(call, dict) and call.get("call_refs") is not None


@_coroutine
def attachments_coroutine(
    state: ParseState, collecting_events: bool
) -> CoroutineGen:  # pragma: no cover
    """Collect the attachments table.

    Filtering on ``state.attachment_refs`` alone is unsafe once events are
    collected: pool entries under ``events_data`` carry refs of their own, and
    that section follows ``attachments`` in the file, so they are unknowable
    here. Retain everything when a retained event carries a pool ref -- or
    when the events section has not streamed yet, since JSON key order is not
    guaranteed and guessing wrong drops data permanently. A section that has
    streamed counts as seen even when it was empty or filtered down to
    nothing. Otherwise the ref filter applies and the table stays bounded.
    """
    attachments_prefix_len = len(ATTACHMENTS_PREFIX)
    retain_all: bool | None = None
    while True:
        prefix, event, value = yield
        if event != "string":
            continue
        if not prefix.startswith(ATTACHMENTS_PREFIX):
            continue
        if retain_all is None:
            retain_all = collecting_events and (
                not state.events_seen
                or any(_event_has_pool_refs(e) for e in state.events)
            )
        end = prefix.find(".", attachments_prefix_len)
        attachment_id = (
            prefix[attachments_prefix_len:]
            if end == -1
            else prefix[attachments_prefix_len:end]
        )
        if retain_all or attachment_id in state.attachment_refs:
            state.attachments[attachment_id] = value


@_coroutine
def metadata_coroutine(state: ParseState) -> CoroutineGen:  # pragma: no cover
    """Coroutine to build the metadata object from streaming JSON events."""
    builder: ObjectBuilder | None = None
    while True:
        prefix, event, value = yield
        # Handle both "metadata" (root) and "metadata." (nested keys)
        if not (prefix == "metadata" or prefix.startswith(METADATA_PREFIX)):
            continue
        if prefix == "metadata" and event == "start_map":
            builder = ObjectBuilder()
            builder.event(event, value)
            continue
        if builder is None:
            continue
        if prefix == "metadata" and event == "end_map":
            try:
                builder.event(event, value)
                state.metadata = builder.value
            except Exception:
                pass
            builder = None
            continue
        try:
            builder.event(event, value)
        except Exception:
            builder = None
            continue


class JsonTextWriter:
    """Re-serialize a stream of ijson events as JSON text.

    The inverse of ``ijson.parse``: feed it the events for one value and it
    writes that value back out, byte for byte as
    ``json.dumps(value, ensure_ascii=False, separators=(",", ":"))`` would --
    without ever building the value as Python objects. Use it for a subtree
    large enough that the object graph is the problem.

    Assumes numbers arrive as ``int``/``float`` (ijson's ``use_float=True``);
    ``Decimal`` would raise, as it would from ``json.dumps``.
    """

    _ENCODER = json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))

    def __init__(self, write: Callable[[bytes], Any]) -> None:
        self._write = write
        self._nonempty: list[bool] = []  # per open container: has an item yet
        self._after_key = False

    def _separator(self) -> None:
        """Write the comma between siblings, if this is not the first."""
        if self._after_key:  # a value right after "key": never takes one
            self._after_key = False
            return
        if self._nonempty:
            if self._nonempty[-1]:
                self._write(b",")
            self._nonempty[-1] = True

    def event(self, event: str, value: Any) -> None:
        if event == "map_key":
            if self._nonempty and self._nonempty[-1]:
                self._write(b",")
            if self._nonempty:
                self._nonempty[-1] = True
            self._write(self._ENCODER.encode(value).encode("utf-8") + b":")
            self._after_key = True
            return
        if event in ("start_map", "start_array"):
            self._separator()
            self._write(b"{" if event == "start_map" else b"[")
            self._nonempty.append(False)
            return
        if event in ("end_map", "end_array"):
            self._nonempty.pop()
            self._write(b"}" if event == "end_map" else b"]")
            return
        self._separator()
        self._write(self._ENCODER.encode(value).encode("utf-8"))


@_coroutine
def spooling_metadata_coroutine(
    write: Callable[[bytes], Any],
) -> CoroutineGen:  # pragma: no cover
    """``metadata_coroutine`` that writes JSON text instead of building objects.

    Sample metadata can be most of a transcript (measured at 1,377 MB of a
    3,223 MB sample), and as an object graph it costs roughly twice that,
    retained for the lifetime of the handle. Written as text it stays on disk
    until something actually needs it.
    """
    writer: JsonTextWriter | None = None
    while True:
        prefix, event, value = yield
        if not (prefix == "metadata" or prefix.startswith(METADATA_PREFIX)):
            continue
        if prefix == "metadata" and event == "start_map":
            writer = JsonTextWriter(write)
            writer.event(event, value)
            continue
        if writer is None:
            continue
        writer.event(event, value)
        if prefix == "metadata" and event == "end_map":
            writer = None


SCORES_PREFIX = "scores."


@_coroutine
def scores_coroutine(state: ParseState) -> CoroutineGen:  # pragma: no cover
    """Coroutine to build the scores object from streaming JSON events."""
    builder: ObjectBuilder | None = None
    while True:
        prefix, event, value = yield
        if not (prefix == "scores" or prefix.startswith(SCORES_PREFIX)):
            continue
        if prefix == "scores" and event == "start_map":
            builder = ObjectBuilder()
            builder.event(event, value)
            continue
        if builder is None:
            continue
        if prefix == "scores" and event == "end_map":
            try:
                builder.event(event, value)
                state.scores = builder.value
            except Exception:
                pass
            builder = None
            continue
        try:
            builder.event(event, value)
        except Exception:
            builder = None
            continue


TARGET_PREFIX = "target."


@_coroutine
def target_coroutine(state: ParseState) -> CoroutineGen:  # pragma: no cover
    """Coroutine to capture the target field (scalar string or list of strings)."""
    while True:
        prefix, event, value = yield
        if prefix != "target" and not prefix.startswith(TARGET_PREFIX):
            continue
        if prefix == "target" and event == "string":
            state.target = value
            return
        if prefix == "target" and event == "start_array":
            items: list[str] = []
            while True:
                prefix, event, value = yield
                if prefix == "target" and event == "end_array":
                    state.target = items
                    return
                if prefix == "target.item" and event == "string":
                    items.append(value)


__all__ = [
    "ListProcessingConfig",
    "ParseState",
    "message_item_coroutine",
    "event_item_coroutine",
    "timeline_item_coroutine",
    "message_pool_item_coroutine",
    "call_pool_item_coroutine",
    "attachments_coroutine",
    "metadata_coroutine",
    "scores_coroutine",
    "target_coroutine",
    "SCORES_PREFIX",
    "TARGET_PREFIX",
    "ATTACHMENT_PREFIX",
    "ATTACHMENT_PREFIX_LEN",
    "ATTACHMENT_REF_LEN",
    "ATTACHMENT_REF_JSON_BYTES",
    "JsonTextWriter",
    "spooling_metadata_coroutine",
    "ATTACHMENTS_PREFIX",
    "MESSAGES_ITEM_PREFIX",
    "EVENTS_ITEM_PREFIX",
    "TIMELINES_ITEM_PREFIX",
    "MESSAGE_POOL_ITEM_PREFIX",
    "CALL_POOL_ITEM_PREFIX",
    "EVENTS_DATA_MESSAGES_ITEM_PREFIX",
    "EVENTS_DATA_CALLS_ITEM_PREFIX",
    "METADATA_PREFIX",
    "ItemSink",
]
