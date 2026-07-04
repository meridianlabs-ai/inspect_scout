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
    ChatMessageSystem,
    ChatMessageUser,
    ContentReasoning,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.interleave import collect_span_external
from inspect_scout._transcript.messages import segment_messages, transcript_messages
from inspect_scout._transcript.timeline import TimelineMessages, timeline_messages
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
    depth: int | None = None,
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
        depth=depth,
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


@pytest.mark.anyio
async def test_grader_model_event_in_scorers_span_never_renders_as_branch() -> None:
    """A ``scorers`` span's grader ModelEvent is excluded even under the new always-render-ModelEvents behavior of ``_collect_span_external``.

    Fix B makes every off-thread/location-excluded ModelEvent render as a
    ``MODEL (BRANCH)`` entry -- except a ``scorers`` span's grader
    ModelEvent, which must remain excluded (``span_in_scorers`` short-
    circuits it before ``_off_thread_model_text`` is ever called). This
    pins that guard directly against the new branch, independent of
    ``test_scorers_span_score_event_attaches_to_last_scannable_span``
    (which exercises the same guard incidentally, via the default
    ``include_scorers=False`` pruning path).
    """
    out_a = ModelOutput.from_content(model="mockllm", content="answer-a")
    span_a = _span_of(
        "span-a", "agent-a", [_model_event([ChatMessageUser(content="qa")], out_a)]
    )
    grader_out = ModelOutput.from_content(model="mockllm", content="grader verdict")
    grader_event = _model_event([ChatMessageUser(content="grade this")], grader_out)
    score = ScoreEvent(score=Score(value=1), scorer="match")
    scorers_span = _span_of(
        "span-scorers", "scorers", [grader_event, score], span_type="scorers"
    )
    root = _span_of("root", "root", [span_a, scorers_span], span_type=None)

    external = collect_span_external(root, ["score"], depth=None)

    rendered = [text for entries in external.values() for _, text in entries]
    assert not any("grader verdict" in text for text in rendered)
    assert not any("MODEL (BRANCH)" in text for text in rendered)
    assert any("SCORE (match)" in text for text in rendered)


@pytest.mark.anyio
async def test_depth_excluded_scannable_span_model_output_renders_after_parent() -> (
    None
):
    """A depth-excluded but structurally scannable span's own ModelEvent renders as a branch entry after the parent.

    The event is an on-thread turn, had the span been walked, and renders
    as a ``MODEL (BRANCH)`` entry after the parent, exactly like every
    other event type already excluded by ``depth`` -- there is no splice
    reconstructing the child's thread for it to be "on".
    """
    out_parent = ModelOutput.from_content(model="mockllm", content="parent-answer")
    out_child = ModelOutput.from_content(model="mockllm", content="child-answer")
    child = _span_of(
        "child",
        "child-agent",
        [_model_event([ChatMessageUser(content="child-q")], out_child)],
    )
    parent = _span_of(
        "parent",
        "parent-agent",
        [_model_event([ChatMessageUser(content="parent-q")], out_parent), child],
    )
    root = _span_of("root", "root", [parent], span_type=None)

    results, combined = await _collect_transcript(root, events=[], depth=1)

    assert len(results) == 1
    assert results[0].span.id == "parent"
    assert re.search(
        r"parent-answer.*\[E1\] MODEL \(BRANCH\):\nchild-answer",
        combined,
        re.DOTALL,
    )


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
    via `_collect_span_external`'s ModelEvent branch as `MODEL (BRANCH)`
    entries attached to its parent. The streaming path already recurses
    into `ToolEvent.events` for both full- and off-thread-event
    substitution (`_collect_pass2_model_events`, `timeline_stream.py`), so
    no changes were needed there either.
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
    # pre-existing `_AnchorWalk` off-thread/fork detection (Fix A) would
    # itself classify main-1 as a fork, independent of anything under test
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
    span_external = collect_span_external(materialized_tree, "all", depth=1)
    materialized_numbering, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            materialized_tree.root,
            messages_as_str=materialized_numbering,
            model="mockllm/model",
            events="all",
            span_external=span_external,
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
      top-level sibling of "solvers"): under the default
      ``include_scorers=False``, this span is pruned from the walked tree
      entirely, so the grader ``ModelEvent`` never renders and the
      ``ScoreEvent`` instead surfaces via external collection from the
      unpruned tree, attributed to the last span actually walked ("main").

    Also inserts a genuine off-thread fork ``ModelEvent`` ("fork-1") into
    "main", immediately before its closing turn, so streaming/materialized
    parity coverage genuinely exercises a ``[E#] MODEL (BRANCH):`` entry
    rather than relying on incidental non-cumulative fixture inputs.

    Also exercises (unmodified, via plain ``agentic_events()``) the "sub"
    utility span's two ``ModelEvent``s ("sub-1"/"sub-2", outputs
    "sub-output-1"/"sub-output-2"): a utility span is never scannable, so
    these are span-external ModelEvents with no thread of their own,
    landing squarely in ``_collect_span_external``'s ModelEvent branch (the
    bug this fixture-level parity test was extended to cover). They render
    as ``MODEL (BRANCH)`` entries attributed to "main" -- the last
    scannable span reached before "sub" -- rather than being silently
    dropped as they were before that fix.
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


