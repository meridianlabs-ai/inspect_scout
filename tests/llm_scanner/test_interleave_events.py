import re

import pytest
from inspect_ai.event import ModelEvent, ScoreEvent
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
    has_interleavable_events,
    interleave_events,
)
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._transcript.types import Transcript, TranscriptContent


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


def test_events_render_when_messages_empty() -> None:
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
    scan = llm_scanner(question="Right?", answer="boolean", model=_mock_model(captured))
    await scan(transcript)
    # Structural check only: the event renders as [E1] after both turns.
    # Exact renderer formatting is pinned by tests/transcript/test_event_text.py.
    assert re.search(r"\[M1\].*\[M2\].*\[E1\] SCORE", captured[0], re.DOTALL)


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


def test_factory_augments_events_with_model() -> None:
    scan = llm_scanner(
        question="q", answer="boolean", content=TranscriptContent(events=["score"])
    )
    content = getattr(scan, SCANNER_CONTENT_ATTR)
    assert set(content.events) == {"score", "model"}


@pytest.mark.anyio
async def test_interleave_with_timeline_raises() -> None:
    from inspect_ai.event import Timeline, TimelineSpan

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
    scan = llm_scanner(question="q", answer="boolean", model=_mock_model([]))
    with pytest.raises(ValueError, match="timeline"):
        await scan(transcript)


@pytest.mark.anyio
async def test_final_score_lands_in_last_chunk_when_split() -> None:
    # Two turns with long-ish content; a modest context_window forces the
    # transcript to split into multiple segments. The score event is
    # anchored after the final assistant turn, so it must appear exactly
    # once, in the last segment sent to the model.
    long_text = (
        "lorem ipsum dolor sit amet consectetur adipiscing elit sed do "
    ) * 5  # ~40 words
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
    )
    await scan(transcript)
    # Multiple segments captured; the score appears once, in the final one.
    assert len(captured) >= 2
    assert sum("[E1] SCORE" in c for c in captured) == 1
    assert "[E1] SCORE" in captured[-1]
