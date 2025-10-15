from typing import Any, Sequence

import rich
from rich.console import RenderableType
from typing_extensions import override

from inspect_scout._display.messages import scan_interrupted_messages

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import ScanStatus
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .messages import scan_complete_message, scan_errors_message
from .protocol import Display


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

    @override
    def start(self, scan: ScanContext, scan_location: str) -> None:
        pass

    @override
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        pass

    @override
    def interrupted(self, message: RenderableType, scan_location: str) -> None:
        self.print(*scan_interrupted_messages(message, scan_location))

    @override
    def complete(self, status: ScanStatus) -> None:
        if status.complete:
            self.print(scan_complete_message(status))
        else:
            self.print(scan_errors_message(status))
