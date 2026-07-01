from inspect_ai.event import ErrorEvent
from inspect_ai.log import EvalError
from inspect_scout._transcript.event_text import event_as_str


def test_event_as_str_importable_from_shared_module() -> None:
    event = ErrorEvent(error=EvalError(message="boom", traceback="", traceback_ansi=""))
    assert event_as_str(event) == "ERROR:\nboom\n"


def test_event_as_str_reexported_from_grep() -> None:
    from inspect_scout._grep_scanner._event import event_as_str as grep_event_as_str
    from inspect_scout._transcript.event_text import event_as_str as shared

    assert grep_event_as_str is shared
