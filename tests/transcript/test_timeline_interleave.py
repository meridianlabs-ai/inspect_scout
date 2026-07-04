"""Tests for per-span event interleaving in ``timeline_messages``."""

from __future__ import annotations

import re
from typing import Literal

import pytest
from inspect_ai.event import (
    CompactionEvent,
    ErrorEvent,
    Event,
    ModelEvent,
    SampleLimitEvent,
    ScoreEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    timeline_build,
    timeline_filter,
)
from inspect_ai.log import EvalError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    ContentReasoning,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.interleave import (
    _span_has_direct_model_event,
    collect_span_external,
)
from inspect_scout._transcript.messages import segment_messages, transcript_messages
from inspect_scout._transcript.timeline import TimelineMessages, timeline_messages
from inspect_scout._transcript.timeline_stream import stream_timeline_messages
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.transcript.fixtures_agentic import (
    _model_event as _agentic_model_event,
)
from tests.transcript.fixtures_agentic import (
    _span_begin,
    _span_end,
    agentic_events,
    agentic_transcript,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_event(input_msgs: list[ChatMessage], output: ModelOutput) -> ModelEvent:
    return ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=list(input_msgs),
        output=output,
        role="assistant",
    )


def _span(span_id: str, name: str, events: list[Event]) -> TimelineSpan:
    return TimelineSpan(
        id=span_id,
        name=name,
        span_type="agent",
        content=[TimelineEvent.model_construct(type="event", event=e) for e in events],
    )


def _span_of(
    span_id: str,
    name: str,
    content: list[Event | TimelineSpan],
    *,
    span_type: str | None = "agent",
) -> TimelineSpan:
    """Like ``_span`` but accepts a mix of events and nested spans, and a span_type."""
    items: list[TimelineEvent | TimelineSpan] = [
        item
        if isinstance(item, TimelineSpan)
        else TimelineEvent.model_construct(type="event", event=item)
        for item in content
    ]
    return TimelineSpan(id=span_id, name=name, span_type=span_type, content=items)


async def _collect_transcript(
    root: TimelineSpan,
    *,
    events: list[str] | str | None,
    include_scorers: bool = False,
    context_window: int = 10_000,
) -> tuple[list[TimelineMessages], str]:
    """Drive segments through transcript_messages() (exercises the collector)."""
    transcript = Transcript(
        transcript_id="t1",
        timelines=[Timeline(name="Default", description="", root=root)],
    )
    msgs_as_str, _ = message_numbering()
    model = get_model("mockllm/model")
    results: list[TimelineMessages] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=context_window,
        events=events,  # type: ignore[arg-type]
        include_scorers=include_scorers,
    ):
        assert isinstance(seg, TimelineMessages)
        results.append(seg)
    combined = "\n".join(r.messages_str for r in results)
    return results, combined


async def _collect(
    root: TimelineSpan,
    *,
    events: list[str] | str | None,
    compaction: str = "all",
    span_external: dict[str, list[tuple[str, str]]] | None = None,
    context_window: int = 10_000,
) -> tuple[list[TimelineMessages], str]:
    """Collect segments plus a combined messages_str for convenience assertions."""
    msgs_as_str, _ = message_numbering()
    model = get_model("mockllm/model")
    results: list[TimelineMessages] = []
    async for seg in timeline_messages(
        root,
        messages_as_str=msgs_as_str,
        model=model,
        context_window=context_window,
        compaction=compaction,  # type: ignore[arg-type]
        events=events,  # type: ignore[arg-type]
        span_external=span_external,
    ):
        results.append(seg)
    combined = "\n".join(r.messages_str for r in results)
    return results, combined


# ---------------------------------------------------------------------------
# Fixtures shared across tests
# ---------------------------------------------------------------------------

_u1 = ChatMessageUser(content="q1")
_u2 = ChatMessageUser(content="q2")


