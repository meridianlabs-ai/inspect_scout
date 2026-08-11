"""Corpus coverage self-checks — an all-green oracle over a corpus that never exercises the hard shapes is worthless (review record: 'validate the harness')."""

from typing import Iterator

from inspect_ai.event import (
    Event,
    ModelEvent,
    ScoreEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
    timeline_build,
)

from tests.transcript.tree_gen import (
    CORPUS_SEEDS,
    GeneratedTranscript,
    all_event_uuids,
    expected_owners,
    generate,
)


def _trees() -> Iterator[tuple[GeneratedTranscript, Timeline]]:
    for seed in CORPUS_SEEDS:
        g = generate(seed)
        yield g, timeline_build(g.events)


def test_corpus_shape_coverage() -> None:
    n_branches = n_grouped = n_nested_tool = n_doubly_nested = 0
    n_scorers_no_direct_model = n_flat_comparable = 0
    for g, tree in _trees():

        def spans(s: TimelineSpan) -> Iterator[TimelineSpan]:
            yield s
            for item in s.content:
                if not hasattr(item, "event"):
                    yield from spans(item)
            for b in s.branches:
                yield from spans(b)

        all_spans = list(spans(tree.root))
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
        n_flat_comparable += 1 if g.flat_comparable else 0

    # Floors, not exact counts: regenerating with new blocks must not break this.
    assert n_branches >= 15, f"corpus has only {n_branches} branch-bearing trees"
    assert n_grouped >= 5
    assert n_nested_tool >= 20
    assert n_doubly_nested >= 5
    assert n_scorers_no_direct_model >= 10
    assert n_flat_comparable >= 25, (
        f"oracle 2 would be vacuous: only {n_flat_comparable} flat-comparable"
    )


def test_reference_total_and_deterministic() -> None:
    g = generate(7)
    tree = timeline_build(g.events)
    a = expected_owners(tree.root, depth=None, include_scorers=False)
    b = expected_owners(tree.root, depth=None, include_scorers=False)
    assert a == b and len(a) > 0


def test_scorers_model_suppression_not_subtree_exclusion() -> None:
    """Scorers rule is model-suppression, not subtree exclusion (design §2/§3).

    At include_scorers=False, grader ModelEvents are suppressed by
    non-existence, but a scorers-subtree ScoreEvent still renders into the
    owner segment while a scorers-subtree ModelEvent must not appear at all.
    """

    def spans(s: TimelineSpan) -> Iterator[TimelineSpan]:
        yield s
        for item in s.content:
            if not hasattr(item, "event"):
                yield from spans(item)
        for b in s.branches:
            yield from spans(b)

    def events_in(s: TimelineSpan) -> Iterator[Event]:
        for item in s.content:
            if isinstance(item, TimelineEvent):
                yield item.event
                if isinstance(item.event, ToolEvent):
                    yield from item.event.events
            else:
                yield from events_in(item)

    for seed in CORPUS_SEEDS:
        g = generate(seed)
        tree = timeline_build(g.events)
        scorers = [s for s in spans(tree.root) if s.span_type == "scorers"]
        if not scorers:
            continue
        model_events = [e for e in events_in(scorers[0]) if isinstance(e, ModelEvent)]
        score_events = [e for e in events_in(scorers[0]) if isinstance(e, ScoreEvent)]
        if not model_events or not score_events:
            continue

        uuids_off = set(all_event_uuids(tree.root, include_scorers=False))
        owners_off = expected_owners(tree.root, depth=None, include_scorers=False)

        assert score_events[0].uuid in uuids_off
        assert score_events[0].uuid in owners_off
        assert model_events[0].uuid not in uuids_off
        return

    raise AssertionError("no corpus seed had both a scorers ModelEvent and ScoreEvent")
