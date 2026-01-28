"""Tests for Logfire trace tree reconstruction."""

from datetime import datetime, timedelta

from inspect_scout.sources._logfire.tree import (
    build_span_tree,
    flatten_tree_chronological,
    get_agent_spans,
    get_llm_spans,
    get_tool_spans,
)

from .mocks import (
    create_agent_span,
    create_multiturn_openai_spans,
    create_openai_llm_span,
    create_pydantic_ai_agent_trace,
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
        now = datetime.now()
        parent = create_agent_span(
            span_id="parent", trace_id="trace-1", parent_span_id=None
        )
        parent["start_timestamp"] = now

        child = create_openai_llm_span(
            span_id="child", trace_id="trace-1", parent_span_id="parent"
        )
        child["start_timestamp"] = now + timedelta(seconds=1)

        roots = build_span_tree([parent, child])

        assert len(roots) == 1
        assert roots[0].span_id == "parent"
        assert len(roots[0].children) == 1
        assert roots[0].children[0].span_id == "child"

    def test_multiple_children_sorted_by_time(self) -> None:
        """Children should be sorted by start_timestamp."""
        now = datetime.now()

        parent = create_agent_span(span_id="parent", trace_id="trace-1")
        parent["start_timestamp"] = now

        child1 = create_openai_llm_span(
            span_id="child1", trace_id="trace-1", parent_span_id="parent"
        )
        child1["start_timestamp"] = now + timedelta(seconds=2)

        child2 = create_tool_span(
            span_id="child2", trace_id="trace-1", parent_span_id="parent"
        )
        child2["start_timestamp"] = now + timedelta(seconds=1)

        roots = build_span_tree([parent, child1, child2])

        assert len(roots[0].children) == 2
        # child2 should come first (earlier timestamp)
        assert roots[0].children[0].span_id == "child2"
        assert roots[0].children[1].span_id == "child1"

    def test_multiple_roots_sorted_by_time(self) -> None:
        """Multiple roots should be sorted by start_timestamp."""
        now = datetime.now()

        span1 = create_openai_llm_span(span_id="span1", trace_id="trace-1")
        span1["start_timestamp"] = now + timedelta(seconds=1)

        span2 = create_openai_llm_span(span_id="span2", trace_id="trace-1")
        span2["start_timestamp"] = now

        roots = build_span_tree([span1, span2])

        assert len(roots) == 2
        # span2 should come first (earlier timestamp)
        assert roots[0].span_id == "span2"
        assert roots[1].span_id == "span1"

    def test_orphan_spans_become_roots(self) -> None:
        """Spans with missing parents become roots."""
        span = create_openai_llm_span(
            span_id="orphan", trace_id="trace-1", parent_span_id="missing-parent"
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
        assert flattened[0]["span_id"] == "span-1"

    def test_flatten_preserves_depth_first_order(self) -> None:
        """Flatten should use depth-first traversal."""
        now = datetime.now()

        parent = create_agent_span(span_id="parent", trace_id="trace-1")
        parent["start_timestamp"] = now

        child = create_openai_llm_span(
            span_id="child", trace_id="trace-1", parent_span_id="parent"
        )
        child["start_timestamp"] = now + timedelta(seconds=1)

        grandchild = create_tool_span(
            span_id="grandchild", trace_id="trace-1", parent_span_id="child"
        )
        grandchild["start_timestamp"] = now + timedelta(seconds=2)

        roots = build_span_tree([parent, child, grandchild])
        flattened = flatten_tree_chronological(roots)

        assert len(flattened) == 3
        assert flattened[0]["span_id"] == "parent"
        assert flattened[1]["span_id"] == "child"
        assert flattened[2]["span_id"] == "grandchild"


class TestMultiturnSpans:
    """Tests for multi-turn conversation span handling."""

    def test_multiturn_spans_ordered(self) -> None:
        """Multi-turn spans maintain chronological order."""
        spans = create_multiturn_openai_spans()
        roots = build_span_tree(spans)
        flattened = flatten_tree_chronological(roots)

        assert len(flattened) == 3
        # Should be in order: turn-1, turn-2, turn-3
        assert flattened[0]["span_id"] == "span-turn-1"
        assert flattened[1]["span_id"] == "span-turn-2"
        assert flattened[2]["span_id"] == "span-turn-3"

    def test_pydantic_ai_agent_trace_structure(self) -> None:
        """Pydantic AI agent trace has correct parent-child structure."""
        spans = create_pydantic_ai_agent_trace(with_tools=True)
        roots = build_span_tree(spans)

        # Should have one root (agent span)
        assert len(roots) == 1
        assert roots[0].span_id == "span-agent-root"

        # Agent should have LLM spans as children
        assert len(roots[0].children) >= 1


class TestSpanFilters:
    """Tests for span filtering functions."""

    def test_get_llm_spans(self) -> None:
        """Filter to only LLM spans."""
        llm_span = create_openai_llm_span(span_id="llm", trace_id="trace-1")
        tool_span = create_tool_span(span_id="tool", trace_id="trace-1")
        agent_span = create_agent_span(span_id="agent", trace_id="trace-1")

        spans = [llm_span, tool_span, agent_span]
        llm_spans = get_llm_spans(spans)

        assert len(llm_spans) == 1
        assert llm_spans[0]["span_id"] == "llm"

    def test_get_llm_spans_multiturn(self) -> None:
        """Filter multi-turn spans to LLM spans."""
        spans = create_multiturn_openai_spans()
        llm_spans = get_llm_spans(spans)

        assert len(llm_spans) == 3  # All 3 turns are LLM spans

    def test_pydantic_ai_agent_span_filtering(self) -> None:
        """Filter Pydantic AI trace spans by type."""
        spans = create_pydantic_ai_agent_trace(with_tools=True)

        llm_spans = get_llm_spans(spans)
        tool_spans = get_tool_spans(spans)
        agent_spans = get_agent_spans(spans)

        assert len(llm_spans) >= 1  # At least one LLM call
        assert len(tool_spans) == 1  # One tool execution
        assert len(agent_spans) == 1  # One agent span

    def test_get_tool_spans(self) -> None:
        """Filter to only tool spans."""
        llm_span = create_openai_llm_span(span_id="llm", trace_id="trace-1")
        tool_span = create_tool_span(span_id="tool", trace_id="trace-1")
        agent_span = create_agent_span(span_id="agent", trace_id="trace-1")

        spans = [llm_span, tool_span, agent_span]
        tool_spans = get_tool_spans(spans)

        assert len(tool_spans) == 1
        assert tool_spans[0]["span_id"] == "tool"

    def test_get_agent_spans(self) -> None:
        """Filter to only agent spans."""
        llm_span = create_openai_llm_span(span_id="llm", trace_id="trace-1")
        tool_span = create_tool_span(span_id="tool", trace_id="trace-1")
        agent_span = create_agent_span(span_id="agent", trace_id="trace-1")

        spans = [llm_span, tool_span, agent_span]
        agent_spans = get_agent_spans(spans)

        assert len(agent_spans) == 1
        assert agent_spans[0]["span_id"] == "agent"
