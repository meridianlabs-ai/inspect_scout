import io
import re

import pytest
from inspect_scout._display.rich import TextProgressRich
from rich.console import Console

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _make_console(buffer: io.StringIO, width: int) -> Console:
    return Console(
        file=buffer,
        width=width,
        force_terminal=True,
        color_system=None,
        legacy_windows=False,
    )


@pytest.fixture
def captured_console(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Console, io.StringIO]:
    buffer = io.StringIO()
    console = _make_console(buffer, width=200)
    # rich.progress imports get_console at module import time, so patch it
    # at the module where Progress resolves it.
    monkeypatch.setattr("rich.progress.get_console", lambda: console)
    return console, buffer


def test_long_text_is_not_truncated_on_wide_terminal(
    captured_console: tuple[Console, io.StringIO],
) -> None:
    """A long text value should not be ellipsized when the terminal is wide."""
    _, buffer = captured_console
    long_path = (
        "file:///Users/foo/reuse/logs/very/specific/transcript_2024_01_01_long.eval"
    )

    progress = TextProgressRich("Indexing", count=True)
    with progress:
        progress.update(long_path)
        progress._progress.refresh()

    visible = ANSI_RE.sub("", buffer.getvalue())
    assert long_path in visible, (
        f"Long path was truncated; visible output was:\n{visible!r}"
    )


def test_progress_display_is_cleared_on_exit(
    captured_console: tuple[Console, io.StringIO],
) -> None:
    """On context exit, the rendered progress region should be cleared from the terminal."""
    _, buffer = captured_console

    progress = TextProgressRich("Indexing", count=True)
    with progress:
        progress.update("/some/log/path.eval")
        progress._progress.refresh()
        # Confirm the line was actually rendered while active.
        assert "Indexing" in ANSI_RE.sub("", buffer.getvalue())

    # When transient cleanup is wired up, Rich's Live emits cursor-up + erase-line
    # ANSI codes at the very tail of the buffer to wipe the rendered region.
    # Without transient cleanup, the buffer tail is just a show-cursor sequence
    # following the last rendered frame.
    output = buffer.getvalue()
    assert re.search(r"\x1b\[\d*A\x1b\[2K\Z", output), (
        "Expected cursor-up + erase-line ANSI sequence at end of buffer "
        "(transient cleanup); progress region was not cleared on exit. "
        f"Buffer tail: {output[-120:]!r}"
    )
