import re
from typing import AsyncIterator, cast

import pytest
from inspect_ai.event import (
    ErrorEvent,
    ModelEvent,
    ScoreEvent,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
)
from inspect_ai.event._event import Event
from inspect_ai.log import EvalError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import llm_scanner
from inspect_scout._llm_scanner.interleave import (
    EventsSpec,
    has_interleavable_events,
    interleave_events,
    stream_interleave_events,
)
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)

from tests.transcript.fixtures_agentic import agentic_transcript


def _handle_for(transcript: Transcript) -> MaterializedTranscriptHandle:
    async def load_fn() -> Transcript:
        return transcript

    info = TranscriptInfo(
        **transcript.model_dump(exclude={"messages", "events", "timelines"})
    )
    return MaterializedTranscriptHandle(load_fn, info)


def _model_event(user_text: str, output: ModelOutput) -> ModelEvent:
    return ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content=user_text)],
        output=output,
        role="assistant",
    )


def _span(span_id: str, name: str, content: list[Event | TimelineSpan]) -> TimelineSpan:
    """Build a scannable ``TimelineSpan`` from a mix of events and nested spans."""
    items: list[TimelineEvent | TimelineSpan] = [
        item
        if isinstance(item, TimelineSpan)
        else TimelineEvent.model_construct(type="event", event=item)
        for item in content
    ]
    return TimelineSpan(id=span_id, name=name, span_type="agent", content=items)


def test_final_score_anchored_after_last_assistant() -> None:
    out = ModelOutput.from_content(model="mockllm", content="4")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="2+2?")
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    result = interleave_events(transcript)
    assert [m.text for m in result[:2]] == [user.text, assistant.text]
    assert result[2].metadata is not None
    assert result[2].metadata[EVENT_MARKER_KEY] is True
    assert result[2].text.startswith("SCORE (match): value=C target=C")


def test_no_events_returns_messages_unchanged() -> None:
    user = ChatMessageUser(content="hi")
    transcript = Transcript(transcript_id="t", messages=[user], events=[])
    assert interleave_events(transcript) == [user]


def test_duplicate_message_ids_do_not_duplicate_events() -> None:
    # Two assistant turns with identical text and no explicit ids share the
    # same fallback _message_id (md5 of text). Each event must still splice
    # after its own turn, exactly once.
    out1 = ModelOutput.from_content(model="mockllm", content="yes")
    out2 = ModelOutput.from_content(model="mockllm", content="yes")
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    a1.id = None
    a2.id = None
    u1 = ChatMessageUser(content="q1", id="u1")
    u2 = ChatMessageUser(content="q2", id="u2")
    transcript = Transcript(
        transcript_id="t",
        messages=[u1, a1, u2, a2],
        events=[
            _model_event("q1", out1),
            ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True),
            _model_event("q2", out2),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    result = interleave_events(transcript)
    assert len(result) == 6
    assert result[2].text.startswith("SCORE (graded)")
    assert result[5].text.startswith("SCORE (match)")
    event_count = sum(
        1 for m in result if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    )
    assert event_count == 2


def test_events_only_transcript_reconstructs_thread() -> None:
    # An events-only load (e.g. content events="all", no messages) must
    # reconstruct the conversation from model events and splice events into
    # it — not emit floating event entries with no conversation.
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    result = interleave_events(transcript)
    assert [m.text for m in result[:2]] == ["2+2?", "4"]
    assert result[2].metadata is not None
    assert result[2].metadata[EVENT_MARKER_KEY] is True
    assert result[2].text.startswith("SCORE (match)")


def test_events_only_no_model_events_renders_leading() -> None:
    # No model events at all -> nothing to reconstruct; events still render
    # (leading) rather than being silently dropped.
    transcript = Transcript(
        transcript_id="t",
        messages=[],
        events=[ScoreEvent(score=Score(value="C"), scorer="match")],
    )
    result = interleave_events(transcript)
    assert len(result) == 1
    assert result[0].metadata is not None
    assert result[0].metadata[EVENT_MARKER_KEY] is True


def test_off_thread_model_event_renders_as_branch_entry() -> None:
    """A ModelEvent whose output is not in `transcript.messages` still renders.

    The second `_model_event("2+2?", fork_out)` produces a different output
    message than the one actually present in `transcript.messages` -- a
    fork/retry whose result was never joined to the final conversation.
    """
    out = ModelOutput.from_content(model="mockllm", content="4")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="2+2?")
    fork_out = ModelOutput.from_content(model="mockllm", content="forked answer")
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            _model_event("2+2?", out),
            _model_event("2+2?", fork_out),
        ],
    )
    result = interleave_events(transcript)
    assert len(result) == 3
    assert [m.text for m in result[:2]] == [user.text, assistant.text]
    assert result[2].metadata is not None
    assert result[2].metadata[EVENT_MARKER_KEY] is True
    assert "MODEL (BRANCH):" in result[2].text
    assert "forked answer" in result[2].text


