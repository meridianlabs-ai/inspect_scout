"""Property oracles for event interleaving (design doc, Verification).

Every oracle here was verified RED on HEAD 8a3fde2df, before the
collect_span_owned implementation landed, per the design's
harness-validation deliverable. To re-verify, copy this file plus
`tree_gen.py` into a detached worktree at that revision and run with
`-p no:cacheprovider`.
"""

from __future__ import annotations

import pytest
from inspect_ai.event import Event, timeline_build
from inspect_ai.model import ChatMessage, get_model
from inspect_scout._scanner.extract import EVENT_MARKER_KEY, message_numbering
from inspect_scout._scanner.util import _message_id
from inspect_scout._transcript.interleave import EventsSpec
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import TimelineMessages
from inspect_scout._transcript.types import Transcript

from tests.transcript.fixtures_agentic import agentic_events
from tests.transcript.tree_gen import (
    CORPUS_SEEDS,
    all_event_uuids,
    branch_event_uuids,
    expected_anchor_message_ids,
    expected_owners,
    generate,
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
async def test_oracle1_document_order(include_scorers: bool, depth: int | None) -> None:
    # All four parametrize combinations are red on HEAD, via leg (d) below
    # (empirically confirmed with `--runxfail`; every combination fails at
    # seed 0 with the identical signature: `u0-13 anchored after m0-16,
    # expected m0-8` -- the "helper" utility-span shape in `generate()`
    # always produces trailing-attributed external content between two of
    # "main"'s own turns, regardless of `depth`/`include_scorers`). Legs
    # (a)-(c) alone are ALSO red for both `include_scorers` values at
    # (depth=None) -- the real mechanism was (former interleave.py:446-493,
    # deleted in Task 10): `_collect_span_external`'s recursive call
    # unconditionally overwrote the caller's `last_scannable` with whatever
    # the callee returned (:483-492), so walking into an earlier *scannable*
    # sibling/descendant set `last_scannable` to it, and that value leaked
    # back to the caller even after the callee returned -- a later
    # non-scannable sibling's own external content then keyed off the stale
    # descendant instead of the correct enclosing/preceding walked span. (A
    # scorers-type span was never itself scannable --
    # `structurally_scannable = not span_in_scorers and
    # span_is_scannable(span)`, :447 -- so there was no "nested grader
    # collapsed by depth" step; the bug was generic to any
    # scannable-then-non-scannable sibling sequence.) `depth=1` was immune
    # to legs (a)-(c) because a nested span could then never satisfy
    # `is_scannable`, so `last_scannable` never moved off the root.
    # `include_scorers=False` shows the IDENTICAL leg-(c) failure at the same
    # seed (seed 1: `u1-25 owned by s1-3 rendered in s1-8`) once the oracle's
    # own reference matches the design's scorers contract (design §2/§3):
    # include_scorers=False suppresses grader ModelEvents by non-existence,
    # it does not exclude the whole scorers subtree. An earlier round of this
    # reference wrongly excluded the whole subtree, which is what made legs
    # (a)/(c) alone artificially green for this parameter (fixed in
    # `_document_events`; see task-3-report.md for the wrong-vs-corrected
    # contract and the full red-check evidence, with and without leg (d),
    # before and after that fix).
    for seed in CORPUS_SEEDS:
        g = generate(seed)
        tree = timeline_build(g.events)
        results = await run_materialized(
            g.events,
            events_spec="all",
            include_scorers=include_scorers,
            depth=depth,
        )
        markers = rendered_markers(results)
        rendered_ids = [eid for _, eid in markers]
        doc_order = all_event_uuids(tree.root, include_scorers=include_scorers)
        branch_ids = branch_event_uuids(tree.root)

        # (a) PER-SEGMENT: within each segment, non-branch entries follow
        # document order (branch entries splice at branched_from positions
        # by design — exempt, see design §4). Filter to ids the tree can
        # identify: events without uuids render under minted ids that
        # document order cannot rank. Deliberately per-segment, not a
        # single global subsequence across all segments' concatenated
        # output: a nested walked span claims its own segment while its
        # parent's thread stays whole, so the parent's post-nesting entries
        # render in a segment that precedes the nested span's — cross-
        # segment chronology is not promised and cannot be under this
        # architecture (design doc, Oracle 1, corrected). Cross-segment
        # misattribution stays covered by the global owner-segment
        # invariant, leg (c) below.
        known = set(doc_order)
        for seg in results:
            seg_ids: list[str] = []
            for m in seg.messages:
                if (m.metadata or {}).get(EVENT_MARKER_KEY):
                    assert m.id is not None
                    seg_ids.append(m.id)
            seg_non_branch = [e for e in seg_ids if e not in branch_ids and e in known]
            assert _is_subsequence(seg_non_branch, doc_order), (
                f"seed {seed}: segment {seg.span.id} rendered order violates "
                f"document order: {seg_non_branch}"
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
        # (d) anchoring: each entry renders after its expected anchor turn's
        # message and before the next own turn's (design, Oracle 1).
        anchors = expected_anchor_message_ids(
            tree.root, depth=depth, include_scorers=include_scorers
        )
        for seg in results:
            msgs = seg.messages
            for i, m in enumerate(msgs):
                if not (m.metadata or {}).get(EVENT_MARKER_KEY):
                    continue
                entry_id = m.id
                if entry_id not in anchors or entry_id in branch_ids:
                    continue
                preceding = [
                    _message_id(p)
                    for p in msgs[:i]
                    if not (p.metadata or {}).get(EVENT_MARKER_KEY)
                ]
                expected = anchors[entry_id]
                actual = preceding[-1] if preceding else None
                assert actual == expected, (
                    f"seed {seed}: {entry_id} anchored after {actual}, expected "
                    f"{expected}"
                )


@pytest.mark.anyio
async def test_oracle1_red_check_agentic_number6() -> None:
    """#6 both instances on the repo's own fixture (design, Evidence base)."""
    events = agentic_events()
    tree = timeline_build(events)
    results = await run_materialized(
        events, events_spec="all", include_scorers=False, depth=None
    )
    markers = rendered_markers(results)
    doc_order = all_event_uuids(tree.root, include_scorers=False)
    branch_ids = branch_event_uuids(tree.root)
    known = set(doc_order)
    # PER-SEGMENT (design doc, Oracle 1, corrected) — see the longer note on
    # test_oracle1_document_order's leg (a) above.
    for seg in results:
        seg_ids: list[str] = []
        for m in seg.messages:
            if (m.metadata or {}).get(EVENT_MARKER_KEY):
                assert m.id is not None
                seg_ids.append(m.id)
        seg_non_branch = [e for e in seg_ids if e not in branch_ids and e in known]
        assert _is_subsequence(seg_non_branch, doc_order)
    owners = expected_owners(tree.root, depth=None, include_scorers=False)
    for seg_span_id, eid in markers:
        if eid in owners:
            assert owners[eid] == seg_span_id


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
            event="model",
            uuid=f"u-{text}",
            model="mockllm",
            input=[ChatMessageUser(content="q")],
            output=ModelOutput.from_content(model="mockllm", content=text),
            role="assistant",
            config=GenerateConfig(),
        )

    def ev(e: Event) -> TimelineEvent:
        return TimelineEvent.model_construct(type="event", event=e)

    grader = TimelineSpan(
        id="g",
        name="grader",
        span_type="agent",
        content=[
            ev(model_event("grader assessment")),
            ev(
                InfoEvent.model_construct(
                    event="info", uuid="u-info", source=None, data="GRADER-INFO"
                )
            ),
        ],
    )
    scorers = TimelineSpan(
        id="sc",
        name="scorers",
        span_type="scorers",
        content=[grader],
    )
    main = TimelineSpan(
        id="m",
        name="main",
        span_type="agent",
        content=[ev(model_event("answer"))],
    )
    root = TimelineSpan(
        id="root",
        name="root",
        span_type=None,
        content=[main, scorers],
    )
    transcript = Transcript(
        transcript_id="t-dr",
        timelines=[Timeline(name="Default", description="", root=root)],
    )
    msgs_as_str, _ = message_numbering()
    results: list[TimelineMessages] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=msgs_as_str,
        model=get_model("mockllm/model"),
        context_window=100_000,
        events="all",
        include_scorers=True,
    ):
        assert isinstance(seg, TimelineMessages)
        results.append(seg)
    rendered_ids = [eid for _, eid in rendered_markers(results)]
    assert len(rendered_ids) == len(set(rendered_ids)), (
        f"duplicate [E#] ids on HEAD: {rendered_ids}"
    )


