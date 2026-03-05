"""Tests for v3 message/call pool resolution."""

from __future__ import annotations

import pytest
from inspect_scout._transcript.json.pool import _expand_refs_raw, resolve_pools
from inspect_scout._transcript.json.reducer import (
    ParseState,
    call_pool_item_coroutine,
    message_pool_item_coroutine,
)


class TestExpandRefsRaw:
    """Unit tests for range-encoded ref expansion."""

    @pytest.mark.parametrize(
        ("refs", "pool", "expected"),
        [
            pytest.param([], [{"role": "user", "content": "hi"}], [], id="empty_refs"),
            pytest.param(
                [[0, 4]], ["a", "b", "c", "d"], ["a", "b", "c", "d"], id="contiguous"
            ),
            pytest.param(
                [[0, 2], [4, 6]],
                ["a", "b", "c", "d", "e", "f"],
                ["a", "b", "e", "f"],
                id="multiple_ranges",
            ),
            pytest.param(
                [[0, 1], [2, 3]], ["a", "b", "c"], ["a", "c"], id="single_element"
            ),
            pytest.param(
                [[2, 3], [5, 6], [8, 9]],
                list(range(10)),
                [2, 5, 8],
                id="non_contiguous",
            ),
        ],
    )
    def test_expand_refs(
        self, refs: list[list[int]], pool: list[object], expected: list[object]
    ) -> None:
        assert _expand_refs_raw(refs, pool) == expected


class TestResolvePools:
    """Tests for resolve_pools post-processing step."""

    def test_noop_when_pools_empty(self) -> None:
        """v2 files: pools are empty, events unchanged."""
        state = ParseState()
        state.events = [
            {"event": "model", "input": [{"role": "user", "content": "hi"}]}
        ]
        original_events = [e.copy() for e in state.events]
        resolve_pools(state)
        assert state.events == original_events

    def test_resolves_input_refs(self) -> None:
        """v3 events with input_refs get input populated from message_pool."""
        state = ParseState()
        state.message_pool = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        state.events = [
            {"event": "model", "input": [], "input_refs": [[0, 2]]},
            {"event": "model", "input": [], "input_refs": [[0, 3]]},
        ]
        resolve_pools(state)
        assert state.events[0]["input"] == [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        assert "input_refs" not in state.events[0]
        assert len(state.events[1]["input"]) == 3

    def test_resolves_call_refs(self) -> None:
        """v3 events with call_refs get request messages from call_pool."""
        state = ParseState()
        state.call_pool = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
        ]
        state.events = [
            {
                "event": "model",
                "call": {
                    "request": {"model": "gpt-4"},
                    "call_refs": [[0, 2]],
                    "call_key": "messages",
                },
            }
        ]
        resolve_pools(state)
        call = state.events[0]["call"]
        assert call["request"]["messages"] == [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
        ]
        assert "call_refs" not in call
        assert "call_key" not in call

    def test_mixed_v2_and_v3_events(self) -> None:
        """Events without refs are left unchanged."""
        state = ParseState()
        state.message_pool = [{"role": "user", "content": "pooled"}]
        state.events = [
            {"event": "model", "input": [{"role": "user", "content": "inline"}]},
            {"event": "model", "input": [], "input_refs": [[0, 1]]},
            {"event": "score", "score": {"value": 1.0}},
        ]
        resolve_pools(state)
        assert state.events[0]["input"] == [{"role": "user", "content": "inline"}]
        assert state.events[1]["input"] == [{"role": "user", "content": "pooled"}]
        assert state.events[2] == {"event": "score", "score": {"value": 1.0}}

    def test_call_key_defaults_to_messages(self) -> None:
        """When call_key is missing, defaults to 'messages'."""
        state = ParseState()
        state.call_pool = [{"role": "user", "content": "msg"}]
        state.events = [
            {
                "event": "model",
                "call": {
                    "request": {"model": "gpt-4"},
                    "call_refs": [[0, 1]],
                },
            }
        ]
        resolve_pools(state)
        assert "messages" in state.events[0]["call"]["request"]

    def test_call_key_contents(self) -> None:
        """call_key='contents' puts messages under 'contents' key."""
        state = ParseState()
        state.call_pool = [{"role": "user", "parts": [{"text": "hi"}]}]
        state.events = [
            {
                "event": "model",
                "call": {
                    "request": {"model": "gemini"},
                    "call_refs": [[0, 1]],
                    "call_key": "contents",
                },
            }
        ]
        resolve_pools(state)
        assert "contents" in state.events[0]["call"]["request"]

    def test_resolves_both_input_and_call_refs(self) -> None:
        """An event with both input_refs and call_refs gets both resolved."""
        state = ParseState()
        state.message_pool = [{"role": "user", "content": "input_msg"}]
        state.call_pool = [{"role": "user", "content": "call_msg"}]
        state.events = [
            {
                "event": "model",
                "input": [],
                "input_refs": [[0, 1]],
                "call": {"request": {}, "call_refs": [[0, 1]]},
            }
        ]
        resolve_pools(state)
        assert state.events[0]["input"] == [{"role": "user", "content": "input_msg"}]
        assert state.events[0]["call"]["request"]["messages"] == [
            {"role": "user", "content": "call_msg"}
        ]
        assert "input_refs" not in state.events[0]
        assert "call_refs" not in state.events[0]["call"]

    def test_call_refs_creates_request_when_missing(self) -> None:
        """call_refs resolution works even when request dict is absent."""
        state = ParseState()
        state.call_pool = [{"role": "user", "content": "msg"}]
        state.events = [
            {
                "event": "model",
                "call": {
                    "call_refs": [[0, 1]],
                },
            }
        ]
        resolve_pools(state)
        assert state.events[0]["call"]["request"]["messages"] == [
            {"role": "user", "content": "msg"}
        ]


class TestPoolCoroutines:
    """Tests for streaming pool coroutines."""

    def test_message_pool_coroutine_collects_items(self) -> None:
        state = ParseState()
        coro = message_pool_item_coroutine(state)
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
        coro = call_pool_item_coroutine(state)
        coro.send(("call_pool.item", "start_map", None))
        coro.send(("call_pool.item", "map_key", "role"))
        coro.send(("call_pool.item.role", "string", "user"))
        coro.send(("call_pool.item", "map_key", "content"))
        coro.send(("call_pool.item.content", "string", "hello"))
        coro.send(("call_pool.item", "end_map", None))
        assert state.call_pool == [{"role": "user", "content": "hello"}]
