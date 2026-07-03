"""Tests for per-span event interleaving in ``timeline_messages``."""

from __future__ import annotations

import re

import pytest
from inspect_ai.event import (
    CompactionEvent,
    ErrorEvent,
    Event,
    ModelEvent,
    ScoreEvent,
    TimelineEvent,
    TimelineSpan,
)
from inspect_ai.log import EvalError
from inspect_ai.model import ChatMessage, ChatMessageUser, ModelOutput, get_model
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.messages import segment_messages
from inspect_scout._transcript.timeline import TimelineMessages, timeline_messages

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
    """compaction='last': an event anchored to a compacted-away turn leads."""
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