def test_grader_model_event_in_scorers_span_excluded() -> None:
    """A grader ModelEvent inside a top-level `scorers` span never renders.

    Mirrors the timeline-path invariant
    (`test_scorers_span_score_event_attaches_to_last_scannable_span` in
    `test_timeline_interleave.py`) on the flat `interleave_events` driver:
    grader model calls must never surface as branch entries even though,
    unlike the per-span path, there is no structural span boundary to stop
    the walk -- `_scorers_model_event_ids` must exclude them explicitly.
    The scorer's own `ScoreEvent` is unaffected and still renders once.
    """
    out = ModelOutput.from_content(model="mockllm", content="4")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="2+2?")
    model_event = ModelEvent(
        span_id="span-main",
        model="mockllm",
        input=[user],
        output=out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    grader_out = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader_event = ModelEvent(
        span_id="span-scorers",
        model="mockllm",
        input=[ChatMessageUser(content="grade this")],
        output=grader_out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    score_event = ScoreEvent(
        span_id="span-scorers", scorer="match", score=Score(value="C")
    )
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            SpanBeginEvent(
                id="span-main",
                parent_id=None,
                type="agent",
                name="main",
                span_id="span-main",
            ),
            model_event,
            SpanEndEvent(id="span-main", span_id="span-main"),
            SpanBeginEvent(
                id="span-scorers",
                parent_id=None,
                type="scorers",
                name="scorers",
                span_id="span-scorers",
            ),
            grader_event,
            score_event,
            SpanEndEvent(id="span-scorers", span_id="span-scorers"),
        ],
    )
    result = interleave_events(transcript)
    event_texts = [
        m.text for m in result if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    ]
    assert sum("MODEL (BRANCH)" in t for t in event_texts) == 0
    assert "grader assessment" not in "\n".join(event_texts)
    assert sum(t.startswith("SCORE (match)") for t in event_texts) == 1


def test_has_interleavable_events() -> None:
    out = ModelOutput.from_content(model="mockllm", content="x")
    with_score = Transcript(
        transcript_id="t",
        messages=[out.choices[0].message],
        events=[ScoreEvent(score=Score(value=1), scorer="s")],
    )
    only_model = Transcript(
        transcript_id="t",
        messages=[out.choices[0].message],
        events=[_model_event("x", out)],
    )
    assert has_interleavable_events(with_score) is True
    assert has_interleavable_events(only_model) is False


def test_intermediate_event_anchored_mid_thread() -> None:
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    out2 = ModelOutput.from_content(model="mockllm", content="second")
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    u1, u2 = ChatMessageUser(content="q1"), ChatMessageUser(content="q2")
    transcript = Transcript(
        transcript_id="t",
        messages=[u1, a1, u2, a2],
        events=[
            _model_event("q1", out1),
            ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True),
            _model_event("q2", out2),
        ],
    )
    result = interleave_events(transcript)
    # The intermediate score splices after turn 1's assistant, before turn 2 —
    # not appended at the end.
    assert [result[0].text, result[1].text, result[3].text, result[4].text] == [
        u1.text,
        a1.text,
        u2.text,
        a2.text,
    ]
    assert result[2].metadata is not None
    assert result[2].metadata[EVENT_MARKER_KEY] is True
    assert result[2].text.startswith("SCORE (graded): value=0.5 intermediate")


def test_multiple_events_on_one_anchor_preserve_order() -> None:
    out = ModelOutput.from_content(model="mockllm", content="ans")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="q")
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            _model_event("q", out),
            ScoreEvent(score=Score(value="A"), scorer="first"),
            ScoreEvent(score=Score(value="B"), scorer="second"),
        ],
    )
    result = interleave_events(transcript)
    assert len(result) == 4
    assert result[2].text.startswith("SCORE (first)")
    assert result[3].text.startswith("SCORE (second)")


