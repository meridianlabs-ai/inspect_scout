from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from pydantic import BaseModel, ConfigDict, JsonValue

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


class ScanRow(BaseModel):
    """Flat scan row for API response - maps directly to client grid columns.

    Fields are either:
    - Extracted from source types (using model_fields to avoid duplication)
    - Transformed/flattened from nested structures
    - Computed aggregates
    """

    # === Fields extracted from source types (no type duplication) ===
    # fmt: off
    scan_id: ScanSpec.model_fields["scan_id"].annotation  # type: ignore[valid-type]  # noqa: F821
    scan_name: ScanSpec.model_fields["scan_name"].annotation  # type: ignore[valid-type]  # noqa: F821
    scan_file: ScanSpec.model_fields["scan_file"].annotation  # type: ignore[valid-type]  # noqa: F821
    timestamp: ScanSpec.model_fields["timestamp"].annotation  # type: ignore[valid-type]  # noqa: F821
    packages: ScanSpec.model_fields["packages"].annotation  # type: ignore[valid-type]  # noqa: F821
    metadata: ScanSpec.model_fields["metadata"].annotation  # type: ignore[valid-type]  # noqa: F821
    scan_args: ScanSpec.model_fields["scan_args"].annotation  # type: ignore[valid-type]  # noqa: F821
    # fmt: on
    location: str  # from Status dataclass

    # === Transformed/flattened fields ===
    status: Literal["active", "error", "complete", "incomplete"]
    scanners: str  # comma-separated scanner names
    model: str | None  # extracted from ModelConfig.model
    tags: str  # comma-separated tags
    revision_version: str | None
    revision_commit: str | None
    revision_origin: str | None

    # === Computed aggregate fields ===
    total_results: int
    total_errors: int
    total_tokens: int

    # === For active scan progress (None if not active) ===
    active_completion_pct: int | None = None

    @staticmethod
    def from_status(
        status: RecorderStatus,
        active_scan_info: ActiveScanInfo | None = None,
    ) -> "ScanRow":
        """Create a ScanRow from a Status object."""
        spec = status.spec

        # Aggregate summary fields
        total_results = 0
        total_errors = 0
        total_tokens = 0
        for scanner_summary in status.summary.scanners.values():
            total_results += scanner_summary.results
            total_errors += scanner_summary.errors
            total_tokens += scanner_summary.tokens

        return ScanRow(
            # Extracted fields
            scan_id=spec.scan_id,
            scan_name=spec.scan_name,
            scan_file=spec.scan_file,
            timestamp=spec.timestamp,
            packages=spec.packages,
            metadata=spec.metadata,
            scan_args=spec.scan_args,
            location=status.location,
            # Computed fields
            status=(
                "active"
                if active_scan_info
                else "error"
                if status.errors
                else "complete"
                if status.complete
                else "incomplete"
            ),
            scanners=",".join(spec.scanners.keys()) if spec.scanners else "",
            model=(
                getattr(spec.model, "model", None) or str(spec.model)
                if spec.model
                else None
            ),
            tags=",".join(spec.tags) if spec.tags else "",
            revision_version=spec.revision.version if spec.revision else None,
            revision_commit=spec.revision.commit if spec.revision else None,
            revision_origin=spec.revision.origin if spec.revision else None,
            total_results=total_results,
            total_errors=total_errors,
            total_tokens=total_tokens,
            active_completion_pct=(
                None
                if active_scan_info is None
                else 0
                if active_scan_info.total_scans == 0
                else round(
                    active_scan_info.metrics.completed_scans
                    / active_scan_info.total_scans
                    * 100
                )
            ),
        )


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

    items: list[ScanRow]
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


class MessagesEventsResponse(BaseModel):
    """Response for GET /transcripts/{dir}/{id}/messages-events endpoint."""

    messages: list[ChatMessage]
    events: list[Event]
    attachments: dict[str, str] | None = None

    model_config = ConfigDict(extra="allow")


@dataclass
class StreamMetadata:
    """Metadata yielded first from streaming generators."""

    compression_method: int | None
    uncompressed_size: int | None
