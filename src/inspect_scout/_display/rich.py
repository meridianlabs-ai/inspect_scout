import contextlib
from functools import lru_cache
from typing import Any, Iterator, Sequence

import psutil
import rich
from inspect_ai._display.core.footer import task_counters, task_resources
from inspect_ai._display.core.results import model_usage_summary
from inspect_ai._display.core.rich import is_vscode_notebook, rich_theme
from inspect_ai._util.constants import CONSOLE_DISPLAY_WIDTH
from inspect_ai.model import ModelUsage
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
    scan_interrupted_message,
    scan_title,
)
from inspect_scout._recorder.summary import Summary, add_model_usage
from inspect_scout._scanspec import ScanSpec

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import Status
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
        summary: Summary,
        transcripts: int,
        skipped: int,
    ) -> Iterator[ScanDisplay]:
        with ScanDisplayRich(
            scan, scan_location, summary, transcripts, skipped
        ) as scan_display:
            yield scan_display

    @override
    def scan_interrupted(self, message: RenderableType, status: Status) -> None:
        if message:
            self.print(message)
        panel = scan_panel(
            spec=status.spec,
            summary=status.summary,
            message=scan_interrupted_message(status),
            model_usage=True,
        )
        self.print(panel)

    @override
    def scan_complete(self, status: Status) -> None:
        panel = scan_panel(
            spec=status.spec,
            summary=status.summary,
            message=scan_complete_message(status)
            if status.complete
            else scan_errors_message(status),
            model_usage=True,
        )
        self.print(panel)

    @override
    def scan_status(self, status: Status) -> None:
        if status.complete or len(status.errors) > 0:
            self.scan_complete(status)
        else:
            self.scan_interrupted("", status)


class ScanDisplayRich(
    ScanDisplay, contextlib.AbstractContextManager["ScanDisplayRich"]
):
    def __init__(
        self,
        scan: ScanContext,
        scan_location: str,
        summary: Summary,
        transcripts: int,
        skipped: int,
    ) -> None:
        self._scan = scan
        self._scan_location = scan_location
        self._transcripts = transcripts
        self._total_scans = transcripts * len(scan.scanners)
        self._skipped_scans = skipped
        self._completed_scans = self._skipped_scans
        self._metrics: ScanMetrics | None = None
        self._scan_summary = summary
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
        self._scan_summary._report(transcript, scanner, results)

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
        panel = scan_panel(
            spec=self._scan.spec,
            summary=self._scan_summary,
            progress=self._progress,
            metrics=self._metrics,
        )
        self._live.update(
            panel,
            refresh=True,
        )


def scan_panel(
    *,
    spec: ScanSpec,
    summary: Summary,
    progress: Progress | None = None,
    metrics: ScanMetrics | None = None,
    message: RenderableType | None = None,
    model_usage: bool = False,
) -> RenderableType:
    theme = rich_theme()
    console = rich.get_console()

    # root table
    table = Table.grid(expand=True)
    table.add_column()

    # scan config
    table.add_row(scan_config(spec), style=theme.light)
    table.add_row()

    # resources
    resources: Table | None = None
    if metrics:
        resources = Table.grid(expand=True)
        resources.add_column()
        resources.add_column(justify="right")
        resources.add_row("[bold]workers[/bold]", "", style=theme.meta)
        resources.add_row("parsing:", f"{metrics.tasks_parsing:,}")
        resources.add_row("scanning:", f"{metrics.tasks_scanning:,}")
        resources.add_row("idle:", f"{metrics.tasks_idle:,}")
        resources.add_row()
        resources.add_row("[bold]resources[/bold]", "", style=theme.meta)
        resources.add_row(
            "memory",
            f"{bytes_to_gigabytes(metrics.memory_usage)} / {bytes_to_gigabytes(total_memory())}",
        )

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
    NONE = f"[{theme.light}]-[/{theme.light}]"
    for scanner in spec.scanners.keys():
        results = summary[scanner]
        scanners.add_row(
            scanner,
            f"{results.results:,}" if results.results else NONE,
            f"{results.errors:,}" if results.errors else NONE,
            f"{results.tokens // results.scans:,}"
            if results.tokens and results.scans
            else NONE,
            f"{results.tokens:,}" if results.tokens else NONE,
        )

    # body
    body = Table.grid(expand=True)
    body.add_column()  # progress/scanners/results
    body.add_column(width=5)
    body.add_column(justify="right", width=30)  # resources

    # model usage
    if model_usage:
        # first aggregate over all scanners
        total_usage: dict[str, ModelUsage] = {}
        for scanner_summary in summary.scanners.values():
            for m, usage in scanner_summary.model_usage.items():
                if m not in total_usage:
                    total_usage[m] = ModelUsage()
                total_usage[m] = add_model_usage(total_usage[m], usage)

        usage_table = Table.grid(expand=False)
        usage_table.add_column()
        usage_table.add_column()
        for model, usage in total_usage.items():
            usage_table.add_row(
                *model_usage_summary(model, usage),
                style=theme.light,
            )
        body.add_row(usage_table, "", "")
        body.add_row()

    scanning_group: list[RenderableType] = []
    if progress:
        scanning_group.extend([progress, ""])
    scanning_group.append(scanners)
    body.add_row(Group(*scanning_group), "", resources or "")
    table.add_row(body)

    # message (if provided)
    if message is not None:
        table.add_row(message)

    # footer (if running)
    if progress is not None:
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
        title=f"[bold][{theme.meta}]{scan_title(spec)}[/{theme.meta}][/bold]",
        title_align="left",
        width=CONSOLE_DISPLAY_WIDTH if is_vscode_notebook(console) else None,
        expand=True,
    )

    return panel


@lru_cache(maxsize=None)
def total_memory() -> int:
    return psutil.virtual_memory().total


def bytes_to_gigabytes(input: int) -> str:
    value = f"{input / 1024 / 1024 / 1024:.1f}".rstrip("0").rstrip(".")
    return f"{value}gb"
