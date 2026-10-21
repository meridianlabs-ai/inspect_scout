"""Tests for v3 message/call pool resolution."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.json.reducer import (
    CALL_POOL_ITEM_PREFIX,
    MESSAGE_POOL_ITEM_PREFIX,
    ParseState,
    call_pool_item_coroutine,
    message_pool_item_coroutine,
)
from inspect_scout._transcript.types import Transcript, TranscriptInfo

POOL = [
    {"id": "p0", "role": "system", "content": "You are helpful"},
    {"id": "p1", "role": "user", "content": "Hello"},
    {"id": "p2", "role": "assistant", "content": "Hi there"},
]


def _model_event(**fields: Any) -> dict[str, Any]:
    return {
        "span_id": "s1",
        "timestamp": "2022-01-01T00:00:00+00:00",
        "working_start": 0,
        "event": "model",
        "model": "m",
        "input": [],
        "output": {"model": "m", "choices": []},
        "tools": [],
        "tool_choice": "auto",
        "config": {},
        **fields,
    }


async def _load(sample: dict[str, Any], raw: bytes | None = None) -> Transcript:
    data = raw if raw is not None else json.dumps(sample).encode()
    return await load_filtered_transcript(
        io.BytesIO(data), TranscriptInfo(transcript_id="t1"), "all", "all"
    )


def _model_events(transcript: Transcript) -> list[ModelEvent]:
    return [e for e in transcript.events if isinstance(e, ModelEvent)]


class TestLoadResolvesPools:
    @pytest.mark.asyncio
    async def test_input_refs_expand_to_shared_messages(self) -> None:
        """Events referencing the same pool entry share one validated message.

        Validating a copy per reference is quadratic in conversation length:
        a long agent transcript expands to tens of millions of messages.
        """
        transcript = await _load(
            {
                "events": [
                    _model_event(input_refs=[[0, 2]]),
                    _model_event(input_refs=[[0, 3]]),
                ],
                "events_data": {"messages": POOL, "calls": []},
            }
        )
        first, second = _model_events(transcript)
        assert [m.text for m in first.input] == ["You are helpful", "Hello"]
        assert [m.text for m in second.input] == [
            "You are helpful",
            "Hello",
            "Hi there",
        ]
        assert first.input_refs is None
        assert first.input[0] is second.input[0]

    @pytest.mark.asyncio
    async def test_non_contiguous_ranges(self) -> None:
        transcript = await _load(
            {
                "events": [_model_event(input_refs=[[0, 1], [2, 3]])],
                "events_data": {"messages": POOL, "calls": []},
            }
        )
        (event,) = _model_events(transcript)
        assert [m.id for m in event.input] == ["p0", "p2"]

    @pytest.mark.asyncio
    async def test_inline_input_unchanged(self) -> None:
        """v2 events carry their input inline and have no refs to expand."""
        transcript = await _load(
            {
                "events": [
                    _model_event(input=[{"role": "user", "content": "inline"}]),
                    _model_event(input_refs=[[1, 2]]),
                ],
                "events_data": {"messages": POOL, "calls": []},
            }
        )
        inline, pooled = _model_events(transcript)
        assert [m.text for m in inline.input] == ["inline"]
        assert [m.text for m in pooled.input] == ["Hello"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("call_key", [None, "contents"])
    async def test_call_refs_expand_under_call_key(self, call_key: str | None) -> None:
        call: dict[str, Any] = {"request": {"model": "m"}, "call_refs": [[0, 2]]}
        if call_key:
            call["call_key"] = call_key
        transcript = await _load(
            {
                "events": [_model_event(call=call)],
                "events_data": {
                    "messages": [],
                    "calls": [{"role": "user", "n": 1}, {"role": "user", "n": 2}],
                },
            }
        )
        (event,) = _model_events(transcript)
        assert event.call is not None
        assert event.call.call_refs is None
        assert event.call.request[call_key or "messages"] == [
            {"role": "user", "n": 1},
            {"role": "user", "n": 2},
        ]

    @pytest.mark.asyncio
    async def test_attachment_ref_in_call_pool_entry_resolves(self) -> None:
        att = "a" * 32
        transcript = await _load(
            {
                "events": [_model_event(call={"request": {}, "call_refs": [[0, 1]]})],
                "attachments": {att: "POOLED CALL CONTENT"},
                "events_data": {
                    "messages": [],
                    "calls": [{"role": "user", "content": f"attachment://{att}"}],
                },
            }
        )
        (event,) = _model_events(transcript)
        assert event.call is not None
        assert event.call.request["messages"] == [
            {"role": "user", "content": "POOLED CALL CONTENT"}
        ]

    @pytest.mark.asyncio
    async def test_unreferenced_pool_is_not_validated(self) -> None:
        """An events filter that keeps no model events never touches the pool."""
        sample = {
            "events": [
                _model_event(input_refs=[[0, 1]]),
                {
                    "span_id": "s1",
                    "timestamp": "2022-01-01T00:00:00+00:00",
                    "working_start": 0,
                    "event": "info",
                    "data": "kept",
                },
            ],
            "events_data": {"messages": [{"role": "bogus"}], "calls": []},
        }
        transcript = await load_filtered_transcript(
            io.BytesIO(json.dumps(sample).encode()),
            TranscriptInfo(transcript_id="t1"),
            None,
            ["info"],
        )
        assert [e.event for e in transcript.events] == ["info"]

    @pytest.mark.asyncio
    async def test_legacy_top_level_pools(self) -> None:
        transcript = await _load(
            {
                "events": [
                    _model_event(
                        input_refs=[[1, 2]],
                        call={"request": {}, "call_refs": [[0, 1]]},
                    )
                ],
                "message_pool": POOL,
                "call_pool": [{"role": "user", "content": "call"}],
            }
        )
        (event,) = _model_events(transcript)
        assert [m.text for m in event.input] == ["Hello"]
        assert event.call is not None
        assert event.call.request["messages"] == [{"role": "user", "content": "call"}]

    @pytest.mark.asyncio
    async def test_json5_fallback_expands_shared_messages(self) -> None:
        """NaN forces the non-streaming fallback, which resolves pools the same way."""
        sample = {
            "metadata": {"x": "NAN_PLACEHOLDER"},
            "events": [
                _model_event(input_refs=[[0, 2]]),
                _model_event(input_refs=[[0, 2]]),
            ],
            "events_data": {"messages": POOL, "calls": []},
        }
        raw = json.dumps(sample).replace('"NAN_PLACEHOLDER"', "NaN").encode()
        transcript = await _load(sample, raw)
        first, second = _model_events(transcript)
        assert [m.text for m in first.input] == ["You are helpful", "Hello"]
        assert first.input[1] is second.input[1]


class TestPoolCoroutines:
    """Tests for streaming pool coroutines."""

    def test_message_pool_coroutine_collects_items(self) -> None:
        state = ParseState()
        coro = message_pool_item_coroutine(state, MESSAGE_POOL_ITEM_PREFIX)
        # Simulate ijson events for: message_pool: [{role: "user", content: "hi"}]
        coro.send(("message_pool.item", "start_map", None))
        coro.send(("message_pool.item", "map_key", "role"))
        coro.send(("message_pool.item.role", "string", "user"))
        coro.send(("message_pool.item", "map_key", "content"))
        coro.send(("message_pool.item.content", "string", "hi"))
        coro.send(("message_pool.item", "end_map", None))
        assert state.message_pool == [{"role": "user", "content": "hi"}]

    def test_call_pool_coroutine_collects_items(self) -> None:
        state = ParseState()
        coro = call_pool_item_coroutine(state, CALL_POOL_ITEM_PREFIX)
        coro.send(("call_pool.item", "start_map", None))
        coro.send(("call_pool.item", "map_key", "role"))
        coro.send(("call_pool.item.role", "string", "user"))
        coro.send(("call_pool.item", "map_key", "content"))
        coro.send(("call_pool.item.content", "string", "hello"))
        coro.send(("call_pool.item", "end_map", None))
        assert state.call_pool == [{"role": "user", "content": "hello"}]
