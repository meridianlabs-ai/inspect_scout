"""Tests for Phoenix trace tree reconstruction."""

from inspect_scout.sources._phoenix.tree import (
    build_span_tree,
    flatten_tree_chronological,
    get_chain_spans,
    get_llm_spans,
    get_tool_spans,
)

from .mocks import (
    create_chain_span,
    create_multiturn_openai_spans,
    create_openai_llm_span,
    create_tool_call_trace,
    create_tool_span,
)


class TestBuildSpanTree:
    """Tests for build_span_tree function."""

    def test_single_span(self) -> None:
        """Build tree with single root span."""
        span = create_openai_llm_span(span_id="span-1", trace_id="trace-1")
        roots = build_span_tree([span])

        assert len(roots) == 1
        assert roots[0].span_id == "span-1"
        assert roots[0].children == []

    def test_parent_child_relationship(self) -> None:
        """Build tree with parent-child relationship."""
        parent = create_chain_span(
            span_id="parent",
            trace_id="trace-1",
            start_time="2025-01-01T00:00:00Z",
        )
        child = create_openai_llm_span(
            span_id="child",
            trace_id="trace-1",
            parent_id="parent",
            start_time="2025-01-01T00:00:01Z",
        )

        roots = build_span_tree([parent, child])

        assert len(roots) == 1
        assert roots[0].span_id == "parent"
        assert len(roots[0].children) == 1
        assert roots[0].children[0].span_id == "child"

    def test_multiple_children_sorted_by_time(self) -> None:
        """Children should be sorted by start_time."""
        parent = create_chain_span(
            span_id="parent",
            trace_id="trace-1",
            start_time="2025-01-01T00:00:00Z",
        )
        child1 = create_openai_llm_span(
            span_id="child1",
            trace_id="trace-1",
            parent_id="parent",
            start_time="2025-01-01T00:00:02Z",
        )
        child2 = create_tool_span(
            span_id="child2",
            trace_id="trace-1",
            parent_id="parent",
            start_time="2025-01-01T00:00:01Z",
        )

        roots = build_span_tree([parent, child1, child2])

        assert len(roots[0].children) == 2
        # child2 should come first (earlier timestamp)
        assert roots[0].children[0].span_id == "child2"
        assert roots[0].children[1].span_id == "child1"

    def test_multiple_roots_sorted_by_time(self) -> None:
        """Multiple roots should be sorted by start_time."""
        span1 = create_openai_llm_span(
            span_id="span1",
            trace_id="trace-1",
            start_time="2025-01-01T00:00:01Z",
        )
        span2 = create_openai_llm_span(
            span_id="span2",
            trace_id="trace-1",
            start_time="2025-01-01T00:00:00Z",
        )

        roots = build_span_tree([span1, span2])

        assert len(roots) == 2
        assert roots[0].span_id == "span2"
        assert roots[1].span_id == "span1"

    def test_orphan_spans_become_roots(self) -> None:
        """Spans with missing parents become roots."""
        span = create_openai_llm_span(
            span_id="orphan",
            trace_id="trace-1",
            parent_id="missing-parent",
        )
        roots = build_span_tree([span])

        assert len(roots) == 1
        assert roots[0].span_id == "orphan"


class TestFlattenTreeChronological:
    """Tests for flatten_tree_chronological function."""

    def test_flatten_single_span(self) -> None:
        """Flatten tree with single span."""
        span = create_openai_llm_span(span_id="span-1", trace_id="trace-1")
        roots = build_span_tree([span])
        flattened = flatten_tree_chronological(roots)

        assert len(flattened) == 1
        context = flattened[0].get("context", {})
        assert context.get("span_id") == "span-1"

    def test_flatten_preserves_depth_first_order(self) -> None:
        """Flatten should use depth-first traversal."""
        parent = create_chain_span(
            span_id="parent",
            trace_id="trace-1",
            start_time="2025-01-01T00:00:00Z",
        )
        child = create_openai_llm_span(
            span_id="child",
            trace_id="trace-1",
            parent_id="parent",
            start_time="2025-01-01T00:00:01Z",
        )
        grandchild = create_tool_span(
            span_id="grandchild",
            trace_id="trace-1",
            parent_id="child",
            start_time="2025-01-01T00:00:02Z",
        )

        roots = build_span_tree([parent, child, grandchild])
        flattened = flatten_tree_chronological(roots)

        assert len(flattened) == 3
        assert flattened[0]["context"]["span_id"] == "parent"
        assert flattened[1]["context"]["span_id"] == "child"
        assert flattened[2]["context"]["span_id"] == "grandchild"


