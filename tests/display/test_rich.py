import io
import re
import unicodedata

import pytest
from inspect_scout._display.rich import (
    TextProgressRich,
    scan_panel,
    scanners_table,
)
from inspect_scout._display.util import (
    scan_complete_message,
    scan_config_str,
    scan_title,
)
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from rich.console import Console

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
PAYLOAD = (
    "VISIBLE-BEFORE"
    "\x1b[2J"
    "\x1b[H"
    "FORGED-SCREEN"
    "\x1b]52;c;UEFTVEVfSElKQUNL\x07"
    "\x1b]8;;file:///etc/passwd\x1b\\"
    "DISGUISED-LINK"
    "\x1b]8;;\x1b\\"
    "\x9b2J"
    "\x9d52;c;UEFTVEVfSElKQUNL\x9c"
    "\r\b\x00\x7f"
    "VISIBLE-AFTER"
    "\nNEXT\tCELL"
)


def _make_console(buffer: io.StringIO, width: int) -> Console:
    return Console(
        file=buffer,
        width=width,
        force_terminal=True,
        color_system=None,
        legacy_windows=False,
    )


def _render(renderable: object) -> str:
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        width=1000,
        force_terminal=False,
        color_system=None,
    )
    console.print(renderable)
    return buffer.getvalue()


def _assert_safe(text: str, *, require_after: bool = True) -> None:
    assert all(
        char in "\n\t" or unicodedata.category(char) not in ("Cc", "Cf")
        for char in text
    )
    assert "VISIBLE-BEFORE" in text
    if require_after:
        assert "VISIBLE-AFTER" in text


def _scan() -> tuple[ScanSpec, Summary]:
    spec = ScanSpec(
        scan_name=PAYLOAD,
        scan_args={"metadata": PAYLOAD},
        scanners={PAYLOAD: ScannerSpec(name=PAYLOAD)},
        transcripts=None,
    )
    summary = Summary(scanners=[PAYLOAD])
    summary[PAYLOAD].metrics = {"group": {PAYLOAD: 1.0}}
    return spec, summary


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


def test_scanner_table_and_panel_remove_terminal_controls() -> None:
    spec, summary = _scan()

    _assert_safe(_render(scanners_table(spec, summary)))
    _assert_safe(_render(scan_panel(spec=spec, summary=summary)))


def test_scan_metadata_and_filename_text_remove_terminal_controls() -> None:
    spec, summary = _scan()
    status = Status(
        complete=True,
        spec=spec,
        location=f"/tmp/{PAYLOAD}",
        summary=summary,
        errors=[],
    )

    _assert_safe(scan_title(spec))
    _assert_safe(scan_config_str(spec), require_after=False)
    _assert_safe(scan_complete_message(status))


def test_text_progress_cleans_caption_and_filename(
    captured_console: tuple[Console, io.StringIO],
) -> None:
    progress = TextProgressRich(PAYLOAD, count=True)
    with progress:
        progress.update(PAYLOAD)
        task = progress._progress.tasks[0]
        _assert_safe(task.description)
        _assert_safe(task.fields["text"])
