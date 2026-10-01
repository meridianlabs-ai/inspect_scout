"""Corpus coverage floors: an oracle that passes over a corpus missing the hard shapes proves nothing."""

from typing import Iterator

from inspect_ai.event import (
    ModelEvent,
    TimelineSpan,
    ToolEvent,
    timeline_build,
)

from tests.transcript.tree_gen import CORPUS_SEEDS, generate


def _spans(s: TimelineSpan) -> Iterator[TimelineSpan]:
    yield s
    for item in s.content:
        if not hasattr(item, "event"):
            yield from _spans(item)
    for b in s.branches:
        yield from _spans(b)


def test_corpus_shape_coverage() -> None:
    n_branches = n_grouped = n_nested_tool = n_doubly_nested = 0
    n_scorers_no_direct_model = 0
    for seed in CORPUS_SEEDS:
        tree = timeline_build(generate(seed).events)
        all_spans = list(_spans(tree.root))
        branch_count = sum(len(s.branches) for s in all_spans)
        n_branches += 1 if branch_count else 0
        n_grouped += 1 if branch_count >= 2 else 0
        for s in all_spans:
            for item in s.content:
                ev = getattr(item, "event", None)
                if isinstance(ev, ToolEvent) and ev.events:
                    n_nested_tool += 1
                    if any(isinstance(n, ToolEvent) and n.events for n in ev.events):
                        n_doubly_nested += 1
            if (
                s.span_type == "scorers"
                and not any(
                    isinstance(getattr(i, "event", None), ModelEvent) for i in s.content
                )
                and s.content
            ):
                n_scorers_no_direct_model += 1

    # Floors, not exact counts: regenerating with new blocks must not break this.
    assert n_branches >= 15, f"corpus has only {n_branches} branch-bearing trees"
    assert n_grouped >= 5
    assert n_nested_tool >= 20
    assert n_doubly_nested >= 5
    assert n_scorers_no_direct_model >= 10
