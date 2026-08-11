"""Unit tests + brute-force differential for walk_owned_spans (design §1, §4)."""

from __future__ import annotations

from inspect_ai.event import (
    BranchEvent,
    ModelEvent,
    SampleLimitEvent,
    ScoreEvent,
    TimelineSpan,
    ToolEvent,
    timeline_build,
)
from inspect_ai.model import ChatMessageUser, ModelOutput
from inspect_ai.scorer import Score
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


def test_tier1_nearest_walked_ancestor_owns_descendant_events() -> None:
    """#6's minimal shape: non-walked child between a parent's turns."""
    out1 = ModelOutput.from_content(model="mockllm", content="t1")
    out2 = ModelOutput.from_content(model="mockllm", content="t2")
    ev1 = _model_event([ChatMessageUser(content="q")], out1)
    util_info = _limit()
    utility_child = _span_of("util", "helper", [util_info], span_type="agent")
    utility_child = utility_child.model_copy(update={"utility": True})
    ev2 = _model_event([ChatMessageUser(content="q")], out2)
    parent = _span_of("parent", "main", [ev1, utility_child, ev2])

    [owned] = _owned(parent)
    assert owned.span.id == "parent"
    assert [(type(i.event).__name__, i.own) for i in owned.items] == [
        ("ModelEvent", True),
        ("SampleLimitEvent", False),  # tier 1, foreign, in DOCUMENT position
        ("ModelEvent", True),
    ]


def test_tier2_latest_preceding_walked_span() -> None:
    """Root-level event between two walked siblings -> preceding sibling."""
    out_a = ModelOutput.from_content(model="mockllm", content="a")
    out_b = ModelOutput.from_content(model="mockllm", content="b")
    span_a = _span(
        "a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    span_b = _span(
        "b", "agent-b", [_model_event([ChatMessageUser(content="qb")], out_b)]
    )
    limit = _limit()
    root = _span_of("root", "root", [span_a, limit, span_b], span_type=None)

    owned = _owned(root)
    assert [o.span.id for o in owned] == ["a", "b"]
    assert any(i.event is limit and not i.own for i in owned[0].items)
    assert not any(i.event is limit for i in owned[1].items)


def test_tier3_orphans_lead_first_walked_span() -> None:
    limit = _limit()
    out = ModelOutput.from_content(model="mockllm", content="a")
    span_a = _span("a", "agent-a", [_model_event([ChatMessageUser(content="q")], out)])
    root = _span_of("root", "root", [limit, span_a], span_type=None)

    owned = _owned(root)
    assert [o.span.id for o in owned] == ["a"]
    assert owned[0].items[0].event is limit and not owned[0].items[0].own


def test_zero_walked_yields_single_orphan_span() -> None:
    limit = _limit()
    score = ScoreEvent(score=Score(value=1.0), scorer="s")
    root = _span_of("root", "root", [limit, score], span_type=None)

    owned = _owned(root)
    assert len(owned) == 1
    assert owned[0].span.id == _ORPHAN_SPAN_ID
    assert [i.own for i in owned[0].items] == [False, False]


def test_depth_zero_and_negative_yield_nothing() -> None:
    limit = _limit()
    root = _span_of("root", "root", [limit], span_type=None)
    assert _owned(root, depth=0) == []
    assert _owned(root, depth=-1) == []


def test_too_deep_scannable_span_events_become_foreign() -> None:
    out_i = ModelOutput.from_content(model="mockllm", content="inner")
    inner = _span(
        "inner", "sub", [_model_event([ChatMessageUser(content="qi")], out_i)]
    )
    out_o = ModelOutput.from_content(model="mockllm", content="outer")
    outer = _span_of(
        "outer",
        "main",
        [_model_event([ChatMessageUser(content="qo")], out_o), inner],
    )

    owned = _owned(outer, depth=1)
    assert [o.span.id for o in owned] == ["outer"]
    assert any(isinstance(i.event, ModelEvent) and not i.own for i in owned[0].items)


def test_tool_event_nested_events_flatten_recursively_as_foreign() -> None:
    out_n = ModelOutput.from_content(model="mockllm", content="nested")
    nested_model = _model_event([ChatMessageUser(content="nq")], out_n)
    out_i = ModelOutput.from_content(model="mockllm", content="inner")
    inner_model = _model_event([ChatMessageUser(content="iq")], out_i)
    inner_tool = ToolEvent.model_construct(
        event="tool",
        id="t2",
        function="f",
        arguments={},
        result="",
        events=[inner_model],
    )
    tool = ToolEvent.model_construct(
        event="tool",
        id="t1",
        function="f",
        arguments={},
        result="",
        events=[nested_model, inner_tool],
    )
    out = ModelOutput.from_content(model="mockllm", content="own")
    span = _span_of(
        "s", "main", [_model_event([ChatMessageUser(content="q")], out), tool]
    )

    [owned] = _owned(span)
    flags = [(i.event, i.own) for i in owned.items]
    assert (tool, True) in flags  # the direct ToolEvent is own
    assert (nested_model, False) in flags  # one level down: foreign
    assert (inner_tool, False) in flags  # tool-in-tool: foreign
    assert (inner_model, False) in flags  # two levels down: foreign


