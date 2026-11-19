"""Tests for json_event_batches and the two sample parsers that read through it."""

from __future__ import annotations

import asyncio
import io
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Self

import anyio
import anyio.lowlevel
import ijson
import pytest
from inspect_scout import TranscriptInfo
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.json.reducer import json_event_batches
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool

Parse = Callable[[AsyncIterable[bytes], Path], Awaitable[None]]


async def _load(source: AsyncIterable[bytes], tmp_path: Path) -> None:
    await load_filtered_transcript(
        source, TranscriptInfo(transcript_id="t1"), "all", "all"
    )


async def _spool(source: AsyncIterable[bytes], tmp_path: Path) -> None:
    result = await stream_parse_to_spool(source, "all", "all", tmp_path)
    result.close()


class _HeldSource:
    """Sample bytes whose second read never returns, and whose cleanup has to wait.

    A member of a local ``.eval`` file is like this: closing it goes to a thread.
    """

    def __init__(self) -> None:
        self.reading = anyio.Event()
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            yield b'{"id": 1, "epoch": 1, "messages": ['
            self.reading.set()
            await anyio.sleep_forever()
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.lowlevel.cancel_shielded_checkpoint()
            self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("parse", [_load, _spool], ids=["load", "spool"])
async def test_a_parse_cancelled_during_a_read_closes_its_source_and_stays_cancellable(
    parse: Parse, tmp_path: Path
) -> None:
    source = _HeldSource()
    scopes: list[anyio.CancelScope] = []
    errors: list[Exception] = []

    async def scan() -> None:
        with anyio.CancelScope() as scope:
            scopes.append(scope)
            try:
                await parse(source, tmp_path)
            except Exception as ex:  # a scan records a failed parse and goes on
                errors.append(ex)
            await anyio.sleep_forever()  # its next checkpoint

    task = asyncio.create_task(scan())
    try:
        with anyio.fail_after(10):
            await source.reading.wait()
        scopes[0].cancel()
        done, _ = await asyncio.wait([task], timeout=10)
        assert done, "the scope's cancellation never reached the task"
        task.result()
    finally:
        if not task.done():
            # a task left inside the source's shielded scope takes only a native cancel
            task.cancel()
            await asyncio.wait([task], timeout=10)
            if task.done() and not task.cancelled():
                task.exception()  # retrieved, so the run reports only its assertion

    assert errors == []
    assert source.closed


class _SmallReads:
    """An async reader that hands out at most a few bytes per read."""

    def __init__(self, data: bytes, size: int) -> None:
        self._stream = io.BytesIO(data)
        self._size = size

    async def read(self, size: int) -> bytes:
        return self._stream.read(min(size, self._size))

    async def aclose(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass


async def _outcome(
    events: AsyncIterable[Any],
) -> tuple[list[tuple[str, str, Any]], str | None]:
    """The events an iteration gave, and the error that ended it, if one did."""
    seen: list[tuple[str, str, Any]] = []
    try:
        async for item in events:
            if isinstance(item, list):
                seen.extend(item)
            else:
                seen.append(item)
    except ijson.JSONError as ex:
        return seen, f"{type(ex).__name__}: {ex}"
    return seen, None


@pytest.mark.asyncio
@pytest.mark.parametrize("read_size", [1, 7])
@pytest.mark.parametrize(
    "backend", [ijson, ijson.get_backend("python")], ids=["default", "python"]
)
@pytest.mark.parametrize(
    "document",
    [
        '{"id": 1, "messages": [{"role": "user", "content": "héllo \U0001f600"}]}'.encode(),
        b'{"target": "bad\\ud800", "numbers": [1, -2.5, 1e3, 9007199254740993], "n": null}',
        b"12",
        b"",
        b'{"a": [1, 2',
        '{"a": "hé'.encode()[:-1],
        b'{"a": NaN}',
        b'{"a": 1} trailing',
        b"[1]\xe2\x82",
    ],
    ids=[
        "multi-byte characters",
        "escapes and numbers",
        "a bare number",
        "empty",
        "cut short",
        "cut inside a character",
        "not JSON",
        "trailing text",
        "trailing bytes",
    ],
)
async def test_the_batches_and_errors_are_those_of_parse_async(
    document: bytes, backend: ModuleType, read_size: int
) -> None:
    expected = await _outcome(
        backend.parse_async(_SmallReads(document, read_size), use_float=True)
    )

    got = await _outcome(json_event_batches(_SmallReads(document, read_size), backend))

    assert got == expected


class _InstantReads(_SmallReads):
    """An async reader that never waits, and asks for a cancellation at its third read."""

    def __init__(self, data: bytes) -> None:
        super().__init__(data, size=64 * 1024)
        self.reads = 0
        self.cancel: Callable[[], object] = lambda: None

    async def read(self, size: int) -> bytes:
        self.reads += 1
        if self.reads == 3:
            asyncio.get_running_loop().call_soon(self.cancel)
        return await super().read(size)


@pytest.mark.asyncio
async def test_a_long_string_from_a_source_that_never_waits_lets_a_cancellation_in() -> (
    None
):
    reads_in_all = 20
    reader = _InstantReads(b'{"s": "' + b"x" * (reads_in_all * 64 * 1024) + b'"}')

    async def parse() -> None:
        async for _ in json_event_batches(reader, ijson):
            pass

    task = asyncio.create_task(parse())
    reader.cancel = task.cancel

    with pytest.raises(asyncio.CancelledError):
        await task
    assert reader.reads < reads_in_all