class TestMultiturnSpans:
    """Tests for multi-turn conversation span handling."""

    def test_multiturn_spans_ordered(self) -> None:
        """Multi-turn spans maintain chronological order."""
        spans = create_multiturn_openai_spans()
        roots = build_span_tree(spans)
        flattened = flatten_tree_chronological(roots)

        assert len(flattened) == 3
        assert flattened[0]["context"]["span_id"] == "span-turn-1"
        assert flattened[1]["context"]["span_id"] == "span-turn-2"
        assert flattened[2]["context"]["span_id"] == "span-turn-3"

    def test_tool_call_trace_structure(self) -> None:
        """Tool call trace has correct parent-child structure."""
        spans = create_tool_call_trace()
        roots = build_span_tree(spans)

        # Should have one root (chain span)
        assert len(roots) == 1
        assert roots[0].span_id == "span-chain-root"

        # Chain should have children
        assert len(roots[0].children) >= 2


class TestSpanFilters:
    """Tests for span filtering functions."""

    def test_get_llm_spans(self) -> None:
        """Filter to only LLM spans."""
        llm_span = create_openai_llm_span(span_id="llm", trace_id="trace-1")
        tool_span = create_tool_span(span_id="tool", trace_id="trace-1")
        chain_span = create_chain_span(span_id="chain", trace_id="trace-1")

        spans = [llm_span, tool_span, chain_span]
        llm_spans = get_llm_spans(spans)

        assert len(llm_spans) == 1
        assert llm_spans[0]["context"]["span_id"] == "llm"

    def test_get_llm_spans_multiturn(self) -> None:
        """Filter multi-turn spans to LLM spans."""
        spans = create_multiturn_openai_spans()
        llm_spans = get_llm_spans(spans)

        assert len(llm_spans) == 3  # All 3 turns are LLM spans

    def test_get_tool_spans(self) -> None:
        """Filter to only tool spans."""
        llm_span = create_openai_llm_span(span_id="llm", trace_id="trace-1")
        tool_span = create_tool_span(span_id="tool", trace_id="trace-1")
        chain_span = create_chain_span(span_id="chain", trace_id="trace-1")

        spans = [llm_span, tool_span, chain_span]
        tool_spans = get_tool_spans(spans)

        assert len(tool_spans) == 1
        assert tool_spans[0]["context"]["span_id"] == "tool"

    def test_get_chain_spans(self) -> None:
        """Filter to only chain spans."""
        llm_span = create_openai_llm_span(span_id="llm", trace_id="trace-1")
        tool_span = create_tool_span(span_id="tool", trace_id="trace-1")
        chain_span = create_chain_span(span_id="chain", trace_id="trace-1")

        spans = [llm_span, tool_span, chain_span]
        chain_spans = get_chain_spans(spans)

        assert len(chain_spans) == 1
        assert chain_spans[0]["context"]["span_id"] == "chain"

    def test_tool_call_trace_filtering(self) -> None:
        """Filter tool call trace spans by type."""
        spans = create_tool_call_trace()

        llm_spans = get_llm_spans(spans)
        tool_spans = get_tool_spans(spans)
        chain_spans = get_chain_spans(spans)

        assert len(llm_spans) == 2  # Two LLM calls
        assert len(tool_spans) == 1  # One tool execution
        assert len(chain_spans) == 1  # One chain span
