"""Tests for per-span event interleaving in ``timeline_messages``."""

from __future__ import annotations

import re
from typing import Literal

import pytest
from inspect_ai.event import (
    Event,
    ModelEvent,
    ScoreEvent,
    SpanEndEvent,
    TimelineSpan,
    timeline_build,
)
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    ContentReasoning,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.interleave import EventsSpec
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import (
    _ORPHAN_SPAN_ID,
    TimelineMessages,
    timeline_messages,
)
from inspect_scout._transcript.timeline_stream import stream_timeline_messages
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.transcript.fixtures_agentic import (
    _compaction_event,
    _span_begin,
    _span_end,
    _tool_event,
    agentic_events,
    agentic_transcript,
)
from tests.transcript.fixtures_agentic import (
    _model_event as _agentic_model_event,
)
from tests.transcript.span_builders import _model_event, _span, _span_of


async def _collect(
    root: TimelineSpan,
    *,
    events: EventsSpec | None,
    compaction: Literal["all", "last"] | int = "all",
) -> tuple[list[TimelineMessages], str]:
    msgs_as_str, _ = message_numbering()
    model = get_model("mockllm/model")
    results: list[TimelineMessages] = []
    async for seg in timeline_messages(
        root,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=10_000,
        compaction=compaction,
        events=events,
    ):
        results.append(seg)
    combined = "\n".join(r.messages_str for r in results)
    return results, combined


@pytest.mark.anyio
async def test_off_thread_model_event_with_reasoning_only_content_renders() -> None:
    """A fork renders in place even with events=[] and an empty `.completion`."""
    u1 = ChatMessageUser(content="q1")
    u2 = ChatMessageUser(content="q2")
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    a1 = out1.choices[0].message
    ev1 = _model_event([u1], out1)

    fork_out = ModelOutput.from_content(
        model="mockllm",
        content=[ContentReasoning(reasoning="secret forked plan")],
    )
    assert fork_out.completion == ""
    fork_ev = _model_event([u1, a1], fork_out)

    out2 = ModelOutput.from_content(model="mockllm", content="second")
    ev2 = _model_event([u1, a1, u2], out2)

    span = _span("span-a", "agent-a", [ev1, fork_ev, ev2])
    root = TimelineSpan(id="root", name="root", span_type=None, content=[span])

    results, combined = await _collect(root, events=[])

    assert len(results) == 1
    assert re.search(
        r"\[M2\].*\[E1\] MODEL \(BRANCH\):\n.*<thinking>secret forked plan</thinking>.*\[M3\]",
        combined,
        re.DOTALL,
    )


@pytest.mark.anyio
async def test_zero_walked_transcript_yields_orphan_segment() -> None:
    root = _span_of(
        "root",
        "root",
        [ScoreEvent(score=Score(value=1.0), scorer="s")],
        span_type=None,
    )
    results, combined = await _collect(root, events="all")
    assert [r.span.id for r in results] == [_ORPHAN_SPAN_ID]
    assert "[E1] SCORE (s)" in combined


