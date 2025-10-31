import contextlib
from typing import Any, Callable, Iterator, Sequence

import rich
from inspect_ai.util import throttle
from rich.console import RenderableType
from typing_extensions import override

from inspect_scout._recorder.summary import Summary

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import Status
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .protocol import Display, ScanDisplay
from .util import (
    scan_complete_message,
    scan_config,
    scan_errors_message,
    scan_interrupted_message,
    scan_title,
)


class DisplayPlain(Display):
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
        yield ScanDisplayPlain(scan, summary, transcripts, skipped, self.print)

    @override
    def scan_interrupted(self, message: RenderableType, status: Status) -> None:
        self.print(message)
        self.print(scan_interrupted_message(status))

    @override
    def scan_complete(self, status: Status) -> None:
        if status.complete:
            self.print(scan_complete_message(status))
        else:
            self.print(scan_errors_message(status))

    @override
    def scan_status(self, status: Status) -> None:
        if status.complete:
            self.print(scan_complete_message(status))
        elif len(status.errors) > 0:
            self.print(scan_errors_message(status))
        else:
            self.print(scan_interrupted_message(status))


class ScanDisplayPlain(ScanDisplay):
    def __init__(
        self,
        scan: ScanContext,
        summary: Summary,
        transcripts: int,
        skipped: int,
        print: Callable[..., None],
    ) -> None:
        self._print = print
        self._print(
            f"{scan_title(scan.spec)}",
        )
        self._print(scan_config(scan.spec), "\n")
        self._total_scans = sum(len(work.transcripts) for work in scan.worklist)
        self._skipped_scans = skipped
        self._completed_scans = self._skipped_scans
        self._parsing = self._scanning = self._idle = self._buffered = 0

    @override
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        self._completed_scans = self._skipped_scans + metrics.completed_scans
        self._parsing = metrics.tasks_parsing
        self._scanning = metrics.tasks_scanning
        self._idle = metrics.tasks_idle
        self._buffered = metrics.buffered_scanner_jobs
        self._update_throttled()

    def _update(self) -> None:
        percent = 100.0 * self._completed_scans / self._total_scans
        self._print(
            f"scanning: {percent:3.0f}% ({self._completed_scans:,}/{self._total_scans:,}) {self._parsing}/{self._scanning}/{self._idle} ({self._buffered})"
        )

    @throttle(8)
    def _update_throttled(self) -> None:
        self._update()
