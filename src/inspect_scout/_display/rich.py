import contextlib
from typing import Any, Iterator, Sequence

import rich
from inspect_ai._display.core.rich import is_vscode_notebook, rich_theme
from inspect_ai._util.constants import CONSOLE_DISPLAY_WIDTH
from inspect_ai.util import throttle
from rich.console import Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from typing_extensions import override

from inspect_scout._display.protocol import Display, ScanDisplay
from inspect_scout._display.util import (
    scan_complete_message,
    scan_errors_message,
    scan_interrupted_messages,
    scan_title,
)
from inspect_scout._progress_utils import UtilizationColumn
from inspect_scout._scanspec import ScanOptions

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import ScanStatus
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo


class DisplayRich(Display):
    @override
    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        markup: bool | None = None,
        highlight: bool | None = None,
    ) -> None:
        console = rich.get_console()
        console.print(*objects, sep=sep, end=end, markup=markup, highlight=False)

    @contextlib.contextmanager
    def scan_display(
        self,
        scan: ScanContext,
        scan_location: str,
        options: ScanOptions,
        transcripts: int,
        skipped: int,
    ) -> Iterator[ScanDisplay]:
        with ScanDisplayRich(
            scan, scan_location, options, transcripts, skipped
        ) as scan_display:
            yield scan_display

    @override
    def scan_interrupted(self, message: RenderableType, scan_location: str) -> None:
        self.print(*scan_interrupted_messages(message, scan_location))

    @override
    def scan_complete(self, status: ScanStatus) -> None:
        if status.complete:
            self.print(scan_complete_message(status))
        else:
            self.print(scan_errors_message(status))


class ScanDisplayRich(
    ScanDisplay, contextlib.AbstractContextManager["ScanDisplayRich"]
):
    def __init__(
        self,
        scan: ScanContext,
        scan_location: str,
        options: ScanOptions,
        transcripts: int,
        skipped: int,
    ) -> None:
        self._scan = scan
        self._scan_location = scan_location
        self._options = options
        self._total_scans = transcripts * len(scan.scanners)
        self._skipped_scans = skipped
        self._completed_scans = self._skipped_scans
        self._live = Live(
            None,
            console=rich.get_console(),
            transient=True,
            auto_refresh=False,
        )
        self._live.start()

        self._progress = Progress(
            TextColumn("Scanning"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TextColumn("(processes/parsing/scanning/waiting) (buffered scan jobs)"),
            UtilizationColumn(),
            TimeElapsedColumn(),
            console=rich.get_console(),
            transient=True,
        )

        # initial update
        self._update()

        # add task
        self._task_id = self._progress.add_task("Scan", total=self._total_scans)

        # skip already completed scans
        if self._completed_scans > 0:
            self._progress.update(self._task_id, completed=self._completed_scans)

    def __exit__(self, *excinfo: Any) -> None:
        self._progress.stop()
        self._live.stop()

    @override
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        # not yet doing anything w/ results
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        self._completed_scans = self._skipped_scans + metrics.completed_scans
        self._progress.update(
            self._task_id,
            metrics=metrics,
            completed=self._completed_scans,
        )
        self._update()

    @throttle(1)
    def _update(self) -> None:
        theme = rich_theme()
        console = rich.get_console()
        panel = Panel(
            Group("", self._progress),
            title=f"[bold][{theme.meta}]{scan_title(self._scan.spec)}[/{theme.meta}][/bold]",
            title_align="left",
            width=CONSOLE_DISPLAY_WIDTH if is_vscode_notebook(console) else None,
            expand=True,
        )
        self._live.update(panel, refresh=True)