def _agentic_events_with_scores() -> list[Event]:
    """``agentic_events()`` augmented to exercise every attachment path.

    - ``ScoreEvent(span_id="main")``: in-span, owned by "main"'s splice.
    - ``ScoreEvent(span_id="sub")``: inside a utility span, collected
      externally and attributed to "main".
    - ``ScoreEvent(span_id="sub2")``: inside a nested scannable span --
      owned by its own splice at ``depth=None``, external (attributed to
      "main") at ``depth=1``.
    - A "scorers" span with grader ``ModelEvent`` + ``ScoreEvent``: the
      grader call is suppressed (model-only) by default and never walked,
      so the score surfaces attributed to whichever span owns it.
    - A genuine off-thread fork ``ModelEvent`` ("fork-1") in "main",
      rendering as a ``[E#] MODEL (BRANCH):`` entry.
    - (From plain ``agentic_events()``) the "sub" utility span's
      ``ModelEvent``s: model calls with no thread of their own, rendered
      as ``MODEL (BRANCH)`` entries attributed to "main".
    """
    events = list(agentic_events())

    # Genuine off-thread fork inserted before the closing "main-3" turn:
    # its output id never joins any reconstructed thread at any compaction
    # value, so it must render as `[E#] MODEL (BRANCH):` with real output
    # text on both the streaming and materialized paths.
    main3_index = next(
        i
        for i, e in enumerate(events)
        if isinstance(e, ModelEvent) and e.uuid == "evt-main-3"
    )
    events.insert(
        main3_index,
        _agentic_model_event(
            label="fork-1",
            system_prompt="MAIN",
            output_text="fork-output-1",
            span_id="main",
        ),
    )

    main_end = next(
        i
        for i, e in enumerate(events)
        if isinstance(e, SpanEndEvent) and e.id == "main"
    )
    events.insert(
        main_end,
        ScoreEvent(
            uuid="evt-in-span-score",
            span_id="main",
            scorer="in-span",
            score=Score(value=1),
        ),
    )

    sub_end = next(
        i for i, e in enumerate(events) if isinstance(e, SpanEndEvent) and e.id == "sub"
    )
    events.insert(
        sub_end,
        ScoreEvent(
            uuid="evt-sub-external-score",
            span_id="sub",
            scorer="sub-external",
            score=Score(value=0),
        ),
    )

    sub2_end = next(
        i
        for i, e in enumerate(events)
        if isinstance(e, SpanEndEvent) and e.id == "sub2"
    )
    events.insert(
        sub2_end,
        ScoreEvent(
            uuid="evt-sub2-nested-score",
            span_id="sub2",
            scorer="sub2-nested",
            score=Score(value=0.75),
        ),
    )

    grader_event = _agentic_model_event(
        label="grader-1",
        system_prompt="GRADER",
        output_text="grader-output",
        span_id="scorers",
    )
    events += [
        _span_begin(
            span_id="scorers", name="scorers", span_type="scorers", parent_id=None
        ),
        grader_event,
        ScoreEvent(
            uuid="evt-scorers-score",
            span_id="scorers",
            scorer="graded",
            score=Score(value=0.5),
        ),
        _span_end(span_id="scorers"),
    ]
    return events


