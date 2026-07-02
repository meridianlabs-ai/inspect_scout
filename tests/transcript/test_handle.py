"""Tests for TranscriptHandle implementations."""

from __future__ import annotations

import io
import json
import pickle
from pathlib import Path
from typing import Any

import anyio
import ijson  # type: ignore
import pytest
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
    TranscriptHandle,
)
from inspect_scout._transcript.json.stream_parse import (
    StreamParseResult,
    stream_parse_to_spool,
)
from inspect_scout._transcript.types import Transcript, TranscriptInfo

INFO = TranscriptInfo(transcript_id="t1", source_type="eval_log", source_id="e1")

SAMPLE: dict[str, Any] = {
    "id": "t1",
    "messages": [
        {"id": "m1", "role": "user", "content": "hello"},
        {"id": "m2", "role": "assistant", "content": "world"},
    ],
    "events": [],
    "attachments": {},
}


def _spooled_handle(tmp_path: Path) -> SpooledTranscriptHandle:
    async def parse() -> Any:
        return await stream_parse_to_spool(
            io.BytesIO(json.dumps(SAMPLE).encode()), "all", None, tmp_path
        )

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    return SpooledTranscriptHandle(INFO, parse, fallback)


@pytest.mark.asyncio
async def test_spooled_handle_multi_shot(tmp_path: Path) -> None:
    async with _spooled_handle(tmp_path) as handle:
        first = [m async for m in handle.messages()]
        second = [m async for m in handle.messages()]
        assert [m.id for m in first] == ["m1", "m2"]
        assert [m.id for m in second] == ["m1", "m2"]


@pytest.mark.asyncio
async def test_spooled_handle_load_memoized(tmp_path: Path) -> None:
    async with _spooled_handle(tmp_path) as handle:
        t1 = await handle.load()
        t2 = await handle.load()
        assert t1 is t2
        assert len(t1.messages) == 2
        assert t1.transcript_id == "t1"


@pytest.mark.asyncio
async def test_handle_refuses_pickle(tmp_path: Path) -> None:
    handle = _spooled_handle(tmp_path)
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(handle)
    await handle.aclose()


@pytest.mark.asyncio
async def test_spooled_handle_lazy_and_cleanup(tmp_path: Path) -> None:
    handle = _spooled_handle(tmp_path)
    # not yet parsed: aclose before use is safe
    await handle.aclose()
    await handle.aclose()  # idempotent


@pytest.mark.asyncio
async def test_materialized_handle(tmp_path: Path) -> None:
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})
    calls = 0

    async def load_fn() -> Transcript:
        nonlocal calls
        calls += 1
        return transcript

    async with MaterializedTranscriptHandle(load_fn, INFO) as handle:
        assert (await handle.load()) is transcript
        assert [m async for m in handle.messages()] == []
        assert calls == 1  # memoized


def _fallback_transcript() -> Transcript:
    return Transcript(
        transcript_id="t1",
        messages=[{"id": "fb1", "role": "user", "content": "fallback"}],  # type: ignore[list-item]
        events=[],
        metadata={},
    )


def _spooled_handle_with_bad_parse(
    fallback_transcript: Transcript,
) -> SpooledTranscriptHandle:
    async def parse() -> StreamParseResult:
        raise ijson.JSONError("nan")

    async def fallback() -> Transcript:
        return fallback_transcript

    return SpooledTranscriptHandle(INFO, parse, fallback)


@pytest.mark.asyncio
async def test_spooled_handle_fallback_via_messages_first() -> None:
    fallback_transcript = _fallback_transcript()
    async with _spooled_handle_with_bad_parse(fallback_transcript) as handle:
        messages = [m async for m in handle.messages()]
        assert [m.id for m in messages] == ["fb1"]

        loaded = await handle.load()
        assert loaded is fallback_transcript


@pytest.mark.asyncio
async def test_spooled_handle_fallback_via_load_first() -> None:
    fallback_transcript = _fallback_transcript()
    async with _spooled_handle_with_bad_parse(fallback_transcript) as handle:
        loaded = await handle.load()
        assert loaded is fallback_transcript

        messages = [m async for m in handle.messages()]
        assert [m.id for m in messages] == ["fb1"]


@pytest.mark.asyncio
async def test_spooled_handle_use_after_close_raises(tmp_path: Path) -> None:
    handle = _spooled_handle(tmp_path)
    await handle.aclose()

    with pytest.raises(RuntimeError, match="closed"):
        await handle.load()

    with pytest.raises(RuntimeError, match="closed"):
        async for _ in handle.messages():
            pass


@pytest.mark.asyncio
async def test_materialized_handle_use_after_close_raises() -> None:
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    async def load_fn() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load_fn, INFO)
    await handle.aclose()

    with pytest.raises(RuntimeError, match="closed"):
        await handle.load()


@pytest.mark.asyncio
async def test_spooled_handle_concurrent_first_use_parses_once(
    tmp_path: Path,
) -> None:
    calls = 0

    async def parse() -> StreamParseResult:
        nonlocal calls
        calls += 1
        await anyio.sleep(0.01)
        return await stream_parse_to_spool(
            io.BytesIO(json.dumps(SAMPLE).encode()), "all", None, tmp_path
        )

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(INFO, parse, fallback)

    async with handle:
        messages_result: list[str | None] = []
        load_result: list[str | None] = []

        async def collect_messages() -> None:
            messages_result.extend([m.id async for m in handle.messages()])

        async def collect_load() -> None:
            transcript = await handle.load()
            load_result.extend([m.id for m in transcript.messages])

        async with anyio.create_task_group() as tg:
            tg.start_soon(collect_messages)
            tg.start_soon(collect_load)

    assert calls == 1
    assert messages_result == ["m1", "m2"]
    assert load_result == ["m1", "m2"]


@pytest.mark.asyncio
async def test_spooled_handle_is_transcript_handle(tmp_path: Path) -> None:
    handle = _spooled_handle(tmp_path)
    assert isinstance(handle, TranscriptHandle)
    await handle.aclose()


@pytest.mark.asyncio
async def test_materialized_handle_is_transcript_handle() -> None:
    async def load_fn() -> Transcript:
        return Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    handle = MaterializedTranscriptHandle(load_fn, INFO)
    assert isinstance(handle, TranscriptHandle)
