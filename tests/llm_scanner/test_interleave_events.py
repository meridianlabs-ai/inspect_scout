from typing import AsyncIterator, Callable, Iterable, NoReturn, TypeVar, cast

import pytest
from inspect_ai.event import (
    BranchEvent,
    CompactionEvent,
    ErrorEvent,
    Event,
    ModelEvent,
    ScoreEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
    timeline_build,
)
from inspect_ai.log import EvalError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import llm_scanner
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
)
from inspect_scout._transcript.interleave import (
    INTERLEAVE_DEPENDENCIES,
    EventsOnlyInterleaveUnsupported,
    EventsSpec,
    interleave_events,
    span_owned_messages,
    stream_interleave_events,
)
from inspect_scout._transcript.json.stream_parse import StreamParseResult
from inspect_scout._transcript.timeline import walk_owned_spans
from inspect_scout._transcript.types import (
    EventType,
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from inspect_scout._util._async import aclosing_iter


def _model_event(user_text: str, output: ModelOutput) -> ModelEvent:
    return ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content=user_text)],
        output=output,
        role="assistant",
        config=GenerateConfig(),
    )


def _span_model_event(question: str, answer: str, span_id: str) -> ModelEvent:
    out = ModelOutput.from_content(model="mockllm", content=answer)
    return ModelEvent(
        span_id=span_id,
        model="mockllm",
        input=[ChatMessageUser(content=question)],
        output=out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )


def _event_texts(messages: Iterable[ChatMessage]) -> list[str]:
    return [m.text for m in messages if m.metadata and m.metadata.get(EVENT_MARKER_KEY)]


def _selectively_loaded(events: list[Event]) -> list[Event]:
    """``events`` as ``llm_scanner(events=["score"])`` would load them."""
    scan = llm_scanner(question="q", answer="boolean", events=["score"])
    loaded = getattr(scan, SCANNER_CONTENT_ATTR).events
    return [e for e in events if e.event in loaded]


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


def _compaction_pruned_and_fork_transcript() -> Transcript:
    """Messages-present transcript with a compaction-pruned turn and a genuine fork.

    ``ev1``'s output is in the untruncated ``compaction="all"`` thread but not in
    ``transcript.messages``: compaction pruned it, so it must stay hidden.
    ``fork_ev``'s output never joins any thread, so it renders as a branch entry.
    """
    ev1 = _model_event("q1", ModelOutput.from_content(model="mockllm", content="first"))
    fork_ev = _model_event(
        "q1", ModelOutput.from_content(model="mockllm", content="forked")
    )
    out2 = ModelOutput.from_content(model="mockllm", content="second")
    return Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q2"), out2.choices[0].message],
        events=[
            ev1,
            CompactionEvent(type="summary"),
            fork_ev,
            _model_event("q2", out2),
        ],
    )


def test_selective_load_keeps_compaction_pruned_turn_hidden() -> None:
    """A selectively loaded, messages-present transcript keeps pruned turns hidden.

    Without ``compaction`` loaded, or without exclusions computed on this path,
    the pruned turn resurfaces as a ``MODEL (BRANCH)`` entry.
    """
    transcript = _compaction_pruned_and_fork_transcript()
    filtered = transcript.model_copy(
        update={"events": _selectively_loaded(transcript.events)}
    )
    assert [m.text for m in interleave_events(filtered, events=["score"])] == [
        "MODEL (BRANCH):\nforked\n",
        "q2",
        "second",
    ]


def _spanless_two_agent_flat_events() -> list[Event]:
    """Two agents' interleaved turns (A1, B1, A2, B2) with no span markers.

    The thread is derived from the last ModelEvent (B2), so both of agent A's
    turns are off-thread.
    """

    def turn(input: list[ChatMessage], answer: str) -> ModelEvent:
        return ModelEvent.model_construct(
            event="model",
            model="mockllm",
            input=input,
            output=ModelOutput.from_content(model="mockllm", content=answer),
            role="assistant",
            config=GenerateConfig(),
        )

    qa1 = ChatMessageUser(content="agent-a-question-1")
    qb1 = ChatMessageUser(content="agent-b-question-1")
    a1 = turn([qa1], "agent-a-answer-1")
    b1 = turn([qb1], "agent-b-answer-1")
    a2 = turn(
        [qa1, a1.output.message, ChatMessageUser(content="agent-a-question-2")],
        "agent-a-answer-2",
    )
    b2 = turn(
        [qb1, b1.output.message, ChatMessageUser(content="agent-b-question-2")],
        "agent-b-answer-2",
    )
    return [a1, b1, a2, b2, ScoreEvent(scorer="match", score=Score(value="C"))]


