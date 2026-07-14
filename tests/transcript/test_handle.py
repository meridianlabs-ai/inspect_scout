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
async def test_spooled_handle_aclose_during_first_parse_does_not_leak(
    tmp_path: Path,
) -> None:
    """aclose() racing an in-flight first parse must not leak the spool fds.

    aclose() takes the same lock as the first parse (``_ensure_parsed``), so
    the two can never truly interleave: aclose() either runs to completion
    before the parse starts (in which case the parse call below observes
    ``self._closed`` and raises before producing a StreamParseResult at all),
    or it blocks until the in-flight parse has stored its StreamParseResult,
    then closes it immediately. Either way, no StreamParseResult can be
    produced and left un-closed -- verified here by asserting the result
    that *was* produced ends up with all of its spool fds released.
    """
    produced: list[StreamParseResult] = []

    async def parse() -> StreamParseResult:
        await anyio.sleep(0.05)
        result = await stream_parse_to_spool(
            io.BytesIO(json.dumps(SAMPLE).encode()), "all", None, tmp_path
        )
        produced.append(result)
        return result

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(INFO, parse, fallback)

    async def start_parse() -> None:
        try:
            await handle.messages().__anext__()
        except (StopAsyncIteration, RuntimeError):
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(start_parse)
        await anyio.sleep(0.01)  # let the parse start before racing aclose()
        tg.start_soon(handle.aclose)

    assert handle._closed is True
    assert handle._result is None  # closed, and not left dangling as "open"

    # If the parse won the race and produced a result, aclose() must have
    # closed it -- its spool fds must all be released, not leaked.
    if produced:
        result = produced[0]
        assert result.messages._fd is None
        assert result.events._fd is None
        assert result.blobs._fd is None


def _large_sample(n_messages: int) -> dict[str, Any]:
    return {
        "id": "t1",
        "messages": [
            {"id": f"m{i}", "role": "user", "content": f"message {i}"}
            for i in range(n_messages)
        ],
        "events": [],
        "attachments": {},
    }


@pytest.mark.asyncio
async def test_spooled_handle_cancel_mid_stream_releases_fds(tmp_path: Path) -> None:
    """Cancelling a mid-stream iterator then aclose() must release spool fds.

    Iterate ``handle.messages()`` incrementally over a spool of ~200 messages,
    cancel the task group after consuming only a few items (deterministically,
    via a cancel scope -- no timing), then close the handle and assert every
    spool fd is released. Mirrors the ``_fd is None`` inspection used by
    ``test_spooled_handle_aclose_during_first_parse_does_not_leak``.
    """
    n_messages = 200
    sample_bytes = json.dumps(_large_sample(n_messages)).encode()

    async def parse() -> StreamParseResult:
        return await stream_parse_to_spool(
            io.BytesIO(sample_bytes), "all", None, tmp_path
        )

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(INFO, parse, fallback)

    consumed: list[str | None] = []

    async with anyio.create_task_group() as tg:

        async def iterate_then_cancel() -> None:
            async for message in handle.messages():
                consumed.append(message.id)
                if len(consumed) >= 3:
                    # Deterministic cancellation once we've streamed a few
                    # items -- the iterator is suspended mid-spool.
                    tg.cancel_scope.cancel()
                    return

        tg.start_soon(iterate_then_cancel)

    # We stopped well short of draining the spool.
    assert 0 < len(consumed) < n_messages
    assert consumed[:3] == ["m0", "m1", "m2"]

    # The parse ran and produced a live result whose spool fds are open.
    assert handle._result is not None
    result = handle._result
    assert result.messages._fd is not None

    await handle.aclose()

    # All spool fds released, nothing leaked.
    assert result.messages._fd is None
    assert result.events._fd is None
    assert result.blobs._fd is None
    assert handle._result is None
    assert handle._closed is True


def _mixed_messages() -> list[dict[str, Any]]:
    return [
        {"id": "m1", "role": "system", "content": "sys"},
        {"id": "m2", "role": "user", "content": "hello"},
        {"id": "m3", "role": "assistant", "content": "world"},
        {"id": "m4", "role": "user", "content": "again"},
    ]


def _mixed_events() -> list[dict[str, Any]]:
    from inspect_ai.event._info import InfoEvent
    from inspect_ai.event._state import StateEvent

    # Two `info` events bracketing one `state` event, serialized from real
    # objects so both the spooled replay path and the materialized-validate
    # path accept them.
    return [
        InfoEvent(data="a").model_dump(mode="json"),
        StateEvent(changes=[]).model_dump(mode="json"),
        InfoEvent(data="b").model_dump(mode="json"),
    ]


def _mixed_spooled_handle(tmp_path: Path) -> SpooledTranscriptHandle:
    sample: dict[str, Any] = {
        "id": "t1",
        "messages": _mixed_messages(),
        "events": _mixed_events(),
        "attachments": {},
    }

    async def parse() -> Any:
        return await stream_parse_to_spool(
            io.BytesIO(json.dumps(sample).encode()), "all", "all", tmp_path
        )

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    return SpooledTranscriptHandle(INFO, parse, fallback)


def _mixed_materialized_handle() -> MaterializedTranscriptHandle:
    from inspect_ai.event._event import Event
    from inspect_ai.model._chat_message import ChatMessage
    from pydantic import TypeAdapter

    messages = TypeAdapter(list[ChatMessage]).validate_python(_mixed_messages())
    events = TypeAdapter(list[Event]).validate_python(_mixed_events())
    transcript = Transcript.model_construct(
        transcript_id="t1",
        messages=messages,
        events=events,
        timelines=[],
        metadata={},
    )

    async def load_fn() -> Transcript:
        return transcript

    return MaterializedTranscriptHandle(load_fn, INFO)


@pytest.mark.asyncio
async def test_messages_types_filters_to_role(tmp_path: Path) -> None:
    for handle in (_mixed_spooled_handle(tmp_path), _mixed_materialized_handle()):
        async with handle:
            users = [m async for m in handle.messages(types=["user"])]
            assert [m.role for m in users] == ["user", "user"]
            assert [m.id for m in users] == ["m2", "m4"]


@pytest.mark.asyncio
async def test_events_types_filters_to_event(tmp_path: Path) -> None:
    for handle in (_mixed_spooled_handle(tmp_path), _mixed_materialized_handle()):
        async with handle:
            infos = [e async for e in handle.events(types=["info"])]
            assert [e.event for e in infos] == ["info", "info"]


@pytest.mark.asyncio
async def test_types_none_yields_everything(tmp_path: Path) -> None:
    for handle in (_mixed_spooled_handle(tmp_path), _mixed_materialized_handle()):
        async with handle:
            msgs = [m async for m in handle.messages()]
            msgs_explicit = [m async for m in handle.messages(types=None)]
            evts = [e async for e in handle.events()]
            assert [m.id for m in msgs] == ["m1", "m2", "m3", "m4"]
            assert [m.id for m in msgs_explicit] == ["m1", "m2", "m3", "m4"]
            assert [e.event for e in evts] == ["info", "state", "info"]


@pytest.mark.asyncio
async def test_types_all_behaves_like_none(tmp_path: Path) -> None:
    for handle in (_mixed_spooled_handle(tmp_path), _mixed_materialized_handle()):
        async with handle:
            msgs = [m async for m in handle.messages(types="all")]
            evts = [e async for e in handle.events(types="all")]
            assert [m.id for m in msgs] == ["m1", "m2", "m3", "m4"]
            assert [e.event for e in evts] == ["info", "state", "info"]


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