def _two_turn_events() -> tuple[ModelEvent, ModelEvent]:
    """Two ModelEvents where the second's input carries the running thread."""
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    a1 = out1.choices[0].message
    ev1 = _model_event([_u1], out1)

    out2 = ModelOutput.from_content(model="mockllm", content="second")
    ev2 = _model_event([_u1, a1, _u2], out2)
    return ev1, ev2


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_mid_span_score_between_model_events_orders_correctly() -> None:
    """A mid-span ScoreEvent lands between the two ModelEvents' messages."""
    ev1, ev2 = _two_turn_events()
    score = ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True)
    scored_span = _span("span-a", "agent-a", [ev1, score, ev2])

    # A sibling span with no events must be unaffected.
    plain_out = ModelOutput.from_content(model="mockllm", content="plain")
    plain_span = _span(
        "span-b", "agent-b", [_model_event([ChatMessageUser(content="p1")], plain_out)]
    )

    root = TimelineSpan(
        id="root", name="root", span_type=None, content=[scored_span, plain_span]
    )

    results, _ = await _collect(root, events=["score"])

    assert len(results) == 2
    scored_text = results[0].messages_str
    plain_text = results[1].messages_str

    # [M...] [E1] [M...] ordering inside the scored span.
    assert re.search(r"\[M2\].*\[E1\] SCORE.*\[M3\]", scored_text, re.DOTALL)
    # The other span is untouched: no event markers at all.
    assert "[E" not in plain_text


@pytest.mark.anyio
async def test_sibling_spans_each_get_own_event_numbering_continues() -> None:
    """Two sibling spans, each scoring itself; [E#] numbering is shared/global."""
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span(
        "span-a",
        "agent-a",
        [
            _model_event([ChatMessageUser(content="qa")], out_a),
            ScoreEvent(score=Score(value="A"), scorer="match-a"),
        ],
    )
    out_b = ModelOutput.from_content(model="mockllm", content="answer-b")
    span_b = _span(
        "span-b",
        "agent-b",
        [
            _model_event([ChatMessageUser(content="qb")], out_b),
            ScoreEvent(score=Score(value="B"), scorer="match-b"),
        ],
    )
    root = TimelineSpan(
        id="root", name="root", span_type=None, content=[span_a, span_b]
    )

    results, _ = await _collect(root, events=["score"])

    assert len(results) == 2
    assert "[E1] SCORE (match-a)" in results[0].messages_str
    assert "[E2] SCORE (match-b)" in results[1].messages_str
    # Each span's rendering contains only its own event.
    assert "match-b" not in results[0].messages_str
    assert "match-a" not in results[1].messages_str


@pytest.mark.anyio
async def test_events_filter_excludes_same_span_error_event() -> None:
    """events=["score"] renders the ScoreEvent but drops a same-span ErrorEvent."""
    out = ModelOutput.from_content(model="mockllm", content="answer")
    span = _span(
        "span-a",
        "agent-a",
        [
            _model_event([ChatMessageUser(content="q")], out),
            ScoreEvent(score=Score(value="C"), scorer="match"),
            ErrorEvent(
                error=EvalError(message="boom", traceback="", traceback_ansi="")
            ),
        ],
    )
    root = TimelineSpan(id="root", name="root", span_type=None, content=[span])

    results, combined = await _collect(root, events=["score"])

    assert len(results) == 1
    assert "SCORE (match)" in combined
    assert "ERROR" not in combined
    assert "boom" not in combined