@pytest.mark.anyio
@pytest.mark.parametrize("events_spec", ["all", ["score"]])
async def test_stream_interleave_matches_materialized(
    events_spec: EventsSpec,
) -> None:
    # Duplicate id=None assistant turns exercise the position-based anchoring
    # through the streaming walk as well.
    out1 = ModelOutput.from_content(model="mockllm", content="yes")
    out2 = ModelOutput.from_content(model="mockllm", content="yes")
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    a1.id = None
    a2.id = None
    transcript = Transcript(
        transcript_id="t",
        messages=[
            ChatMessageUser(content="q1", id="u1"),
            a1,
            ChatMessageUser(content="q2", id="u2"),
            a2,
        ],
        events=[
            _model_event("q1", out1),
            ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True),
            _model_event("q2", out2),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
            ErrorEvent(
                error=EvalError(message="boom", traceback="", traceback_ansi="")
            ),
        ],
    )
    expected = interleave_events(transcript, events=events_spec)
    streamed = [
        m
        async for m in stream_interleave_events(
            _handle_for(transcript), events=events_spec
        )
    ]
    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]


@pytest.mark.anyio
async def test_stream_multi_agent_branch_entries_match_materialized() -> None:
    """Flat streaming messages-present path: two off-thread agents both surface.

    `transcript.messages` carries only agent A's on-thread conversation.
    Agent B contributes two entirely separate ``ModelEvent``s -- genuine
    forks, since their outputs never join ``transcript.messages`` at all
    (there is no compaction here, so this is unambiguously the fork case,
    not a compaction-pruned turn). The messages-present branch of
    ``stream_interleave_events`` streams full events with no stub
    skeleton, so both materialized ``interleave_events`` and the streaming
    driver must surface agent B's outputs as ``[E#] MODEL (BRANCH):``
    entries, and the two outputs must match exactly.
    """
    out_a = ModelOutput.from_content(model="mockllm", content="agent-a-answer")
    a = out_a.choices[0].message
    user_a = ChatMessageUser(content="agent-a-question")

    out_b1 = ModelOutput.from_content(model="mockllm", content="agent-b-answer-1")
    out_b2 = ModelOutput.from_content(model="mockllm", content="agent-b-answer-2")

    model_a = _model_event("agent-a-question", out_a)
    model_b1 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-b-question-1")],
        output=out_b1,
        role="assistant",
    )
    model_b2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-b-question-2")],
        output=out_b2,
        role="assistant",
    )

    transcript = Transcript(
        transcript_id="t",
        messages=[user_a, a],
        events=[model_a, model_b1, model_b2],
    )

    expected = interleave_events(transcript)
    streamed = [m async for m in stream_interleave_events(_handle_for(transcript))]

    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]

    event_texts = [
        m.text for m in streamed if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    ]
    assert sum("MODEL (BRANCH):" in t for t in event_texts) == 2
    combined = "\n".join(event_texts)
    assert "agent-b-answer-1" in combined
    assert "agent-b-answer-2" in combined


@pytest.mark.anyio
@pytest.mark.parametrize("compaction", ["all", "last"])
async def test_stream_interleave_events_only_matches_materialized(
    compaction: str,
) -> None:
    # Events-only transcript with two turns (second ModelEvent's input carries
    # the running thread) and a mid-thread + final score. The streaming
    # reconstruction must equal the materialized one under both compaction
    # modes.
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    out2 = ModelOutput.from_content(model="mockllm", content="second")
    ev1 = _model_event("q1", out1)
    ev2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[
            ChatMessageUser(content="q1"),
            out1.choices[0].message,
            ChatMessageUser(content="q2"),
        ],
        output=out2,
        role="assistant",
    )
    transcript = Transcript(
        transcript_id="t",
        messages=[],
        events=[
            ev1,
            ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True),
            ev2,
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    expected = interleave_events(transcript, compaction=compaction)  # type: ignore[arg-type]
    streamed = [
        m
        async for m in stream_interleave_events(
            _handle_for(transcript),
            compaction=compaction,  # type: ignore[arg-type]
        )
    ]
    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]
    # sanity: the reconstructed thread is present, and the final score last
    assert any(m.text == "second" for m in streamed)
    assert streamed[-1].text.startswith("SCORE (match)")


@pytest.mark.anyio
async def test_llm_scanner_events_only_scan_shows_thread_and_scores() -> None:
    # The transcript-tab shape: content events="all", no messages loaded.
    # The judge must see the ModelEvent-derived conversation AND the score.
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)
    assert re.search(r"\[M1\].*2\+2\?.*\[M2\].*\[E1\] SCORE", captured[0], re.DOTALL)


