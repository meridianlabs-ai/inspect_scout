"""Property oracles for event interleaving (design doc, Verification).

Every oracle here was RED on HEAD 8a3fde2df before the collect_span_owned
implementation landed (xfail strict pins that), per the design's
harness-validation deliverable.
"""

from __future__ import annotations

import pytest
from inspect_ai.event import Event, timeline_build
from inspect_ai.model import get_model
from inspect_scout._scanner.extract import EVENT_MARKER_KEY, message_numbering
from inspect_scout._transcript.interleave import EventsSpec
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import TimelineMessages
from inspect_scout._transcript.types import Transcript

from tests.transcript.fixtures_agentic import agentic_events
from tests.transcript.tree_gen import (
    CORPUS_SEEDS,
    all_event_uuids,
    branch_event_uuids,
    expected_owners,
    generate,
)

XFAIL_RED = pytest.mark.xfail(
    strict=True, reason="red until collect_span_owned lands (#5/#6)"
)


def rendered_markers(results: list[TimelineMessages]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for seg in results:
        for m in seg.messages:
            if (m.metadata or {}).get(EVENT_MARKER_KEY):
                assert m.id is not None
                out.append((seg.span.id, m.id))
    return out


async def run_materialized(
    events: list[Event],
    *,
    events_spec: EventsSpec,
    include_scorers: bool,
    depth: int | None,
) -> list[TimelineMessages]:
    tree = timeline_build(events)
    transcript = Transcript(transcript_id="t", timelines=[tree])
    msgs_as_str, _ = message_numbering()
    results: list[TimelineMessages] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=msgs_as_str,
        model=get_model("mockllm/model"),
        context_window=100_000,
        events=events_spec,
        include_scorers=include_scorers,
        depth=depth,
    ):
        assert isinstance(seg, TimelineMessages)
        results.append(seg)
    return results


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    it = iter(haystack)
    return all(x in it for x in needle)


@pytest.mark.anyio
@pytest.mark.parametrize("include_scorers", [False, True])
@pytest.mark.parametrize("depth", [None, 1])
async def test_oracle1_document_order(
    request: pytest.FixtureRequest, include_scorers: bool, depth: int | None
) -> None:
    # Only (depth=None, include_scorers=True) is red on HEAD: depth=1 collapses
    # the nested scorers/grader span into a single walked span before the #5/#6
    # misattribution can surface, and include_scorers=False never enters the
    # scorers subtree at all. Marking xfail(strict) per-combination (rather than
    # on the whole parametrized function) keeps the pin accurate to what was
    # actually observed red on HEAD instead of asserting redness that isn't
    # there — see task-3-report.md for the full red-check evidence.
    if depth is None and include_scorers:
        request.node.add_marker(XFAIL_RED)
    for seed in CORPUS_SEEDS:
        g = generate(seed)
        tree = timeline_build(g.events)
        results = await run_materialized(
            g.events, events_spec="all",
            include_scorers=include_scorers, depth=depth,
        )
        markers = rendered_markers(results)
        rendered_ids = [eid for _, eid in markers]
        doc_order = all_event_uuids(tree.root, include_scorers=include_scorers)
        branch_ids = branch_event_uuids(tree.root)

        # (a) non-branch entries follow document order (branch entries splice
        # at branched_from positions by design — exempt, see design §4).
        # Filter to ids the tree can identify: events without uuids render
        # under minted ids that document order cannot rank.
        known = set(doc_order)
        non_branch = [
            e for e in rendered_ids if e not in branch_ids and e in known
        ]
        assert _is_subsequence(non_branch, doc_order), (
            f"seed {seed}: rendered order violates document order: {non_branch}"
        )
        # (b) GLOBAL: no id renders twice.
        assert len(rendered_ids) == len(set(rendered_ids)), (
            f"seed {seed}: duplicate [E#] ids: {rendered_ids}"
        )
        # (c) GLOBAL: every entry renders in its owner's segment.
        owners = expected_owners(
            tree.root, depth=depth, include_scorers=include_scorers
        )
        for seg_span_id, eid in markers:
            if eid in owners:
                assert owners[eid] == seg_span_id, (
                    f"seed {seed}: {eid} owned by {owners[eid]} rendered in "
                    f"{seg_span_id}"
                )


@XFAIL_RED
@pytest.mark.anyio
async def test_oracle1_red_check_agentic_number6() -> None:
    """#6 both instances on the repo's own fixture (design, Evidence base)."""
    events = agentic_events()
    tree = timeline_build(events)
    results = await run_materialized(
        events, events_spec="all", include_scorers=False, depth=None
    )
    markers = rendered_markers(results)
    rendered_ids = [eid for _, eid in markers]
    doc_order = all_event_uuids(tree.root, include_scorers=False)
    branch_ids = branch_event_uuids(tree.root)
    known = set(doc_order)
    non_branch = [e for e in rendered_ids if e not in branch_ids and e in known]
    assert _is_subsequence(non_branch, doc_order)
    owners = expected_owners(tree.root, depth=None, include_scorers=False)
    for seg_span_id, eid in markers:
        if eid in owners:
            assert owners[eid] == seg_span_id


@XFAIL_RED
@pytest.mark.anyio
async def test_oracle1_red_check_double_render_include_scorers() -> None:
    """include_scorers=True double-render (design 'The problem', 4th consequence).

    Unreachable via timeline_build (it flattens scorers subtrees), so built
    by hand — the stored-timeline shape.
    """
    from inspect_ai.event import (
        InfoEvent,
        ModelEvent,
        Timeline,
        TimelineEvent,
        TimelineSpan,
    )
    from inspect_ai.model import ChatMessageUser, GenerateConfig, ModelOutput

    def model_event(text: str) -> ModelEvent:
        return ModelEvent.model_construct(
            event="model", uuid=f"u-{text}", model="mockllm",
            input=[ChatMessageUser(content="q")],
            output=ModelOutput.from_content(model="mockllm", content=text),
            role="assistant", config=GenerateConfig(),
        )

    def ev(e: Event) -> TimelineEvent:
        return TimelineEvent.model_construct(type="event", event=e)

    grader = TimelineSpan(
        id="g", name="grader", span_type="agent",
        content=[
            ev(model_event("grader assessment")),
            ev(InfoEvent.model_construct(
                event="info", uuid="u-info", source=None, data="GRADER-INFO")),
        ],
    )
    scorers = TimelineSpan(
        id="sc", name="scorers", span_type="scorers", content=[grader],
    )
    main = TimelineSpan(
        id="m", name="main", span_type="agent",
        content=[ev(model_event("answer"))],
    )
    root = TimelineSpan(
        id="root", name="root", span_type=None, content=[main, scorers],
    )
    transcript = Transcript(
        transcript_id="t-dr",
        timelines=[Timeline(name="Default", description="", root=root)],
    )
    msgs_as_str, _ = message_numbering()
    results: list[TimelineMessages] = []
    async for seg in transcript_messages(
        transcript, messages_as_str=msgs_as_str,
        model=get_model("mockllm/model"), context_window=100_000,
        events="all", include_scorers=True,
    ):
        assert isinstance(seg, TimelineMessages)
        results.append(seg)
    rendered_ids = [eid for _, eid in rendered_markers(results)]
    assert len(rendered_ids) == len(set(rendered_ids)), (
        f"duplicate [E#] ids on HEAD: {rendered_ids}"
    )