@pytest.mark.anyio
async def test_events_none_matches_direct_segment_messages() -> None:
    """events=None must not interleave anything: identical to segment_messages(span)."""
    out = ModelOutput.from_content(model="mockllm", content="answer")
    span = _span(
        "span-a",
        "agent-a",
        [
            _model_event([ChatMessageUser(content="q")], out),
            ScoreEvent(score=Score(value="C"), scorer="match"),
        ],
    )
    root = TimelineSpan(id="root", name="root", span_type=None, content=[span])

    model = get_model("mockllm/model")

    msgs_as_str_a, _ = message_numbering()
    via_timeline = [
        seg
        async for seg in timeline_messages(
            root,
            messages_as_str=msgs_as_str_a,
            model=model,
            context_window=10_000,
        )
    ]

    msgs_as_str_b, _ = message_numbering()
    via_segment_messages = [
        seg
        async for seg in segment_messages(
            span,
            messages_as_str=msgs_as_str_b,
            model=model,
            context_window=10_000,
        )
    ]

    assert [s.messages_str for s in via_timeline] == [
        s.messages_str for s in via_segment_messages
    ]
    assert [s.messages for s in via_timeline] == [
        s.messages for s in via_segment_messages
    ]
    # Sanity: the score is genuinely not interleaved on the default path.
    assert "[E" not in via_timeline[0].messages_str
    assert "SCORE" not in via_timeline[0].messages_str


@pytest.mark.anyio
async def test_compaction_last_drops_anchor_event_becomes_leading() -> None:
    """compaction='last': an event anchored to a compacted-away turn leads.

    The compacted-away turn's output id IS present in the untruncated
    compaction="all" thread (it is simply the region "last" pruned away),
    so the discriminator (`_AnchorWalk`'s `excluded_ids`) recognizes it as
    compaction-pruned rather than a genuine fork: it stays fully hidden,
    not resurrected as a `MODEL (BRANCH)` entry.
    """
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    a1 = out1.choices[0].message
    ev1 = _model_event([_u1], out1)
    score = ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True)
    compaction_event = CompactionEvent(type="summary")
    out2 = ModelOutput.from_content(model="mockllm", content="second")
    # Fresh input (no history carried) -- mirrors what remains post-compaction.
    ev2 = _model_event([_u2], out2)

    span = _span("span-a", "agent-a", [ev1, score, compaction_event, ev2])
    root = TimelineSpan(id="root", name="root", span_type=None, content=[span])

    results, combined = await _collect(root, events=["score"], compaction="last")

    assert len(results) == 1
    # The score leads (renders before the surviving M1/M2 turns).
    assert re.search(r"\[E1\] SCORE.*\[M1\].*\[M2\]", combined, re.DOTALL)
    assert a1.text not in combined  # confirms the anchor turn really was dropped


@pytest.mark.anyio
async def test_compaction_last_drops_anchor_event_fork_still_renders() -> None:
    """compaction='last': a genuine fork still renders while the pruned turn hides.

    Same fixture as `test_compaction_last_drops_anchor_event_becomes_leading`,
    plus a genuine fork ModelEvent inserted after the compaction boundary
    whose output never joins ANY thread (not even compaction="all"'s,
    unlike `ev1`, which is merely the compacted-away region "last"). The
    discriminator must tell them apart: `ev1` stays hidden (compaction-
    pruned), `fork_ev` still renders as a `MODEL (BRANCH)` entry.
    """
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    a1 = out1.choices[0].message
    ev1 = _model_event([_u1], out1)
    score = ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True)
    compaction_event = CompactionEvent(type="summary")

    fork_out = ModelOutput.from_content(model="mockllm", content="forked")
    fork_ev = _model_event([_u1, a1], fork_out)

    out2 = ModelOutput.from_content(model="mockllm", content="second")
    # Fresh input (no history carried) -- mirrors what remains post-compaction.
    # fork_ev sits between the boundary and ev2 without ev2 consuming its
    # output, so fork_ev never joins compaction="last" NOR compaction="all"'s
    # thread (only ev2, the region's last, is kept in either case).
    ev2 = _model_event([_u2], out2)

    span = _span("span-a", "agent-a", [ev1, score, compaction_event, fork_ev, ev2])
    root = TimelineSpan(id="root", name="root", span_type=None, content=[span])

    results, combined = await _collect(root, events=["score"], compaction="last")

    assert len(results) == 1
    # ev1 (compaction-pruned) stays hidden; fork_ev (genuine fork) renders as
    # a branch entry, leading alongside the score, ahead of the surviving
    # M1/M2 turns.
    assert re.search(
        r"\[E1\] SCORE.*\[E2\] MODEL \(BRANCH\):\n.*forked.*\[M1\].*\[M2\]",
        combined,
        re.DOTALL,
    )
    assert a1.text not in combined  # the compacted-away turn stays absent
    assert "forked" in combined  # the genuine fork still surfaces


