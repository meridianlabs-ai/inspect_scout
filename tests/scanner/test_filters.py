"""Tests for message and event filter functionality."""

from collections.abc import Callable
from typing import Any

import pytest
from inspect_scout import EventType, MessageType
from inspect_scout._scanner.filter import (
    normalize_events_filter,
    normalize_messages_filter,
    normalize_timeline_filter,
    validate_events_filter,
    validate_messages_filter,
)

# Message filter tests


def test_valid_message_filters() -> None:
    """Valid message filters should be accepted."""
    valid_filters = [
        ["system"],
        ["user"],
        ["assistant"],
        ["tool"],
        ["system", "user"],
        ["system", "user", "assistant", "tool"],
    ]

    for filter_list in valid_filters:
        # Should not raise
        validate_messages_filter(filter_list)  # type: ignore[arg-type]
        normalized = normalize_messages_filter(filter_list)  # type: ignore[arg-type]
        assert normalized == filter_list


def test_all_message_filter() -> None:
    """'all' filter should pass through unchanged."""
    result = normalize_messages_filter("all")
    assert result == "all"


def test_duplicate_message_filters() -> None:
    """Duplicate filters should be deduplicated."""
    filter_list = ["system", "user", "system", "user", "assistant"]
    result = normalize_messages_filter(filter_list)  # type: ignore[arg-type]
    assert result == ["system", "user", "assistant"]


def test_empty_message_filter() -> None:
    """Empty filter list should raise ValueError."""
    with pytest.raises(ValueError, match="is not allowed"):
        validate_messages_filter([])


def test_invalid_message_filter() -> None:
    """Invalid filter types should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid messages filter"):
        validate_messages_filter(["invalid"])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="Invalid messages filter"):
        validate_messages_filter(["system", "invalid", "user"])  # type: ignore[list-item]


def test_none_message_filter() -> None:
    """None filter should not raise."""
    validate_messages_filter(None)  # Should not raise


def test_message_filter_order_preserved() -> None:
    """Filter order should be preserved after normalization."""
    filter_list = ["assistant", "system", "user"]
    result = normalize_messages_filter(filter_list)  # type: ignore[arg-type]
    assert result == ["assistant", "system", "user"]


@pytest.mark.parametrize("filter_type", ["system", "user", "assistant", "tool"])
def test_each_message_type(filter_type: MessageType) -> None:
    """Each message type should be valid on its own."""
    validate_messages_filter([filter_type])
    result = normalize_messages_filter([filter_type])
    assert result == [filter_type]


# Event filter tests


def test_valid_event_filters() -> None:
    """Valid event filters should be accepted."""
    valid_filters = [
        ["model"],
        ["tool"],
        ["model", "tool"],
        ["sample_init"],
        ["sample_limit"],
        ["sandbox"],
        ["state"],
        ["store"],
        ["approval"],
        ["input"],
        ["score"],
        ["error"],
        ["logger"],
        ["info"],
        ["span_begin"],
        ["span_end"],
        ["compaction"],
        ["model", "tool", "error", "logger"],
    ]

    for filter_list in valid_filters:
        # Should not raise
        validate_events_filter(filter_list)  # type: ignore[arg-type]
        normalized = normalize_events_filter(filter_list)  # type: ignore[arg-type]
        assert normalized == filter_list


def test_all_event_filter() -> None:
    """'all' filter should pass through unchanged."""
    result = normalize_events_filter("all")
    assert result == "all"


def test_duplicate_event_filters() -> None:
    """Duplicate filters should be deduplicated."""
    filter_list = ["model", "tool", "model", "error", "tool"]
    result = normalize_events_filter(filter_list)  # type: ignore[arg-type]
    assert result == ["model", "tool", "error"]


def test_empty_event_filter() -> None:
    """Empty filter list should raise ValueError."""
    with pytest.raises(ValueError, match="is not allowed"):
        validate_events_filter([])


def test_invalid_event_filter() -> None:
    """Invalid filter types should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid events filter"):
        validate_events_filter(["invalid"])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="Invalid events filter"):
        validate_events_filter(["model", "invalid", "tool"])  # type: ignore[list-item]


def test_deprecated_event_filters() -> None:
    """Deprecated event types should raise ValueError."""
    # step and subtask are deprecated
    with pytest.raises(ValueError, match="Invalid events filter"):
        validate_events_filter(["step"])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="Invalid events filter"):
        validate_events_filter(["subtask"])  # type: ignore[list-item]


def test_none_event_filter() -> None:
    """None filter should not raise."""
    validate_events_filter(None)  # Should not raise


def test_event_filter_order_preserved() -> None:
    """Filter order should be preserved after normalization."""
    filter_list = ["tool", "model", "error"]
    result = normalize_events_filter(filter_list)  # type: ignore[arg-type]
    assert result == ["tool", "model", "error"]


@pytest.mark.parametrize(
    "filter_type",
    [
        "model",
        "tool",
        "sample_init",
        "sample_limit",
        "sandbox",
        "state",
        "store",
        "approval",
        "input",
        "score",
        "error",
        "logger",
        "info",
        "span_begin",
        "span_end",
        "compaction",
    ],
)
def test_each_event_type(filter_type: EventType) -> None:
    """Each event type should be valid on its own."""
    validate_events_filter([filter_type])
    result = normalize_events_filter([filter_type])
    assert result == [filter_type]


