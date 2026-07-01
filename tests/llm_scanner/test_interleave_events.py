from inspect_ai.event import ModelEvent, ScoreEvent
from inspect_ai.model import ChatMessageUser, ModelOutput
from inspect_ai.scorer import Score
from inspect_scout._llm_scanner.interleave import (
    has_interleavable_events,
    interleave_events,
)
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._transcript.types import Transcript


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
