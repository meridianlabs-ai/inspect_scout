import abc
import contextlib
from typing import Any, Iterator, Sequence

from typing_extensions import override

from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scancontext import ScanContext
from inspect_scout._scanner.result import ResultReport
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
    def text_progress(
        self, caption: str, count: bool | int
    ) -> Iterator["TextProgress"]:
        yield TextProgressNone()

    @contextlib.contextmanager
    def scan_display(
        self,
        scan: ScanContext,
        scan_location: str,
        summary: Summary,
        total: int,
        skipped: int,
    ) -> Iterator["ScanDisplay"]:
        yield ScanDisplayNone()

    @abc.abstractmethod
    def scan_interrupted(
        self, message_or_exc: str | Exception, status: Status
    ) -> None: ...

    @abc.abstractmethod
    def scan_complete(self, status: Status) -> None: ...

    @abc.abstractmethod
    def scan_status(self, status: Status) -> None: ...


class ScanDisplay(abc.ABC):
    @abc.abstractmethod
    def results(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None: ...

    @abc.abstractmethod
    def metrics(self, metrics: ScanMetrics) -> None: ...


class ScanDisplayNone(ScanDisplay):
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
        pass


class TextProgress(abc.ABC):
    @abc.abstractmethod
    def update(self, text: str) -> None: ...


class TextProgressNone(TextProgress):
    def update(self, text: str) -> None:
        pass
