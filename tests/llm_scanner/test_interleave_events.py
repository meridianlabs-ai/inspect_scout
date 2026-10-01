from typing import Iterable

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
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.interleave import (
    INTERLEAVE_DEPENDENCIES,
    EventsSpec,
    interleave_events,
    span_owned_messages,
    stream_interleave_events,
)
from inspect_scout._transcript.timeline import walk_owned_spans
from inspect_scout._transcript.types import (
    EventType,
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


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


# Streaming driver: stream_interleave_events


def _handle_for(transcript: Transcript) -> MaterializedTranscriptHandle:
    async def load_fn() -> Transcript:
        return transcript

    info = TranscriptInfo(
        **transcript.model_dump(exclude={"messages", "events", "timelines"})
    )
    return MaterializedTranscriptHandle(load_fn, info)


@pytest.mark.anyio
async def test_stream_interleave_matches_materialized() -> None:
    """Streaming matches materialized with id-less duplicate turns and a filter.

    The ``["score"]`` selection must drop the ErrorEvent on both paths.
    """
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
    expected = interleave_events(transcript, events=["score"])
    streamed = [
        m
        async for m in stream_interleave_events(
            _handle_for(transcript), events=["score"]
        )
    ]
    assert [(m.id, m.text) for m in streamed] == [(m.id, m.text) for m in expected]
