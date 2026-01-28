"""Trace tree reconstruction from LangSmith runs.

LangSmith stores runs in a flat structure with parent_run_id references.
This module reconstructs the hierarchical tree structure for proper
event ordering and span nesting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RunNode:
    """A node in the run tree."""

    run: Any
    children: list["RunNode"] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(getattr(self.run, "id", ""))

    @property
    def parent_id(self) -> str | None:
        return str(getattr(self.run, "parent_run_id", None) or "")

    @property
    def start_time(self) -> datetime | None:
        return getattr(self.run, "start_time", None)

    @property
    def run_type(self) -> str:
        return str(getattr(self.run, "run_type", "")).lower()


def build_run_tree(runs: list[Any]) -> list[RunNode]:
    """Build a tree structure from flat list of runs.

    Args:
        runs: Flat list of LangSmith runs with parent_run_id references

    Returns:
        List of root RunNode objects (runs without parents)
    """
    # Create nodes for all runs
    nodes: dict[str, RunNode] = {}
    for run in runs:
        run_id = str(getattr(run, "id", ""))
        if run_id:
            nodes[run_id] = RunNode(run=run)

    # Build parent-child relationships
    roots: list[RunNode] = []
    for node in nodes.values():
        parent_id = node.parent_id
        if parent_id and parent_id in nodes:
            nodes[parent_id].children.append(node)
        else:
            roots.append(node)

    # Sort children by start_time at each level
    def sort_children(node: RunNode) -> None:
        node.children.sort(key=lambda n: n.start_time or datetime.min)
        for child in node.children:
            sort_children(child)

    for root in roots:
        sort_children(root)

    # Sort roots by start_time
    roots.sort(key=lambda n: n.start_time or datetime.min)

    return roots


def flatten_tree_chronological(roots: list[RunNode]) -> list[Any]:
    """Flatten tree to chronologically ordered list of runs.

    Performs a depth-first traversal, emitting runs in the order
    they would have executed.

    Args:
        roots: List of root RunNode objects

    Returns:
        Chronologically ordered list of runs
    """
    result: list[Any] = []

    def visit(node: RunNode) -> None:
        result.append(node.run)
        for child in node.children:
            visit(child)

    for root in roots:
        visit(root)

    return result


def get_llm_runs(runs: list[Any]) -> list[Any]:
    """Filter runs to only LLM-type runs.

    Args:
        runs: List of LangSmith runs

    Returns:
        List of runs with run_type == "llm"
    """
    return [run for run in runs if str(getattr(run, "run_type", "")).lower() == "llm"]


def get_tool_runs(runs: list[Any]) -> list[Any]:
    """Filter runs to only tool-type runs.

    Args:
        runs: List of LangSmith runs

    Returns:
        List of runs with run_type == "tool"
    """
    return [run for run in runs if str(getattr(run, "run_type", "")).lower() == "tool"]


def get_chain_runs(runs: list[Any]) -> list[Any]:
    """Filter runs to chain/agent-type runs.

    Args:
        runs: List of LangSmith runs

    Returns:
        List of runs with run_type in ("chain", "agent")
    """
    return [
        run
        for run in runs
        if str(getattr(run, "run_type", "")).lower() in ("chain", "agent")
    ]