def _cumulative_compaction_events() -> list[Event]:
    """One "main" span with compaction regions [t1, t2], [t3], [fork, t4], then a score.

    t2's input embeds t1's output, as real transcripts do, so once region 1 is
    pruned t1 is recoverable only through t2's input.
    """
    ev_t1 = _agentic_model_event(
        label="cc-t1", system_prompt="MAIN", output_text="turn1-output", span_id="main"
    )
    a1 = ev_t1.output.choices[0].message
    ev_t2 = _agentic_model_event(
        label="cc-t2",
        system_prompt="MAIN",
        output_text="turn2-output",
        span_id="main",
        input_messages=[
            ChatMessageSystem(content="MAIN"),
            ev_t1.input[1],
            a1,
            ChatMessageUser(content="user-input-cc-t2b"),
        ],
    )
    compaction1 = _compaction_event(label="cc-c1", type="summary", span_id="main")
    ev_t3 = _agentic_model_event(
        label="cc-t3", system_prompt="MAIN", output_text="turn3-output", span_id="main"
    )
    compaction2 = _compaction_event(label="cc-c2", type="summary", span_id="main")
    fork_ev = _agentic_model_event(
        label="cc-fork", system_prompt="MAIN", output_text="fork-output", span_id="main"
    )
    ev_t4 = _agentic_model_event(
        label="cc-t4", system_prompt="MAIN", output_text="turn4-output", span_id="main"
    )
    score = ScoreEvent(
        uuid="evt-cc-score", span_id="main", scorer="final", score=Score(value=1)
    )
    return [
        _span_begin(span_id="main", name="main", span_type="agent", parent_id=None),
        ev_t1,
        ev_t2,
        compaction1,
        ev_t3,
        compaction2,
        fork_ev,
        ev_t4,
        score,
        _span_end(span_id="main"),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("compaction", ["all", "last"])
async def test_cumulative_compaction_does_not_resurface_pruned_regions(
    compaction: Literal["all", "last"],
) -> None:
    """A pruned turn stays hidden rather than rendering as ``MODEL (BRANCH)``; a fork still renders."""
    _, combined = await _collect(
        timeline_build(_cumulative_compaction_events()).root,
        events=["score"],
        compaction=compaction,
    )

    if compaction == "all":
        assert "turn1-output" in combined
    else:
        assert "turn1-output" not in combined
    assert "fork-output" in combined
    assert combined.count("turn4-output") == 1


@pytest.mark.anyio
async def test_events_selection_does_not_bypass_compaction_on_span_transcripts() -> (
    None
):
    """`events=` keeps a span-structured transcript on the timeline path.

    The flat path ignores `compaction`, so rerouting there makes it a no-op.
    """

    async def render(
        compaction: Literal["all", "last"], events: EventsSpec | None
    ) -> str:
        transcript = Transcript(
            transcript_id="t",
            messages=[ChatMessageUser(content="q"), ChatMessageAssistant(content="a")],
            events=agentic_events(),
        )
        msgs_as_str, _ = message_numbering()
        out: list[str] = []
        async for seg in transcript_messages(
            transcript,
            messages_as_str=msgs_as_str,
            model=get_model("mockllm/model"),
            compaction=compaction,
            events=events,
        ):
            out.append(seg.messages_str)
        return "\n".join(out)

    # control: compaction discriminates without events=
    assert await render("all", None) != await render("last", None)
    assert await render("all", ["score"]) != await render("last", ["score"])


@pytest.mark.anyio
async def test_stream_tool_event_nested_subagent_depth_excluded_parity() -> None:
    """A ``ToolEvent``-hoisted nested subagent's on-thread turns render as branch entries when ``depth``-excluded, with materialized and streaming parity.

    Pins down the ToolEvent.events investigation for this fix: `timeline_
    build` (inspect_ai) already hoists a flat `ToolEvent` carrying `agent`/
    `events` into its own nested `TimelineSpan` (`tool_invoked=True`, never
    classified utility) via `_event_to_node`; no changes to `timeline_build`
    are needed. Once hoisted, this nested span is handled identically to
    any other structurally scannable span: walked directly when within
    `depth`, or -- as exercised here -- excluded by `depth` and surfaced
    via ``walk_owned_spans``' foreign-item folding as `MODEL (BRANCH)`
    entries attached to its parent. The streaming path already recurses
    into `ToolEvent.events` for both full- and off-thread-event
    substitution (`_collect_pass2_model_events`, `timeline_stream.py`), so
    no changes were needed there either. For this fixture shape, the
    streaming and materialized ownership-traversal-backed paths already
    agree (verified via `--runxfail`).
    """
    main_1 = _agentic_model_event(
        label="main-1",
        system_prompt="MAIN",
        output_text="main-output-1",
        span_id="main",
    )
    # main-2's input embeds main-1's own output message, making it a
    # genuine cumulative on-thread continuation (matching how a real
    # transcript's ModelEvent.input grows turn over turn) -- otherwise the
    # pre-existing `_AnchorWalk` off-thread/fork detection would itself
    # classify main-1 as a fork, independent of anything under test
    # here (see `_two_turn_events`/`_cumulative_compaction_events` above).
    main_2 = _agentic_model_event(
        label="main-2",
        system_prompt="MAIN",
        output_text="main-output-2",
        span_id="main",
        input_messages=[
            ChatMessageSystem(content="MAIN"),
            main_1.input[1],
            main_1.output.choices[0].message,
            ChatMessageUser(content="user-input-main-2-followup"),
        ],
    )
    events: list[Event] = [
        _span_begin(span_id="main", name="main", span_type="agent", parent_id=None),
        main_1,
        _tool_event(
            label="handoff-tool",
            function="handoff",
            payload="p",
            span_id="main",
            agent="handoff_agent",
            events=[
                _agentic_model_event(
                    label="handoff-1",
                    system_prompt="MAIN",
                    output_text="handoff-output-1",
                    span_id="main",
                ),
                _agentic_model_event(
                    label="handoff-2",
                    system_prompt="MAIN",
                    output_text="handoff-output-2",
                    span_id="main",
                ),
            ],
        ),
        main_2,
        _span_end(span_id="main"),
    ]
    transcript = agentic_transcript(events=events)

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(
        load, TranscriptInfo(transcript_id=transcript.transcript_id)
    )

    streamed_numbering, _ = message_numbering()
    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=streamed_numbering,
            model="mockllm/model",
            events="all",
            depth=1,
        )
    ]

    materialized_tree = timeline_build(events)
    materialized_numbering, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            materialized_tree.root,
            messages_as_str=materialized_numbering,
            model="mockllm/model",
            events="all",
            depth=1,
        )
    ]

    assert streamed
    assert streamed == materialized
    combined = "\n".join(text for _, text in streamed)
    # Both nested on-thread turns render as branch entries (no thread of
    # their own reconstructed, since the hoisted span is depth-excluded),
    # attached to "main" -- the last (and only) span actually walked.
    assert combined.count("MODEL (BRANCH)") == 2
    assert "handoff-output-1" in combined
    assert "handoff-output-2" in combined
    main_text = next(text for span_id, text in streamed if span_id == "main")
    assert "handoff-output-1" in main_text
    assert "handoff-output-2" in main_text
    # The span's own on-thread turns are unaffected -- still rendered
    # inline as ordinary messages, not as branch entries.
    assert "main-output-1" in main_text
    assert "main-output-2" in main_text


