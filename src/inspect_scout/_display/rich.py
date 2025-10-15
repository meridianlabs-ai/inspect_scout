import contextlib
from typing import Any, Iterator, Sequence

import rich
from rich.console import RenderableType
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from typing_extensions import override

from inspect_scout._display.messages import (
    scan_complete_message,
    scan_errors_message,
    scan_interrupted_messages,
)
from inspect_scout._display.protocol import Display, ScanDisplay
from inspect_scout._progress_utils import UtilizationColumn

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
        self, scan: ScanContext, scan_location: str, transcripts: int, skipped: int
    ) -> Iterator[ScanDisplay]:
        with ScanDisplayRich(scan, scan_location, transcripts, skipped) as scan_display:
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
        self, scan: ScanContext, scan_location: str, transcripts: int, skipped: int
    ) -> None:
        self._progress = Progress(
            TextColumn("Scanning"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TextColumn("(processes/parsing/scanning/waiting) (buffered scan jobs)"),
            UtilizationColumn(),
            TimeElapsedColumn(),
            transient=True,
        )

        self._progress.start()
        scans_per_transcript = len(scan.scanners)
        total_ticks = transcripts * scans_per_transcript
        self._task_id = self._progress.add_task("Scan", total=total_ticks)

        # skip already completed scans
        self._skipped = skipped
        if self._skipped > 0:
            self._progress.update(self._task_id, completed=self._skipped)

    def __exit__(self, *excinfo: Any) -> None:
        self._progress.stop()

    @override
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        # not yet doing anything w/ results
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        self._progress.update(
            self._task_id,
            metrics=metrics,
            completed=self._skipped + metrics.completed_scans,
        )
