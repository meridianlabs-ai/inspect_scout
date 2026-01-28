"""Tests for LangSmith trace tree reconstruction.

Tests build_run_tree(), flatten_tree_chronological(), and run filtering
functions that reconstruct hierarchical tree structure from flat run lists.
"""

from datetime import datetime, timedelta

from inspect_scout.sources._langsmith.tree import (
    RunNode,
    build_run_tree,
    flatten_tree_chronological,
    get_chain_runs,
    get_llm_runs,
    get_tool_runs,
)

from tests.sources.langsmith_source.mocks import MockRun


class TestBuildRunTree:
    """Tests for build_run_tree function."""

    def test_single_root_run(self) -> None:
        """Build tree with a single root run."""
        runs = [MockRun(id="run-1", parent_run_id=None)]
        tree = build_run_tree(runs)

        assert len(tree) == 1
        assert tree[0].id == "run-1"
        assert len(tree[0].children) == 0

    def test_parent_child_relationship(self) -> None:
        """Build tree with parent-child relationship."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        runs = [
            MockRun(id="parent", parent_run_id=None, start_time=base_time),
            MockRun(
                id="child",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=1),
            ),
        ]
        tree = build_run_tree(runs)

        assert len(tree) == 1
        assert tree[0].id == "parent"
        assert len(tree[0].children) == 1
        assert tree[0].children[0].id == "child"

    def test_multiple_children(self) -> None:
        """Build tree with multiple children under one parent."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        runs = [
            MockRun(id="parent", parent_run_id=None, start_time=base_time),
            MockRun(
                id="child-1",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=1),
            ),
            MockRun(
                id="child-2",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=2),
            ),
            MockRun(
                id="child-3",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=3),
            ),
        ]
        tree = build_run_tree(runs)

        assert len(tree) == 1
        assert tree[0].id == "parent"
        assert len(tree[0].children) == 3
        # Children should be sorted by start_time
        assert tree[0].children[0].id == "child-1"
        assert tree[0].children[1].id == "child-2"
        assert tree[0].children[2].id == "child-3"

    def test_nested_hierarchy(self) -> None:
        """Build tree with nested hierarchy (grandchildren)."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        runs = [
            MockRun(id="root", parent_run_id=None, start_time=base_time),
            MockRun(
                id="child",
                parent_run_id="root",
                start_time=base_time + timedelta(seconds=1),
            ),
            MockRun(
                id="grandchild",
                parent_run_id="child",
                start_time=base_time + timedelta(seconds=2),
            ),
        ]
        tree = build_run_tree(runs)

        assert len(tree) == 1
        root = tree[0]
        assert root.id == "root"
        assert len(root.children) == 1

        child = root.children[0]
        assert child.id == "child"
        assert len(child.children) == 1

        grandchild = child.children[0]
        assert grandchild.id == "grandchild"
        assert len(grandchild.children) == 0

    def test_multiple_roots(self) -> None:
        """Build tree with multiple root runs."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        runs = [
            MockRun(id="root-1", parent_run_id=None, start_time=base_time),
            MockRun(
                id="root-2",
                parent_run_id=None,
                start_time=base_time + timedelta(seconds=1),
            ),
        ]
        tree = build_run_tree(runs)

        assert len(tree) == 2
        assert tree[0].id == "root-1"
        assert tree[1].id == "root-2"

    def test_orphan_becomes_root(self) -> None:
        """Run with missing parent becomes a root."""
        runs = [
            MockRun(id="orphan", parent_run_id="nonexistent"),
        ]
        tree = build_run_tree(runs)

        assert len(tree) == 1
        assert tree[0].id == "orphan"

    def test_empty_run_list(self) -> None:
        """Handle empty run list."""
        tree = build_run_tree([])
        assert len(tree) == 0

    def test_children_sorted_by_start_time(self) -> None:
        """Children should be sorted by start_time."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        # Create children out of order
        runs = [
            MockRun(id="parent", parent_run_id=None, start_time=base_time),
            MockRun(
                id="child-late",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=10),
            ),
            MockRun(
                id="child-early",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=1),
            ),
            MockRun(
                id="child-middle",
                parent_run_id="parent",
                start_time=base_time + timedelta(seconds=5),
            ),
        ]
        tree = build_run_tree(runs)

        children = tree[0].children
        assert children[0].id == "child-early"
        assert children[1].id == "child-middle"
        assert children[2].id == "child-late"


class TestFlattenTreeChronological:
    """Tests for flatten_tree_chronological function."""

    def test_flatten_single_node(self) -> None:
        """Flatten single node tree."""
        run = MockRun(id="run-1")
        tree = [RunNode(run=run)]
        result = flatten_tree_chronological(tree)

        assert len(result) == 1
        assert result[0].id == "run-1"

    def test_flatten_parent_child(self) -> None:
        """Flatten parent-child tree (DFS order)."""
        parent_run = MockRun(id="parent")
        child_run = MockRun(id="child")

        parent_node = RunNode(run=parent_run)
        child_node = RunNode(run=child_run)
        parent_node.children = [child_node]

        tree = [parent_node]
        result = flatten_tree_chronological(tree)

        assert len(result) == 2
        assert result[0].id == "parent"
        assert result[1].id == "child"

    def test_flatten_preserves_dfs_order(self) -> None:
        """Flatten preserves depth-first traversal order."""
        # Structure: root -> [child1 -> grandchild, child2]
        root_run = MockRun(id="root")
        child1_run = MockRun(id="child1")
        child2_run = MockRun(id="child2")
        grandchild_run = MockRun(id="grandchild")

        root_node = RunNode(run=root_run)
        child1_node = RunNode(run=child1_run)
        child2_node = RunNode(run=child2_run)
        grandchild_node = RunNode(run=grandchild_run)

        child1_node.children = [grandchild_node]
        root_node.children = [child1_node, child2_node]

        tree = [root_node]
        result = flatten_tree_chronological(tree)

        assert len(result) == 4
        # DFS order: root, child1, grandchild, child2
        assert result[0].id == "root"
        assert result[1].id == "child1"
        assert result[2].id == "grandchild"
        assert result[3].id == "child2"

    def test_flatten_multiple_roots(self) -> None:
        """Flatten multiple root nodes."""
        root1_run = MockRun(id="root1")
        root2_run = MockRun(id="root2")

        tree = [RunNode(run=root1_run), RunNode(run=root2_run)]
        result = flatten_tree_chronological(tree)

        assert len(result) == 2
        assert result[0].id == "root1"
        assert result[1].id == "root2"

    def test_flatten_empty_tree(self) -> None:
        """Flatten empty tree."""
        result = flatten_tree_chronological([])
        assert len(result) == 0


class TestGetLlmRuns:
    """Tests for get_llm_runs filter function."""

    def test_filter_llm_runs(self) -> None:
        """Filter only LLM type runs."""
        runs = [
            MockRun(id="llm-1", run_type="llm"),
            MockRun(id="tool-1", run_type="tool"),
            MockRun(id="llm-2", run_type="llm"),
            MockRun(id="chain-1", run_type="chain"),
        ]

        llm_runs = get_llm_runs(runs)

        assert len(llm_runs) == 2
        assert llm_runs[0].id == "llm-1"
        assert llm_runs[1].id == "llm-2"

    def test_filter_llm_runs_case_insensitive(self) -> None:
        """LLM filter should be case insensitive."""
        runs = [
            MockRun(id="llm-1", run_type="LLM"),
            MockRun(id="llm-2", run_type="Llm"),
            MockRun(id="llm-3", run_type="llm"),
        ]

        llm_runs = get_llm_runs(runs)

        assert len(llm_runs) == 3

    def test_filter_llm_runs_empty_list(self) -> None:
        """Return empty list when no LLM runs."""
        runs = [
            MockRun(id="tool-1", run_type="tool"),
            MockRun(id="chain-1", run_type="chain"),
        ]

        llm_runs = get_llm_runs(runs)

        assert len(llm_runs) == 0


class TestGetToolRuns:
    """Tests for get_tool_runs filter function."""

    def test_filter_tool_runs(self) -> None:
        """Filter only tool type runs."""
        runs = [
            MockRun(id="llm-1", run_type="llm"),
            MockRun(id="tool-1", run_type="tool"),
            MockRun(id="tool-2", run_type="tool"),
            MockRun(id="chain-1", run_type="chain"),
        ]

        tool_runs = get_tool_runs(runs)

        assert len(tool_runs) == 2
        assert tool_runs[0].id == "tool-1"
        assert tool_runs[1].id == "tool-2"

    def test_filter_tool_runs_empty_list(self) -> None:
        """Return empty list when no tool runs."""
        runs = [
            MockRun(id="llm-1", run_type="llm"),
            MockRun(id="chain-1", run_type="chain"),
        ]

        tool_runs = get_tool_runs(runs)

        assert len(tool_runs) == 0


class TestGetChainRuns:
    """Tests for get_chain_runs filter function."""

    def test_filter_chain_runs(self) -> None:
        """Filter chain and agent type runs."""
        runs = [
            MockRun(id="llm-1", run_type="llm"),
            MockRun(id="chain-1", run_type="chain"),
            MockRun(id="agent-1", run_type="agent"),
            MockRun(id="tool-1", run_type="tool"),
        ]

        chain_runs = get_chain_runs(runs)

        assert len(chain_runs) == 2
        assert chain_runs[0].id == "chain-1"
        assert chain_runs[1].id == "agent-1"

    def test_filter_chain_runs_case_insensitive(self) -> None:
        """Chain filter should be case insensitive."""
        runs = [
            MockRun(id="chain-1", run_type="CHAIN"),
            MockRun(id="agent-1", run_type="Agent"),
        ]

        chain_runs = get_chain_runs(runs)

        assert len(chain_runs) == 2

    def test_filter_chain_runs_empty_list(self) -> None:
        """Return empty list when no chain/agent runs."""
        runs = [
            MockRun(id="llm-1", run_type="llm"),
            MockRun(id="tool-1", run_type="tool"),
        ]

        chain_runs = get_chain_runs(runs)

        assert len(chain_runs) == 0


class TestRunNodeProperties:
    """Tests for RunNode dataclass properties."""

    def test_run_node_id(self) -> None:
        """RunNode.id returns run ID."""
        run = MockRun(id="test-123")
        node = RunNode(run=run)
        assert node.id == "test-123"

    def test_run_node_parent_id(self) -> None:
        """RunNode.parent_id returns parent run ID."""
        run = MockRun(parent_run_id="parent-123")
        node = RunNode(run=run)
        assert node.parent_id == "parent-123"

    def test_run_node_parent_id_none(self) -> None:
        """RunNode.parent_id returns empty string for None."""
        run = MockRun(parent_run_id=None)
        node = RunNode(run=run)
        assert node.parent_id == ""

    def test_run_node_start_time(self) -> None:
        """RunNode.start_time returns run start time."""
        time = datetime(2024, 1, 1, 12, 0, 0)
        run = MockRun(start_time=time)
        node = RunNode(run=run)
        assert node.start_time == time

    def test_run_node_run_type(self) -> None:
        """RunNode.run_type returns run type lowercased."""
        run = MockRun(run_type="LLM")
        node = RunNode(run=run)
        assert node.run_type == "llm"
