from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from inspect_scout._query.order_by import OrderBy

from .._query.condition import Condition
from .._recorder.recorder import Status as RecorderStatus
from .._recorder.summary import Summary
from .._scanner.result import Error
from .._scanspec import ScanSpec
from .._transcript.types import TranscriptInfo


@dataclass
class Pagination:
    limit: int
    cursor: dict[str, Any] | None
    direction: Literal["forward", "backward"]


@dataclass
class TranscriptsResponse:
    items: list[TranscriptInfo]
    total_count: int
    next_cursor: dict[str, Any] | None = None


@dataclass
class IPCDataFrame:
    """Data frame serialized as Arrow IPC format."""

    format: Literal["arrow.feather"] = "arrow.feather"
    """Type of serialized data frame."""

    version: int = 2
    """Version of serialization format."""

    encoding: Literal["base64"] = "base64"
    """Encoding of serialized data frame."""

    data: str | None = None
    """Data frame serialized as Arrow IPC format."""

    row_count: int | None = None
    """Number of rows in data frame."""

    column_names: list[str] | None = None
    """List of column names in data frame."""


@dataclass
class IPCSerializableResults(RecorderStatus):
    """Scan results as serialized data frames."""

    scanners: dict[str, IPCDataFrame]
    """Dict of scanner name to serialized data frame."""

    def __init__(
        self,
        complete: bool,
        spec: ScanSpec,
        location: str,
        summary: Summary,
        errors: list[Error],
        scanners: dict[str, IPCDataFrame],
    ) -> None:
        super().__init__(complete, spec, location, summary, errors)
        self.scanners = scanners


ScanStatus: TypeAlias = RecorderStatus


@dataclass
class PaginatedRequest:
    """Base request with filter, order_by, and pagination."""

    filter: Condition | None = None
    order_by: OrderBy | list[OrderBy] | None = None
    pagination: Pagination | None = None


@dataclass
class TranscriptsRequest(PaginatedRequest):
    """Request body for POST /transcripts endpoint."""

    pass


@dataclass
class ScansRequest(PaginatedRequest):
    """Request body for POST /scans endpoint."""

    pass


@dataclass
class ScansResponse:
    """Response body for POST /scans endpoint."""

    items: list[RecorderStatus]
    total_count: int
    next_cursor: dict[str, Any] | None = None


@dataclass
class AppConfig:
    """Application configuration returned by GET /config."""

    transcripts_dir: str | None
    scans_dir: str
