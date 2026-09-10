"""Interrupted scans must display failures nested inside task groups."""

import io
import sys

from inspect_scout._display.util import exception_to_rich_traceback
from rich.console import Console

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


def test_task_group_display_includes_nested_failures() -> None:
    exception = ExceptionGroup(
        "scan failed",
        [
            ExceptionGroup("worker", [RuntimeError("remote diagnostic fixture")]),
            ValueError("another failure fixture"),
        ],
    )
    output = io.StringIO()
    Console(file=output, width=120, color_system=None).print(
        exception_to_rich_traceback(exception)
    )
    diagnostic = output.getvalue()
    assert "remote diagnostic fixture" in diagnostic
    assert "another failure fixture" in diagnostic
    assert "RuntimeError" in diagnostic
    assert "ValueError" in diagnostic
