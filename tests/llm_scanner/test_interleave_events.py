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
    assert "[E1] SCORE (match): value=C target=C" in captured[0]
    assert "[M1]" in captured[0] and "[M2]" in captured[0]


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
