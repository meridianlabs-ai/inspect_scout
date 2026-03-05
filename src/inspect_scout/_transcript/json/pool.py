"""V3 message/call pool resolution for streaming-parsed eval samples.

Expands range-encoded pool references (input_refs, call_refs) back into
inline data on raw event dicts. Operates entirely in the dict domain --
no Pydantic models involved.
"""

from __future__ import annotations

from typing import Any

from .reducer import ParseState


def _expand_refs_raw(refs: list[list[int]], pool: list[Any]) -> list[Any]:
    """Expand range-encoded refs against a pool.

    Each element is [start, end_exclusive) -- a half-open range yielding
    pool[start:end_exclusive].
    """
    result: list[Any] = []
    for start, end_exclusive in refs:
        result.extend(pool[start:end_exclusive])
    return result


def _resolve_events_pools(
    events: list[dict[str, Any]],
    message_pool: list[Any],
    call_pool: list[Any],
) -> None:
    """Expand pool refs in event dicts (mutates in-place). No-op when pools are empty."""
    if not message_pool and not call_pool:
        return
    for event_dict in events:
        input_refs = event_dict.get("input_refs")
        if input_refs and message_pool:
            event_dict["input"] = _expand_refs_raw(input_refs, message_pool)
            event_dict.pop("input_refs", None)
        call = event_dict.get("call")
        if call and call.get("call_refs") is not None and call_pool:
            key = call.get("call_key", "messages")
            call.setdefault("request", {})[key] = _expand_refs_raw(
                call["call_refs"], call_pool
            )
            call.pop("call_refs", None)
            call.pop("call_key", None)


def resolve_pools(state: ParseState) -> None:
    """Expand message_pool/call_pool refs in parsed events (mutates in-place).

    No-op when pools are empty (v2 files).
    """
    _resolve_events_pools(state.events, state.message_pool, state.call_pool)