@pytest.mark.anyio
async def test_spanless_multi_agent_off_thread_agent_renders_via_branch_entries() -> (
    None
):
    """Events-only multi-agent scan: the off-thread agent surfaces as branch entries."""
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
    assert "agent-b-question-1" in combined
    assert "agent-b-answer-1" in combined
    assert "agent-b-question-2" in combined
    assert "MODEL (BRANCH):" in combined
    assert "agent-a-answer-1" in combined
    assert "agent-a-answer-2" in combined
    assert "SCORE" in combined


def test_interleave_filters_to_selected_event_types() -> None:
    """``_interleavable_text`` defaults to ``"all"``, so a dropped selection still type-checks."""
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
    event_texts = _event_texts(interleave_events(transcript, events=["score"]))
    assert len(event_texts) == 1
    assert event_texts[0].startswith("SCORE")


@pytest.mark.anyio
async def test_loaded_events_without_events_param_not_interleaved() -> None:
    # Loading events via content= (e.g. for template_variables) must not change
    # the prompt; only the events= parameter interleaves.
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


@pytest.mark.parametrize(
    ("events", "content_events", "expected"),
    [
        pytest.param(
            ["score"],
            ["error"],
            {"score", "error", *INTERLEAVE_DEPENDENCIES},
            id="selected-plus-content-plus-dependencies",
        ),
        pytest.param("all", None, "all", id="all"),
    ],
)
def test_events_param_extends_loaded_events(
    events: EventsSpec,
    content_events: list[EventType] | None,
    expected: set[str] | str,
) -> None:
    content = TranscriptContent(
        messages=["user"], events=content_events, timeline=["model"], metadata=False
    )
    scan = llm_scanner(question="q", answer="boolean", events=events, content=content)
    loaded = getattr(scan, SCANNER_CONTENT_ATTR)
    assert (loaded.events if loaded.events == "all" else set(loaded.events)) == expected
    assert (loaded.messages, loaded.timeline, loaded.metadata) == (
        ["user"],
        ["model"],
        False,
    )


def test_selective_load_preserves_branch_structure() -> None:
    """A selective ``events=`` load must not flatten branch spans into the thread.

    ``timeline_build`` only forms a ``TimelineSpan.branches`` entry when it
    finds a ``BranchEvent`` among the span's children. Filter ``BranchEvent``
    out and the branch's conversation is unrolled into its parent, so the
    scanner reads the branch as the main thread and demotes the real answer
    to a ``MODEL (BRANCH)`` entry.
    """
    events: list[Event] = [
        SpanBeginEvent(
            id="main", parent_id=None, type="agent", name="main", span_id="main"
        ),
        _span_model_event("main q", "MAIN ANSWER", "main"),
        SpanBeginEvent(
            id="br", parent_id="main", type="branch", name="br", span_id="br"
        ),
        BranchEvent(span_id="br"),
        _span_model_event("branch q", "BRANCH ONLY", "br"),
        SpanEndEvent(id="br", span_id="br"),
        SpanEndEvent(id="main", span_id="main"),
    ]

    owned = next(walk_owned_spans(timeline_build(_selectively_loaded(events)).root))
    thread = span_owned_messages(owned, events=[], compaction="all")
    assert [m.text for m in thread] == [
        "main q",
        "MAIN ANSWER",
        "MODEL (BRANCH):\nBRANCH ONLY\n",
    ]
    assert len(owned.branches) == 1


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
    # At window=350 the four ~55-token turns plus the score need two segments
    # (stable for windows 300-425); the len check fails loudly if tokenization
    # or template overhead shifts the boundary.
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


def test_selective_load_preserves_nested_tool_agent_models() -> None:
    """``tool`` never renders, but loading it keeps the sub-agent models nested in it."""
    tool_event = ToolEvent(
        span_id="span-main",
        id="call-1",
        function="delegate",
        arguments={},
        result="done",
        events=[_span_model_event("sub q", "SUB ANSWER", "span-main")],
    )
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q"), ChatMessageAssistant(content="a")],
        events=_selectively_loaded([tool_event]),
    )
    entries = _event_texts(interleave_events(transcript, ["score"]))
    assert any("SUB ANSWER" in text for text in entries)


