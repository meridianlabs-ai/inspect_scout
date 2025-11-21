import json
from logging import getLogger
from typing import Any, Literal, Sequence

from inspect_ai._util.json import jsonable_python, to_json_str_safe
from inspect_ai.model import ModelUsage
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from shortuuid import uuid

from inspect_scout._scanner.types import ScannerInput, ScannerInputNames

logger = getLogger(__name__)


class Reference(BaseModel):
    """Reference to scanned content."""

    type: Literal["message", "event"]
    """Reference type."""

    cite: str | None = Field(default=None)
    """Cite text used when the entity was referenced (optional).

    For example, a model may have pointed to a message using something like [M22], which is the cite.
    """

    id: str
    """Reference id (message or event id)"""


class Result(BaseModel):
    """Scan result."""

    uuid: str | None = Field(default_factory=uuid)
    """Unique identifer for scan result."""

    value: JsonValue
    """Scan value."""

    answer: str | None = Field(default=None)
    """Answer extracted from model output (optional)"""

    explanation: str | None = Field(default=None)
    """Explanation of result (optional)."""

    metadata: dict[str, Any] | None = Field(default=None)
    """Additional metadata related to the result (optional)"""

    references: list[Reference] = Field(default_factory=list)
    """References to relevant messages or events."""

    label: str | None = Field(default=None)
    """Label for result to indicate its origin."""

    type: str | None = Field(default=None)
    """Type to designate contents of 'value' (used in `value_type` field in result data frames)."""


def as_resultset(results: list[Result]) -> Result:
    return Result(value=jsonable_python(results), type="resultset")


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

    refusal: bool
    """Was this error a refusal."""


class ResultValidation(BaseModel):
    target: JsonValue
    valid: bool | dict[str, bool]


class ResultReport(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    input_type: ScannerInputNames

    input_ids: list[str]

    input: ScannerInput

    result: Result | None

    validation: ResultValidation | None

    error: Error | None

    events: Sequence[dict[str, Any]]

    model_usage: dict[str, ModelUsage]

    def to_df_columns(self) -> dict[str, str | bool | int | float | None]:
        columns: dict[str, str | bool | int | float | None] = {}

        # input (transcript, event, or message)
        columns["input_type"] = self.input_type
        columns["input_ids"] = json.dumps(self.input_ids)
        columns["input"] = to_json_str_safe(self.input)

        if self.result is not None:
            # result
            columns["uuid"] = self.result.uuid
            columns["label"] = self.result.label
            if isinstance(self.result.value, str | bool | int | float | None):
                columns["value"] = self.result.value
                if isinstance(self.result.value, str):
                    columns["value_type"] = "string"
                elif isinstance(self.result.value, bool):
                    columns["value_type"] = "boolean"
                elif isinstance(self.result.value, int | float):
                    columns["value_type"] = "number"
                else:
                    columns["value_type"] = "null"

            else:
                columns["value"] = to_json_str_safe(self.result.value)
                if self.result.type is not None:
                    columns["value_type"] = self.result.type
                else:
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
                    [ref for ref in self.result.references if ref.type == type]
                )

            columns["message_references"] = references_json("message")
            columns["event_references"] = references_json("event")

            # error/refusal
            columns["scan_error"] = None
            columns["scan_error_traceback"] = None
            columns["scan_error_type"] = None
        elif self.error is not None:
            columns["uuid"] = uuid()
            columns["label"] = None
            columns["value"] = None
            columns["value_type"] = "null"
            columns["answer"] = None
            columns["explanation"] = None
            columns["metadata"] = to_json_str_safe({})
            columns["message_references"] = to_json_str_safe([])
            columns["event_references"] = to_json_str_safe([])
            columns["scan_error"] = self.error.error
            columns["scan_error_traceback"] = self.error.traceback
            columns["scan_error_type"] = "refusal"
        else:
            raise ValueError(
                "A scan result must have either a 'result', 'refusal, or 'error' field."
            )

        # report validation
        if self.validation is not None:
            columns["validation_target"] = (
                to_json_str_safe(self.validation.target)
                if isinstance(self.validation.target, list | dict)
                else self.validation.target
            )
            columns["validation_result"] = (
                to_json_str_safe(self.validation.valid)
                if isinstance(self.validation.valid, dict)
                else self.validation.valid
            )
            if isinstance(self.validation.valid, dict):
                for k, v in self.validation.valid.items():
                    columns[f"validation_result_{k}"] = v

        else:
            columns["validation_target"] = None
            columns["validation_result"] = None

        # report tokens
        total_tokens = 0
        for usage in self.model_usage.values():
            total_tokens += usage.total_tokens

        columns["scan_total_tokens"] = total_tokens
        columns["scan_model_usage"] = to_json_str_safe(self.model_usage)
        columns["scan_events"] = to_json_str_safe(self.events)

        return columns
