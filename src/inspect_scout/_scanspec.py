from datetime import datetime
from typing import Any

from inspect_ai.model._model_config import ModelConfig
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
)
from shortuuid import uuid
from typing_extensions import Literal, NotRequired, Required, TypedDict

from inspect_scout._validation.types import ValidationSet

from ._util.constants import DEFAULT_MAX_TRANSCRIPTS


class ScannerSpec(BaseModel):
    """Scanner used by scan."""

    name: str
    """Scanner name."""

    version: int = Field(default=0)
    """Scanner version."""

    package_version: str | None = Field(default=None)
    """Scanner package version (if in a package)."""

    file: str | None = Field(default=None)
    """Scanner source file (if not in a package)."""

    params: dict[str, Any] = Field(default_factory=dict)
    """Scanner arguments."""


GIT_VERSION_UNKNOWN = "0.0.0-dev.0+unknown"


class ScanRevision(BaseModel):
    """Git revision for scan."""

    type: Literal["git"]
    """Type of revision (currently only "git")"""

    origin: str
    """Revision origin server"""

    version: str = Field(default=GIT_VERSION_UNKNOWN)
    """Revision version (based on tags)."""

    commit: str
    """Revision commit."""


class ScanOptions(BaseModel):
    """Options used for scan."""

    max_transcripts: int = Field(default=DEFAULT_MAX_TRANSCRIPTS)
    """Maximum number of concurrent transcripts (defaults to 25)."""

    max_processes: int | None = Field(default=None)
    """Number of worker processes. Defaults to 4."""

    limit: int | None = Field(default=None)
    """Transcript limit (maximum number of transcripts to read)."""

    shuffle: bool | int | None = Field(default=None)
    """Shuffle order of transcripts."""


class TranscriptField(TypedDict, total=False):
    """Field in transcript data frame."""

    name: Required[str]
    """Field name."""

    type: Required[str]
    """Field type ("integer", "number", "boolean", "string", or "datetime")"""

    tz: NotRequired[str]
    """Timezone (for "datetime" fields)."""


class ScanTranscripts(BaseModel):
    """Transcripts targeted by a scan."""

    type: Literal["eval_log", "database"]
    """Transcripts backing store type ('eval_log' or 'database')."""

    location: str | None = Field(default=None)
    """Location of transcript collection (e.g. database location)."""

    transcript_ids: dict[str, str | None] = Field(default_factory=dict)
    """IDs of transcripts mapped to optional location hints.

    The location value depends on the backing store:
    - For parquet databases: the parquet filename containing the transcript
    - For eval logs: the log file path containing the transcript
    - For other stores (e.g., relational DB): may be None if ID alone suffices
    """

    # deprecated fields

    count: int = Field(default=0)
    """Trancript count (deprecated)."""

    fields: list[TranscriptField] | None = Field(default=None)
    """Data types of transcripts fields (deprecated)"""

    data: str | None = Field(default=None)
    """Transcript data as a csv (deprecated)"""


class Worklist(BaseModel):
    """List of transcript ids to process for a scanner."""

    scanner: str
    """Scanner name."""

    transcripts: list[str]
    """List of transcript ids."""


class ScanSpec(BaseModel):
    """Scan specification (scanners, transcripts, config)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    scan_id: str = Field(default_factory=uuid)
    """Globally unique id for scan job."""

    scan_name: str
    """Scan job name."""

    scan_file: str | None = Field(default=None)
    """Source file for scan job."""

    scan_args: dict[str, Any] | None = Field(default=None)
    """Arguments used for invoking the scan job."""

    timestamp: datetime = Field(default_factory=datetime.now)
    """Time created."""

    tags: list[str] | None = Field(default=None)
    """Tags associated with the scan."""

    metadata: dict[str, Any] | None = Field(default=None)
    """Additional scan metadata."""

    model: ModelConfig | None = Field(default=None)
    """Model used for eval."""

    model_roles: dict[str, ModelConfig] | None = Field(default=None)
    """Model roles."""

    revision: ScanRevision | None = Field(default=None)
    """Source revision of scan."""

    packages: dict[str, str] = Field(default_factory=dict)
    """Package versions for scan."""

    options: ScanOptions = Field(default_factory=ScanOptions)
    """Scan options."""

    transcripts: ScanTranscripts | None = Field(default=None)
    """Transcripts to scan."""

    scanners: dict[str, ScannerSpec]
    """Scanners to apply to transcripts."""

    worklist: list[Worklist] | None = Field(default=None)
    """Transcript ids to process for each scanner (defaults to processing all transcripts)."""

    validation: dict[str, ValidationSet] | None = Field(default=None)
    """Validation cases to apply for scanners."""

    @field_serializer("timestamp")
    def serialize_created(self, timestamp: datetime) -> str:
        return timestamp.astimezone().isoformat()