def test_legacy_raw_dict_subevents_are_skipped_not_crashed() -> None:
    """Legacy raw-dict ``ToolEvent.events`` entries (unvalidated upstream) are skipped."""
    tool_event = ToolEvent.model_validate(
        {
            "event": "tool",
            "id": "call-1",
            "function": "f",
            "arguments": {},
            "result": "ok",
            "events": [{"event": "info", "data": "legacy"}],
        }
    )
    assert isinstance(tool_event.events[0], dict), "fixture must reproduce the raw dict"

    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q")],
        events=[tool_event],
    )

    assert [m.text for m in interleave_events(transcript, "all")] == ["q"]


# Streaming drivers: stream_interleave_events and stream_timeline_messages(events=...)


def _handle_for(transcript: Transcript) -> MaterializedTranscriptHandle:
    async def load_fn() -> Transcript:
        return transcript

    info = TranscriptInfo(
        **transcript.model_dump(exclude={"messages", "events", "timelines"})
    )
    return MaterializedTranscriptHandle(load_fn, info)


def _scorers_span_transcript() -> Transcript:
    """Transcript whose grader model call sits in a top-level `scorers` span."""
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
    return transcript


@pytest.mark.anyio
async def test_events_only_transcripts_are_rejected_by_the_streaming_flat_driver() -> (
    None
):
    out = ModelOutput.from_content(model="mockllm", content="a1")
    events_only = Transcript(
        transcript_id="t", messages=[], events=[_model_event("q1", out)]
    )
    with pytest.raises(EventsOnlyInterleaveUnsupported):
        async for _ in stream_interleave_events(_handle_for(events_only), "all"):
            pass


@pytest.mark.anyio
async def test_stream_messages_present_hides_compaction_pruned_turn() -> None:
    """Streaming hides a compaction-pruned turn and shows a fork, as materialized.

    Same fixture as `test_messages_present_hides_compaction_pruned_turn`.
    """
    transcript = _compaction_pruned_and_fork_transcript()
    expected = interleave_events(transcript)
    streamed = [m async for m in stream_interleave_events(_handle_for(transcript))]

    assert expected  # non-vacuous
    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]


@pytest.mark.anyio
async def test_stream_trim_compaction_hides_pruned_turn_like_materialized() -> None:
    """A trim's pruned turn stays hidden when a side call ends the region.

    `span_messages` derives the trimmed prefix from the FIRST ModelEvent after
    the trim, not from the region's last one (here a side call with an
    unrelated input).
    """

    def model_event(input: list[ChatMessage], text: str, id: str) -> ModelEvent:
        output = ModelOutput.from_content(model="mockllm", content=text)
        output.choices[0].message.id = id
        return ModelEvent.model_construct(
            event="model",
            model="mockllm",
            input=input,
            output=output,
            role="assistant",
            config=GenerateConfig(),
        )

    u1 = ChatMessageUser(content="task", id="u1")
    a1 = ChatMessageAssistant(content="pruned turn", id="a1")
    u2 = ChatMessageUser(content="continue", id="u2")
    a2 = ChatMessageAssistant(content="second", id="a2")
    u3 = ChatMessageUser(content="more", id="u3")
    a3 = ChatMessageAssistant(content="third", id="a3")
    transcript = Transcript(
        transcript_id="t",
        messages=[u2, a2, u3, a3],
        events=[
            model_event([u1], "pruned turn", "a1"),
            model_event([u1, a1, u2], "second", "a2"),
            CompactionEvent(type="trim"),
            model_event([u2, a2, u3], "third", "a3"),
            model_event([ChatMessageUser(content="side")], "side answer", "s1"),
        ],
    )
    expected = interleave_events(transcript)
    streamed = [m async for m in stream_interleave_events(_handle_for(transcript))]

    assert "pruned turn" not in "\n".join(m.text for m in expected)  # non-vacuous
    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]


