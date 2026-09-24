from typing import Literal

from .._transcript.types import EventType, MessageType


def _reject_bare_string(filter: object, param: str) -> None:
    """Reject a non-empty bare string filter other than "all".

    A string is iterable, so a filter like `assistant` would otherwise be read as
    its characters and rejected as a list of single letters, which says nothing
    about what the caller did wrong. The empty string is left alone so that it
    still reaches the existing "provide at least one filter" message, which is
    the right advice for it.
    """
    if isinstance(filter, str) and filter:
        # str.__str__ so that a str-mixin enum renders its value rather than its
        # member name, keeping the quoted value and the worked example in step.
        value = str.__str__(filter)
        raise ValueError(
            f'{param}={value!r} is not a valid filter. Use "all", or a list, '
            f'for example ["{value}"].'
        )


def normalize_messages_filter(
    filter: list[MessageType] | Literal["all"],
) -> list[MessageType] | Literal["all"]:
    if filter == "all":
        return filter
    _reject_bare_string(filter, "messages")
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
    _reject_bare_string(filter, "events")
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
    allowed: set[str] = {"all", "system", "user", "assistant", "tool"}
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
    _reject_bare_string(filter, "timeline")
    uniq: list[EventType] = []
    seen: set[EventType] = set()
    for x in filter:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    validate_events_filter(uniq)
    return uniq


def validate_events_filter(filter: list[EventType] | None) -> None:
    if filter is None:
        return
    allowed: set[str] = {
        "all",
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
        raise ValueError("events=[] is not allowed; provide at least one filter")
    bad = [x for x in filter if x not in allowed]
    if bad:
        raise ValueError(f"Invalid events filter(s): {bad}. Allowed: {sorted(allowed)}")
