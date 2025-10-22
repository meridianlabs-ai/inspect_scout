from typing import Any, Literal, Sequence

from inspect_ai._util.json import to_json_str_safe
from inspect_ai.event import Event
from inspect_ai.model import ModelUsage
from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Reference(BaseModel):
    """Reference to scanned content."""

    type: Literal["message", "event"]
    """Reference type."""

    id: str
    """Reference id (message or event id)"""


class Result(BaseModel):
    """Scan result."""

    value: JsonValue
    """Scan value (can be `None` if the scan didn't find what is was looking for)."""

    answer: str | None = Field(default=None)
    """Answer extracted from model output (optional)"""

    explanation: str | None = Field(default=None)
    """Explanation of result (optional)."""

    metadata: dict[str, Any] | None = Field(default=None)
    """Additional metadata related to the result (optional)"""

    references: list[Reference] = Field(default_factory=list)
    """References to relevant messages or events."""


class Error(BaseModel):
    """Scan error (runtime error which occurred during scan)."""

    transcript_id: str
    """Target transcript id."""

    scanner: str
    """Scanner name."""

    error: str
    """Error message."""

    traceback: str
    """Error traceback."""


class ResultReport(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    input_type: Literal["transcript", "event", "message"]

    input_id: str

    result: Result | None

    error: Error | None

    events: Sequence[Event]

    model_usage: dict[str, ModelUsage]

    def to_df_columns(self) -> dict[str, str | bool | int | float | None]:
        columns: dict[str, str | bool | int | float | None] = {}

        # input (transcript, event, or message)
        columns["input_type"] = self.input_type
        columns["input_id"] = self.input_id

        if self.result is not None:
            # result
            if isinstance(self.result.value, str | bool | int | float | None):
                columns["value"] = self.result.value
                if isinstance(self.result.value, str):
                    columns["value_type"] = "string"
                elif isinstance(self.result.value, int | float):
                    columns["value_type"] = "number"
                elif isinstance(self.result.value, bool):
                    columns["value_type"] = "boolean"
                else:
                    columns["value_type"] = "null"

            else:
                columns["value"] = to_json_str_safe(self.result.value)
                columns["value_type"] = (
                    "array" if isinstance(self.result.value, list) else "object"
                )
            columns["answer"] = self.result.answer
            columns["explanation"] = self.result.explanation
            columns["metadata"] = to_json_str_safe(self.result.metadata or {})

            # references
            def references_json(type: str) -> str:
                assert self.result
                return to_json_str_safe(
                    [ref.id for ref in self.result.references if ref.type == type]
                )

            columns["message_references"] = references_json("message")
            columns["event_references"] = references_json("event")

            # error
            columns["scan_error"] = None
            columns["scan_error_traceback"] = None
        elif self.error is not None:
            columns["value"] = None
            columns["value_type"] = "null"
            columns["answer"] = None
            columns["explanation"] = None
            columns["metadata"] = to_json_str_safe({})
            columns["message_references"] = to_json_str_safe([])
            columns["event_references"] = to_json_str_safe([])
            columns["scan_error"] = self.error.error
            columns["scan_error_traceback"] = self.error.traceback
        else:
            raise ValueError(
                "A scan result must have either a 'result' or 'error' field."
            )

        # report tokens
        total_tokens = 0
        for usage in self.model_usage.values():
            total_tokens += usage.total_tokens

        columns["scan_total_tokens"] = total_tokens
        columns["scan_model_usage"] = to_json_str_safe(self.model_usage)
        columns["scan_events"] = to_json_str_safe(self.events)

        return columns
