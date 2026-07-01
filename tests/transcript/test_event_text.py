from inspect_ai.event import (
    ErrorEvent,
    InputEvent,
    SampleLimitEvent,
    SandboxEvent,
    ScoreEvent,
)
from inspect_ai.log import EvalError
from inspect_ai.scorer import Score
from inspect_scout._transcript.event_text import event_as_str


def test_event_as_str_importable_from_shared_module() -> None:
    event = ErrorEvent(error=EvalError(message="boom", traceback="", traceback_ansi=""))
    assert event_as_str(event) == "ERROR:\nboom\n"


def test_event_as_str_reexported_from_grep() -> None:
    from inspect_scout._grep_scanner._event import event_as_str as grep_event_as_str
    from inspect_scout._transcript.event_text import event_as_str as shared

    assert grep_event_as_str is shared


def test_score_event_full() -> None:
    event = ScoreEvent(
        score=Score(value="C", answer="Paris", explanation="Matched target."),
        target="C",
        scorer="match",
    )
    assert event_as_str(event) == (
        "SCORE (match): value=C target=C answer=Paris\n  explanation: Matched target.\n"
    )


def test_score_event_intermediate_no_target() -> None:
    event = ScoreEvent(
        score=Score(value=0.8, explanation="Mostly right."),
        scorer="graded",
        intermediate=True,
    )
    assert event_as_str(event) == (
        "SCORE (graded): value=0.8 intermediate\n  explanation: Mostly right.\n"
    )


def test_score_event_list_target_no_scorer() -> None:
    event = ScoreEvent(score=Score(value="A"), target=["A", "B"])
    assert event_as_str(event) == "SCORE (unknown): value=A target=A, B\n"


def test_sample_limit_event() -> None:
    event = SampleLimitEvent(type="token", message="Token limit exceeded", limit=1000)
    assert event_as_str(event) == "LIMIT (token): Token limit exceeded\n"


def test_input_event() -> None:
    event = InputEvent(input="hello there", input_ansi="hello there")
    assert event_as_str(event) == "INPUT:\nhello there\n"


def test_sandbox_exec_event() -> None:
    event = SandboxEvent(action="exec", cmd="ls -la")
    assert event_as_str(event) == "SANDBOX (exec): ls -la\n"


def test_sandbox_file_event() -> None:
    event = SandboxEvent(action="read_file", file="/etc/hosts")
    assert event_as_str(event) == "SANDBOX (read_file): /etc/hosts\n"
