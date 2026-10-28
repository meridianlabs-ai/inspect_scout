"""Which of a trace's model calls belong to its root agent."""

from collections.abc import Mapping, Sequence, Set

from inspect_ai.event import ModelEvent


def root_agent_calls(
    calls: Sequence[ModelEvent],
    parents: Mapping[str, str | None],
    tools: Set[str],
    levels: Set[str] | None = None,
) -> list[ModelEvent]:
    """Return the model calls made by the trace's root agent.

    A call made inside a tool belongs to whatever the tool ran (a sub-agent,
    or a helper that calls a model), so it is left out. A sub-agent or helper
    that isn't behind a tool runs in a nested span, so of the remaining calls
    only those at the smallest depth are kept.

    If every call is inside a tool, the tool rule is dropped.

    Args:
        calls: The trace's model calls, each with `uuid` set to the source's
            ID for the call.
        parents: Parent ID of every span, call and tool in the trace.
        tools: IDs of the trace's tool calls.
        levels: The ancestors that count toward a call's depth, for formats
            that mark agent spans. All ancestors count when None.

    Returns:
        The root agent's calls, in their original order.
    """
    ancestry = [_ancestors(call.uuid, parents) for call in calls]
    candidates = [
        i
        for i, ancestors in enumerate(ancestry)
        if not any(a in tools for a in ancestors)
    ] or list(range(len(calls)))
    if not candidates:
        return []

    def depth(i: int) -> int:
        return sum(1 for a in ancestry[i] if levels is None or a in levels)

    least = min(depth(i) for i in candidates)
    return [calls[i] for i in candidates if depth(i) == least]


def _ancestors(node: str | None, parents: Mapping[str, str | None]) -> list[str]:
    ancestors: list[str] = []
    parent = parents.get(node) if node else None
    while parent and parent not in ancestors and parent != node:
        ancestors.append(parent)
        parent = parents.get(parent)
    return ancestors
