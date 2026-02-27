"""Trace tree reconstruction from W&B Weave calls.

Weave stores calls in a flat structure with parent_id references.
This module reconstructs the hierarchical tree structure for proper
event ordering and span nesting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CallNode:
    """A node in the call tree."""

    call: Any
    children: list["CallNode"] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(getattr(self.call, "id", ""))

    @property
    def parent_id(self) -> str | None:
        parent = getattr(self.call, "parent_id", None)
        return str(parent) if parent else None

    @property
    def started_at(self) -> datetime | None:
        return getattr(self.call, "started_at", None)

    @property
    def op_name(self) -> str:
        return str(getattr(self.call, "op_name", "")).lower()

    def is_llm_call(self) -> bool:
        """Check if this call is an LLM call.

        Weave marks LLM calls with specific op names or attributes.
        """
        op = self.op_name
        # Check for common LLM call patterns
        llm_patterns = [
            "openai",
            "anthropic",
            "google",
            "gemini",
            "chat",
            "completion",
            "generate",
            "llm",
        ]
        return any(pattern in op for pattern in llm_patterns)

    def is_tool_call(self) -> bool:
        """Check if this call is a tool/function call."""
        op = self.op_name
        # Check for tool call patterns
        tool_patterns = ["tool", "function", "action"]
        return any(pattern in op for pattern in tool_patterns)


def build_call_tree(calls: list[Any]) -> list[CallNode]:
    """Build a tree structure from flat list of calls.

    Args:
        calls: Flat list of Weave calls with parent_id references

    Returns:
        List of root CallNode objects (calls without parents)
    """
    # Create nodes for all calls
    nodes: dict[str, CallNode] = {}
    for call in calls:
        call_id = str(getattr(call, "id", ""))
        if call_id:
            nodes[call_id] = CallNode(call=call)

    # Build parent-child relationships
    roots: list[CallNode] = []
    for node in nodes.values():
        parent_id = node.parent_id
        if parent_id and parent_id in nodes:
            nodes[parent_id].children.append(node)
        else:
            roots.append(node)

    # Sort children by started_at at each level
    def sort_children(node: CallNode) -> None:
        node.children.sort(key=lambda n: n.started_at or datetime.min)
        for child in node.children:
            sort_children(child)

    for root in roots:
        sort_children(root)

    # Sort roots by started_at
    roots.sort(key=lambda n: n.started_at or datetime.min)

    return roots


def flatten_tree_chronological(roots: list[CallNode]) -> list[Any]:
    """Flatten tree to chronologically ordered list of calls.

    Performs a depth-first traversal, emitting calls in the order
    they would have executed.

    Args:
        roots: List of root CallNode objects

    Returns:
        Chronologically ordered list of calls
    """
    result: list[Any] = []

    def visit(node: CallNode) -> None:
        result.append(node.call)
        for child in node.children:
            visit(child)

    for root in roots:
        visit(root)

    return result


def _is_llm_call(call: Any) -> bool:
    """Check if a call is an LLM call.

    Uses Weave's ``kind`` attribute when available, falling back to
    op_name pattern matching for API-level call signatures.

    Args:
        call: Weave call object

    Returns:
        True if this is an LLM call
    """
    # Prefer the structured kind attribute set by Weave's integrations
    attrs = getattr(call, "attributes", None)
    if isinstance(attrs, dict):
        weave_meta = attrs.get("weave")
        if isinstance(weave_meta, dict) and weave_meta.get("kind") == "llm":
            return True

    # Fall back to op_name, but only match API-level call patterns
    # (not broad provider names which may appear in user function names)
    op_name = str(getattr(call, "op_name", "")).lower()
    llm_patterns = [
        "chat.completions",
        "messages.create",
        "generate_content",
        "completion",
    ]
    return any(pattern in op_name for pattern in llm_patterns)


def get_llm_calls(calls: list[Any]) -> list[Any]:
    """Filter calls to only LLM-type calls.

    Args:
        calls: List of Weave calls

    Returns:
        List of calls that are LLM calls
    """
    return [call for call in calls if _is_llm_call(call)]


def get_tool_calls(calls: list[Any]) -> list[Any]:
    """Filter calls to only tool-type calls.

    Args:
        calls: List of Weave calls

    Returns:
        List of calls that are tool calls
    """
    result = []
    for call in calls:
        op_name = str(getattr(call, "op_name", "")).lower()
        # Check for tool call patterns
        if "tool" in op_name or "function" in op_name:
            result.append(call)
    return result


def get_span_calls(calls: list[Any]) -> list[Any]:
    """Filter calls to span/chain-type calls.

    Args:
        calls: List of Weave calls

    Returns:
        List of calls that are span/chain type
    """
    # Spans are typically calls that have children but aren't LLM or tool calls
    llm_calls = set(id(c) for c in get_llm_calls(calls))
    tool_calls = set(id(c) for c in get_tool_calls(calls))

    return [
        call
        for call in calls
        if id(call) not in llm_calls and id(call) not in tool_calls
    ]
