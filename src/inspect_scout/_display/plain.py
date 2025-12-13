import contextlib
import time
from typing import Any, Callable, Iterator, Sequence

import rich
from inspect_ai._util.format import format_progress_time
from inspect_ai.util import throttle
from typing_extensions import override

from inspect_scout._recorder.summary import Summary

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import Status
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .protocol import Display, ScanDisplay, TextProgress
from .util import (
    exception_to_rich_traceback,
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
    def text_progress(self, caption: str, count: bool | int) -> Iterator[TextProgress]:
        yield TextProgressPlain(caption, count, self.print)

    @contextlib.contextmanager
    def scan_display(
        self,
        scan: ScanContext,
        scan_location: str,
        summary: Summary,
        total: int,
        skipped: int,
    ) -> Iterator[ScanDisplay]:
        yield ScanDisplayPlain(scan, summary, total, skipped, self.print)

    @override
    def scan_interrupted(self, message_or_exc: str | Exception, status: Status) -> None:
        if isinstance(message_or_exc, Exception):
            self.print(exception_to_rich_traceback(message_or_exc))
        else:
            self.print(message_or_exc)
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
        total: int,
        skipped: int,
        print: Callable[..., None],
    ) -> None:
        self._print = print
        self._print(
            f"{scan_title(scan.spec)}",
        )
        self._print(scan_config(scan.spec), "\n")
        self._total_scans = total
        self._skipped_scans = skipped
        self._completed_scans = self._skipped_scans
        self._parsing = self._scanning = self._idle = self._buffered = 0
        self._batch_oldest_created: int | None = None
        self._batch_pending = 0
        self._batch_failures = 0

    @override
    def results(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        self._completed_scans = self._skipped_scans + metrics.completed_scans
        self._parsing = metrics.tasks_parsing
        self._scanning = metrics.tasks_scanning
        self._idle = metrics.tasks_idle
        self._buffered = metrics.buffered_scanner_jobs
        self._batch_oldest_created = metrics.batch_oldest_created
        self._batch_pending = metrics.batch_pending
        self._batch_failures = metrics.batch_failures
        self._update_throttled()

    def _update(self) -> None:
        percent = 100.0 * self._completed_scans / self._total_scans
        msg = f"scanning: {percent:3.0f}% ({self._completed_scans:,}/{self._total_scans:,}) {self._parsing}/{self._scanning}/{self._idle} ({self._buffered})"
        if self._batch_oldest_created is not None:
            batch_age = int(time.time() - self._batch_oldest_created)
            batch_info = f" batch: {self._batch_pending}/"
            if self._batch_failures:
                batch_info += f"{self._batch_failures}/"
            batch_info += f"{format_progress_time(batch_age, pad_hours=False)}"
            msg += batch_info
        self._print(msg)

    @throttle(5)
    def _update_throttled(self) -> None:
        self._update()


class TextProgressPlain(TextProgress):
    def __init__(
        self,
        caption: str,
        count: bool | int,
        print: Callable[..., None],
    ):
        self._caption = caption
        self._count = count
        self._print = print
        self._total = 0

    def update(self, text: str) -> None:
        self._total += 1
        msg = f"{self._caption}: {text}"
        if self._count:
            msg = f"{msg} - {(self._total,)}"
            if not isinstance(self._count, bool):
                msg = f"{msg}/{(self._count,)}"
        if self._total == 1:
            self._print(msg)
        else:
            self._print_throttled(msg)

    @throttle(5)
    def _print_throttled(self, msg: str) -> None:
        self._print(msg)
