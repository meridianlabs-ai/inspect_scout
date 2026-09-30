from typing import Literal

from .._transcript.types import EventType, MessageType


def normalize_messages_filter(
    filter: list[MessageType] | Literal["all"],
) -> list[MessageType] | Literal["all"]:
    if filter == "all":
        return filter
    uniq: list[MessageType] = []
    seen: set[MessageType] = set()
    for x in filter:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    validate_messages_filter(uniq)
    return uniq


def normalize_events_filter(
    filter: list[EventType] | Literal["all"],
) -> list[EventType] | Literal["all"]:
    if filter == "all":
        return filter
    uniq: list[EventType] = []
    seen: set[EventType] = set()
    for x in filter:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    validate_events_filter(uniq)
    return uniq


def validate_messages_filter(filter: list[MessageType] | None) -> None:
    if filter is None:
        return
    # "all" is deliberately absent: it selects every message as a bare filter, but
    # inside a list it is matched against message roles, where nothing carries it.
    allowed: set[str] = {"system", "user", "assistant", "tool"}
    if not filter:
        raise ValueError("messages=[] is not allowed; provide at least one filter")
    bad = [x for x in filter if x not in allowed]
    if bad:
        raise ValueError(
            f"Invalid messages filter(s): {bad}. Allowed: {sorted(allowed)}"
        )


TIMELINE_DEFAULT_EVENTS: list[EventType] = [
    "model",
    "tool",
    "approval",
    "compaction",
    "branch",
    "error",
    "info",
    "span_begin",
    "span_end",
]


def normalize_timeline_filter(
    filter: Literal[True] | list[EventType] | Literal["all"],
) -> list[EventType] | Literal["all"]:
    if filter is True:
        return list(TIMELINE_DEFAULT_EVENTS)
    if filter == "all":
        return filter
    uniq: list[EventType] = []
    seen: set[EventType] = set()
    for x in filter:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    validate_events_filter(uniq, "timeline")
    return uniq


def validate_events_filter(
    filter: list[EventType] | None, param: str = "events"
) -> None:
    """Validate an event-type list.

    ``normalize_timeline_filter`` reuses this validator, so ``param`` names the
    caller's own argument and a timeline filter is not reported as an events one.
    """
    if filter is None:
        return
    # "all" is deliberately absent: it selects every event as a bare filter, but
    # inside a list it is matched against event types, where nothing carries it.
    allowed: set[str] = {
        "model",
        "tool",
        "sample_init",
        "sample_limit",
        "sandbox",
        "state",
        "store",
        "approval",
        "compaction",
        "branch",
        "input",
        "score",
        "error",
        "logger",
        "info",
        "span_begin",
        "span_end",
    }
    if not filter:
        raise ValueError(f"{param}=[] is not allowed; provide at least one filter")
    bad = [x for x in filter if x not in allowed]
    if bad:
        raise ValueError(
            f"Invalid {param} filter(s): {bad}. Allowed: {sorted(allowed)}"
        )
