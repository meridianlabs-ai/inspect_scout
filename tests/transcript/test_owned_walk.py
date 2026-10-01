"""Tests for ``walk_owned_spans``."""

from __future__ import annotations

from inspect_ai.event import (
    BranchEvent,
    ModelEvent,
    SampleLimitEvent,
    TimelineSpan,
    timeline_build,
)
from inspect_ai.model import ChatMessageUser, ModelOutput
from inspect_scout._transcript.timeline import (
    _ORPHAN_SPAN_ID,
    OwnedSpan,
    walk_owned_spans,
)

from tests.transcript.span_builders import _model_event, _span, _span_of
from tests.transcript.tree_gen import (
    CORPUS_SEEDS,
    expected_owners,
    generate,
)


def _limit() -> SampleLimitEvent:
    return SampleLimitEvent.model_construct(
        event="sample_limit", type="message", limit=1, message="limit hit"
    )


def _owned(
    root: TimelineSpan, *, depth: int | None = None, include_scorers: bool = False
) -> list[OwnedSpan]:
    return list(walk_owned_spans(root, depth=depth, include_scorers=include_scorers))


def test_tier3_orphans_lead_first_walked_span() -> None:
    limit = _limit()
    out = ModelOutput.from_content(model="mockllm", content="a")
    span_a = _span("a", "agent-a", [_model_event([ChatMessageUser(content="q")], out)])
    root = _span_of("root", "root", [limit, span_a], span_type=None)

    owned = _owned(root)
    assert [o.span.id for o in owned] == ["a"]
    assert owned[0].items[0].event is limit and not owned[0].items[0].own


def test_depth_zero_and_negative_yield_nothing() -> None:
    limit = _limit()
    root = _span_of("root", "root", [limit], span_type=None)
    assert _owned(root, depth=0) == []
    assert _owned(root, depth=-1) == []


def test_branch_without_branch_event_splices_everything() -> None:
    """Stored timelines (``add_timeline``) need not carry a ``BranchEvent``."""
    out_alt = ModelOutput.from_content(model="mockllm", content="ALT")
    alt = _model_event([ChatMessageUser(content="bq")], out_alt)
    branch = _span_of("b1", "branch", [alt], span_type="agent")
    out = ModelOutput.from_content(model="mockllm", content="own")
    owner = _span("o", "main", [_model_event([ChatMessageUser(content="q")], out)])
    owner = owner.model_copy(update={"branches": [branch]})

    [owned] = _owned(owner)
    assert [i.event for i in owned.branches[0].items] == [alt]


def test_spans_inside_branches_are_never_walked() -> None:
    out_n = ModelOutput.from_content(model="mockllm", content="nested-agent")
    nested_agent = _span(
        "na", "sub", [_model_event([ChatMessageUser(content="nq")], out_n)]
    )
    branch = _span_of("b1", "branch", [BranchEvent(), nested_agent], span_type="agent")
    out = ModelOutput.from_content(model="mockllm", content="own")
    owner = _span("o", "main", [_model_event([ChatMessageUser(content="q")], out)])
    owner = owner.model_copy(update={"branches": [branch]})

    owned = _owned(owner)
    assert [o.span.id for o in owned] == ["o"]
    branch_events = [i.event for i in owned[0].branches[0].items]
    assert any(isinstance(e, ModelEvent) for e in branch_events)


def test_tier2_latest_started_not_latest_touched_with_nested_walked_span() -> None:
    """Tier 2 picks the walked span that started last, not the one control returned to."""
    out_a = ModelOutput.from_content(model="mockllm", content="mA")
    out_s = ModelOutput.from_content(model="mockllm", content="mS")
    out_b = ModelOutput.from_content(model="mockllm", content="mB")
    m_a = _model_event([ChatMessageUser(content="qa")], out_a)
    m_s = _model_event([ChatMessageUser(content="qs")], out_s)
    m_b = _model_event([ChatMessageUser(content="qb")], out_b)
    sub = _span("sub", "sub-agent", [m_s])
    main = _span_of("main", "main-agent", [m_a, sub, m_b])
    limit = _limit()
    root = _span_of("root", "root", [main, limit], span_type=None)

    owned = _owned(root)
    assert [o.span.id for o in owned] == ["main", "sub"]
    by_id = {o.span.id: o for o in owned}
    assert any(i.event is limit and not i.own for i in by_id["sub"].items)
    assert not any(i.event is limit for i in by_id["main"].items)

    # oracle 3 trusts the brute-force reference; it must agree here
    assert limit.uuid is not None
    reference = expected_owners(root, depth=None, include_scorers=False)
    assert reference[limit.uuid] == "sub"


def test_nested_branches_flatten_onto_owners_branch_list() -> None:
    """A branch's own branches flatten onto the owner's list, each replay-cut."""
    out_replay1 = ModelOutput.from_content(model="mockllm", content="replay1")
    replay1 = _model_event([ChatMessageUser(content="bq1")], out_replay1)
    out_alt1 = ModelOutput.from_content(model="mockllm", content="alt1")
    alt1 = _model_event([ChatMessageUser(content="bq1")], out_alt1)
    cut1 = BranchEvent(from_anchor="anchor-1")

    out_replay2 = ModelOutput.from_content(model="mockllm", content="replay2")
    replay2 = _model_event([ChatMessageUser(content="bq2")], out_replay2)
    out_alt2 = ModelOutput.from_content(model="mockllm", content="alt2")
    alt2 = _model_event([ChatMessageUser(content="bq2")], out_alt2)
    cut2 = BranchEvent(from_anchor="anchor-2")

    b2 = _span_of("b2", "branch2", [replay2, cut2, alt2], span_type="agent")
    b2 = b2.model_copy(update={"branched_from": "anchor-2"})

    b1 = _span_of("b1", "branch1", [replay1, cut1, alt1], span_type="agent")
    b1 = b1.model_copy(update={"branched_from": "anchor-1", "branches": [b2]})

    out = ModelOutput.from_content(model="mockllm", content="own")
    owner = _span("o", "main", [_model_event([ChatMessageUser(content="q")], out)])
    owner = owner.model_copy(update={"branches": [b1]})

    [owned] = _owned(owner)
    assert len(owned.branches) == 2
    ob1, ob2 = owned.branches
    assert ob1.branched_from == "anchor-1"
    assert ob2.branched_from == "anchor-2"
    events1 = [i.event for i in ob1.items]
    events2 = [i.event for i in ob2.items]
    assert replay1 not in events1 and cut1 in events1 and alt1 in events1
    assert replay2 not in events2 and cut2 in events2 and alt2 in events2
    assert all(not i.own for i in ob1.items)
    assert all(not i.own for i in ob2.items)


def test_oracle3_differential_against_brute_force() -> None:
    """Oracle 3: ownership matches the brute-force reference across the corpus."""
    for seed in CORPUS_SEEDS:
        tree = timeline_build(generate(seed).events)
        for include_scorers in (False, True):
            for depth in (None, 1):
                reference = expected_owners(
                    tree.root, depth=depth, include_scorers=include_scorers
                )
                actual: dict[str, str] = {}
                for owned in walk_owned_spans(
                    tree.root, depth=depth, include_scorers=include_scorers
                ):
                    key = "" if owned.span.id == _ORPHAN_SPAN_ID else owned.span.id
                    for item in owned.items:
                        if item.event.uuid is not None:
                            actual[item.event.uuid] = key
                    for ob in owned.branches:
                        for item in ob.items:
                            if item.event.uuid is not None:
                                actual[item.event.uuid] = key
                assert actual == reference, (
                    f"seed={seed} scorers={include_scorers} depth={depth}"
                )
