import abc
from dataclasses import dataclass
from types import TracebackType
from typing import Callable, Sequence, TypeAlias

import duckdb
import pandas as pd

from .._scanner.result import Error, ResultReport
from .._scanspec import ScanSpec
from .._transcript.types import TranscriptInfo


@dataclass
class ScanStatus:
    complete: bool
    spec: ScanSpec
    location: str


@dataclass
class ScanResults(ScanStatus):
    data: dict[str, pd.DataFrame]

    def __init__(
        self,
        status: bool,
        spec: ScanSpec,
        location: str,
        data: dict[str, pd.DataFrame],
    ) -> None:
        super().__init__(status, spec, location)
        self.data = data


ScanResultsFilter: TypeAlias = Callable[[pd.DataFrame], pd.Series]


@dataclass
class ScanResultsDB(ScanStatus):
    conn: duckdb.DuckDBPyConnection

    def __init__(
        self,
        status: bool,
        spec: ScanSpec,
        location: str,
        conn: duckdb.DuckDBPyConnection,
    ) -> None:
        super().__init__(status, spec, location)
        self.conn = conn

    def __enter__(self) -> "ScanResultsDB":
        """Enter the async context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.conn.close()


class ScanRecorder(abc.ABC):
    @abc.abstractmethod
    async def init(self, spec: ScanSpec, scans_location: str) -> None: ...

    @abc.abstractmethod
    async def resume(self, scan_location: str) -> ScanSpec: ...

    @abc.abstractmethod
    async def location(self) -> str: ...

    @abc.abstractmethod
    async def is_recorded(self, transcript: TranscriptInfo, scanner: str) -> bool: ...

    @abc.abstractmethod
    async def record(
        self, transcript: TranscriptInfo, scanner: str, results: Sequence[ResultReport]
    ) -> None: ...

    @abc.abstractmethod
    async def flush(self) -> None: ...

    @abc.abstractmethod
    async def errors(self) -> list[Error]: ...

    @abc.abstractmethod
    async def complete(self) -> ScanStatus: ...

    @staticmethod
    @abc.abstractmethod
    async def status(scan_location: str) -> ScanStatus: ...

    @staticmethod
    @abc.abstractmethod
    async def results(
        scan_location: str,
        *,
        scanner: str | None = None,
        filter: ScanResultsFilter | None = None,
    ) -> ScanResults: ...

    @staticmethod
    @abc.abstractmethod
    async def results_db(scan_location: str) -> ScanResultsDB: ...
