import re
from typing import AsyncIterator, cast

import pytest
from inspect_ai.event import ErrorEvent, ModelEvent, ScoreEvent, Timeline, TimelineSpan
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
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


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
async def test_interleave_with_timeline_raises() -> None:
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="2+2?"), out.choices[0].message],
        events=[ScoreEvent(score=Score(value="C"), scorer="match")],
        timelines=[
            Timeline(
                name="Default",
                description="",
                root=TimelineSpan(
                    id="root", name="Transcript", span_type=None, content=[]
                ),
            )
        ],
    )
    scan = llm_scanner(
        question="q", answer="boolean", model=_mock_model([]), events=["score"]
    )
    with pytest.raises(ValueError, match="timeline"):
        await scan(transcript)


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
