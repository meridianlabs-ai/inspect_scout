from typing import Protocol, Sequence

from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._recorder.recorder import ScanStatus
from inspect_scout._scancontext import ScanContext
from inspect_scout._scanner.result import ResultReport
from inspect_scout._transcript.types import TranscriptInfo


class Display(Protocol):
    def print(self, message: str) -> None: ...

    def start(self, can: ScanContext, scan_location: str) -> None: ...

    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None: ...

    def metrics(self, metrics: ScanMetrics) -> None: ...

    def complete(self, status: ScanStatus) -> None: ...