def _two_agent_flat_events() -> list[Event]:
    """Events-only, multi-agent flat event list (the Hawk "transcript tab" shape).

    Two parallel agent spans, each with a single distinctive ModelEvent, plus
    a root-level (span-external) score. Used by both the materialized and
    streaming multi-agent regression tests below.
    """
    out_a = ModelOutput.from_content(model="mockllm", content="agent-a-answer")
    out_b = ModelOutput.from_content(model="mockllm", content="agent-b-answer")
    model_a = ModelEvent(
        span_id="span-a",
        model="mockllm",
        input=[ChatMessageUser(content="agent-a-question")],
        output=out_a,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    model_b = ModelEvent(
        span_id="span-b",
        model="mockllm",
        input=[ChatMessageUser(content="agent-b-question")],
        output=out_b,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    return [
        SpanBeginEvent(
            id="span-a", parent_id=None, type="agent", name="agent-a", span_id="span-a"
        ),
        SpanBeginEvent(
            id="span-b", parent_id=None, type="agent", name="agent-b", span_id="span-b"
        ),
        model_a,
        model_b,
        SpanEndEvent(id="span-a", span_id="span-a"),
        SpanEndEvent(id="span-b", span_id="span-b"),
        ScoreEvent(scorer="match", score=Score(value="C")),
    ]


@pytest.mark.anyio
async def test_events_only_multi_agent_renders_all_agents() -> None:
    # Events-only transcript (messages=[], events present) with TWO parallel
    # agent spans. The flat interleave reconstruction (span_messages) keeps
    # only the region-last ModelEvent, so with multiple parallel agents only
    # the last agent's turn survives -- agent A's question is silently
    # dropped. The fix routes events-only transcripts through the timeline
    # machinery instead, which builds one segment per agent span, so both
    # agents (and the score) are visible across the captured prompts.
    transcript = Transcript(
        transcript_id="t", messages=[], events=_two_agent_flat_events()
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)

    combined = "\n".join(captured)
    assert "agent-a-question" in combined
    assert "agent-b-question" in combined
    assert "SCORE" in combined


def _spanless_two_agent_flat_events() -> list[Event]:
    """Events-only, multi-agent flat event list with NO span structure at all.

    Four interleaved ``ModelEvent``s (A1, B1, A2, B2, chronological) for two
    agents with no ``SpanBeginEvent``/``SpanEndEvent`` markers -- the
    "fork-heavy eval" repro shape: ``timeline_build`` wraps this into a
    single synthetic "main" span, and ``span_messages`` (with no
    ``CompactionEvent`` to bound regions) keeps only the region-last
    ``ModelEvent`` (B2) to derive the thread. B2's input carries B1's
    output (so agent B's exchange is on-thread), but neither of agent A's
    turns ever appear in B2's input -- both are off-thread.
    """
    out_a1 = ModelOutput.from_content(model="mockllm", content="agent-a-answer-1")
    out_b1 = ModelOutput.from_content(model="mockllm", content="agent-b-answer-1")
    a1 = out_a1.choices[0].message
    b1 = out_b1.choices[0].message
    out_a2 = ModelOutput.from_content(model="mockllm", content="agent-a-answer-2")
    out_b2 = ModelOutput.from_content(model="mockllm", content="agent-b-answer-2")

    model_a1 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-a-question-1")],
        output=out_a1,
        role="assistant",
    )
    model_b1 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-b-question-1")],
        output=out_b1,
        role="assistant",
    )
    model_a2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[
            ChatMessageUser(content="agent-a-question-1"),
            a1,
            ChatMessageUser(content="agent-a-question-2"),
        ],
        output=out_a2,
        role="assistant",
    )
    model_b2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[
            ChatMessageUser(content="agent-b-question-1"),
            b1,
            ChatMessageUser(content="agent-b-question-2"),
        ],
        output=out_b2,
        role="assistant",
    )
    return [
        model_a1,
        model_b1,
        model_a2,
        model_b2,
        ScoreEvent(scorer="match", score=Score(value="C")),
    ]


@pytest.mark.anyio
async def test_spanless_multi_agent_off_thread_agent_renders_via_branch_entries() -> (
    None
):
    # Minimal repro from the task background: a fork-heavy eval with no span
    # structure at all. Agent A's entire exchange is off-thread relative to
    # the region-last ModelEvent (agent B's second turn) that
    # `span_messages` uses to derive "the" thread. Before rendering
    # off-thread outputs as branch entries, agent A's content was silently
    # dropped entirely; now it surfaces via `[E#] MODEL (BRANCH):` entries.
    transcript = Transcript(
        transcript_id="t", messages=[], events=_spanless_two_agent_flat_events()
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)

    combined = "\n".join(captured)
    # Agent B's exchange is on-thread as ordinary turns.
    assert "agent-b-question-1" in combined
    assert "agent-b-answer-1" in combined
    assert "agent-b-question-2" in combined
    # Agent A's off-thread outputs now surface via branch entries.
    assert "MODEL (BRANCH):" in combined
    assert "agent-a-answer-1" in combined
    assert "agent-a-answer-2" in combined
    assert "SCORE" in combined