def marker_anchor_pairs(
    messages: list[ChatMessage],
) -> list[tuple[str, str | None]]:
    """(marker.id, last preceding non-marker message id or None), in order.

    Driver-agnostic: works over the flat driver's single rendered-message
    list and equally over a concatenation of the timeline driver's
    per-segment ``.messages`` (segments in emission order) -- both are just
    "a list of ChatMessage, some of which are [E#] markers" (amendment to
    task-4-brief.md, strengthening oracle 2 beyond the id-sequence-only
    comparison: two drivers can render identical ids in identical relative
    order while anchoring them after different preceding turns, which is
    exactly what #6 (foreign-child anchoring) does).
    """
    pairs: list[tuple[str, str | None]] = []
    last_non_marker: str | None = None
    for m in messages:
        if (m.metadata or {}).get(EVENT_MARKER_KEY):
            assert m.id is not None
            pairs.append((m.id, last_non_marker))
        else:
            last_non_marker = _message_id(m)
    return pairs


@pytest.mark.anyio
async def test_oracle2_flat_vs_timeline() -> None:
    """The flat driver already gets document order right (design, Oracle 2).

    Applies only to flat-comparable transcripts; the applicability floor
    guards against a vacuously green oracle (review record: 'validate the
    harness'). Corpus floor: >= 25 applicable (pinned in test_tree_gen).

    Per controller amendment to task-4-brief.md, the brief's id-SEQUENCE
    comparison is REPLACED (not supplemented) by comparing (event_id,
    anchor_message_id) pairs: id-sequence alone is blind to anchoring
    differences -- both drivers can render the same ids in the same
    relative order while attaching them after different preceding turns
    (anchoring is the heart of #6) -- and pair equality strictly implies
    id-sequence equality, so keeping both assertions would make which one
    governs the oracle's red status an accident of seed order, invisible
    under strict-xfail.

    Measured now (decorator off, `-p no:cacheprovider`, all 200 seeds, at
    77705cb88): 26 seeds are flat-comparable in the shipped corpus --
    re-measure rather than trust this number, since `tree_gen.py`'s
    generator has changed the flat-comparable count before and can again.
    A pure id-sequence comparison would be vacuously green on some of
    those 26: both drivers can render the same ids in the same order
    while anchoring them after different preceding turns (the "helper"
    utility-span shape: the flat driver anchors the helper's foreign info
    event in document position, right after main's turn that precedes the
    helper span, while the timeline driver anchors it after the whole
    "main" segment's last own turn instead -- exactly the #6 divergence
    the amendment exists to catch). That's why the pair assertion below
    replaces rather than supplements the id-sequence check; it was red on
    every applicable seed against the pre-fix baseline (see this module's
    docstring for the revision).
    """
    from inspect_scout._transcript.interleave import interleave_events

    applicable = 0
    for seed in CORPUS_SEEDS:
        g = generate(seed)
        if not g.flat_comparable:
            continue
        applicable += 1
        flat_transcript = Transcript(
            transcript_id="t", messages=g.messages, events=g.events
        )
        flat = interleave_events(flat_transcript, "all")
        results = await run_materialized(
            g.events, events_spec="all", include_scorers=False, depth=None
        )

        # (event_id, anchor_message_id) pairs: same walk over the flat
        # driver's single list and over the timeline driver's segments
        # concatenated in emission order. Sole assertion (amendment
        # replaces, not supplements, the brief's id-sequence comparison).
        flat_pairs = marker_anchor_pairs(flat)
        timeline_messages = [m for seg in results for m in seg.messages]
        timeline_pairs = marker_anchor_pairs(timeline_messages)
        assert flat_pairs == timeline_pairs, (
            f"seed {seed}: flat_pairs={flat_pairs} timeline_pairs={timeline_pairs}"
        )
    assert applicable >= 25, f"oracle 2 nearly vacuous: {applicable} applicable"


