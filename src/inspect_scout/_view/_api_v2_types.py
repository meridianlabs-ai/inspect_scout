from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from typing import Literal

from pydantic import BaseModel, Field

from .._recorder.recorder import Status as RecorderStatus
from .._recorder.summary import Summary
from .._scanner.result import Error
from .._scanspec import ScanSpec


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


class RestScanStatus(BaseModel):
    """
    Scan status for REST API responses.

    It extends Recorder's Status type replacing completed with statue
    """

    status: Literal["running", "completed", "incomplete"] = Field(
        description="Scan job status"
    )
    spec: ScanSpec
    location: str
    summary: Summary
    errors: list[Error]

    @staticmethod
    def _derive_status(
        location: str, complete: bool, running_scans: set[str]
    ) -> Literal["running", "completed", "incomplete"]:
        if location in running_scans:
            return "running"
        return "completed" if complete else "incomplete"

    @classmethod
    def from_recorder_status(
        cls,
        status_obj: RecorderStatus,
        running_scans: set[str],
    ) -> "RestScanStatus":
        """Convert Status dataclass to RestScanStatus.

        Uses dataclass introspection so new Status fields are automatically
        included.
        """
        field_values = {
            f.name: getattr(status_obj, f.name)
            for f in dataclass_fields(status_obj)
            if f.name != "complete"
        }
        return cls(
            status=cls._derive_status(
                status_obj.location, status_obj.complete, running_scans
            ),
            **field_values,
        )


class ScansRestResponse(BaseModel):
    """Response containing list of scans from a results directory."""

    results_dir: str = Field(
        description="Path to the results directory containing scans.",
        examples=["/path/to/results"],
    )
    scans: list[RestScanStatus] = Field(
        description="List of scan statuses from the results directory."
    )
