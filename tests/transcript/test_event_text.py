import pytest
from inspect_ai._util.json import JsonChange
from inspect_ai.dataset import Sample
from inspect_ai.event import (
    BranchEvent,
    ErrorEvent,
    Event,
    InfoEvent,
    InputEvent,
    SampleInitEvent,
    SampleLimitEvent,
    SandboxEvent,
    ScoreEvent,
    StateEvent,
    StoreEvent,
)
from inspect_ai.log import EvalError
from inspect_ai.scorer import Score
from inspect_scout._transcript.event_text import event_as_str


def test_event_as_str_reexported_from_grep() -> None:
    from inspect_scout._grep_scanner._event import event_as_str as grep_event_as_str
    from inspect_scout._transcript.event_text import event_as_str as shared

    assert grep_event_as_str is shared


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
            SampleInitEvent(sample=Sample(input="x"), state={}),
            "SAMPLE INIT\n",
            id="sample-init",
        ),
    ],
)
def test_event_as_str_renders_expected_text(event: Event, expected: str | None) -> None:
    assert event_as_str(event) == expected