@pytest.mark.anyio
async def test_stream_events_only_multi_agent_renders_all_agents() -> None:
    # Streaming twin of the above: a handle with NO messages and events for
    # two parallel agents. Exercises the streaming flat-events branch's
    # probe (handle.messages() is empty) rerouting into
    # stream_timeline_messages instead of the flat stream_interleave_events
    # reconstruction. ModelEvents get an auto-generated uuid from the
    # regular constructor, so pass-2 substitution succeeds without
    # materializing -- load() must never be called.
    flat_events = _two_agent_flat_events()

    class _NoLoadHandle(MaterializedTranscriptHandle):
        async def messages(self, *, types: object = None) -> AsyncIterator[ChatMessage]:
            no_messages: tuple[ChatMessage, ...] = ()
            for message in no_messages:
                yield message

        async def events(self, *, types: object = None) -> AsyncIterator[Event]:
            for e in flat_events:
                yield e

        async def load(self) -> Transcript:
            raise AssertionError("streaming timeline interleave must not materialize")

    async def load_fn() -> Transcript:
        raise AssertionError("streaming timeline interleave must not materialize")

    handle = _NoLoadHandle(load_fn, TranscriptInfo(transcript_id="t"))

    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(cast(Transcript, handle))

    combined = "\n".join(captured)
    assert "agent-a-question" in combined
    assert "agent-b-question" in combined
    assert "SCORE" in combined


def _timeline_scorers_flat_events() -> list[Event]:
    """A "main" agent span plus a top-level "scorers" span with a grader call.

    Timeline-shaped (span-structured) flat events, distinct from
    `_two_agent_flat_events()`: exercises `stream_timeline_messages`'s
    per-span walk/prune, not the flat `interleave_events` reconstruction
    already covered by `test_grader_model_event_in_scorers_span_excluded`.
    Real `ModelEvent(...)` construction auto-generates a uuid, required for
    streaming pass-2 substitution.
    """
    out_main = ModelOutput.from_content(model="mockllm", content="answer")
    model_event = ModelEvent(
        span_id="span-main",
        model="mockllm",
        input=[ChatMessageUser(content="2+2?")],
        output=out_main,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    grader_out = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader_event = ModelEvent(
        span_id="span-scorers",
        model="mockllm",
        input=[ChatMessageUser(content="grade this")],
        output=grader_out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    score_event = ScoreEvent(
        span_id="span-scorers", scorer="match", score=Score(value="C")
    )
    return [
        SpanBeginEvent(
            id="solvers",
            parent_id=None,
            type="solvers",
            name="solvers",
            span_id="solvers",
        ),
        SpanBeginEvent(
            id="span-main",
            parent_id="solvers",
            type="agent",
            name="main",
            span_id="span-main",
        ),
        model_event,
        SpanEndEvent(id="span-main", span_id="span-main"),
        SpanEndEvent(id="solvers", span_id="solvers"),
        SpanBeginEvent(
            id="span-scorers",
            parent_id=None,
            type="scorers",
            name="scorers",
            span_id="span-scorers",
        ),
        grader_event,
        score_event,
        SpanEndEvent(id="span-scorers", span_id="span-scorers"),
    ]


@pytest.mark.anyio
async def test_stream_timeline_scorers_span_excluded_matches_materialized() -> None:
    """A scorers span's grader thread must be excluded on BOTH scan paths.

    Regression test for the streaming/materialized divergence:
    `stream_timeline_messages` never pruned `scorers` spans, so a
    handle-based (streaming) scan of this exact fixture saw the grader's
    "grader assessment" text in its judge prompt while a Transcript-based
    (materialized) scan of the same events did not -- answer/rubric
    leakage into the judge's context. Both paths must exclude the grader
    thread and render the scorer's own `ScoreEvent` exactly once.
    """
    flat_events = _timeline_scorers_flat_events()

    transcript = Transcript(transcript_id="t", messages=[], events=flat_events)
    captured_transcript: list[str] = []
    scan_t = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured_transcript),
        events=["score"],
    )
    await scan_t(transcript)

    class _NoLoadHandle(MaterializedTranscriptHandle):
        async def messages(self, *, types: object = None) -> AsyncIterator[ChatMessage]:
            no_messages: tuple[ChatMessage, ...] = ()
            for message in no_messages:
                yield message

        async def events(self, *, types: object = None) -> AsyncIterator[Event]:
            for e in flat_events:
                yield e

        async def load(self) -> Transcript:
            raise AssertionError("streaming timeline interleave must not materialize")

    async def load_fn() -> Transcript:
        raise AssertionError("streaming timeline interleave must not materialize")

    handle = _NoLoadHandle(load_fn, TranscriptInfo(transcript_id="t"))

    captured_handle: list[str] = []
    scan_h = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured_handle),
        events=["score"],
    )
    await scan_h(cast(Transcript, handle))

    for label, captured in (
        ("transcript", captured_transcript),
        ("handle", captured_handle),
    ):
        combined = "\n".join(captured)
        assert "grader assessment" not in combined, label
        assert "grade this" not in combined, label
        assert combined.count("SCORE (match)") == 1, label