@pytest.mark.anyio
@pytest.mark.parametrize("events_spec", ["all", ["score"]])
async def test_stream_excludes_grader_model_event_like_materialized(
    events_spec: EventsSpec,
) -> None:
    """Streaming hides a scorers span's grader model call, as materialized.

    Shown, the grader's output would be a `MODEL (BRANCH)` entry that leaks
    the answer into the judge prompt.
    """
    transcript = _scorers_span_transcript()
    expected = interleave_events(transcript, events=events_spec)
    streamed = [
        m
        async for m in stream_interleave_events(
            _handle_for(transcript), events=events_spec
        )
    ]
    assert "grader assessment" not in "\n".join(_event_texts(streamed))
    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]


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
    """An off-thread agent's model calls surface as branch entries, as materialized.

    `transcript.messages` holds only agent A's thread and there is no
    compaction, so agent B's two calls are forks: both render as
    ``[E#] MODEL (BRANCH):`` entries, identically on both paths.
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
        config=GenerateConfig(),
    )
    model_b2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-b-question-2")],
        output=out_b2,
        role="assistant",
        config=GenerateConfig(),
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


def _no_load_handle(events: list[Event]) -> SpooledTranscriptHandle:
    """A spooled handle that streams `events`, no messages, and raises on ``load()``.

    Spooled, since ``llm_scanner`` loads every ``MaterializedTranscriptHandle``.
    """

    class _NoLoadHandle(SpooledTranscriptHandle):
        async def messages(self) -> AsyncIterator[ChatMessage]:
            no_messages: list[ChatMessage] = []
            for m in no_messages:
                yield m

        async def events(self) -> AsyncIterator[Event]:
            for e in events:
                yield e

        async def load(self) -> Transcript:
            raise AssertionError("streaming interleave must not materialize")

    async def parse() -> StreamParseResult:
        raise AssertionError("not called")

    async def fallback() -> Transcript:
        raise AssertionError("not called")

    return _NoLoadHandle(TranscriptInfo(transcript_id="t"), parse, fallback)


def _timeline_scorers_flat_events() -> list[Event]:
    """A "main" agent span plus a top-level "scorers" span with a grader call.

    Timeline-shaped (span-structured) flat events, distinct from
    `_spanless_two_agent_flat_events()`: exercises `stream_timeline_messages`'s
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
    """A scorers span's grader thread is excluded on both scan paths.

    Handle and Transcript scans of the same events both omit the grader's
    input and output and render the scorer's `ScoreEvent` exactly once.
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

    handle = _no_load_handle(flat_events)

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

    handle = _no_load_handle(flat_events)

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


T = TypeVar("T")


class _StreamTrackingHandle(SpooledTranscriptHandle):
    """Streams `transcript` from memory and counts the streams left suspended.

    Holding every stream it hands out keeps garbage collection from closing
    one a caller abandoned, so `suspended` counts exactly the streams started
    but neither exhausted nor closed.
    """

    def __init__(self, transcript: Transcript) -> None:
        async def unused() -> NoReturn:
            raise AssertionError("not called")

        super().__init__(
            TranscriptInfo(transcript_id=transcript.transcript_id), unused, unused
        )
        self._content = transcript
        self._streams: list[AsyncIterator[object]] = []
        self.suspended = 0
        self.loads = 0

    def messages(self) -> AsyncIterator[ChatMessage]:
        return self._track(self._content.messages)

    def events(self) -> AsyncIterator[Event]:
        return self._track(self._content.events)

    async def load(self) -> Transcript:
        self.loads += 1
        return self._content

    def _track(self, items: list[T]) -> AsyncIterator[T]:
        async def stream() -> AsyncIterator[T]:
            self.suspended += 1
            try:
                for item in items:
                    yield item
            finally:
                self.suspended -= 1

        tracked = stream()
        self._streams.append(tracked)
        return tracked


def _uuidless_off_thread_span_transcript() -> Transcript:
    """`_timeline_scorers_flat_events` plus a uuid-less side call in "span-main".

    The side call's output is off-thread and renders, so pass 2 cannot
    substitute it and the scan falls back to `load()` partway through.
    """
    events = _timeline_scorers_flat_events()
    side_call = _span_model_event("aside?", "aside", "span-main")
    events.insert(2, side_call.model_copy(update={"uuid": None}))
    return Transcript(transcript_id="t", events=events)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("make_transcript", "falls_back"),
    [
        pytest.param(_compaction_pruned_and_fork_transcript, False, id="flat"),
        pytest.param(_scorers_span_transcript, False, id="messages-and-spans"),
        pytest.param(_uuidless_off_thread_span_transcript, True, id="spans-fallback"),
    ],
)
async def test_llm_scanner_handle_scan_closes_every_stream(
    make_transcript: Callable[[], Transcript], falls_back: bool
) -> None:
    """A streamed events= scan closes each handle stream, however it stops reading."""
    handle = _StreamTrackingHandle(make_transcript())
    scan = llm_scanner(
        question="Right?", answer="boolean", model=_mock_model([]), events="all"
    )
    await scan(cast(Transcript, handle))

    assert handle.suspended == 0
    assert bool(handle.loads) is falls_back


@pytest.mark.anyio
async def test_closing_stream_interleave_early_closes_the_handle_stream() -> None:
    handle = _StreamTrackingHandle(
        Transcript(
            transcript_id="t",
            messages=[ChatMessageUser(content="q1"), ChatMessageUser(content="q2")],
        )
    )
    async with aclosing_iter(stream_interleave_events(handle)) as stream:
        await anext(stream)

    assert handle.suspended == 0