@pytest.mark.anyio
async def test_off_thread_model_event_renders_as_branch_entry() -> None:
    """A fork's ModelEvent output that never joins the thread still renders.

    span-a has model events A1, FORK, A2 where FORK's output is not part
    of A2's input (A1's is): FORK is an off-thread branch that diverged
    and was discarded. It must render as a `[E1] MODEL (BRANCH):` entry
    anchored right after A1, not be silently dropped.
    """
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    a1 = out1.choices[0].message
    ev1 = _model_event([_u1], out1)

    fork_out = ModelOutput.from_content(model="mockllm", content="forked reasoning")
    fork_ev = _model_event([_u1, a1], fork_out)

    out2 = ModelOutput.from_content(model="mockllm", content="second")
    ev2 = _model_event([_u1, a1, _u2], out2)

    span = _span("span-a", "agent-a", [ev1, fork_ev, ev2])
    root = TimelineSpan(id="root", name="root", span_type=None, content=[span])

    # events=[] still renders off-thread outputs -- they are always-on and
    # not gated by the `events` selection.
    results, combined = await _collect(root, events=[])

    assert len(results) == 1
    assert re.search(
        r"\[M2\].*\[E1\] MODEL \(BRANCH\):\n.*forked reasoning.*\[M3\]",
        combined,
        re.DOTALL,
    )
    # Not double-counted as a normal turn.
    assert combined.count("forked reasoning") == 1


@pytest.mark.anyio
async def test_off_thread_model_event_with_reasoning_only_content_renders() -> None:
    """A fork output with only reasoning content (empty `.completion`) still renders.

    Rendering must go through `message_as_str` on the output message, not
    `event.output.completion`: a message whose content is entirely
    `ContentReasoning` parts has an empty `.completion`/`.text`, so relying
    on `completion` would silently drop the branch entirely.
    """
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    a1 = out1.choices[0].message
    ev1 = _model_event([_u1], out1)

    fork_out = ModelOutput.from_content(
        model="mockllm",
        content=[ContentReasoning(reasoning="secret forked plan")],
    )
    assert fork_out.completion == ""  # sanity: the trap this test guards against
    fork_ev = _model_event([_u1, a1], fork_out)

    out2 = ModelOutput.from_content(model="mockllm", content="second")
    ev2 = _model_event([_u1, a1, _u2], out2)

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
async def test_span_external_prepend_and_append() -> None:
    """span_external: "" prepends to the first span; span id appends to that span."""
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    out_b = ModelOutput.from_content(model="mockllm", content="answer-b")
    span_b = _span(
        "span-b", "agent-b", [_model_event([ChatMessageUser(content="qb")], out_b)]
    )
    root = TimelineSpan(
        id="root", name="root", span_type=None, content=[span_a, span_b]
    )

    results, _ = await _collect(
        root,
        events=[],
        span_external={
            "": [("lead-1", "LEADING TEXT")],
            "span-b": [("trail-1", "TRAILING TEXT")],
        },
    )

    assert len(results) == 2
    span_a_text = results[0].messages_str
    span_b_text = results[1].messages_str

    # Leading entry is the very first thing rendered for the first span.
    assert re.match(r"\[E1\] LEADING TEXT", span_a_text)
    assert "TRAILING TEXT" not in span_a_text

    # Trailing entry lands after span-b's own messages.
    assert re.search(r"\[M\d+\].*\[E2\] TRAILING TEXT", span_b_text, re.DOTALL)
    assert "LEADING TEXT" not in span_b_text


