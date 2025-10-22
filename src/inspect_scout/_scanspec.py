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

from ._util.constants import DEFAULT_MAX_TRANSCRIPTS
from ._util.process import default_max_processes


class ScanScanner(BaseModel):
    """Scanner used by scan."""

    name: str
    """Scanner name."""

    file: str | None = Field(default=None)
    """Scanner source file (if not in a package)."""

    params: dict[str, Any] = Field(default_factory=dict)
    """Scanner arguments."""


class ScanRevision(BaseModel):
    """Git revision for scan."""

    type: Literal["git"]
    """Type of revision (currently only "git")"""

    origin: str
    """Revision origin server"""

    commit: str
    """Revision commit."""


class ScanOptions(BaseModel):
    """Options used for scan."""

    max_transcripts: int = Field(default=DEFAULT_MAX_TRANSCRIPTS)
    """Maximum number of concurrent transcripts (defaults to 25)."""

    max_processes: int = Field(default_factory=default_max_processes)
    """Number of worker processes. Defaults to `multiprocessing.cpu_count()`."""

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
    """Transcripts target by a scan."""

    type: str
    """Transcripts backing store type (currently only 'eval_log')."""

    fields: list[TranscriptField]
    """Data types of transcripts fields."""

    count: int = Field(default=0)
    """Trancript count."""

    data: str
    """Transcript data as a csv."""


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

    transcripts: ScanTranscripts
    """Transcripts to scan."""

    scanners: dict[str, ScanScanner]
    """Scanners to apply to transcripts."""

    @field_serializer("timestamp")
    def serialize_created(self, timestamp: datetime) -> str:
        return timestamp.astimezone().isoformat()
