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

    def test_message_pool_coroutine_events_data_prefix(self) -> None:
        """Inspect AI PR #3519 consolidated pools under events_data.{messages,calls}.

        The coroutine accepts an explicit prefix so a single ParseState can
        host coroutines listening on either schema.
        """
        from inspect_scout._transcript.json.reducer import (
            EVENTS_DATA_MESSAGES_ITEM_PREFIX,
        )

        state = ParseState()
        coro = message_pool_item_coroutine(state, EVENTS_DATA_MESSAGES_ITEM_PREFIX)
        coro.send(("events_data.messages.item", "start_map", None))
        coro.send(("events_data.messages.item", "map_key", "role"))
        coro.send(("events_data.messages.item.role", "string", "user"))
        coro.send(("events_data.messages.item", "map_key", "content"))
        coro.send(("events_data.messages.item.content", "string", "hi"))
        coro.send(("events_data.messages.item", "end_map", None))
        # Both schemas alias the same state field — the streaming dispatcher
        # routes either prefix into state.message_pool, so downstream code
        # never has to ask which schema the producer used.
        assert state.message_pool == [{"role": "user", "content": "hi"}]

    def test_call_pool_coroutine_events_data_prefix(self) -> None:
        from inspect_scout._transcript.json.reducer import (
            EVENTS_DATA_CALLS_ITEM_PREFIX,
        )

        state = ParseState()
        coro = call_pool_item_coroutine(state, EVENTS_DATA_CALLS_ITEM_PREFIX)
        coro.send(("events_data.calls.item", "start_map", None))
        coro.send(("events_data.calls.item", "map_key", "role"))
        coro.send(("events_data.calls.item.role", "string", "assistant"))
        coro.send(("events_data.calls.item", "end_map", None))
        assert state.call_pool == [{"role": "assistant"}]

    def test_pool_coroutine_ignores_non_matching_prefix(self) -> None:
        """A coroutine bound to one prefix must not consume events on another.

        The streaming parser instantiates two coroutines per pool — one for
        each accepted schema — and dispatches every pool-section event to
        both. Only the one whose prefix matches must activate.
        """
        state = ParseState()
        legacy = message_pool_item_coroutine(state)  # message_pool.item
        # Send events_data-schema events; legacy coro should ignore them.
        legacy.send(("events_data.messages.item", "start_map", None))
        legacy.send(("events_data.messages.item", "map_key", "role"))
        legacy.send(("events_data.messages.item.role", "string", "user"))
        legacy.send(("events_data.messages.item", "end_map", None))
        assert state.message_pool == []


