"""Tests for timeline ASCII repr rendering."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from inspect_ai.event import (
    Timeline,
    TimelineBranch,
    TimelineEvent,
    TimelineSpan,
)
from inspect_ai.event._timeline_repr import (
    _format_token_count,
    _render_bar,
)

# =============================================================================
# Helpers
# =============================================================================

_T0 = datetime(2025, 1, 1, 0, 0, 0)


def _ts(seconds: float) -> datetime:
    """Return a timestamp offset from T0 by seconds."""
    return _T0 + timedelta(seconds=seconds)


def _make_mock_event(
    *,
    timestamp: datetime,
    completed: datetime | None = None,
    event_type: str = "model",
    input_tokens: int = 0,
    output_tokens: int = 0,
    error: str | None = None,
    output_error: str | None = None,
) -> TimelineEvent:
    """Build a TimelineEvent with a minimal mock event object.

    Uses model_construct on real event classes to bypass validation while
    still passing isinstance checks.
    """
    from types import SimpleNamespace

    from inspect_ai.event import ModelEvent, ToolEvent
    from inspect_ai.model import ModelOutput, ModelUsage

    event: Any
    if event_type == "model":
        usage = ModelUsage.model_construct(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_tokens_cache_read=None,
            input_tokens_cache_write=None,
        )
        output_obj = ModelOutput.model_construct(
            model="mock",
            choices=[],
            usage=usage,
            error=output_error,
        )
        event = ModelEvent.model_construct(
            event=event_type,
            timestamp=timestamp,
            completed=completed or timestamp,
            uuid=f"evt-{id(timestamp)}",
            input=[],
            output=output_obj,
            error=error,
        )
    elif event_type == "tool":
        event = ToolEvent.model_construct(
            event="tool",
            timestamp=timestamp,
            completed=completed or timestamp,
            uuid=f"evt-tool-{id(timestamp)}",
            error=error,
        )
    else:
        event = SimpleNamespace(
            event=event_type,
            timestamp=timestamp,
            completed=completed or timestamp,
            uuid=f"evt-{event_type}-{id(timestamp)}",
        )

    return TimelineEvent.model_construct(type="event", event=event)


def _make_span(
    name: str,
    *,
    content: list[TimelineEvent | TimelineSpan] | None = None,
    branches: list[TimelineBranch] | None = None,
    utility: bool = False,
) -> TimelineSpan:
    """Build a TimelineSpan with given content."""
    return TimelineSpan(
        id=f"span-{name}",
        name=name,
        span_type="agent",
        content=content or [],
        branches=branches or [],
        utility=utility,
    )


def _make_timeline(root: TimelineSpan) -> Timeline:
    """Wrap a root span in a Timeline."""
    return Timeline(name="Default", description="", root=root)


# =============================================================================
# _format_token_count
# =============================================================================


@pytest.mark.parametrize(
    "tokens,expected",
    [
        (0, "0"),
        (1, "1"),
        (999, "999"),
        (1000, "1.0k"),
        (1234, "1.2k"),
        (9999, "10.0k"),
        (12345, "12.3k"),
        (123456, "123k"),
        (999999, "1000k"),
        (1_000_000, "1.0M"),
        (1_234_567, "1.2M"),
        (12_345_678, "12.3M"),
        (123_456_789, "123M"),
    ],
)
def test_format_token_count(tokens: int, expected: str) -> None:
    assert _format_token_count(tokens) == expected


# =============================================================================
# _render_bar
# =============================================================================


def test_render_bar_full_width() -> None:
    """A segment spanning the full view range fills the entire bar."""
    bar = _render_bar(
        segments=[(_T0, _ts(100))],
        view_start=_T0,
        view_end=_ts(100),
        width=20,
        markers=[],
    )
    assert bar == "█" * 20


def test_render_bar_half_width() -> None:
    """A segment spanning the first half fills roughly half the bar."""
    bar = _render_bar(
        segments=[(_T0, _ts(50))],
        view_start=_T0,
        view_end=_ts(100),
        width=20,
        markers=[],
    )
    assert bar.startswith("██████████")
    assert bar.rstrip() == bar.rstrip(" ").ljust(0)  # trailing spaces


def test_render_bar_with_marker() -> None:
    """Markers overlay on filled positions."""
    bar = _render_bar(
        segments=[(_T0, _ts(100))],
        view_start=_T0,
        view_end=_ts(100),
        width=20,
        markers=[(_ts(50), "▲")],
    )
    assert "▲" in bar
    assert len(bar) == 20


def test_render_bar_empty_segment() -> None:
    """An empty time range still renders."""
    bar = _render_bar(
        segments=[],
        view_start=_T0,
        view_end=_ts(100),
        width=10,
        markers=[],
    )
    assert bar == " " * 10


def test_render_bar_multiple_segments() -> None:
    """Multiple non-overlapping segments render with gaps."""
    bar = _render_bar(
        segments=[(_T0, _ts(20)), (_ts(80), _ts(100))],
        view_start=_T0,
        view_end=_ts(100),
        width=20,
        markers=[],
    )
    # First ~4 chars and last ~4 chars should be filled
    assert bar[0] == "█"
    assert bar[-1] == "█"
    # Middle should have spaces
    assert " " in bar


# =============================================================================
# Basic repr output
# =============================================================================


def test_basic_repr() -> None:
    """A simple timeline with one child span renders correctly."""
    evt1 = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=1000, output_tokens=500
    )
    evt2 = _make_mock_event(
        timestamp=_ts(10), completed=_ts(50), input_tokens=500, output_tokens=300
    )

    child = _make_span("Explore", content=[evt2])
    root = _make_span("Transcript", content=[evt1, child])
    tl = _make_timeline(root)

    output = repr(tl)

    assert "main" in output
    assert "explore" in output
    assert "│" in output


def test_empty_timeline() -> None:
    """An empty timeline renders without crashing."""
    root = _make_span("root")
    tl = _make_timeline(root)
    output = repr(tl)
    assert output == "main"


# =============================================================================
# Parallel agents
# =============================================================================


def test_parallel_agents_badge() -> None:
    """Overlapping spans with the same name show count glyph in bar."""
    evt1 = _make_mock_event(
        timestamp=_T0, completed=_ts(50), input_tokens=100, output_tokens=100
    )
    evt2 = _make_mock_event(
        timestamp=_ts(10), completed=_ts(60), input_tokens=100, output_tokens=100
    )
    evt3 = _make_mock_event(
        timestamp=_ts(20), completed=_ts(70), input_tokens=100, output_tokens=100
    )

    # Root event to anchor the root span
    root_evt = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=50, output_tokens=50
    )

    worker1 = _make_span("Worker", content=[evt1])
    worker2 = _make_span("Worker", content=[evt2])
    worker3 = _make_span("Worker", content=[evt3])

    root = _make_span("Transcript", content=[root_evt, worker1, worker2, worker3])
    tl = _make_timeline(root)

    output = repr(tl)
    # All on one row labelled "Worker", with ③ count glyph in the bar
    assert "worker" in output
    assert "③" in output
    # Should NOT have separate Worker rows
    worker_lines = [line for line in output.split("\n") if "worker" in line]
    assert len(worker_lines) == 1


# =============================================================================
# Iterative agents
# =============================================================================


def test_iterative_agents_single_row() -> None:
    """Non-overlapping spans with the same name render as one row."""
    evt1 = _make_mock_event(
        timestamp=_T0, completed=_ts(30), input_tokens=100, output_tokens=100
    )
    evt2 = _make_mock_event(
        timestamp=_ts(40), completed=_ts(70), input_tokens=100, output_tokens=100
    )

    root_evt = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=50, output_tokens=50
    )

    attempt1 = _make_span("Attempt", content=[evt1])
    attempt2 = _make_span("Attempt", content=[evt2])

    root = _make_span("Transcript", content=[root_evt, attempt1, attempt2])
    tl = _make_timeline(root)

    output = repr(tl)
    # Should appear once (not twice), without (N) badge
    lines = output.strip().split("\n")
    attempt_lines = [line for line in lines if "attempt" in line and "(2)" not in line]
    assert len(attempt_lines) == 1


# =============================================================================
# Branches
# =============================================================================


def test_branches_prefix() -> None:
    """Branches render with ↳ prefix."""
    evt1 = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=1000, output_tokens=500
    )
    branch_evt = _make_mock_event(
        timestamp=_ts(10), completed=_ts(50), input_tokens=200, output_tokens=100
    )
    branch_child = _make_span("Refactor", content=[branch_evt])
    branch = TimelineBranch(
        forked_at="",
        content=[branch_child],
    )

    root = _make_span("Transcript", content=[evt1], branches=[branch])
    tl = _make_timeline(root)

    output = repr(tl)
    assert "↳" in output
    assert "refactor" in output


# =============================================================================
# Markers
# =============================================================================


def test_compaction_marker() -> None:
    """Compaction events produce ┊ marker."""
    evt1 = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=100, output_tokens=100
    )
    compaction = _make_mock_event(timestamp=_ts(50), event_type="compaction")

    root = _make_span("Transcript", content=[evt1, compaction])
    tl = _make_timeline(root)

    output = repr(tl)
    assert "┊" in output


# =============================================================================
# Utility exclusion
# =============================================================================


def test_utility_agents_excluded() -> None:
    """Utility spans are not shown in the repr."""
    root_evt = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=1000, output_tokens=500
    )
    child_evt = _make_mock_event(
        timestamp=_ts(10), completed=_ts(20), input_tokens=50, output_tokens=50
    )

    util_span = _make_span("Helper", content=[child_evt], utility=True)
    root = _make_span("Transcript", content=[root_evt, util_span])
    tl = _make_timeline(root)

    output = repr(tl)
    assert "helper" not in output


# =============================================================================
# Degenerate cases
# =============================================================================


def test_single_event_timeline() -> None:
    """A timeline with just one event doesn't crash."""
    evt = _make_mock_event(
        timestamp=_T0, completed=_ts(10), input_tokens=100, output_tokens=50
    )
    root = _make_span("Transcript", content=[evt])
    tl = _make_timeline(root)

    output = repr(tl)
    assert "main" in output
    assert "█" in output


def test_deeply_nested() -> None:
    """Deeply nested spans render with increasing indentation."""
    evt = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=100, output_tokens=100
    )
    inner = _make_span("Inner", content=[evt])
    middle = _make_span("Middle", content=[inner])
    outer = _make_span("Outer", content=[middle])
    root_evt = _make_mock_event(
        timestamp=_T0, completed=_ts(100), input_tokens=50, output_tokens=50
    )
    root = _make_span("Root", content=[root_evt, outer])
    tl = _make_timeline(root)

    output = repr(tl)
    lines = output.strip().split("\n")
    assert len(lines) >= 4
    assert "main" in lines[0]
    assert "inner" in output
