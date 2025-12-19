from dataclasses import dataclass
from typing import Literal, TypeAlias

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


RestScanStatus: TypeAlias = RecorderStatus


class ScansRestResponse(BaseModel):
    """Response containing list of scans from a results directory."""

    # TODO: Alias results_dir to something less Pythonic and more RESTy like results-dir?
    results_dir: str = Field(
        description="Path to the results directory containing scans.",
        examples=["/path/to/results"],
    )
    scans: list[RestScanStatus] = Field(
        description="List of scan statuses from the results directory."
    )
