import contextlib
from typing import Any, Iterator, Sequence

import rich
from inspect_ai._display.core.footer import task_counters, task_resources
from inspect_ai._display.core.rich import is_vscode_notebook, rich_theme
from inspect_ai._util.constants import CONSOLE_DISPLAY_WIDTH
from inspect_ai._util.path import pretty_path
from inspect_ai.util import throttle
from rich.console import Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from typing_extensions import override

from inspect_scout._display.protocol import Display, ScanDisplay
from inspect_scout._display.util import (
    scan_complete_message,
    scan_config,
    scan_errors_message,
    scan_interrupted_messages,
    scan_title,
)
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
        self._transcripts = transcripts
        self._total_scans = transcripts * len(scan.scanners)
        self._skipped_scans = skipped
        self._completed_scans = self._skipped_scans
        self._metrics: ScanMetrics | None = None
        self._live = Live(
            None,
            console=rich.get_console(),
            transient=True,
            auto_refresh=False,
        )
        self._live.start()

        self._progress = Progress(
            TextColumn("Scanning"),
            BarColumn(bar_width=None),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=rich.get_console(),
            transient=True,
        )

        # initial update
        self._update()

        # add task
        self._task_id = self._progress.add_task("Scan", total=self._total_scans)

        # skip already completed scans
        self._progress.update(self._task_id, completed=self._completed_scans or 1)

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
        self._metrics = metrics
        self._completed_scans = self._skipped_scans + metrics.completed_scans
        self._progress.update(
            self._task_id,
            completed=self._completed_scans,
        )
        self._update_throttled()

    @throttle(1)
    def _update_throttled(self) -> None:
        self._update()

    def _update(self) -> None:
        theme = rich_theme()
        console = rich.get_console()

        # root table
        table = Table.grid(expand=True)
        table.add_column()

        # scan config
        table.add_row(scan_config(self._scan.spec, self._options), style=theme.light)
        table.add_row()

        # resources
        resources = Table.grid(expand=True)
        resources.add_column()
        resources.add_column(justify="right")
        if self._metrics:
            resources.add_row("[bold]workers[/bold]", "", style=theme.meta)
            resources.add_row("parsing:", str(self._metrics.tasks_parsing))
            resources.add_row("scanning:", str(self._metrics.tasks_scanning))
            resources.add_row("waiting:", str(self._metrics.tasks_waiting))
            resources.add_row()
            resources.add_row("[bold]resources[/bold]", "", style=theme.meta)
            resources.add_row("cpu %:", "80%")
            resources.add_row("memory", "2.12gb")

        # scanners
        scanners = Table.grid(expand=True)
        scanners.add_column()  # scanner
        scanners.add_column(justify="right")  # results
        scanners.add_column(justify="right")  # erorrs
        scanners.add_column(justify="right")  # tokens/transcript
        scanners.add_column(justify="right")  # total tokens
        scanners.add_row(
            "[bold]scanner[/bold]",
            "[bold]results[/bold]",
            "[bold]errors[/bold]",
            "[bold]tokens/scan[/bold]",
            "[bold]total tokens[/bold]",
            style=theme.meta,
        )
        for scanner in self._scan.spec.scanners.keys():
            scanners.add_row(scanner, "5", "1", "1,200", "10,000")

        # body
        body = Table.grid(expand=True)
        body.add_column()  # progress/scanners/results
        body.add_column(width=5)
        body.add_column(justify="right", width=30)  # resources
        body.add_row(Group(self._progress, "", scanners), "", resources)
        table.add_row(body)

        # footer
        footer = Table.grid(expand=True)
        footer.add_column()
        footer.add_column(justify="right")
        footer.add_row()
        footer.add_row(
            Text.from_markup(task_resources(), style=theme.light),
            Text.from_markup(task_counters({}), style=theme.light),
        )
        table.add_row(footer)

        # create main panel and update
        panel = Panel(
            table,
            title=f"[bold][{theme.meta}]{scan_title(self._scan.spec, self._transcripts)}[/{theme.meta}][/bold]",
            title_align="left",
            width=CONSOLE_DISPLAY_WIDTH if is_vscode_notebook(console) else None,
            expand=True,
        )
        self._live.update(panel, refresh=True)
