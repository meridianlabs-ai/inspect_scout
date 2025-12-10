from dataclasses import dataclass, fields
from functools import reduce
from typing import (
    AbstractSet,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Literal,
    NamedTuple,
    Protocol,
)

from .._scanner.result import ResultReport
from .._scanner.scanner import Scanner
from .._transcript.types import Transcript, TranscriptInfo


@dataclass
class ScanMetrics:
    """Encapsulates all worker-related metrics."""

    process_count: int = 0
    task_count: int = 0
    tasks_idle: int = 0
    tasks_parsing: int = 0
    tasks_scanning: int = 0
    buffered_scanner_jobs: int = 0
    completed_scans: int = 0
    # RSS for now, but we can revisit
    memory_usage: int = 0
    batch_pending: int = 0
    batch_failures: int = 0
    batch_oldest_created: int | None = None


def _min_or_value(a: int | None, b: int | None) -> int | None:
    return b if a is None else a if b is None else min(a, b)


_MIN_FIELDS = {"batch_oldest_created"}


def sum_metrics(metrics_list: Iterable[ScanMetrics]) -> ScanMetrics:
    def combine_metrics(a: ScanMetrics, b: ScanMetrics) -> ScanMetrics:
        combined: dict[str, Any] = {
            f.name: (
                _min_or_value(getattr(a, f.name), getattr(b, f.name))
                if f.name in _MIN_FIELDS
                else getattr(a, f.name) + getattr(b, f.name)
            )
            for f in fields(ScanMetrics)
        }
        return ScanMetrics(**combined)

    return reduce(combine_metrics, metrics_list, ScanMetrics())


class ParseJob(NamedTuple):
    """Represents a unit of work for parsing/filtering a transcript in preparation for scanning with multiple scanners."""

    transcript_info: TranscriptInfo
    """Metadata identifying which transcript to process."""

    scanner_indices: AbstractSet[int]
    """Indices into the scanner list indicating which scanners need to process this transcript."""


class ScannerJob(NamedTuple):
    """Represents a unit of work for filtering a union transcript and scanning it with a specific scanner."""

    union_transcript: Transcript
    """Transcript pre-filtered with the union of ALL scanners' content filters.

    This contains a superset of the data needed by all scanners and typically needs
    to be filtered again per-scanner (based on that scanner's specific content filter)
    before being passed to the scanner.
    """

    scanner: Scanner[Any]
    """The specific scanner to apply to the (further filtered) transcript."""

    scanner_name: str
    """The name of the scanner within the scan job."""


ParseFunctionResult = (
    tuple[Literal[True], list[ScannerJob]] | tuple[Literal[False], list[ResultReport]]
)


class ConcurrencyStrategy(Protocol):
    """Callable strategy interface (Strategy Pattern) for executing scanner work.

    This callable protocol allows either a plain async function or a class with
    an ``__call__`` coroutine method to serve as a concurrency strategy.

    Implementations control HOW work items are scheduled and executed while the
    caller supplies WHAT to execute through the `item_processor` callback.
    """

    async def __call__(
        self,
        *,
        parse_jobs: AsyncIterator[ParseJob],
        parse_function: Callable[[ParseJob], Awaitable[ParseFunctionResult]],
        scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]],
        record_results: Callable[
            [TranscriptInfo, str, list[ResultReport]], Awaitable[None]
        ],
        update_metrics: Callable[[ScanMetrics], None],
        completed: Callable[[], Awaitable[None]],
    ) -> None: ...
