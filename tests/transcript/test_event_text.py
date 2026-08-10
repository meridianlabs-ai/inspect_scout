from typing import get_args

import pytest
from inspect_ai._util.json import JsonChange
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
from inspect_scout._transcript.interleave import _NON_INTERLEAVED
from inspect_scout._transcript.types import EventType


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        pytest.param(
            ErrorEvent(
                error=EvalError(message="boom", traceback="", traceback_ansi="")
            ),
            "ERROR:\nboom\n",
            id="error",
        ),
        pytest.param(
            ScoreEvent(
                score=Score(value="C", answer="Paris", explanation="Matched target."),
                target="C",
                scorer="match",
            ),
            "SCORE (match): value=C target=C answer=Paris\n"
            "  explanation: Matched target.\n",
            id="score-full",
        ),
        pytest.param(
            ScoreEvent(
                score=Score(value=0.8, explanation="Mostly right."),
                scorer="graded",
                intermediate=True,
            ),
            "SCORE (graded): value=0.8 intermediate\n  explanation: Mostly right.\n",
            id="score-intermediate-no-target",
        ),
        pytest.param(
            ScoreEvent(score=Score(value="A"), target=["A", "B"]),
            "SCORE (unknown): value=A target=A, B\n",
            id="score-list-target-no-scorer",
        ),
        pytest.param(
            ScoreEvent(score=Score(value={"a": 1.0, "b": 0.5}), scorer="multi"),
            "SCORE (multi): value={'a': 1.0, 'b': 0.5}\n",
            id="score-dict-value",
        ),
        pytest.param(
            SampleLimitEvent(type="token", message="Token limit exceeded", limit=1000),
            "LIMIT (token): Token limit exceeded\n",
            id="sample-limit",
        ),
        pytest.param(
            InputEvent(input="hello there", input_ansi="hello there"),
            "INPUT:\nhello there\n",
            id="input",
        ),
        pytest.param(
            SandboxEvent(action="exec", cmd="ls -la"),
            "SANDBOX (exec): ls -la\n",
            id="sandbox-cmd",
        ),
        pytest.param(
            SandboxEvent(action="read_file", file="/etc/hosts"),
            "SANDBOX (read_file): /etc/hosts\n",
            id="sandbox-file",
        ),
        pytest.param(
            SandboxEvent(action="exec"),
            "SANDBOX (exec)\n",
            id="sandbox-no-detail",
        ),
        pytest.param(
            InfoEvent(data={"k": 1}),
            'INFO:\n{"k": 1}\n',
            id="info-json-data",
        ),
        pytest.param(
            InfoEvent(data="plain"),
            "INFO:\nplain\n",
            id="info-str-data",
        ),
        pytest.param(InfoEvent(data=None), None, id="info-no-data"),
        pytest.param(StateEvent(changes=[]), "STATE: 0 changes\n", id="state-empty"),
        pytest.param(
            StoreEvent(changes=[JsonChange(op="add", path="/x", value=1)]),
            "STORE: 1 change\n",
            id="store-singular",
        ),
        pytest.param(BranchEvent(), "BRANCH\n", id="branch"),
        pytest.param(
            ScoreEditEvent(score_name="acc", edit=ScoreEdit(value="I")),
            "SCORE EDIT (acc): value=I\n",
            id="score-edit-value",
        ),
        pytest.param(
            ScoreEditEvent(
                score_name="acc", edit=ScoreEdit(value="I", explanation="wrong")
            ),
            "SCORE EDIT (acc): value=I\n  explanation: wrong\n",
            id="score-edit-explanation-on-own-line",
        ),
        pytest.param(
            ScoreEditEvent(score_name="acc", edit=ScoreEdit(metadata={"k": 1})),
            "SCORE EDIT (acc): metadata edited\n",
            id="score-edit-metadata-only",
        ),
        pytest.param(
            ScoreEditEvent(score_name="acc", edit=ScoreEdit(answer=None)),
            "SCORE EDIT (acc): answer=None\n",
            id="score-edit-clearing-answer-is-a-real-edit",
        ),
        pytest.param(
            InterruptEvent(source="limit", interrupted="generate"),
            "INTERRUPT (limit): during generate\n",
            id="interrupt",
        ),
        pytest.param(
            SampleInitEvent(sample=Sample(input="x"), state={}),
            "SAMPLE INIT\n",
            id="sample-init",
        ),
    ],
)
def test_event_as_str_renders_expected_text(event: Event, expected: str | None) -> None:
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
    "sample_init": SampleInitEvent(sample=Sample(input="x"), state={}),
    "sample_limit": SampleLimitEvent(type="token", message="limit", limit=1),
    "sandbox": SandboxEvent(action="exec", cmd="ls"),
    "score": ScoreEvent(score=Score(value="C")),
    "score_edit": ScoreEditEvent(score_name="s", edit=ScoreEdit(value="I")),
    "state": StateEvent(changes=[]),
    "store": StoreEvent(changes=[]),
}


def test_event_samples_cover_every_interleavable_type() -> None:
    """Guards the guard below: a new EventType must gain a sample here."""
    assert set(_EVENT_SAMPLES) | set(_NON_INTERLEAVED) == set(get_args(EventType))


def test_every_interleavable_event_type_renders() -> None:
    """No event type may be selectable for interleaving yet render nothing.

    `EventType` gates what `llm_scanner(events=...)` accepts and loads, and
    `_NON_INTERLEAVED` names the structural types deliberately never rendered.
    A type outside both is accepted, loaded, then silently dropped by
    `event_as_str` -- which is how score_edit, anchor, checkpoint and
    interrupt behaved when they were first added to the literal.
    """
    unrenderable = sorted(
        name for name, event in _EVENT_SAMPLES.items() if event_as_str(event) is None
    )
    assert unrenderable == []
