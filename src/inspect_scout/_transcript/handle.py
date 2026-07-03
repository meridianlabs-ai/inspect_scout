"""TranscriptHandle protocol and implementations for streaming transcript reads.

A ``TranscriptHandle`` provides streaming, multi-shot access to a transcript's
messages/events without necessarily materializing the whole ``Transcript`` in
memory. ``MaterializedTranscriptHandle`` wraps an eagerly-loaded (or lazily
loaded, but fully in-memory once loaded) ``Transcript`` -- the small-file
path. ``SpooledTranscriptHandle`` wraps a disk-spool-backed
``StreamParseResult`` -- the large-file path -- deferring the parse until
first use so prefetched handles don't pin resources.

Deliberately not exported from ``inspect_scout.__init__`` -- the shape must
survive phase 2 (``types=`` pushdown, region-level access) before freezing.
"""

from __future__ import annotations

from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    NoReturn,
    Protocol,
    runtime_checkable,
)

import anyio
import ijson  # type: ignore
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage

from .json.stream_parse import StreamParseResult, replay_events, replay_messages
from .types import EventFilter, MessageFilter, Transcript, TranscriptInfo
from .util import _matches_filter

_CHECKPOINT_INTERVAL = 64


def _passes(item: ChatMessage | Event, types: MessageFilter | EventFilter) -> bool:
    """Whether `item` passes an additional in-Python `types` filter.

    Shared by both handle implementations and both iterator methods. A
    ``types`` of ``None`` or ``"all"`` passes everything (the "no additional
    narrowing" case); a sequence narrows on ``msg.role`` / ``event.event``
    via the shared ``_matches_filter`` semantics.
    """
    if types is None or types == "all":
        return True
    return _matches_filter(item, types)


@runtime_checkable
class TranscriptHandle(Protocol):
    """Streaming access to transcript content. Async context manager.

    Multi-shot contract:
        Each ``messages()``/``events()`` call opens a fresh iteration;
        implementations must retain replay capability (e.g. the spool) for
        the handle's lifetime. Future forward-cursor backends must either
        spool locally or document single-shot deviation before this protocol
        is exported.

    Reservation note:
        Phase 2 will add a region-level accessor (e.g. ``conversations()``)
        for compaction-aware event streaming; keep this protocol unexported
        until then.
    """

    @property
    def info(self) -> TranscriptInfo:
        """Transcript identifier, location, and metadata."""
        ...

    def messages(
        self, *, types: MessageFilter | None = None
    ) -> AsyncIterator[ChatMessage]:
        """Iterate messages. Multi-shot: may be called more than once.

        Args:
            types: Additional message-type narrowing. Default ``None`` means
                "everything the handle was opened with" (the content the
                handle already carries, unchanged). Passing a non-None
                ``types`` narrows further by filtering on ``msg.role``
                (``"all"`` passes everything, like ``None``). Phase-2
                columnar backends may push this down to storage; phase-1
                filters post-hoc in Python.
        """
        ...

    def events(self, *, types: EventFilter | None = None) -> AsyncIterator[Event]:
        """Iterate events. Multi-shot: may be called more than once.

        Args:
            types: Additional event-type narrowing. Default ``None`` means
                "everything the handle was opened with" (the content the
                handle already carries, unchanged). Passing a non-None
                ``types`` narrows further by filtering on ``event.event``
                (``"all"`` passes everything, like ``None``). Phase-2
                columnar backends may push this down to storage; phase-1
                filters post-hoc in Python.
        """
        ...

    async def load(self) -> Transcript:
        """Materialize the full transcript. Memoized.

        Materializes the full requested content in memory (may parse a
        multi-GB sample); memoized. Prefer ``messages()``/``events()`` for
        bounded-memory access.
        """
        ...

    async def __aenter__(self) -> "TranscriptHandle": ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def aclose(self) -> None:
        """Release any underlying resources. Idempotent."""
        ...


