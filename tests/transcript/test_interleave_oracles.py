"""Property oracles for event interleaving over the seeded ``tree_gen`` corpus."""

from __future__ import annotations

import pytest
from inspect_ai.event import InfoEvent, Timeline, timeline_build
from inspect_ai.model import ChatMessage, ChatMessageUser, ModelOutput, get_model
from inspect_scout._scanner.extract import EVENT_MARKER_KEY, message_numbering
from inspect_scout._scanner.util import _message_id
from inspect_scout._transcript.interleave import EventsSpec, interleave_events
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import TimelineMessages
from inspect_scout._transcript.types import Transcript

from tests.transcript.span_builders import _model_event, _span, _span_of
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
    tree: Timeline,
    *,
    events_spec: EventsSpec,
    include_scorers: bool,
    depth: int | None,
) -> list[TimelineMessages]:
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
    for seed in CORPUS_SEEDS:
        g = generate(seed)
        tree = timeline_build(g.events)
        results = await run_materialized(
            tree,
            events_spec="all",
            include_scorers=include_scorers,
            depth=depth,
        )
        markers = rendered_markers(results)
        rendered_ids = [eid for _, eid in markers]
        doc_order = all_event_uuids(tree.root, include_scorers=include_scorers)
        branch_ids = branch_event_uuids(tree.root)

        # (a) Within each segment, non-branch entries follow document order
        # (branch entries splice at branched_from instead). Uuid-less events
        # render under minted ids that document order cannot rank. Order is
        # only promised per segment: a nested walked span gets its own
        # segment while its parent's thread stays whole, so the parent's later
        # entries render in a segment that precedes the nested span's.
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
        # (b) No id renders twice.
        assert len(rendered_ids) == len(set(rendered_ids)), (
            f"seed {seed}: duplicate [E#] ids: {rendered_ids}"
        )
        # (c) Every entry renders in its owner's segment.
        owners = expected_owners(
            tree.root, depth=depth, include_scorers=include_scorers
        )
        for seg_span_id, eid in markers:
            if eid in owners:
                assert owners[eid] == seg_span_id, (
                    f"seed {seed}: {eid} owned by {owners[eid]} rendered in "
                    f"{seg_span_id}"
                )
        # (d) Each entry renders after its expected anchor turn's message and
        # before the next own turn's.
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
async def test_include_scorers_renders_nested_grader_events_once() -> None:
    # A grader span nested under scorers is a stored-timeline shape: timeline_build
    # flattens scorers subtrees, so the corpus never generates it.
    grader_out = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader = _span_of(
        "g",
        "grader",
        [
            _model_event([ChatMessageUser(content="grade")], grader_out),
            InfoEvent(data="GRADER-INFO"),
        ],
    )
    answer = ModelOutput.from_content(model="mockllm", content="answer")
    main = _span("m", "main", [_model_event([ChatMessageUser(content="q")], answer)])
    scorers = _span_of("sc", "scorers", [grader], span_type="scorers")
    root = _span_of("root", "root", [main, scorers], span_type=None)

    results = await run_materialized(
        Timeline(name="Default", description="", root=root),
        events_spec="all",
        include_scorers=True,
        depth=None,
    )
    rendered_ids = [eid for _, eid in rendered_markers(results)]
    assert len(rendered_ids) == len(set(rendered_ids)), rendered_ids


def marker_anchor_pairs(
    messages: list[ChatMessage],
) -> list[tuple[str, str | None]]:
    """(marker id, id of the last preceding non-marker message), in order."""
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
    """The flat and timeline drivers agree on flat-comparable transcripts.

    Compares (event id, anchor) pairs, not id sequences: the drivers can render
    the same ids in the same order while anchoring them after different turns.
    """
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
            timeline_build(g.events),
            events_spec="all",
            include_scorers=False,
            depth=None,
        )

        flat_pairs = marker_anchor_pairs(flat)
        timeline_messages = [m for seg in results for m in seg.messages]
        timeline_pairs = marker_anchor_pairs(timeline_messages)
        assert flat_pairs == timeline_pairs, (
            f"seed {seed}: flat_pairs={flat_pairs} timeline_pairs={timeline_pairs}"
        )
    assert applicable >= 25, f"oracle 2 nearly vacuous: {applicable} applicable"
