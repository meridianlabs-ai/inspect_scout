from inspect_ai.event import ErrorEvent, ScoreEvent
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
