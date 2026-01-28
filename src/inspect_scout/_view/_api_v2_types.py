from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, JsonValue

from inspect_scout._project.types import ProjectConfig
from inspect_scout._query.order_by import OrderBy

from .._query.condition import Condition
from .._recorder.active_scans_store import ActiveScanInfo
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
class ScanStatusWithActiveInfo(RecorderStatus):
    """Scan status with optional active scan info for in-progress scans."""

    active_scan_info: ActiveScanInfo | None = None

    def __init__(
        self,
        complete: bool,
        spec: ScanSpec,
        location: str,
        summary: Summary,
        errors: list[Error],
        active_scan_info: ActiveScanInfo | None = None,
    ) -> None:
        super().__init__(complete, spec, location, summary, errors)
        self.active_scan_info = active_scan_info


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
class DistinctRequest:
    """Request body for POST /transcripts/{dir}/distinct endpoint."""

    column: str
    filter: Condition | None = None


@dataclass
class ScansRequest(PaginatedRequest):
    """Request body for POST /scans endpoint."""

    pass


@dataclass
class ScansResponse:
    """Response body for POST /scans endpoint."""

    items: list[ScanStatusWithActiveInfo]
    total_count: int
    next_cursor: dict[str, Any] | None = None


@dataclass
class ActiveScansResponse:
    """Response body for GET /scans/active endpoint."""

    items: dict[str, ActiveScanInfo]


class AppDir(BaseModel):
    """Directory with source tracking."""

    dir: str
    source: Literal["project", "cli"]


class AppConfig(ProjectConfig):
    """Application configuration returned by GET /config."""

    home_dir: str
    project_dir: str
    transcripts: AppDir | None  # type: ignore[assignment]
    scans: AppDir  # type: ignore[assignment]


@dataclass
class ValidationCaseRequest:
    """Request body for creating or updating a validation case."""

    id: str | list[str] | None = None
    """Case ID (required for create, optional for upsert where ID comes from URL path)."""

    target: JsonValue | None = None
    """Target value for the case (mutually exclusive with labels)."""

    labels: dict[str, bool] | None = None
    """Label presence/absence expectations for resultset validation (mutually exclusive with target)."""

    split: str | None = None
    """Optional split name for organizing cases."""

    predicate: str | None = None
    """Optional predicate for comparing scanner result to target."""


@dataclass
class CreateValidationSetRequest:
    """Request body for POST /validations endpoint."""

    path: str
    """Absolute URI for the new file (e.g., 'file:///Users/.../my_set.csv')."""

    cases: list[ValidationCaseRequest] = field(default_factory=list)
    """Initial cases to add to the validation set."""


@dataclass
class RenameValidationSetRequest:
    """Request body for PUT /validations/{uri}/rename endpoint."""

    name: str
    """New name for the validation set (without extension)."""


@dataclass
class ScannerParam:
    """Parameter definition for a scanner factory."""

    name: str
    """Parameter name."""

    schema: dict[str, Any]
    """JSON Schema for the parameter type."""

    required: bool
    """Whether the parameter is required."""

    default: Any | None = None
    """Default value if not required."""


@dataclass
class ScannerInfo:
    """Info about a registered scanner factory."""

    name: str
    """Scanner name."""

    version: int
    """Scanner version."""

    description: str | None
    """First line of scanner docstring."""

    params: list[ScannerParam]
    """Scanner parameters."""


@dataclass
class ScannersResponse:
    """Response body for GET /scanners endpoint."""

    items: list[ScannerInfo]