class MaterializedTranscriptHandle:
    """Handle over an already/eagerly loaded Transcript (small-file path)."""

    def __init__(
        self, load_fn: Callable[[], Awaitable[Transcript]], info: TranscriptInfo
    ) -> None:
        self._load_fn = load_fn
        self._info = info
        self._transcript: Transcript | None = None
        self._closed = False
        self._lock = anyio.Lock()

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "TranscriptHandle cannot be pickled (must not cross process boundaries)"
        )

    @property
    def info(self) -> TranscriptInfo:
        return self._info

    async def load(self) -> Transcript:
        if self._transcript is not None:
            return self._transcript
        async with self._lock:
            if self._closed:
                raise RuntimeError("TranscriptHandle is closed")
            if self._transcript is None:
                self._transcript = await self._load_fn()
        return self._transcript

    async def messages(
        self, *, types: MessageFilter | None = None
    ) -> AsyncIterator[ChatMessage]:
        transcript = await self.load()
        for i, message in enumerate(transcript.messages):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
            if _passes(message, types):
                yield message

    async def events(self, *, types: EventFilter | None = None) -> AsyncIterator[Event]:
        transcript = await self.load()
        for i, event in enumerate(transcript.events):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
            if _passes(event, types):
                yield event

    async def aclose(self) -> None:
        """Marks the handle closed. No underlying resources to release."""
        self._closed = True

    async def __aenter__(self) -> "MaterializedTranscriptHandle":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


class SpooledTranscriptHandle:
    """Handle backed by a StreamParseResult spool (large-file path)."""

    def __init__(
        self,
        info: TranscriptInfo,
        parse: Callable[[], Awaitable[StreamParseResult]],
        load_fallback: Callable[[], Awaitable[Transcript]],
    ) -> None:
        self._info = info
        self._parse = parse
        self._load_fallback = load_fallback
        self._result: StreamParseResult | None = None
        self._fallback_transcript: Transcript | None = None
        self._transcript: Transcript | None = None
        self._closed = False
        self._lock = anyio.Lock()

    def __reduce__(self) -> NoReturn:
        raise TypeError(
            "TranscriptHandle cannot be pickled (must not cross process boundaries)"
        )

    @property
    def info(self) -> TranscriptInfo:
        return self._info

    async def _ensure_parsed(self) -> StreamParseResult | None:
        """Parse on first use (memoized). Returns None if the fallback was used."""
        async with self._lock:
            if self._closed:
                raise RuntimeError("TranscriptHandle is closed")
            if self._result is not None:
                return self._result
            if self._fallback_transcript is not None:
                return None
            try:
                self._result = await self._parse()
            except ijson.JSONError:
                self._fallback_transcript = await self._load_fallback()
                return None
            return self._result

    async def messages(
        self, *, types: MessageFilter | None = None
    ) -> AsyncIterator[ChatMessage]:
        result = await self._ensure_parsed()
        if result is None:
            assert self._fallback_transcript is not None
            for i, message in enumerate(self._fallback_transcript.messages):
                if i % _CHECKPOINT_INTERVAL == 0:
                    await anyio.lowlevel.checkpoint()
                if _passes(message, types):
                    yield message
            return
        for i, message in enumerate(replay_messages(result)):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
            if _passes(message, types):
                yield message

    async def events(self, *, types: EventFilter | None = None) -> AsyncIterator[Event]:
        result = await self._ensure_parsed()
        if result is None:
            assert self._fallback_transcript is not None
            for i, event in enumerate(self._fallback_transcript.events):
                if i % _CHECKPOINT_INTERVAL == 0:
                    await anyio.lowlevel.checkpoint()
                if _passes(event, types):
                    yield event
            return
        for i, event in enumerate(replay_events(result)):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
            if _passes(event, types):
                yield event

    async def load(self) -> Transcript:
        if self._transcript is not None:
            return self._transcript
        if self._closed:
            raise RuntimeError("TranscriptHandle is closed")

        result = await self._ensure_parsed()
        if result is None:
            assert self._fallback_transcript is not None
            self._transcript = self._fallback_transcript
            return self._transcript

        messages = [m async for m in self.messages()]
        events = [e async for e in self.events()]
        metadata = _merge_unthinned(self._info.metadata, result)

        self._transcript = Transcript.model_construct(
            **self._info.model_dump(exclude={"metadata"}),
            metadata=metadata,
            messages=messages,
            events=events,
            timelines=[],
        )
        return self._transcript

    async def aclose(self) -> None:
        async with self._lock:
            if self._result is not None:
                self._result.close()
                self._result = None
            self._closed = True

    async def __aenter__(self) -> "SpooledTranscriptHandle":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


def _merge_unthinned(base: dict[str, Any], result: StreamParseResult) -> dict[str, Any]:
    """Merge unthinned fields from a StreamParseResult into transcript metadata.

    Mirrors ``_merge_unthinned`` in ``json/load_filtered.py``.
    """
    overrides: dict[str, Any] = {}
    if result.metadata:
        overrides["sample_metadata"] = result.metadata
    if result.target is not None:
        overrides["target"] = result.target
    if result.scores:
        overrides["scores"] = result.scores
    return base.copy() | overrides if overrides else base
