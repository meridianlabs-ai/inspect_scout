import contextlib
from typing import Any, Iterator, Sequence

import rich
from rich.console import RenderableType
from typing_extensions import override

from inspect_scout._display.util import scan_interrupted_messages
from inspect_scout._scanspec import ScanOptions

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import ScanStatus
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .util import scan_complete_message, scan_errors_message
from .protocol import Display, ScanDisplay


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
        options: ScanOptions,
        transcripts: int,
        skipped: int,
    ) -> Iterator[ScanDisplay]:
        yield ScanDisplayPlain()

    @override
    def scan_interrupted(self, message: RenderableType, scan_location: str) -> None:
        self.print(*scan_interrupted_messages(message, scan_location))

    @override
    def scan_complete(self, status: ScanStatus) -> None:
        if status.complete:
            self.print(scan_complete_message(status))
        else:
            self.print(scan_errors_message(status))


class ScanDisplayPlain(ScanDisplay):
    @override
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        pass
