"""Which of a trace's model calls belong to its root agent."""

from collections.abc import Mapping, Sequence, Set

from inspect_ai.event import ModelEvent


def root_agent_calls(
    calls: Sequence[ModelEvent],
    parents: Mapping[str, str | None],
    tools: Set[str],
    spans: Set[str],
) -> list[ModelEvent]:
    """Return the model calls made by the trace's root agent.

    A call made inside a tool belongs to whatever the tool ran (a sub-agent,
    or a helper that calls a model), so it is left out. A sub-agent that
    isn't behind a tool runs in a nested span, so of the remaining calls only
    those at the smallest depth are kept. A lone call above the agent loop
    (rewriting the query, a guardrail) is a helper, so the smallest depth
    with more than one call wins over it.

    Depth counts the spans and tools above a call; a model call span wrapping
    another (a framework's span around the SDK's) doesn't count, so both stay.
    If every call is inside a tool, the tool rule is dropped.

    Args:
        calls: The trace's model calls, each with `uuid` set to the source's
            ID for the call.
        parents: Parent ID of every span, call and tool in the trace.
        tools: IDs of the trace's tool calls.
        spans: IDs of the trace's agent or chain spans.

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
        return sum(1 for a in ancestry[i] if a in tools or a in spans)

    by_depth: dict[int, list[ModelEvent]] = {}
    for i in candidates:
        by_depth.setdefault(depth(i), []).append(calls[i])
    depths = sorted(by_depth)
    loop = next((d for d in depths if len(by_depth[d]) > 1), depths[0])
    return by_depth[loop]


def _ancestors(node: str | None, parents: Mapping[str, str | None]) -> list[str]:
    ancestors: list[str] = []
    parent = parents.get(node) if node else None
    while parent and parent not in ancestors and parent != node:
        ancestors.append(parent)
        parent = parents.get(parent)
    return ancestors