@pytest.mark.anyio
@pytest.mark.parametrize("include_scorers", [False, True])
async def test_oracle4_streamed_equals_materialized(include_scorers: bool) -> None:
    """Cross-path differential (design Oracle 4) — the record's most productive tool.

    Compares (span.id, messages_str) segment-for-segment; message paths
    only, never result aggregation (design §3 'Flag, do not fix').
    """
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages
    from inspect_scout._transcript.types import TranscriptInfo

    for seed in CORPUS_SEEDS:
        g = generate(seed)
        transcript = Transcript(transcript_id=f"t{seed}", events=g.events)

        async def load(transcript: Transcript = transcript) -> Transcript:
            return transcript

        handle = MaterializedTranscriptHandle(
            load, TranscriptInfo(transcript_id=f"t{seed}")
        )
        msgs_as_str, _ = message_numbering()
        streamed = [
            (seg.span.id, seg.messages_str)
            async for seg in stream_timeline_messages(
                handle,
                messages_as_str=msgs_as_str,
                model=get_model("mockllm/model"),
                context_window=100_000,
                events="all",
                include_scorers=include_scorers,
            )
        ]
        results = await run_materialized(
            g.events,
            events_spec="all",
            include_scorers=include_scorers,
            depth=None,
        )
        # message_numbering is stateful; re-number the materialized pass fresh
        materialized = [(seg.span.id, seg.messages_str) for seg in results]
        assert streamed == materialized, f"seed {seed}"