def test_scorers_model_only_suppression_and_walked_by_include_scorers() -> None:
    """Scorers subtree: MODEL-only suppression and include_scorers gating.

    include_scorers=False suppresses grader MODEL events only (design §2);
    the scorers subtree's non-model events (ScoreEvent!) stay foreign items —
    decision 2 exists so 'SCORE (graded)' is never lost.
    """
    out_g = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader = _span(
        "g",
        "grader",
        [
            _model_event([ChatMessageUser(content="grade")], out_g),
            ScoreEvent(score=Score(value=1.0), scorer="graded"),
        ],
    )
    scorers = _span_of("sc", "scorers", [grader], span_type="scorers")
    out_m = ModelOutput.from_content(model="mockllm", content="answer")
    main = _span("m", "main", [_model_event([ChatMessageUser(content="q")], out_m)])
    root = _span_of("root", "root", [main, scorers], span_type=None)

    owned_false = _owned(root, include_scorers=False)
    assert [o.span.id for o in owned_false] == ["m"]
    events_false = [i.event for i in owned_false[0].items]
    assert not any(
        isinstance(e, ModelEvent) and e.span_id == "g" for e in events_false
    )  # grader model: gone
    assert any(isinstance(e, ScoreEvent) for e in events_false)  # score: foreign
    # include_scorers=True: the grader child is WALKED and owns its events
    # exactly once (the double-render fix, design "The problem").
    ids = [o.span.id for o in _owned(root, include_scorers=True)]
    assert ids == ["m", "g"]


def test_branches_ride_owner_with_replay_cut_and_nesting() -> None:
    out_alt = ModelOutput.from_content(model="mockllm", content="ALT")
    alt = _model_event([ChatMessageUser(content="bq")], out_alt)
    out_replay = ModelOutput.from_content(model="mockllm", content="replayed")
    replay = _model_event([ChatMessageUser(content="bq")], out_replay)
    cut = BranchEvent(from_anchor="anchor-msg")
    branch = _span_of("b1", "branch", [replay, cut, alt], span_type="agent")
    branch = branch.model_copy(update={"branched_from": "anchor-msg"})

    out = ModelOutput.from_content(model="mockllm", content="own")
    owner = _span("o", "main", [_model_event([ChatMessageUser(content="q")], out)])
    owner = owner.model_copy(update={"branches": [branch]})

    [owned] = _owned(owner)
    assert len(owned.branches) == 1
    ob = owned.branches[0]
    assert ob.branched_from == "anchor-msg"
    events_in_branch = [i.event for i in ob.items]
    assert replay not in events_in_branch  # replay prefix cut
    assert cut in events_in_branch  # the BranchEvent itself splices
    assert alt in events_in_branch
    assert all(not i.own for i in ob.items)


def test_branch_without_branch_event_splices_everything() -> None:
    out_alt = ModelOutput.from_content(model="mockllm", content="ALT")
    alt = _model_event([ChatMessageUser(content="bq")], out_alt)
    branch = _span_of("b1", "branch", [alt], span_type="agent")
    out = ModelOutput.from_content(model="mockllm", content="own")
    owner = _span("o", "main", [_model_event([ChatMessageUser(content="q")], out)])
    owner = owner.model_copy(update={"branches": [branch]})

    [owned] = _owned(owner)
    assert owned.branches[0].branched_from == ""  # None -> ""
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
    assert [o.span.id for o in owned] == ["o"]  # "na" claims NO segment
    branch_events = [i.event for i in owned[0].branches[0].items]
    assert any(isinstance(e, ModelEvent) for e in branch_events)


