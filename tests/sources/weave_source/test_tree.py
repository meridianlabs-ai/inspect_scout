"""Tests for W&B Weave call tree building."""

from datetime import datetime, timedelta

from tests.sources.weave_source.mocks import (
    create_openai_llm_call,
    create_span_call,
    create_tool_call,
    create_trace_with_tool_calls,
)


class TestBuildCallTree:
    """Tests for build_call_tree function."""

    def test_single_root_call(self) -> None:
        """Build tree from single root call."""
        from inspect_scout.sources._weave.tree import build_call_tree

        call = create_span_call(call_id="root-1")
        tree = build_call_tree([call])

        assert len(tree) == 1
        assert tree[0].id == "root-1"
        assert len(tree[0].children) == 0

    def test_parent_child_relationship(self) -> None:
        """Build tree with parent-child relationship."""
        from inspect_scout.sources._weave.tree import build_call_tree

        root = create_span_call(call_id="root")
        child = create_openai_llm_call(call_id="child", parent_id="root")
        child.trace_id = "root"

        tree = build_call_tree([root, child])

        assert len(tree) == 1
        assert tree[0].id == "root"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].id == "child"

    def test_multiple_children(self) -> None:
        """Build tree with multiple children."""
        from inspect_scout.sources._weave.tree import build_call_tree

        root = create_span_call(call_id="root")
        child1 = create_openai_llm_call(call_id="child1", parent_id="root")
        child1.trace_id = "root"
        child2 = create_tool_call(call_id="child2", parent_id="root")
        child2.trace_id = "root"

        tree = build_call_tree([root, child1, child2])

        assert len(tree) == 1
        assert len(tree[0].children) == 2

    def test_deep_nesting(self) -> None:
        """Build tree with deep nesting."""
        from inspect_scout.sources._weave.tree import build_call_tree

        root = create_span_call(call_id="root")
        level1 = create_span_call(call_id="level1", parent_id="root")
        level1.trace_id = "root"
        level2 = create_openai_llm_call(call_id="level2", parent_id="level1")
        level2.trace_id = "root"

        tree = build_call_tree([root, level1, level2])

        assert len(tree) == 1
        assert len(tree[0].children) == 1
        assert len(tree[0].children[0].children) == 1
        assert tree[0].children[0].children[0].id == "level2"

    def test_children_sorted_by_time(self) -> None:
        """Verify children are sorted by start time."""
        from inspect_scout.sources._weave.tree import build_call_tree

        base_time = datetime.now()
        root = create_span_call(call_id="root")
        root.started_at = base_time

        child1 = create_openai_llm_call(call_id="child1", parent_id="root")
        child1.trace_id = "root"
        child1.started_at = base_time + timedelta(seconds=2)

        child2 = create_tool_call(call_id="child2", parent_id="root")
        child2.trace_id = "root"
        child2.started_at = base_time + timedelta(seconds=1)

        tree = build_call_tree([root, child1, child2])

        # child2 should come first (earlier start time)
        assert tree[0].children[0].id == "child2"
        assert tree[0].children[1].id == "child1"

    def test_multiple_roots(self) -> None:
        """Build tree with multiple root calls."""
        from inspect_scout.sources._weave.tree import build_call_tree

        root1 = create_span_call(call_id="root1")
        root2 = create_span_call(call_id="root2")

        tree = build_call_tree([root1, root2])

        assert len(tree) == 2


