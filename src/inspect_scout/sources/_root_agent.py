"""Which of a trace's model calls belong to its root agent."""

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field
from typing import NamedTuple

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
    ancestry = _Ancestry(parents, tools, spans)
    above = [ancestry.above(call.uuid) for call in calls]
    candidates = [i for i, (in_tool, _) in enumerate(above) if not in_tool] or list(
        range(len(calls))
    )
    if not candidates:
        return []

    shallowest = min(above[i].depth for i in candidates)
    top = [
        conversation
        for conversation in _conversations(calls, candidates)
        if any(above[i].depth == shallowest for i in conversation.calls)
    ]
    if len(top) == 1 and top[0].turns > 1:
        return [calls[i] for i in top[0].calls]
    return [calls[i] for i in candidates]


@dataclass
class _Conversation:
    calls: list[int] = field(default_factory=list)
    turns: int = 0
    latest: "_Prefix | None" = None


@dataclass(eq=False)
class _Prefix:
    """A sequence of input message IDs, as a node of a prefix tree.

    `conversation` is the conversation whose latest input it is, if any.
    """

    next: dict[str | None, "_Prefix"] = field(default_factory=dict)
    conversation: _Conversation | None = None


def _conversations(
    calls: Sequence[ModelEvent], indexes: list[int]
) -> list[_Conversation]:
    """Group calls into conversations, each continuing an earlier call's input.

    A call continues the conversation whose latest input is the longest
    prefix of its own input. Inputs are indexed in a prefix tree, so grouping
    takes time linear in the total input length.
    """
    conversations: list[_Conversation] = []
    root = _Prefix()
    for i in indexes:
        prefix = root
        continued: _Conversation | None = None
        for message in calls[i].input:
            prefix = prefix.next.setdefault(message.id, _Prefix())
            continued = prefix.conversation or continued
        if continued is None or not calls[i].input:
            continued = _Conversation()
            conversations.append(continued)
        continued.calls.append(i)
        if continued.latest is not prefix:
            continued.turns += 1
            if continued.latest and continued.latest.conversation is continued:
                continued.latest.conversation = None
            if calls[i].input:
                continued.latest = prefix
                prefix.conversation = continued
    return conversations


class _Above(NamedTuple):
    """Whether a tool is above a node, and how many spans and tools are."""

    in_tool: bool
    depth: int


class _Ancestry:
    """`_Above` for nodes of one trace, cached as ancestors are walked."""

    def __init__(
        self, parents: Mapping[str, str | None], tools: Set[str], spans: Set[str]
    ) -> None:
        self._parents = parents
        self._tools = tools
        self._spans = spans
        self._above: dict[str, _Above] = {}

    def above(self, node: str | None) -> _Above:
        if not node:
            return _Above(False, 0)
        if node in self._above:
            return self._above[node]
        path: list[str] = []
        on_path = {node}
        parent = self._parents.get(node)
        while parent and parent not in on_path and parent not in self._above:
            path.append(parent)
            on_path.add(parent)
            parent = self._parents.get(parent)
        cycle = bool(parent) and parent in on_path
        above = (
            self._including(parent, self._above[parent])
            if parent and not cycle
            else _Above(False, 0)
        )
        for ancestor in reversed(path):
            if not cycle:
                self._above[ancestor] = above
            above = self._including(ancestor, above)
        return above

    def _including(self, node: str, above: _Above) -> _Above:
        """`above` for a node's child: the node's own `above`, plus the node."""
        in_tool = node in self._tools
        return _Above(
            above.in_tool or in_tool,
            above.depth + (1 if in_tool or node in self._spans else 0),
        )