@pytest.mark.anyio
async def test_stream_interleave_no_events_passthrough() -> None:
    transcript = Transcript(
        transcript_id="t", messages=[ChatMessageUser(content="hi", id="u1")], events=[]
    )
    streamed = [m async for m in stream_interleave_events(_handle_for(transcript))]
    assert [m.id for m in streamed] == ["u1"]


def test_interleave_filters_to_selected_event_types() -> None:
    out = ModelOutput.from_content(model="mockllm", content="ans")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q"), out.choices[0].message],
        events=[
            _model_event("q", out),
            ScoreEvent(score=Score(value="C"), scorer="match"),
            ErrorEvent(
                error=EvalError(message="boom", traceback="", traceback_ansi="")
            ),
        ],
    )
    result = interleave_events(transcript, events=["score"])
    event_texts = [
        m.text for m in result if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    ]
    assert len(event_texts) == 1
    assert event_texts[0].startswith("SCORE")


def _mock_model(captured: list[str]) -> Model:
    def _outputs(
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        captured.append(input[0].text)
        return ModelOutput.from_content(model="mockllm", content="ok\n\nANSWER: yes")

    return get_model("mockllm/model", custom_outputs=_outputs)


@pytest.mark.anyio
async def test_llm_scanner_interleaves_score() -> None:
    out = ModelOutput.from_content(model="mockllm", content="4")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="2+2?")
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)
    # Structural check only: the event renders as [E1] after both turns.
    # Exact renderer formatting is pinned by tests/transcript/test_event_text.py.
    assert re.search(r"\[M1\].*\[M2\].*\[E1\] SCORE", captured[0], re.DOTALL)


@pytest.mark.anyio
async def test_loaded_events_without_events_param_not_interleaved() -> None:
    # Loading events via content= (e.g. for template_variables use) must not
    # change the rendered prompt; interleaving requires the events= parameter.
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="2+2?"), out.choices[0].message],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        content=TranscriptContent(events=["score", "model"]),
    )
    await scan(transcript)
    assert "[E1]" not in captured[0]
    assert "SCORE" not in captured[0]


@pytest.mark.anyio
async def test_llm_scanner_no_events_has_no_event_entries() -> None:
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="2+2?"), out.choices[0].message],
        events=[],
    )
    captured: list[str] = []
    scan = llm_scanner(question="Right?", answer="boolean", model=_mock_model(captured))
    await scan(transcript)
    assert "[E1]" not in captured[0]


@pytest.mark.anyio
async def test_llm_scanner_handle_scan_interleaves_without_load() -> None:
    # A handle input with events= streams: same prompt as the Transcript
    # input, and load() (full materialization) is never called. Uses a stub
    # handle that raises on load() — MaterializedTranscriptHandle can't
    # prove this since its messages()/events() call load() internally.
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="2+2?"), out.choices[0].message],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )

    # Subclass (scan() narrows on the concrete handle classes): iteration
    # reads the transcript directly; load() — full materialization — raises.
    class _NoLoadHandle(MaterializedTranscriptHandle):
        async def messages(self, *, types: object = None) -> AsyncIterator[ChatMessage]:
            for m in transcript.messages:
                yield m

        async def events(self, *, types: object = None) -> AsyncIterator[Event]:
            for e in transcript.events:
                if types is None or e.event in cast(list[str], types):
                    yield e

        async def load(self) -> Transcript:
            raise AssertionError("streaming interleave must not materialize")

    async def load_fn() -> Transcript:
        return transcript

    handle = _NoLoadHandle(
        load_fn,
        TranscriptInfo(
            **transcript.model_dump(exclude={"messages", "events", "timelines"})
        ),
    )

    captured_handle: list[str] = []
    captured_transcript: list[str] = []

    scan_h = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured_handle),
        events=["score"],
    )
    await scan_h(cast(Transcript, handle))

    scan_t = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured_transcript),
        events=["score"],
    )
    await scan_t(transcript)

    assert captured_handle == captured_transcript
    assert "[E1] SCORE" in captured_handle[0]


