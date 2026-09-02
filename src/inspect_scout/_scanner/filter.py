from typing import Literal, get_args

from .._transcript.types import EventFilter, EventType, MessageType


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


def widen_timeline_for_events(
    timeline: list[EventType] | Literal["all"] | None, events: EventFilter
) -> list[EventType] | Literal["all"] | None:
    """Widen a timeline filter to cover an explicit events selection.

    Timeline content is pruned by its own filter, and interleaved entries are
    rendered from the timeline -- so an event type present in ``events`` but
    absent from the timeline filter is dropped silently rather than rendered.
    The caller normalizes ``timeline=True`` first, and that default set
    excludes ``score`` -- the case this exists for.
    """
    if timeline is None:
        return timeline
    if timeline == "all" or events == "all":
        return "all"
    if events is None:
        return timeline
    # Iterate the known event types rather than the selection: `events` admits
    # arbitrary strings, and only real event types can widen a timeline filter.
    selected = set(events)
    widened = list(timeline)
    for event_type in get_args(EventType):
        if event_type in selected and event_type not in widened:
            widened.append(event_type)
    return widened if len(widened) > len(timeline) else timeline


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
    validate_events_filter(uniq)
    return uniq


def validate_events_filter(filter: list[EventType] | None) -> None:
    if filter is None:
        return
    # Derived from EventType rather than duplicated: the two lists drifted apart
    # once already, leaving the literal narrower than what this accepted.
    allowed: set[str] = {"all", *get_args(EventType)}
    if not filter:
        raise ValueError("events=[] is not allowed; provide at least one filter")
    bad = [x for x in filter if x not in allowed]
    if bad:
        raise ValueError(f"Invalid events filter(s): {bad}. Allowed: {sorted(allowed)}")
