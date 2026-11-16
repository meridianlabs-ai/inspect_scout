"""Hydration of legacy nested ``ToolEvent.events``, shared by both read paths."""

from __future__ import annotations

from typing import Any, Callable

from inspect_ai.event._event import Event
from pydantic import TypeAdapter, ValidationError

_EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)


def hydrate_nested_tool_events(
    item: dict[str, Any], resolve: Callable[[dict[str, Any]], dict[str, Any]]
) -> None:
    """Recursively resolve and validate a `ToolEvent` item's nested `events`, in place.

    `ToolEvent.events` is typed `list[Any]` (a legacy field for tool-spawned
    agents), so validating the outer event leaves its entries as raw dicts.
    Consumers that walk nested events expect real `Event` instances, so each
    nested dict is passed through `resolve` (attachment/pool resolution; the
    identity when the caller has already resolved the whole item) and
    validated the same way top-level events are.

    Anything that does not validate is passed through unchanged. The field is
    legacy and loosely shaped: a non-dict entry, or a dict from a future or
    unknown event type, must not take down the surrounding events -- and a
    dict that is not an event at all must not be coerced into an invented one
    (`TypeAdapter(Event)` happily turns `{"hello": "world"}` into a
    `BranchEvent`).
    """
    nested = item.get("events")
    if not nested:
        return
    hydrated: list[Any] = []
    for nested_item in nested:
        if not isinstance(nested_item, dict):
            hydrated.append(nested_item)
            continue
        resolved = resolve(nested_item)
        hydrate_nested_tool_events(resolved, resolve)
        if "event" not in resolved:
            hydrated.append(resolved)  # not an event: validating would invent one
            continue
        try:
            hydrated.append(_EVENT_ADAPTER.validate_python(resolved))
        except ValidationError:
            hydrated.append(resolved)  # unknown or future event type
    item["events"] = hydrated
