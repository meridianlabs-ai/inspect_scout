"""TranscriptHandle protocol and implementations for streaming transcript reads.

A ``TranscriptHandle`` provides streaming, multi-shot access to a transcript's
messages/events without necessarily materializing the whole ``Transcript`` in
memory. ``MaterializedTranscriptHandle`` wraps an eagerly-loaded (or lazily
loaded, but fully in-memory once loaded) ``Transcript`` -- the small-file
path. ``SpooledTranscriptHandle`` wraps a disk-spool-backed
``StreamParseResult`` -- the large-file path -- deferring the parse until
first use so prefetched handles don't pin resources.
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
from .types import Transcript, TranscriptInfo

STREAMING_THRESHOLD_BYTES: int = 64 * 1024 * 1024
"""Sample byte-size threshold above which streaming (spooled) reads are used."""

_CHECKPOINT_INTERVAL = 64


@runtime_checkable
class TranscriptHandle(Protocol):
    """Streaming access to transcript content. Async context manager."""

    @property
    def info(self) -> TranscriptInfo:
        """Transcript identifier, location, and metadata."""
        ...

    def messages(self) -> AsyncIterator[ChatMessage]:
        """Iterate messages. Multi-shot: may be called more than once."""
        ...

    def events(self) -> AsyncIterator[Event]:
        """Iterate events. Multi-shot: may be called more than once."""
        ...

    async def load(self) -> Transcript:
        """Materialize the full transcript. Memoized."""
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

    async def messages(self) -> AsyncIterator[ChatMessage]:
        transcript = await self.load()
        for i, message in enumerate(transcript.messages):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
            yield message

    async def events(self) -> AsyncIterator[Event]:
        transcript = await self.load()
        for i, event in enumerate(transcript.events):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
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

    async def messages(self) -> AsyncIterator[ChatMessage]:
        result = await self._ensure_parsed()
        if result is None:
            assert self._fallback_transcript is not None
            for i, message in enumerate(self._fallback_transcript.messages):
                if i % _CHECKPOINT_INTERVAL == 0:
                    await anyio.lowlevel.checkpoint()
                yield message
            return
        for i, message in enumerate(replay_messages(result)):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
            yield message

    async def events(self) -> AsyncIterator[Event]:
        result = await self._ensure_parsed()
        if result is None:
            assert self._fallback_transcript is not None
            for i, event in enumerate(self._fallback_transcript.events):
                if i % _CHECKPOINT_INTERVAL == 0:
                    await anyio.lowlevel.checkpoint()
                yield event
            return
        for i, event in enumerate(replay_events(result)):
            if i % _CHECKPOINT_INTERVAL == 0:
                await anyio.lowlevel.checkpoint()
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
