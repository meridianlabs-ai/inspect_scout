"""Tests for resolving reference-mode scan inputs in the viewer API."""

import asyncio
import gc
import json
import threading
from pathlib import Path
from typing import Any

import anyio
import pytest
from anyio.lowlevel import _run_vars
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai.log import read_eval_log_sample_summaries
from inspect_scout._scanner.result import _serialize_input
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.reference import (
    InputReference,
    InputReferenceUnavailable,
    read_referenced_transcript,
)
from inspect_scout._transcript.types import Transcript, TranscriptContent
from inspect_scout._view import _input_reference
from inspect_scout._view._input_reference import (
    InputReferenceResolver,
    source_uri_locator,
)
from starlette.exceptions import HTTPException
from starlette.requests import Request

EVAL_LOG = (
    Path(__file__).parent.parent
    / "recorder"
    / "logs"
    / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
)
SAMPLE_UUID = read_eval_log_sample_summaries(str(EVAL_LOG))[0].uuid
CONTENT = TranscriptContent(messages="all", events="all")
ROW: dict[str, Any] = {
    "input_storage": "reference",
    "transcript_id": SAMPLE_UUID,
    "transcript_source_uri": str(EVAL_LOG),
    "transcript_task_id": "1",
    "transcript_task_repeat": 1,
    "input_content": CONTENT.to_json(),
}


def _request() -> Request:
    return Request({"type": "http"})


@pytest.mark.asyncio
async def test_resolves_to_the_copy_mode_columns() -> None:
    async with EvalLogTranscriptsView(str(EVAL_LOG)) as view:
        info = [i async for i in view.select()][0]
        expected = await view.read(info, CONTENT)
    expected_input, expected_data = _serialize_input(
        expected, "transcript", pool_dedup=True
    )

    resolved = await InputReferenceResolver(source_uri_locator).resolve(_request(), ROW)

    actual = json.loads(resolved.input)
    copied = json.loads(expected_input)
    assert actual["transcript_id"] == SAMPLE_UUID
    assert actual["messages"] == copied["messages"]
    assert actual["events"] == copied["events"]
    assert expected_data is not None
    assert resolved.input_data == expected_data.decode()


@pytest.mark.asyncio
async def test_reads_off_the_server_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    async def spy(
        location: str, ref: InputReference, *, max_bytes: int | None = None
    ) -> Transcript:
        seen["thread"] = threading.get_ident()
        seen["loop"] = asyncio.get_running_loop()
        async with AsyncFilesystem() as fs:
            seen["fs"] = fs
        return await read_referenced_transcript(location, ref, max_bytes=max_bytes)

    monkeypatch.setattr(_input_reference, "read_referenced_transcript", spy)

    # A host may share one filesystem per request (bound to the server loop);
    # the private loop must not pick it up.
    async with AsyncFilesystem() as server_fs:
        await InputReferenceResolver(source_uri_locator).resolve(_request(), ROW)

    assert seen["thread"] != threading.get_ident()
    assert seen["loop"] is not asyncio.get_running_loop()
    assert seen["fs"] is not server_fs


@pytest.mark.asyncio
async def test_resolves_release_their_private_loops() -> None:
    # anyio keeps per-loop state in `_run_vars`. A run that used its threadpool
    # (local reads do) pins its loop, task and result there for the life of
    # the process unless the entry is released.
    await anyio.to_thread.run_sync(lambda: None)  # this test loop's own entry
    gc.collect()
    before = len(_run_vars)

    resolver = InputReferenceResolver(source_uri_locator)
    for _ in range(3):
        await resolver.resolve(_request(), ROW)
    gc.collect()

    assert len(_run_vars) <= before


@pytest.mark.asyncio
async def test_concurrency_is_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    lock = threading.Lock()
    active = 0
    peak = 0

    async def slow(
        location: str, ref: InputReference, *, max_bytes: int | None = None
    ) -> Transcript:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        await asyncio.sleep(0.05)
        with lock:
            active -= 1
        return Transcript(transcript_id=ref.transcript_id)

    monkeypatch.setattr(_input_reference, "read_referenced_transcript", slow)
    resolver = InputReferenceResolver(source_uri_locator, concurrency=1)

    await asyncio.gather(*(resolver.resolve(_request(), ROW) for _ in range(3)))

    assert peak == 1


@pytest.mark.asyncio
async def test_passes_max_bytes_to_the_reader() -> None:
    resolver = InputReferenceResolver(source_uri_locator, max_bytes=100)
    with pytest.raises(InputReferenceUnavailable) as ex:
        await resolver.resolve(_request(), ROW)
    assert ex.value.reason == "too_large"


@pytest.mark.asyncio
async def test_locator_errors_propagate() -> None:
    row = ROW | {"transcript_source_uri": None}
    with pytest.raises(InputReferenceUnavailable) as ex:
        await InputReferenceResolver(source_uri_locator).resolve(_request(), row)
    assert ex.value.reason == "not_found"


@pytest.mark.asyncio
async def test_other_locator_errors_propagate() -> None:
    # Hosts rely on this: an authorization outage must not read as `unavailable`.
    async def outage(request: Request, ref: InputReference) -> str:
        raise HTTPException(status_code=503, detail="policy outage")

    with pytest.raises(HTTPException):
        await InputReferenceResolver(outage).resolve(_request(), ROW)


@pytest.mark.asyncio
async def test_unexpected_errors_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(
        location: str, ref: InputReference, *, max_bytes: int | None = None
    ) -> Transcript:
        raise RuntimeError(f"secret detail about {location}")

    monkeypatch.setattr(_input_reference, "read_referenced_transcript", boom)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await InputReferenceResolver(source_uri_locator).resolve(_request(), ROW)
    assert ex.value.reason == "unavailable"
    assert str(EVAL_LOG) not in ex.value.message