def test_tier2_latest_not_first_with_three_siblings() -> None:
    """Regression: tier 2 must pick the LATEST preceding walked span.

    Two siblings can't distinguish "latest" from "first" (both coincide
    whenever the tier-2 event falls after the only walked span seen so
    far); three siblings with the event after the second one can.
    """
    out_a = ModelOutput.from_content(model="mockllm", content="a")
    out_b = ModelOutput.from_content(model="mockllm", content="b")
    out_c = ModelOutput.from_content(model="mockllm", content="c")
    span_a = _span(
        "a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    span_b = _span(
        "b", "agent-b", [_model_event([ChatMessageUser(content="qb")], out_b)]
    )
    span_c = _span(
        "c", "agent-c", [_model_event([ChatMessageUser(content="qc")], out_c)]
    )
    limit = _limit()
    root = _span_of("root", "root", [span_a, span_b, limit, span_c], span_type=None)

    owned = _owned(root)
    assert [o.span.id for o in owned] == ["a", "b", "c"]
    by_id = {o.span.id: o for o in owned}
    assert any(i.event is limit and not i.own for i in by_id["b"].items)
    assert not any(i.event is limit for i in by_id["a"].items)
    assert not any(i.event is limit for i in by_id["c"].items)


def test_tier2_latest_started_not_latest_touched_with_nested_walked_span() -> None:
    """Regression for I3: tier 2 wants the latest-STARTING walked span.

    ``sub`` nests inside ``main`` and starts strictly after ``main``. Once
    control returns to ``main`` for ``mB``, that event is still tier-1-owned
    by ``main`` itself -- but it must NOT make ``main`` "latest" again for
    tier 2: the trailing root-level ``limit`` (no walked ancestor) belongs
    to whichever walked span started most recently in document order, which
    is the deeper ``sub``, not ``main``. A buggy reference that overwrites
    "latest" on every tier-1 attribution instead of on first touch gets this
    wrong (returns ``main``); both ``walk_owned_spans`` and the brute-force
    ``expected_owners`` must agree on ``sub``.
    """
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

    assert limit.uuid is not None
    reference = expected_owners(root, depth=None, include_scorers=False)
    assert reference[limit.uuid] == "sub"


def test_branch_on_nonwalked_carrier_owner_captured_at_span_start() -> None:
    """A non-walked carrier's branch rides the owner AT THE CARRIER'S START.

    Design §1, "Spans are owned too": a span's owner is the owner an event
    at its start position would get. The carrier here is unwalked but
    contains both a nested walked descendant AND a branch; the branch must
    ride the tier-2 owner as of entering the carrier (main1, the latest
    walked span at that point) -- not the nested descendant that only
    becomes `latest` once the carrier's own content is processed, and not
    main2, which comes later still.
    """
    out_m1 = ModelOutput.from_content(model="mockllm", content="m1")
    main1 = _span(
        "m1", "main1", [_model_event([ChatMessageUser(content="q1")], out_m1)]
    )

    out_nested = ModelOutput.from_content(model="mockllm", content="nested")
    nested = _span(
        "nested",
        "nested-agent",
        [_model_event([ChatMessageUser(content="qn")], out_nested)],
    )

    out_alt = ModelOutput.from_content(model="mockllm", content="ALT")
    branch_event = _model_event([ChatMessageUser(content="bq")], out_alt)
    branch = _span_of("br", "branch", [branch_event], span_type="agent")
    carrier = _span_of("carrier", "carrier", [nested], span_type="agent")
    carrier = carrier.model_copy(update={"branches": [branch]})

    out_m2 = ModelOutput.from_content(model="mockllm", content="m2")
    main2 = _span(
        "m2", "main2", [_model_event([ChatMessageUser(content="q2")], out_m2)]
    )

    root = _span_of("root", "root", [main1, carrier, main2], span_type=None)

    owned = _owned(root)
    assert [o.span.id for o in owned] == ["m1", "nested", "m2"]
    by_id = {o.span.id: o for o in owned}
    assert len(by_id["m1"].branches) == 1
    assert by_id["nested"].branches == []
    assert by_id["m2"].branches == []

    # The brute-force reference must agree: the branch's own ModelEvent is
    # owned by "m1", not "nested" (tree_gen.py's `_document_events` used to
    # attribute a carrier's branches using `latest` as it stood AFTER the
    # carrier's content was walked, since it yielded content before
    # branches; fixed to yield branches first, snapshotting the owner at
    # the carrier's entry, matching `walk_owned_spans`).
    assert branch_event.uuid is not None
    reference = expected_owners(root, depth=None, include_scorers=False)
    assert reference[branch_event.uuid] == "m1"


def test_nested_branches_flatten_onto_owners_branch_list() -> None:
    """A branch's own ``.branches`` (branch-of-a-branch) flattens onto the same.

    owner's branch list, b1 then b2, each independently replay-cut
    (design §4 flattening loop over ``nested_branches``).
    """
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
    """Design Oracle 3: ownership fuzz vs the deliberately-slow reference."""
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