def test_events_param_opts_in_to_streaming() -> None:
    from inspect_scout._scanner.scanner import SCANNER_SUPPORTS_STREAMING_ATTR

    scan = llm_scanner(question="q", answer="boolean", events=["score"])
    assert getattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, False) is True


def test_events_param_loads_selected_and_model_events() -> None:
    scan = llm_scanner(question="q", answer="boolean", events=["score"])
    content = getattr(scan, SCANNER_CONTENT_ATTR)
    assert set(content.events) == {"score", "model"}


def test_events_param_merges_with_content_events() -> None:
    scan = llm_scanner(
        question="q",
        answer="boolean",
        events=["score"],
        content=TranscriptContent(events=["error"]),
    )
    content = getattr(scan, SCANNER_CONTENT_ATTR)
    assert set(content.events) == {"score", "error", "model"}


def test_events_all_loads_all_events() -> None:
    scan = llm_scanner(question="q", answer="boolean", events="all")
    content = getattr(scan, SCANNER_CONTENT_ATTR)
    assert content.events == "all"


@pytest.mark.anyio
async def test_interleave_with_timeline_renders_per_span() -> None:
    # Timeline-shaped transcript + events= must no longer raise: each span's
    # own events render in that span's own thread, and the resultset shape
    # matches an events=None run over the same transcript.
    out_a = ModelOutput.from_content(model="mockllm", content="4")
    out_b = ModelOutput.from_content(model="mockllm", content="9")
    span_a = _span(
        "span-a",
        "agent-a",
        [
            _model_event("2+2?", out_a),
            ScoreEvent(score=Score(value="C"), scorer="match"),
        ],
    )
    span_b = _span("span-b", "agent-b", [_model_event("3+3?", out_b)])
    root = TimelineSpan(
        id="root", name="Transcript", span_type=None, content=[span_a, span_b]
    )
    transcript = Transcript(
        transcript_id="t",
        timelines=[Timeline(name="Default", description="", root=root)],
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="q", answer="boolean", model=_mock_model(captured), events=["score"]
    )
    result = await scan(transcript)

    assert any("2+2?" in c for c in captured)
    assert any("3+3?" in c for c in captured)
    assert sum("[E1] SCORE" in c for c in captured) == 1

    captured_no_events: list[str] = []
    scan_no_events = llm_scanner(
        question="q", answer="boolean", model=_mock_model(captured_no_events)
    )
    result_no_events = await scan_no_events(transcript)

    assert isinstance(result, Result)
    assert isinstance(result_no_events, Result)
    assert result.type == result_no_events.type == "resultset"
    assert isinstance(result.value, list)
    assert isinstance(result_no_events.value, list)
    assert len(result.value) == len(result_no_events.value) == 2


@pytest.mark.anyio
async def test_llm_scanner_handle_events_content_interleaves_without_load() -> None:
    # The transcript-tab-with-spans shape on a handle: content requests
    # events="all" (timeline-shaped streaming) and events=["score"] asks for
    # per-span score interleaving. Conversation and score must both render,
    # and load() (full materialization) must never be called.
    out = ModelOutput.from_content(model="mockllm", content="4")
    model_event = ModelEvent(
        span_id="main",
        model="mockllm",
        input=[ChatMessageUser(content="2+2?")],
        output=out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    score_event = ScoreEvent(span_id="main", scorer="match", score=Score(value="C"))
    flat_events: list[Event] = [
        SpanBeginEvent(
            id="main", parent_id=None, type="agent", name="main", span_id="main"
        ),
        model_event,
        score_event,
        SpanEndEvent(id="main", span_id="main"),
    ]

    class _NoLoadHandle(MaterializedTranscriptHandle):
        async def events(self, *, types: object = None) -> AsyncIterator[Event]:
            for e in flat_events:
                yield e

        async def load(self) -> Transcript:
            raise AssertionError("streaming timeline interleave must not materialize")

    async def load_fn() -> Transcript:
        raise AssertionError("streaming timeline interleave must not materialize")

    handle = _NoLoadHandle(load_fn, TranscriptInfo(transcript_id="t"))

    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        content=TranscriptContent(events="all"),
        events=["score"],
    )
    await scan(cast(Transcript, handle))

    assert any("2+2?" in c for c in captured)
    assert any("[E1] SCORE" in c for c in captured)


