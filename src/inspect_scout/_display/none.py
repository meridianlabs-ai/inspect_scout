from typing import Any, Sequence

from rich.console import RenderableType
from typing_extensions import override

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import ScanStatus
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .protocol import Display


class DisplayNone(Display):
    @override
    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        markup: bool | None = None,
        highlight: bool | None = None,
    ) -> None:
        pass

    @override
    def start(self, can: ScanContext, scan_location: str) -> None:
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
        pass

    @override
    def complete(self, status: ScanStatus) -> None:
        pass
