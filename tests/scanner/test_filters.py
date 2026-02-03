"""Tests for message and event filter functionality."""

import pytest
from inspect_scout import EventType, MessageType
from inspect_scout._scanner.filter import (
    normalize_events_filter,
    normalize_messages_filter,
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
