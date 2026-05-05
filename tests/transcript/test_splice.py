"""Unit tests for `splice()` and `splice_to_timeline()`."""

import pytest
from inspect_ai.event import (
    AnchorEvent,
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
)
from inspect_ai.model import ChatMessageAssistant, ModelOutput
from inspect_scout import splice, splice_to_timeline


def _model(completion: str) -> ModelEvent:
    return ModelEvent(
        model="mock",
        input=[],
        tools=[],
        tool_choice="auto",
        config={},  # type: ignore[arg-type]
        output=ModelOutput.from_message(ChatMessageAssistant(content=completion)),
    )


def _span(
    *,
    id: str,
    branched_from: str | None = None,
    content: list[Event],
    branches: list[TimelineSpan] | None = None,
) -> TimelineSpan:
    return TimelineSpan(
        id=id,
        name="trajectory",
        span_type="branch",
        branched_from=branched_from,
        content=[TimelineEvent(event=e) for e in content],
        branches=branches or [],
    )


def _completions(events: list[Event]) -> list[str]:
    return [e.output.completion for e in events if isinstance(e, ModelEvent)]


def _tl(root: TimelineSpan) -> Timeline:
    return Timeline(name="t", description="", root=root)


class TestAncestorChain:
    def test_root_only(self) -> None:
        root = _span(id="r", content=[_model("R1")])
        assert _completions(splice(_tl(root), root)) == ["R1"]

    def test_single_branch_cuts_at_anchor(self) -> None:
        b = _span(id="b", branched_from="A", content=[_model("B1")])
        root = _span(
            id="r",
            content=[_model("R1"), AnchorEvent(anchor_id="A"), _model("R2")],
            branches=[b],
        )
        assert _completions(splice(_tl(root), b)) == ["R1", "B1"]

    def test_nested_branch(self) -> None:
        c = _span(id="c", branched_from="B", content=[_model("C1")])
        b = _span(
            id="b",
            branched_from="A",
            content=[_model("B1"), AnchorEvent(anchor_id="B"), _model("B2")],
            branches=[c],
        )
        root = _span(
            id="r",
            content=[_model("R1"), AnchorEvent(anchor_id="A")],
            branches=[b],
        )
        assert _completions(splice(_tl(root), c)) == ["R1", "B1", "C1"]

    def test_restart_clears_ancestor_prefix(self) -> None:
        b = _span(id="b", branched_from="", content=[_model("B1")])
        root = _span(id="r", content=[_model("R1")], branches=[b])
        assert _completions(splice(_tl(root), b)) == ["B1"]

    def test_anchor_not_found_includes_full_ancestor(self) -> None:
        b = _span(id="b", branched_from="missing", content=[_model("B1")])
        root = _span(id="r", content=[_model("R1"), _model("R2")], branches=[b])
        assert _completions(splice(_tl(root), b)) == ["R1", "R2", "B1"]

    def test_unreachable_target_raises(self) -> None:
        root = _span(id="r", content=[])
        orphan = _span(id="o", content=[])
        with pytest.raises(ValueError, match="not reachable"):
            splice(_tl(root), orphan)


class TestSuffixStripping:
    def test_span_ids_stripped_per_segment(self) -> None:
        b = _span(
            id="B",
            branched_from="A",
            content=[
                SpanEndEvent(id="x#0:B"),
                SpanBeginEvent(id="x#1:B", name="x", parent_id="B"),
                SpanEndEvent(id="x#1:B"),
            ],
        )
        root = _span(
            id="R",
            content=[
                SpanBeginEvent(id="x#0:R", name="x", parent_id="R"),
                AnchorEvent(anchor_id="A", span_id="x#0:R"),
            ],
            branches=[b],
        )
        events = splice(_tl(root), b)
        ids = [e.id for e in events if isinstance(e, (SpanBeginEvent, SpanEndEvent))]
        assert ids == ["x#0", "x#0", "x#1", "x#1"]

    def test_parent_id_at_trajectory_root_normalized(self) -> None:
        root = _span(
            id="R",
            content=[SpanBeginEvent(id="x#0:R", name="x", parent_id="R")],
        )
        [e] = splice(_tl(root), root)
        assert isinstance(e, SpanBeginEvent)
        assert e.parent_id == ""


class TestSpliceToTimeline:
    def test_builds_timeline_from_spliced_events(self) -> None:
        b = _span(id="b", branched_from="A", content=[_model("B1")])
        root = _span(
            id="r",
            content=[_model("R1"), AnchorEvent(anchor_id="A")],
            branches=[b],
        )
        result = splice_to_timeline(_tl(root), b)
        events = [
            item.event
            for item in result.root.content
            if isinstance(item, TimelineEvent)
        ]
        assert _completions(events) == ["R1", "B1"]
