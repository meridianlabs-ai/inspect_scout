"""Reconstruct a branch's full event stream from a delta-encoded `Timeline`."""

from inspect_ai.event import (
    AnchorEvent,
    Event,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    timeline_build,
)

__all__ = ["splice", "splice_to_timeline"]


def splice(timeline: Timeline, target: TimelineSpan) -> list[Event]:
    """Reconstruct `target`'s full event stream by concatenating ancestor prefixes.

    For each ancestor, take events up to the `AnchorEvent` matching the next child's `branched_from`, strip the `:{span_id}` suffix from span IDs, and concatenate. The result is what a standalone unbranched run of `target`'s lineage would have produced.
    """
    chain = _ancestor_chain(timeline.root, target)
    out: list[Event] = []
    for i, node in enumerate(chain):
        events = [
            item.event for item in node.content if isinstance(item, TimelineEvent)
        ]
        if i + 1 < len(chain):
            anchor = chain[i + 1].branched_from
            if not anchor:
                out.clear()
                continue
            cut = _index_of_anchor(events, anchor)
            events = events[: cut + 1] if cut is not None else events
        out.extend(_strip_suffix(e, node.id) for e in events)
    return out


def splice_to_timeline(timeline: Timeline, target: TimelineSpan) -> Timeline:
    """Splice `target` and rebuild it as a standalone (unbranched) `Timeline`."""
    return timeline_build(events=splice(timeline, target), name=target.name)


def _ancestor_chain(root: TimelineSpan, target: TimelineSpan) -> list[TimelineSpan]:
    path: list[TimelineSpan] = []

    def walk(node: TimelineSpan) -> bool:
        path.append(node)
        if node is target or node.id == target.id:
            return True
        for child in node.branches:
            if walk(child):
                return True
        path.pop()
        return False

    if not walk(root):
        raise ValueError(
            f"TimelineSpan {target.id!r} is not reachable from timeline root"
        )
    return path


def _index_of_anchor(events: list[Event], anchor_id: str) -> int | None:
    for i, e in enumerate(events):
        if isinstance(e, AnchorEvent) and e.anchor_id == anchor_id:
            return i
    return None


def _strip_suffix(event: Event, trajectory_id: str) -> Event:
    """Return a copy of `event` with `:{trajectory_id}` stripped from span-ID fields."""
    suffix = f":{trajectory_id}"
    update: dict[str, str] = {}
    if event.span_id is not None and event.span_id.endswith(suffix):
        update["span_id"] = event.span_id.removesuffix(suffix)
    if isinstance(event, (SpanBeginEvent, SpanEndEvent)) and event.id.endswith(suffix):
        update["id"] = event.id.removesuffix(suffix)
    if isinstance(event, SpanBeginEvent) and event.parent_id is not None:
        if event.parent_id.endswith(suffix):
            update["parent_id"] = event.parent_id.removesuffix(suffix)
        elif event.parent_id == trajectory_id:
            update["parent_id"] = ""
    return event.model_copy(update=update) if update else event