def _materialized_walk_tree(tree: Timeline) -> Timeline:
    """Mirror ``stream_timeline_messages``' default (``include_scorers=False``) walk tree.

    ``scorers`` spans are pruned from the tree that gets walked, matching
    ``transcript_messages``' default: a ``scorers`` span's own events (e.g.
    a grader ``ModelEvent``) never enter any span's message thread. The
    UNPRUNED ``tree`` remains the events collection source (passed directly
    to ``collect_span_external`` by callers), so a pruned ``scorers``
    span's non-``ModelEvent`` events (e.g. its final ``ScoreEvent``) still
    surface externally instead of being silently dropped.
    """
    return timeline_filter(tree, lambda s: s.span_type != "scorers")


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

    # `stream_timeline_messages`' default (`include_scorers=False`) prunes
    # `scorers` spans from the walked tree but collects events from the
    # UNPRUNED tree; mirror both sides here.
    materialized_tree = timeline_build(events)
    span_external = collect_span_external(materialized_tree, ["score"], depth=depth)

    materialized_numbering, _ = message_numbering()
    materialized = [
        (seg.span.id, seg.messages_str)
        async for seg in timeline_messages(
            _materialized_walk_tree(materialized_tree).root,
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
    # The "sub" utility span's two ModelEvents are non-scannable,
    # off-thread-by-location events with no thread of their own -- they
    # must render as branch entries attached to "main" (the fix under
    # test), not be silently dropped.
    assert combined.count("sub-output-1") == 1
    assert combined.count("sub-output-2") == 1
    main_text = next(text for span_id, text in streamed if span_id == "main")
    assert "sub-output-1" in main_text
    assert "sub-output-2" in main_text
    # The scorers span's grader ModelEvent is pruned from the walk (default
    # include_scorers=False); its own ScoreEvent still surfaces exactly
    # once via external collection.
    assert "grader-output" not in combined
    assert combined.count("SCORE (graded)") == 1


def _cumulative_compaction_events() -> list[Event]:
    """A single "main" span with genuinely CUMULATIVE, multi-region compaction.

    - Region 1: turn "t1" (fresh input), then turn "t2" whose input is
      cumulative -- it literally embeds "t1"'s own output message object
      (``[System, user1, assistant1, user2]``), mirroring how a real
      transcript's ``ModelEvent.input`` grows turn over turn. "t2" is
      region 1's last event.
    - A ``CompactionEvent(type="summary")`` boundary.
    - Region 2: turn "t3" alone (fresh input).
    - A second ``CompactionEvent(type="summary")`` boundary.
    - Region 3: a genuine off-thread fork ("fork", fresh, unrelated input)
      whose output never joins ANY reconstructed thread (it is not any
      region's last event), then turn "t4" (fresh input) -- region 3's
      (and the whole span's) last event.
    - A trailing in-span ``ScoreEvent``.

    Reproduces the streaming compaction-discriminator bug: under
    ``compaction in ("last", 2)``, region 1 is pruned from the actual kept
    thread, but ``span_interleaved_messages``' ``excluded_ids`` can only
    recover "t1"'s output through "t2"'s cumulative input -- so "t2" must
    be retained in full (not output-only) by the streaming path for the
    discriminator to classify "t1" as compaction-pruned rather than a
    genuine fork.
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
@pytest.mark.parametrize("compaction", ["last", 2, "all"])
async def test_stream_timeline_messages_cumulative_compaction_discriminator_parity(
    compaction: Literal["all", "last"] | int,
) -> None:
    """Cumulative region-last inputs must not corrupt the streaming discriminator.

    Regression test for the bug where pass 2 substituted only the ACTUAL
    compaction's ``needed`` ModelEvents in full, leaving every other
    region's last ModelEvent output-only (``input=[]``). Because
    ``span_interleaved_messages`` computes ``excluded_ids`` by
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


@pytest.mark.anyio
async def test_stream_timeline_messages_events_none_unchanged() -> None:
    """``events=None`` on the streaming path prunes `scorers` spans like the materialized path.

    Regression guard: adding the ``events`` parameter must not perturb the
    default (``events=None``) streaming behavior already covered by
    ``test_stream_equals_materialized_segments`` in
    ``test_timeline_stream.py``, and the ``include_scorers=False`` default
    (unconditional, regardless of ``events``) must still match
    ``transcript_messages``' pruning of ``scorers`` spans.
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
            _materialized_walk_tree(materialized_tree).root,
            messages_as_str=numbering2,
            model="mockllm/model",
        )
    ]

    assert streamed == materialized
    # Sanity: the score events truly are not interleaved when events=None.
    assert not any("SCORE" in text for _, text in streamed)
    # The scorers span (and its grader ModelEvent) is pruned by default.
    combined = "\n".join(text for _, text in streamed)
    assert "grader-output" not in combined


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
