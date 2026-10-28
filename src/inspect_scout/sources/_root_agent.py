"""Which of a trace's model calls belong to its root agent."""

from collections.abc import Mapping, Sequence, Set

from inspect_ai.event import ModelEvent


def root_agent_calls(
    calls: Sequence[ModelEvent],
    parents: Mapping[str, str | None],
    tools: Set[str],
    spans: Set[str],
) -> list[ModelEvent]:
    """Return the model calls that may hold the trace's root agent conversation.

    A call made inside a tool belongs to whatever the tool ran (a sub-agent,
    or a helper that calls a model), so it is left out unless every call is.

    The rest are grouped into conversations: a call continues an earlier one
    when that conversation's latest input is a prefix of its input (the same
    input again, as when a framework's span and the SDK's both record one
    request, adds no turn). The root agent's conversation is the one that
    reaches the fewest spans and tools above a call, when it is the only
    conversation there and it has more than one turn. Anything else (a lone
    call above a deeper agent loop, or two conversations at the same depth)
    is ambiguous, and every call outside a tool is returned.

    Args:
        calls: The trace's model calls, each with `uuid` set to the source's
            ID for the call and message IDs assigned (a message sent again
            keeps its ID).
        parents: Parent ID of every span, call and tool in the trace.
        tools: IDs of the trace's tool calls.
        spans: IDs of the trace's agent or chain spans.

    Returns:
        The calls, in their original order.
    """
    ancestry = [_ancestors(call.uuid, parents) for call in calls]
    candidates = [
        i
        for i, ancestors in enumerate(ancestry)
        if not any(a in tools for a in ancestors)
    ] or list(range(len(calls)))
    if not candidates:
        return []

    depths = {
        i: sum(1 for a in ancestry[i] if a in tools or a in spans) for i in candidates
    }
    shallowest = min(depths.values())
    top = [
        conversation
        for conversation in _conversations(calls, candidates)
        if any(depths[i] == shallowest for i in conversation)
    ]
    if len(top) == 1 and _turns(calls, top[0]) > 1:
        return [calls[i] for i in top[0]]
    return [calls[i] for i in candidates]


def _conversations(calls: Sequence[ModelEvent], indexes: list[int]) -> list[list[int]]:
    """Group calls into conversations, each continuing an earlier call's input."""
    conversations: list[list[int]] = []
    inputs: list[list[str | None]] = []
    # Conversations by their latest input's length and last message ID; a
    # match is confirmed by comparing the whole prefix.
    by_end: dict[tuple[int, str | None], list[int]] = {}
    for i in indexes:
        ids = [message.id for message in calls[i].input]
        continued = next(
            (
                c
                for k in range(len(ids), 0, -1)
                for c in reversed(by_end.get((k, ids[k - 1]), []))
                if inputs[c] == ids[:k]
            ),
            None,
        )
        if continued is None:
            continued = len(conversations)
            conversations.append([])
            inputs.append([])
        elif inputs[continued] != ids:
            by_end[(len(inputs[continued]), inputs[continued][-1])].remove(continued)
        conversations[continued].append(i)
        if ids and inputs[continued] != ids:
            inputs[continued] = ids
            by_end.setdefault((len(ids), ids[-1]), []).append(continued)
    return conversations


def _turns(calls: Sequence[ModelEvent], conversation: list[int]) -> int:
    return len({tuple(message.id for message in calls[i].input) for i in conversation})


def _ancestors(node: str | None, parents: Mapping[str, str | None]) -> list[str]:
    ancestors: list[str] = []
    parent = parents.get(node) if node else None
    while parent and parent not in ancestors and parent != node:
        ancestors.append(parent)
        parent = parents.get(parent)
    return ancestors