class TestResolvePoolsFromDict:
    """Tests for the JSON5 fallback path's pool resolution.

    The streaming parser does not handle JSON5 extensions (NaN, Inf, ...),
    so a fully-buffered json5 parse is used as fallback. That path resolves
    pools via ``_resolve_pools_from_dict`` rather than coroutines.
    """

    def test_events_data_schema(self) -> None:
        """Consolidated events_data schema (inspect_ai PR #3519) is resolved."""
        from inspect_scout._transcript.json.load_filtered import (
            _resolve_pools_from_dict,
        )

        data: dict[str, object] = {
            "events_data": {
                "messages": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                ],
                "calls": [{"role": "user", "content": "call_msg"}],
            },
            "events": [
                {"event": "model", "input": [], "input_refs": [[0, 2]]},
                {
                    "event": "model",
                    "call": {"call_refs": [[0, 1]]},
                },
            ],
        }
        _resolve_pools_from_dict(data)
        events = data["events"]  # type: ignore[assignment]
        assert events[0]["input"] == [  # type: ignore[index]
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        assert "input_refs" not in events[0]  # type: ignore[operator]
        assert events[1]["call"]["request"]["messages"] == [  # type: ignore[index]
            {"role": "user", "content": "call_msg"}
        ]

    def test_legacy_top_level_pool_schema(self) -> None:
        """Pre-PR#3519 top-level message_pool / call_pool still resolves."""
        from inspect_scout._transcript.json.load_filtered import (
            _resolve_pools_from_dict,
        )

        data: dict[str, object] = {
            "message_pool": [{"role": "user", "content": "pooled"}],
            "call_pool": [{"role": "user", "content": "call_pooled"}],
            "events": [
                {"event": "model", "input": [], "input_refs": [[0, 1]]},
                {"event": "model", "call": {"call_refs": [[0, 1]]}},
            ],
        }
        _resolve_pools_from_dict(data)
        events = data["events"]  # type: ignore[assignment]
        assert events[0]["input"] == [{"role": "user", "content": "pooled"}]  # type: ignore[index]
        assert events[1]["call"]["request"]["messages"] == [  # type: ignore[index]
            {"role": "user", "content": "call_pooled"}
        ]

    def test_noop_when_neither_pool_present(self) -> None:
        """A v2 log (no pools either schema) is left unchanged."""
        from inspect_scout._transcript.json.load_filtered import (
            _resolve_pools_from_dict,
        )

        data: dict[str, object] = {
            "events": [
                {"event": "model", "input": [{"role": "user", "content": "inline"}]},
            ],
        }
        _resolve_pools_from_dict(data)
        events = data["events"]  # type: ignore[assignment]
        assert events[0]["input"] == [{"role": "user", "content": "inline"}]  # type: ignore[index]

    def test_events_data_present_but_empty_does_not_fall_back_to_legacy(
        self,
    ) -> None:
        """events_data presence is authoritative — empty new-schema pools
        must NOT silently fall back to stale legacy ``message_pool`` /
        ``call_pool`` keys that a transitional producer might have left in.
        """
        from inspect_scout._transcript.json.load_filtered import (
            _resolve_pools_from_dict,
        )

        data: dict[str, object] = {
            "events_data": {"messages": [], "calls": []},
            # stale, must not be used
            "message_pool": [{"role": "user", "content": "STALE"}],
            "call_pool": [{"role": "user", "content": "STALE_CALL"}],
            "events": [
                {"event": "model", "input": [], "input_refs": [[0, 1]]},
                {"event": "model", "call": {"call_refs": [[0, 1]]}},
            ],
        }
        _resolve_pools_from_dict(data)
        events = data["events"]  # type: ignore[assignment]
        # message_pool empty -> input stays [] (inspect_ai's resolver leaves
        # input_refs intact when pool is empty; what matters here is that the
        # stale legacy entry was NOT substituted).
        assert events[0]["input"] == []  # type: ignore[index]
        # call_pool empty -> request.messages should not be set to STALE_CALL.
        # _resolve_events_pools short-circuits on empty pool, so call_refs
        # stays — but the legacy value definitely doesn't surface.
        assert events[1]["call"].get("request", {}).get("messages") != [  # type: ignore[index]
            {"role": "user", "content": "STALE_CALL"}
        ]

    def test_events_data_null_falls_through_to_legacy(self) -> None:
        """`events_data: null` is indistinguishable from a missing key and
        falls through to the legacy schema. (Real producers never emit both
        an explicit null events_data AND a populated legacy pool; this test
        just pins down the documented contract.)"""
        from inspect_scout._transcript.json.load_filtered import (
            _resolve_pools_from_dict,
        )

        data: dict[str, object] = {
            "events_data": None,
            "message_pool": [{"role": "user", "content": "legacy"}],
            "events": [
                {"event": "model", "input": [], "input_refs": [[0, 1]]},
            ],
        }
        _resolve_pools_from_dict(data)
        events = data["events"]  # type: ignore[assignment]
        assert events[0]["input"] == [{"role": "user", "content": "legacy"}]  # type: ignore[index]

    def test_events_data_non_dict_does_not_crash(self) -> None:
        """Malformed `events_data: "string"` must not raise AttributeError."""
        from inspect_scout._transcript.json.load_filtered import (
            _resolve_pools_from_dict,
        )

        data: dict[str, object] = {
            "events_data": "unsupported",
            "events": [
                {"event": "model", "input": [{"role": "user", "content": "x"}]},
            ],
        }
        # Should not raise — falls through to empty pools, events unchanged.
        _resolve_pools_from_dict(data)
        events = data["events"]  # type: ignore[assignment]
        assert events[0]["input"] == [{"role": "user", "content": "x"}]  # type: ignore[index]