class TestFlattenTreeChronological:
    """Tests for flatten_tree_chronological function."""

    def test_single_call(self) -> None:
        """Flatten tree with single call."""
        from inspect_scout.sources._weave.tree import (
            build_call_tree,
            flatten_tree_chronological,
        )

        call = create_span_call()
        tree = build_call_tree([call])
        flat = flatten_tree_chronological(tree)

        assert len(flat) == 1

    def test_preserves_all_calls(self) -> None:
        """Verify flattening preserves all calls."""
        from inspect_scout.sources._weave.tree import (
            build_call_tree,
            flatten_tree_chronological,
        )

        calls = create_trace_with_tool_calls()
        tree = build_call_tree(calls)
        flat = flatten_tree_chronological(tree)

        assert len(flat) == len(calls)

    def test_depth_first_order(self) -> None:
        """Verify depth-first traversal order."""
        from inspect_scout.sources._weave.tree import (
            build_call_tree,
            flatten_tree_chronological,
        )

        root = create_span_call(call_id="root")
        child = create_openai_llm_call(call_id="child", parent_id="root")
        child.trace_id = "root"
        grandchild = create_tool_call(call_id="grandchild", parent_id="child")
        grandchild.trace_id = "root"

        tree = build_call_tree([root, child, grandchild])
        flat = flatten_tree_chronological(tree)

        # Depth-first: root -> child -> grandchild
        assert flat[0].id == "root"
        assert flat[1].id == "child"
        assert flat[2].id == "grandchild"

    def test_empty_tree(self) -> None:
        """Handle empty tree."""
        from inspect_scout.sources._weave.tree import flatten_tree_chronological

        flat = flatten_tree_chronological([])
        assert flat == []


class TestGetLlmCalls:
    """Tests for get_llm_calls function."""

    def test_filters_llm_calls(self) -> None:
        """Filter to only LLM calls."""
        from inspect_scout.sources._weave.tree import get_llm_calls

        calls = create_trace_with_tool_calls()
        llm_calls = get_llm_calls(calls)

        # Should have at least one LLM call
        assert len(llm_calls) >= 1

        # All should be LLM calls
        for call in llm_calls:
            op_name = str(getattr(call, "op_name", "")).lower()
            assert any(
                p in op_name
                for p in ["openai", "anthropic", "chat", "completion", "messages"]
            )

    def test_excludes_non_llm_calls(self) -> None:
        """Verify non-LLM calls are excluded."""
        from inspect_scout.sources._weave.tree import get_llm_calls

        calls = [
            create_span_call(name="agent_run"),
            create_tool_call(tool_name="get_weather"),
            create_openai_llm_call(),
        ]

        llm_calls = get_llm_calls(calls)

        assert len(llm_calls) == 1

    def test_empty_list(self) -> None:
        """Handle empty list."""
        from inspect_scout.sources._weave.tree import get_llm_calls

        llm_calls = get_llm_calls([])
        assert llm_calls == []


class TestGetToolCalls:
    """Tests for get_tool_calls function."""

    def test_filters_tool_calls(self) -> None:
        """Filter to only tool calls."""
        from inspect_scout.sources._weave.tree import get_tool_calls

        calls = create_trace_with_tool_calls()
        tool_calls = get_tool_calls(calls)

        # Should have tool call
        assert len(tool_calls) >= 1

        # All should be tool calls
        for call in tool_calls:
            op_name = str(getattr(call, "op_name", "")).lower()
            assert "tool" in op_name or "function" in op_name

    def test_excludes_non_tool_calls(self) -> None:
        """Verify non-tool calls are excluded."""
        from inspect_scout.sources._weave.tree import get_tool_calls

        calls = [
            create_span_call(name="agent_run"),
            create_openai_llm_call(),
            create_tool_call(tool_name="get_weather"),
        ]

        tool_calls = get_tool_calls(calls)

        assert len(tool_calls) == 1


class TestGetSpanCalls:
    """Tests for get_span_calls function."""

    def test_filters_span_calls(self) -> None:
        """Filter to only span calls (non-LLM, non-tool)."""
        from inspect_scout.sources._weave.tree import get_span_calls

        calls = create_trace_with_tool_calls()
        span_calls = get_span_calls(calls)

        # Should have at least the root span
        assert len(span_calls) >= 1

    def test_excludes_llm_and_tool_calls(self) -> None:
        """Verify LLM and tool calls are excluded."""
        from inspect_scout.sources._weave.tree import get_span_calls

        calls = [
            create_span_call(name="agent_run"),
            create_openai_llm_call(),
            create_tool_call(tool_name="get_weather"),
        ]

        span_calls = get_span_calls(calls)

        assert len(span_calls) == 1
        assert span_calls[0].op_name == "agent_run"