@pytest.mark.anyio
async def test_interleave_with_timeline_depth_limit_attaches_to_parent() -> None:
    # A nested scannable child span beyond `depth` is not walked as its own
    # segment; its events are span-external, attached to the last span that
    # IS within the depth limit (its parent), and render exactly once each.
    # The child's ModelEvent has no thread of its own to be "on" (the span
    # is never walked, so `span_interleaved_messages` never splices it) --
    # it renders as a `MODEL (BRANCH)` entry, ahead of the child's
    # ScoreEvent, matching document order.
    out_parent = ModelOutput.from_content(model="mockllm", content="parent-ans")
    out_child = ModelOutput.from_content(model="mockllm", content="child-ans")
    child = _span(
        "child",
        "child-agent",
        [
            _model_event("child-q", out_child),
            ScoreEvent(score=Score(value="C"), scorer="childscore"),
        ],
    )
    parent = _span(
        "parent", "parent-agent", [_model_event("parent-q", out_parent), child]
    )
    root = TimelineSpan(id="root", name="Transcript", span_type=None, content=[parent])
    transcript = Transcript(
        transcript_id="t",
        timelines=[Timeline(name="Default", description="", root=root)],
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="q",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
        depth=1,
    )
    await scan(transcript)

    # Only the parent is walked as its own segment -- the child (depth 2)
    # never gets its own scan.
    assert len(captured) == 1
    assert "parent-q" in captured[0]
    assert "child-q" not in captured[0]
    assert captured[0].count("[E1] MODEL (BRANCH):\nchild-ans") == 1
    assert captured[0].count("[E2] SCORE (childscore)") == 1


@pytest.mark.anyio
async def test_agentic_transcript_utility_span_fork_model_events_visible() -> None:
    """End-to-end regression: a utility span's off-thread ModelEvent outputs are no longer silently dropped.

    Before this fix, `_collect_span_external` routed every event --
    including `ModelEvent`s -- through `_interleavable_text`, which hard-
    excludes "model"; a utility span's `ModelEvent`s (no thread of their
    own, since the span is never scanned) vanished entirely, never
    appearing in any prompt.

    Uses the shared `agentic_transcript()` fixture's "sub" utility span
    (two `ModelEvent`s, outputs "sub-output-1"/"sub-output-2"): a
    single-turn, foreign-prompt span classified utility by
    `timeline_build`, nested under "main". With `events="all"`, both
    outputs must now render as `MODEL (BRANCH)` entries attached to
    "main" -- the last scannable span reached before "sub".
    """
    transcript = agentic_transcript()
    captured: list[str] = []
    scan = llm_scanner(
        question="q", answer="boolean", model=_mock_model(captured), events="all"
    )
    await scan(transcript)

    combined = "\n".join(captured)
    assert combined.count("sub-output-1") == 1
    assert combined.count("sub-output-2") == 1
    main_prompt = next(c for c in captured if "main-output-1" in c)
    assert "sub-output-1" in main_prompt
    assert "sub-output-2" in main_prompt


@pytest.mark.anyio
async def test_final_score_lands_in_last_chunk_when_split() -> None:
    long_text = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do " * 5
    out1 = ModelOutput.from_content(
        model="mockllm", content=f"{long_text} first answer"
    )
    out2 = ModelOutput.from_content(
        model="mockllm", content=f"{long_text} second answer"
    )
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    u1, u2 = (
        ChatMessageUser(content=f"{long_text} q1"),
        ChatMessageUser(content=f"{long_text} q2"),
    )
    transcript = Transcript(
        transcript_id="t",
        messages=[u1, a1, u2, a2],
        events=[
            _model_event(u1.text, out1),
            _model_event(u2.text, out2),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    # Each turn is ~55 tokens (tiktoken o200k on the repeated lorem text), so
    # the four turns plus the score exceed one segment's budget at window=350
    # (~330 after the safety margin, minus ~180 template overhead) but fit in
    # two. Verified stable for windows 300-425; len(captured) >= 2 below fails
    # loudly if tokenization or template overhead ever shifts the boundary.
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        context_window=350,
        events=["score"],
    )
    await scan(transcript)
    assert len(captured) >= 2
    assert sum("[E1] SCORE" in c for c in captured) == 1
    assert "[E1] SCORE" in captured[-1]


def test_interleave_primitives_shared_with_transcript() -> None:
    from inspect_scout._llm_scanner import interleave as scanner_mod
    from inspect_scout._transcript import interleave as transcript_mod

    assert scanner_mod._AnchorWalk is transcript_mod._AnchorWalk
    assert scanner_mod.EventsSpec is transcript_mod.EventsSpec
