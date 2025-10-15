import abc
import contextlib
from typing import Any, Iterator, Sequence, override

from rich.console import RenderableType

from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._recorder.recorder import ScanStatus
from inspect_scout._scancontext import ScanContext
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanspec import ScanOptions
from inspect_scout._transcript.types import TranscriptInfo


class Display(abc.ABC):
    @abc.abstractmethod
    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        markup: bool | None = None,
        highlight: bool | None = None,
    ) -> None: ...

    @contextlib.contextmanager
    def scan_display(
        self,
        scan: ScanContext,
        scan_location: str,
        options: ScanOptions,
        transcripts: int,
        skipped: int,
    ) -> Iterator["ScanDisplay"]:
        yield ScanDisplayNone()

    @abc.abstractmethod
    def scan_interrupted(self, message: RenderableType, scan_location: str) -> None: ...

    @abc.abstractmethod
    def scan_complete(self, status: ScanStatus) -> None: ...


class ScanDisplay(abc.ABC):
    @abc.abstractmethod
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None: ...

    @abc.abstractmethod
    def metrics(self, metrics: ScanMetrics) -> None: ...


class ScanDisplayNone(ScanDisplay):
    @override
    def results(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None:
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        pass
