from typing import Sequence

from typing_extensions import override

from .._concurrency.common import ScanMetrics
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .plain import DisplayPlain


class DisplayRich(DisplayPlain):
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
