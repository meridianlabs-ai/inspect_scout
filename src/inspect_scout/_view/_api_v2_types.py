from dataclasses import dataclass
from typing import Annotated, Literal, TypeAlias, Union

from inspect_ai.event import Event
from inspect_ai.model import ChatMessage
from pydantic import Field

from .._recorder.recorder import Status as RecorderStatus
from .._recorder.summary import Summary
from .._scanner.result import Error
from .._scanspec import ScanSpec
from .._transcript.types import Transcript


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


# Individual variants for discriminated union
@dataclass
class TranscriptInput:
    """Transcript input variant."""

    input: Transcript
    input_type: Literal["transcript"] = "transcript"


@dataclass
class MessageInput:
    """Single message input variant."""

    input: ChatMessage
    input_type: Literal["message"] = "message"


@dataclass
class MessagesInput:
    """Multiple messages input variant."""

    input: list[ChatMessage]
    input_type: Literal["messages"] = "messages"


@dataclass
class EventInput:
    """Single event input variant."""

    input: Event
    input_type: Literal["event"] = "event"


@dataclass
class EventsInput:
    """Multiple events input variant."""

    input: list[Event]
    input_type: Literal["events"] = "events"


# Discriminated union for scanner input
ScanResultInputData = Annotated[
    Union[TranscriptInput, MessageInput, MessagesInput, EventInput, EventsInput],
    Field(discriminator="input_type"),
]
