"""Tests for TranscriptHandle implementations."""

from __future__ import annotations

import io
import json
import pickle
from pathlib import Path
from typing import Any

import pytest
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
)
from inspect_scout._transcript.json.stream_parse import stream_parse_to_spool
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
