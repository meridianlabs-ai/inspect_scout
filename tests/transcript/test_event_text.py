from typing import get_args

import pytest
from inspect_ai.dataset import Sample
from inspect_ai.event import (
    ApprovalEvent,
    BranchEvent,
    ErrorEvent,
    Event,
    InfoEvent,
    InputEvent,
    InterruptEvent,
    LoggerEvent,
    LoggingMessage,
    ReviewEvent,
    SampleInitEvent,
    SampleLimitEvent,
    SandboxEvent,
    ScoreEvent,
    StateEvent,
    StoreEvent,
)
from inspect_ai.event._score_edit import ScoreEditEvent
from inspect_ai.log import EvalError
from inspect_ai.scorer import Score, ScoreEdit
from inspect_ai.tool import ToolCall
from inspect_scout._transcript.event_text import event_as_str
from inspect_scout._transcript.interleave import _NON_INTERLEAVED, _interleavable_text
from inspect_scout._transcript.types import EventType


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        pytest.param(
            ScoreEvent(
                score=Score(value="C", answer="Paris", explanation="Matched target."),
                target="C",
                scorer="match",
            ),
            "SCORE (match): value=C target=C\n"
            "  answer: Paris\n"
            "  explanation: Matched target.\n",
            id="score-full",
        ),
        pytest.param(
            ScoreEvent(score=Score(value="A"), target=["A", "B"], intermediate=True),
            "SCORE (unknown): value=A target=A, B intermediate\n",
            id="score-list-target-intermediate-no-scorer",
        ),
        pytest.param(
            ScoreEditEvent(
                score_name="acc",
                edit=ScoreEdit(
                    value="I", answer="42", metadata={"k": 1}, explanation="why, then"
                ),
            ),
            "SCORE EDIT (acc): value=I metadata edited\n"
            "  answer: 42\n"
            "  explanation: why, then\n",
            id="score-edit-all-fields",
        ),
        pytest.param(
            ScoreEditEvent(score_name="acc", edit=ScoreEdit(answer=None)),
            "SCORE EDIT (acc)\n  answer: (cleared)\n",
            id="score-edit-clearing-answer-is-a-real-edit",
        ),
    ],
)
def test_event_as_str_renders_expected_text(event: Event, expected: str) -> None:
    assert event_as_str(event) == expected


_EVENT_SAMPLES: dict[str, Event] = {
    "approval": ApprovalEvent(
        message="m",
        call=ToolCall(id="1", function="f", arguments={}),
        approver="human",
        decision="approve",
    ),
    "branch": BranchEvent(),
    "error": ErrorEvent(
        error=EvalError(message="boom", traceback="", traceback_ansi="")
    ),
    "info": InfoEvent(data={"k": 1}),
    "input": InputEvent(input="hi", input_ansi="hi"),
    "interrupt": InterruptEvent(source="limit", interrupted="generate"),
    "logger": LoggerEvent(
        message=LoggingMessage(level="info", message="m", created=0.0)
    ),
    "review": ReviewEvent(
        message="m",
        call=ToolCall(id="1", function="f", arguments={}),
        reviewer="monitor",
        decision="terminate",
    ),
    "sample_init": SampleInitEvent(sample=Sample(input="x"), state={}),
    "sample_limit": SampleLimitEvent(type="token", message="limit", limit=1),
    "sandbox": SandboxEvent(action="exec", cmd="ls"),
    "score": ScoreEvent(score=Score(value="C")),
    "score_edit": ScoreEditEvent(score_name="s", edit=ScoreEdit(value="I")),
    "state": StateEvent(changes=[]),
    "store": StoreEvent(changes=[]),
}


def test_every_interleavable_event_type_renders() -> None:
    """A type `llm_scanner(events=...)` accepts but cannot render is silently dropped."""
    assert set(_EVENT_SAMPLES) | set(_NON_INTERLEAVED) == set(get_args(EventType))
    unrenderable = sorted(
        name
        for name, event in _EVENT_SAMPLES.items()
        if _interleavable_text(event) is None
    )
    assert unrenderable == []
