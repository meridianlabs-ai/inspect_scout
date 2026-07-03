"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from inspect_ai.event import timeline_build
from inspect_scout._transcript.timeline import TimelineSpan

from tests.transcript.fixtures_agentic import agentic_events


def _collect_utility(span: TimelineSpan) -> list[TimelineSpan]:
    """Recursively collect every utility-classified span in the tree."""
    utility: list[TimelineSpan] = []
    if span.utility:
        utility.append(span)
    for item in span.content:
        if isinstance(item, TimelineSpan):
            utility.extend(_collect_utility(item))
    return utility


def test_agentic_fixture_classification() -> None:
    """The fixture must exercise the classification paths the spec names."""
    from inspect_scout._transcript.timeline import _walk_spans

    tree = timeline_build(agentic_events())
    spans = list(_walk_spans(tree.root, depth=None))
    names = [s.name for s in spans]
    # main agent, sub2 (non-utility nested agent), and the tool-spawned agent
    # are scannable; "sub" (utility) and the wrapped helper are NOT.
    assert "main" in names
    assert "sub2" in names
    assert "browser" in names
    assert "sub" not in names
    utility_spans = _collect_utility(tree.root)
    assert len(utility_spans) >= 2  # "sub" + wrapped foreign-prompt helper