# Filter combination tests


def test_message_and_event_filters_together() -> None:
    """Both message and event filters can be used together."""
    messages = ["system", "user"]
    events = ["model", "tool"]

    # Normalize both
    norm_messages = normalize_messages_filter(messages)  # type: ignore[arg-type]
    norm_events = normalize_events_filter(events)  # type: ignore[arg-type]

    assert norm_messages == messages
    assert norm_events == events


def test_all_filters_together() -> None:
    """'all' can be used for both messages and events."""
    norm_messages = normalize_messages_filter("all")
    norm_events = normalize_events_filter("all")

    assert norm_messages == "all"
    assert norm_events == "all"


def test_mixed_specific_and_all() -> None:
    """Can mix specific filter with 'all' filter."""
    norm_messages = normalize_messages_filter(["system", "user"])
    norm_events = normalize_events_filter("all")

    assert norm_messages == ["system", "user"]
    assert norm_events == "all"


# Timeline filter tests


def test_all_timeline_filter() -> None:
    """'all' filter should pass through unchanged."""
    from inspect_scout._scanner.filter import normalize_timeline_filter

    result = normalize_timeline_filter("all")
    assert result == "all"


def test_timeline_filter_list() -> None:
    """Event type timeline filter should be accepted."""
    from inspect_scout._scanner.filter import normalize_timeline_filter

    result = normalize_timeline_filter(["model"])
    assert result == ["model"]


def test_timeline_filter_multiple_event_types() -> None:
    """Multiple event types in timeline filter should be accepted."""
    from inspect_scout._scanner.filter import normalize_timeline_filter

    result = normalize_timeline_filter(["model", "tool"])
    assert result == ["model", "tool"]


def test_duplicate_timeline_filters() -> None:
    """Duplicate filters should be deduplicated."""
    from inspect_scout._scanner.filter import normalize_timeline_filter

    result = normalize_timeline_filter(["model", "tool", "model"])
    assert result == ["model", "tool"]


def test_empty_timeline_filter() -> None:
    """Empty filter list should raise ValueError."""
    from inspect_scout._scanner.filter import normalize_timeline_filter

    with pytest.raises(ValueError, match="is not allowed"):
        normalize_timeline_filter([])


def test_invalid_timeline_filter() -> None:
    """Invalid event types in timeline filter should raise ValueError.

    Reported against `timeline`, the argument the caller wrote, rather than
    against `events`, which it is converted to before loading.
    """
    from inspect_scout._scanner.filter import normalize_timeline_filter

    with pytest.raises(ValueError, match="Invalid timeline filter"):
        normalize_timeline_filter(["invalid"])  # type: ignore[list-item]


def test_timeline_filter_true() -> None:
    """True should expand to the default event set."""
    from inspect_scout._scanner.filter import (
        TIMELINE_DEFAULT_EVENTS,
        normalize_timeline_filter,
    )

    result = normalize_timeline_filter(True)
    assert result == TIMELINE_DEFAULT_EVENTS


def test_timeline_filter_true_contains_expected_types() -> None:
    """Default event set should contain the expected conversation event types."""
    from inspect_scout._scanner.filter import TIMELINE_DEFAULT_EVENTS

    expected = {
        "model",
        "tool",
        "approval",
        "compaction",
        "branch",
        "error",
        "info",
        "span_begin",
        "span_end",
    }
    assert set(TIMELINE_DEFAULT_EVENTS) == expected


# "all" inside a list


# Typed as Any so these need no suppression: a list containing "all" is a static
# type error as well as a runtime one, and the runtime path is what is under test.
ALL_IN_LIST: list[tuple[str, Callable[[Any], object]]] = [
    ("messages", normalize_messages_filter),
    ("events", normalize_events_filter),
    ("timeline", normalize_timeline_filter),
]


@pytest.mark.parametrize(
    ("param", "normalize"), ALL_IN_LIST, ids=[n[0] for n in ALL_IN_LIST]
)
def test_all_inside_a_list_is_rejected(
    param: str, normalize: Callable[[Any], object]
) -> None:
    """A list containing "all" selected nothing rather than everything.

    "all" is not a message role or an event type, so selection matched it against
    neither and the scan quietly ran on an empty list.
    """
    with pytest.raises(ValueError) as exc_info:
        normalize(["all"])

    message = str(exc_info.value)
    assert f"Invalid {param} filter(s): ['all']" in message
    # and the rejection must not go on to advertise "all" as allowed
    assert "'all'" not in message.split("Allowed:")[1]


@pytest.mark.parametrize(
    ("param", "normalize"), ALL_IN_LIST, ids=[n[0] for n in ALL_IN_LIST]
)
def test_all_mixed_into_a_list_is_rejected(
    param: str, normalize: Callable[[Any], object]
) -> None:
    """The same holds when "all" is one entry among valid ones."""
    valid = "user" if param == "messages" else "model"
    with pytest.raises(ValueError, match=r"Invalid .* filter\(s\): \['all'\]"):
        normalize([valid, "all"])


def test_timeline_filter_order_preserved() -> None:
    """Filter order should be preserved after normalization."""
    from inspect_scout._scanner.filter import normalize_timeline_filter

    result = normalize_timeline_filter(["tool", "model", "error"])
    assert result == ["tool", "model", "error"]