# ---------------------------------------------------------------------------
# collect_span_external() via transcript_messages() (Task 3)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scorers_span_score_event_attaches_to_last_scannable_span() -> None:
    """A pruned `scorers` span's ScoreEvent surfaces after the last real span.

    The scorers span also contains a grader ModelEvent, which must not
    become its own thread (the span is pruned, by default).
    """
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span_of(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    grader_out = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader_event = _model_event([ChatMessageUser(content="grade this")], grader_out)
    score = ScoreEvent(score=Score(value=1), scorer="match")
    scorers_span = _span_of(
        "span-scorers", "scorers", [grader_event, score], span_type="scorers"
    )
    root = _span_of("root", "root", [span_a, scorers_span], span_type=None)

    results, combined = await _collect_transcript(root, events=["score"])

    assert len(results) == 1
    assert results[0].span.id == "span-a"
    assert re.search(r"answer-a.*\[E1\] SCORE \(match\)", combined, re.DOTALL)
    # The grader's model call never becomes its own rendered thread.
    assert "grader assessment" not in combined
    assert "grade this" not in combined


@pytest.mark.anyio
async def test_root_level_event_between_spans_attaches_to_earlier_span() -> None:
    """A root-level event between two scannable spans attaches to the earlier one."""
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span_of(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    limit_event = SampleLimitEvent(type="operator", message="stopped early")
    out_b = ModelOutput.from_content(model="mockllm", content="answer-b")
    span_b = _span_of(
        "span-b", "agent-b", [_model_event([ChatMessageUser(content="qb")], out_b)]
    )
    root = _span_of("root", "root", [span_a, limit_event, span_b], span_type=None)

    results, _ = await _collect_transcript(root, events=["sample_limit"])

    assert len(results) == 2
    span_a_text = results[0].messages_str
    span_b_text = results[1].messages_str

    assert "LIMIT (operator): stopped early" in span_a_text
    assert "LIMIT" not in span_b_text


@pytest.mark.anyio
async def test_event_before_any_scannable_span_leads_first_span() -> None:
    """A root-level event before any scannable span leads the first span."""
    limit_event = SampleLimitEvent(type="operator", message="pre-existing limit")
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span_of(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    root = _span_of("root", "root", [limit_event, span_a], span_type=None)

    results, _ = await _collect_transcript(root, events=["sample_limit"])

    assert len(results) == 1
    assert re.match(
        r"\[E1\] LIMIT \(operator\): pre-existing limit", results[0].messages_str
    )


@pytest.mark.anyio
async def test_include_scorers_true_renders_grader_thread_and_score_once() -> None:
    """include_scorers=True: grader thread renders AND score interleaves, once."""
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span_of(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    grader_out = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader_event = _model_event([ChatMessageUser(content="grade this")], grader_out)
    score = ScoreEvent(score=Score(value=1), scorer="match")
    scorers_span = _span_of(
        "span-scorers", "scorers", [grader_event, score], span_type="scorers"
    )
    root = _span_of("root", "root", [span_a, scorers_span], span_type=None)

    results, combined = await _collect_transcript(
        root, events=["score"], include_scorers=True
    )

    # Both the agent span and the scorers span (now unpruned) render.
    assert len(results) == 2
    assert results[1].span.id == "span-scorers"
    # The grader's model call now renders as its own thread.
    assert "grader assessment" in combined
    # The score entry appears exactly once (spliced into the scorers
    # span's own thread) -- not doubled by external collection.
    assert combined.count("SCORE (match)") == 1


@pytest.mark.anyio
async def test_include_scorers_true_non_model_graded_score_collected_once() -> None:
    """include_scorers=True: score from a scorers span with no ModelEvent.

    A scorers span with no ModelEvent (e.g. a non-model-graded scorer like
    ``match``) is never walked by ``_walk_spans``, so its ScoreEvent must
    still surface via span-external collection rather than being silently
    dropped.
    """
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span_of(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    score = ScoreEvent(score=Score(value=1), scorer="match")
    scorers_span = _span_of("span-scorers", "scorers", [score], span_type="scorers")
    root = _span_of("root", "root", [span_a, scorers_span], span_type=None)

    results, combined = await _collect_transcript(
        root, events=["score"], include_scorers=True
    )

    # The scorers span has no direct ModelEvent, so it is never walked as
    # its own scannable span; its score must instead surface as an
    # external event attached to the last scannable span (span-a).
    assert len(results) == 1
    assert results[0].span.id == "span-a"
    assert combined.count("SCORE (match)") == 1


# ---------------------------------------------------------------------------
# Streaming parity (Task 4): stream_timeline_messages(events=...) vs the
# materialized timeline_messages(events=...) call it must match.
# ---------------------------------------------------------------------------


def _agentic_events_with_scores() -> list[Event]:
    """``agentic_events()`` augmented with in-span/external/scorers/nested scores.

    Exercises all four attachment paths ``collect_span_external``
    distinguishes:

    - An in-span ``ScoreEvent(span_id="main")`` lands directly in "main"'s
      own content, owned by "main"'s own ``span_interleaved_messages``
      splice (never externally collected).
    - A ``ScoreEvent(span_id="sub")`` lands inside the "sub" utility span
      (not scannable), so it is collected externally and attributed to the
      last scannable span reached before "sub" ("main").
    - A ``ScoreEvent(span_id="sub2")`` lands inside "sub2", a nested
      *scannable* span (its own direct ``ModelEvent``s, not utility) two
      scannable levels deep under the synthetic root (root == "main" here,
      since ``timeline_build`` collapses the trivial "solvers" wrapper --
      see ``_materialized_collection_source``'s tree). This is the case
      where the ``depth`` axis genuinely matters for collection: at
      ``depth=None`` "sub2" is walked directly and the score is owned by
      its own splice; at ``depth=1`` "sub2" exceeds the depth limit and is
      never walked, so the score must instead surface via external
      collection, attributed to the last span actually walked ("main").
    - A "scorers" span with a direct grader ``ModelEvent`` plus its own
      ``ScoreEvent``, appended at the end of "main"'s content (per
      ``timeline_build``'s phase-span handling, a "scorers" span with no
      other siblings ends up nested as the last child of "main", not a
      top-level sibling of "solvers"): since it has a direct
      ``ModelEvent``, it is walked as an ordinary scannable span (its
      score splices into its own thread, matching
      ``include_scorers=True`` semantics) rather than being collected
      externally.

    Also inserts a genuine off-thread fork ``ModelEvent`` ("fork-1") into
    "main", immediately before its closing turn, so streaming/materialized
    parity coverage genuinely exercises a ``[E#] MODEL (BRANCH):`` entry
    rather than relying on incidental non-cumulative fixture inputs.
    """
    events = list(agentic_events())

    # Genuine off-thread fork: a "main"-prompt ModelEvent inserted right
    # before the closing "main-3" turn, with the default fresh (non-
    # cumulative) input `_model_event()` builds absent an explicit
    # `input_messages=` override. Its output id therefore never joins ANY
    # reconstructed thread, at any `compaction` value -- unlike a
    # compaction-pruned turn (which IS a member of the untruncated
    # `compaction="all"` thread). Exercises the fork/compaction-pruned
    # discriminator (`_AnchorWalk`'s `excluded_ids`,
    # `_transcript/interleave.py`) end-to-end on both the streaming and
    # materialized paths: it must render as `[E#] MODEL (BRANCH):` with its
    # real output text on both, never as an empty stub.
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


def _materialized_collection_source(tree: Timeline) -> Timeline | TimelineSpan:
    """Mirror ``stream_timeline_messages``' events collection source.

    ``stream_timeline_messages`` never prunes ``scorers`` spans, so its
    collection source matches ``transcript_messages(...,
    include_scorers=True)``'s: only a ``scorers`` span with a direct
    ``ModelEvent`` is filtered out (it is walked as an ordinary scannable
    span instead, splicing its own events).
    """
    return timeline_filter(
        tree,
        lambda s: not (s.span_type == "scorers" and _span_has_direct_model_event(s)),
    )


@pytest.mark.anyio
@pytest.mark.parametrize("compaction", ["all", "last", 2])
@pytest.mark.parametrize("depth", [None, 1])
async def test_stream_timeline_messages_events_parity(
    compaction: Literal["all", "last"] | int, depth: int | None
) -> None:
    """``stream_timeline_messages(events=...)`` matches the materialized path.

    Drives a multi-span fixture with an in-span score, a span-external
    score (collected via a utility span), and a scorers-span score through
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
    collection_source = _materialized_collection_source(materialized_tree)
    span_external = collect_span_external(collection_source, ["score"], depth=depth)

    materialized_numbering, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            materialized_tree.root,
            messages_as_str=materialized_numbering,
            model="mockllm/model",
            events=["score"],
            span_external=span_external,
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


@pytest.mark.anyio
async def test_stream_timeline_messages_events_none_unchanged() -> None:
    """``events=None`` on the streaming path is byte-identical to before.

    Regression guard: adding the ``events`` parameter must not perturb the
    default (``events=None``) streaming behavior already covered by
    ``test_stream_equals_materialized_segments`` in
    ``test_timeline_stream.py``.
    """
    events = _agentic_events_with_scores()
    transcript = agentic_transcript(events=events)

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(
        load, TranscriptInfo(transcript_id=transcript.transcript_id)
    )

    numbering, _ = message_numbering()
    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle, messages_as_str=numbering, model="mockllm/model"
        )
    ]

    materialized_tree = timeline_build(events)
    numbering2, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            materialized_tree.root, messages_as_str=numbering2, model="mockllm/model"
        )
    ]

    assert streamed == materialized
    # Sanity: the score events truly are not interleaved when events=None.
    assert not any("SCORE" in text for _, text in streamed)


@pytest.mark.anyio
async def test_stream_timeline_messages_events_uuidless_raises() -> None:
    """``_StubSkeletonUnsupported`` still raises with ``events`` set.

    Companion to ``test_selection_uuidless_raises``
    (``test_timeline_stream.py``): a needed ``ModelEvent`` lacking a uuid
    makes pass 1 fail regardless of ``events``, since events never add
    needed uuids (they don't contribute thread messages) and the raise
    happens in pass 1, before ``events``/``span_external`` are ever
    consulted.

    This stands in for extending the llm_scanner-level
    ``test_stub_unsupported_falls_back`` fallback test
    (``tests/llm_scanner/test_streaming.py``) with ``events=["score"]``:
    that test drives ``llm_scanner()``, whose routing does not yet thread
    an ``events`` argument into its ``stream_timeline_messages`` call (that
    wiring is Task 5), so passing ``events`` there today would not
    exercise this parameter at all. Testing directly against
    ``stream_timeline_messages`` instead proves the property Task 5's test
    will rely on: passing ``events`` cannot mask or change a
    ``_StubSkeletonUnsupported`` raise.
    """
    from inspect_scout._transcript.timeline_stream import _StubSkeletonUnsupported

    events = agentic_events()
    target = next(e for e in reversed(events) if isinstance(e, ModelEvent))
    events = [e.model_copy(update={"uuid": None}) if e is target else e for e in events]
    transcript = agentic_transcript(events=events)

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(
        load, TranscriptInfo(transcript_id=transcript.transcript_id)
    )

    with pytest.raises(_StubSkeletonUnsupported):
        [
            seg
            async for seg in stream_timeline_messages(
                handle,
                messages_as_str=message_numbering()[0],
                model="mockllm/model",
                events=["score"],
                compaction="last",
            )
        ]
