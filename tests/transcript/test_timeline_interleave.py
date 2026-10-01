"""Tests for per-span event interleaving in ``timeline_messages``."""

from __future__ import annotations

import re
from typing import Literal

import pytest
from inspect_ai.event import (
    Event,
    ScoreEvent,
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
from inspect_scout._transcript.interleave import EventsSpec
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import (
    _ORPHAN_SPAN_ID,
    TimelineMessages,
    timeline_messages,
)
from inspect_scout._transcript.types import Transcript

from tests.transcript.fixtures_agentic import (
    _compaction_event,
    _span_begin,
    _span_end,
    agentic_events,
)
from tests.transcript.fixtures_agentic import (
    _model_event as _agentic_model_event,
)
from tests.transcript.span_builders import _model_event, _span, _span_of
from tests.transcript.stream_parity import both_paths


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
async def test_streamed_compaction_pruned_turns_stay_hidden() -> None:
    """Compaction-pruned regions stay hidden when streamed, as materialized.

    `span_owned_messages` reads every region's last ModelEvent input to find
    the pruned turns, so pass 2 must substitute those events in full.
    """
    streamed, materialized = await both_paths(
        _cumulative_compaction_events(), events_spec=["score"], compaction="last"
    )

    combined = "\n".join(text for _, text in streamed)
    assert "turn1-output" not in combined
    assert combined.count("fork-output") == 1
    assert streamed == materialized