@pytest.mark.anyio
@pytest.mark.parametrize("compaction", ["all", "last", 2])
@pytest.mark.parametrize("depth", [None, 1])
async def test_stream_timeline_messages_events_parity(
    compaction: Literal["all", "last"] | int, depth: int | None
) -> None:
    """``stream_timeline_messages(events=...)`` matches the materialized path.

    Drives a multi-span fixture with an in-span score, a score attributed
    from a non-scannable utility span, and a scorers-span score through
    both the streaming and materialized ``timeline_messages`` call and
    asserts the yielded ``(span.id, messages_str)`` sequences match --
    across every ``compaction``/``depth`` combination.
    """
    events = _agentic_events_with_scores()
    transcript = agentic_transcript(events=events)

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(
        load, TranscriptInfo(transcript_id=transcript.transcript_id)
    )

    # Fresh message_numbering() per side so [M#]/[E#] ordinals match.
    streamed_numbering, _ = message_numbering()
    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=streamed_numbering,
            model="mockllm/model",
            events=["score"],
            compaction=compaction,
            depth=depth,
        )
    ]

    materialized_tree = timeline_build(events)

    materialized_numbering, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            materialized_tree.root,
            messages_as_str=materialized_numbering,
            model="mockllm/model",
            events=["score"],
            compaction=compaction,
            depth=depth,
        )
    ]

    assert streamed  # non-vacuous
    assert streamed == materialized
    # The "fork-1" off-thread ModelEvent must render as a branch entry with
    # its real output text, not an empty stub, on the streaming path.
    combined = "\n".join(text for _, text in streamed)
    assert "MODEL (BRANCH)" in combined
    assert "fork-output-1" in combined
    # The "sub" utility span's two ModelEvents are non-scannable,
    # off-thread-by-location events with no thread of their own -- they
    # must render as branch entries attached to "main" (the fix under
    # test), not be silently dropped.
    assert combined.count("sub-output-1") == 1
    assert combined.count("sub-output-2") == 1
    main_text = next(text for span_id, text in streamed if span_id == "main")
    assert "sub-output-1" in main_text
    assert "sub-output-2" in main_text
    # The scorers span's grader ModelEvent is suppressed (model-only) by
    # default (include_scorers=False); its own ScoreEvent still surfaces
    # exactly once, owned by whichever walked span precedes it in
    # document order.
    assert "grader-output" not in combined
    assert combined.count("SCORE (graded)") == 1


@pytest.mark.anyio
@pytest.mark.parametrize("compaction", ["last", 2, "all"])
async def test_stream_timeline_messages_cumulative_compaction_discriminator_parity(
    compaction: Literal["all", "last"] | int,
) -> None:
    """Cumulative region-last inputs must not corrupt the streaming discriminator.

    Regression test for the bug where pass 2 substituted only the ACTUAL
    compaction's ``needed`` ModelEvents in full, leaving every other
    region's last ModelEvent output-only (``input=[]``). Because
    ``span_owned_messages`` computes ``excluded_ids`` by
    reconstructing the ``compaction="all"`` thread -- which reads every
    region-last ModelEvent's ``input`` -- and "t2" (region 1's last event)
    has a cumulative input embedding "t1"'s output, stripping "t2"'s input
    made "t1"'s output vanish from the "all" reconstruction. It then missed
    ``excluded_ids`` and misrendered as a spurious ``[E#] MODEL (BRANCH):``
    entry under ``compaction in ("last", 2)``. ``compaction="all"`` never
    prunes anything and is included for completeness/non-regression.
    """
    events = _cumulative_compaction_events()
    transcript = agentic_transcript(events=events)

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(
        load, TranscriptInfo(transcript_id=transcript.transcript_id)
    )

    streamed_numbering, _ = message_numbering()
    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=streamed_numbering,
            model="mockllm/model",
            events=["score"],
            compaction=compaction,
        )
    ]

    materialized_tree = timeline_build(events)
    materialized_numbering, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            materialized_tree.root,
            messages_as_str=materialized_numbering,
            model="mockllm/model",
            events=["score"],
            compaction=compaction,
        )
    ]

    assert streamed  # non-vacuous
    assert streamed == materialized

    combined = "\n".join(text for _, text in streamed)
    if compaction != "all":
        # Region 1 ("t1"/"t2") is compaction-pruned under both "last" and 2;
        # it must stay fully hidden on both paths, never resurrected as a
        # branch entry.
        assert "turn1-output" not in combined
        assert "turn2-output" not in combined
    if compaction == "last":
        assert "turn3-output" not in combined  # only the final region survives

    # The genuine fork always renders, exactly once, on both paths.
    assert combined.count("MODEL (BRANCH)") == 1
    assert combined.count("fork-output") == 1
