"""Trace tree reconstruction from Phoenix spans.

Phoenix stores spans in a flat structure with context.span_id/parent_id references.
This module reconstructs the hierarchical tree structure for proper
event ordering and span nesting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SpanNode:
    """A node in the span tree."""

    span: dict[str, Any]
    children: list["SpanNode"] = field(default_factory=list)

    @property
    def span_id(self) -> str:
        context = self.span.get("context") or {}
        return str(context.get("span_id", ""))

    @property
    def parent_id(self) -> str | None:
        parent = self.span.get("parent_id")
        return str(parent) if parent else None

    @property
    def start_time(self) -> datetime | None:
        ts = self.span.get("start_time")
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @property
    def trace_id(self) -> str:
        context = self.span.get("context") or {}
        return str(context.get("trace_id", ""))


def build_span_tree(spans: list[dict[str, Any]]) -> list[SpanNode]:
    """Build a tree structure from flat list of spans.

    Args:
        spans: Flat list of Phoenix spans with parent_id references

    Returns:
        List of root SpanNode objects (spans without parents)
    """
    # Create nodes for all spans
    nodes: dict[str, SpanNode] = {}
    for span in spans:
        context = span.get("context") or {}
        span_id = str(context.get("span_id", ""))
        if span_id:
            nodes[span_id] = SpanNode(span=span)

    # Build parent-child relationships
    roots: list[SpanNode] = []
    for node in nodes.values():
        parent_id = node.parent_id
        if parent_id and parent_id in nodes:
            nodes[parent_id].children.append(node)
        else:
            roots.append(node)

    # Sort children by start_time at each level
    def sort_children(node: SpanNode) -> None:
        node.children.sort(key=lambda n: n.start_time or datetime.min)
        for child in node.children:
            sort_children(child)

    for root in roots:
        sort_children(root)

    # Sort roots by start_time
    roots.sort(key=lambda n: n.start_time or datetime.min)

    return roots


def flatten_tree_chronological(roots: list[SpanNode]) -> list[dict[str, Any]]:
    """Flatten tree to chronologically ordered list of spans.

    Performs a depth-first traversal, emitting spans in the order
    they would have executed.

    Args:
        roots: List of root SpanNode objects

    Returns:
        Chronologically ordered list of spans
    """
    result: list[dict[str, Any]] = []

    def visit(node: SpanNode) -> None:
        result.append(node.span)
        for child in node.children:
            visit(child)

    for root in roots:
        visit(root)

    return result


def get_llm_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter spans to only LLM operation spans.

    Args:
        spans: List of Phoenix spans

    Returns:
        List of LLM spans
    """
    from .detection import is_llm_span

    return [span for span in spans if is_llm_span(span)]


def get_tool_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter spans to only tool execution spans.

    Args:
        spans: List of Phoenix spans

    Returns:
        List of tool spans
    """
    from .detection import is_tool_span

    return [span for span in spans if is_tool_span(span)]


def get_chain_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter spans to chain/agent spans.

    Args:
        spans: List of Phoenix spans

    Returns:
        List of chain/agent spans
    """
    from .detection import is_chain_span

    return [span for span in spans if is_chain_span(span)]
