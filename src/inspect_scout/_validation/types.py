import base64
from typing import Any, Callable

import dill  # type: ignore
from pydantic import BaseModel, Field, JsonValue, field_serializer, field_validator


class ValidationCase(BaseModel):
    """Validation case for comparing to scanner results.

    A `ValidationCase` specifies the ground truth for a scan of particular id (e.g. transcript id, message id, etc.
    """

    id: str | list[str]
    """Target id (e.g. transcript_id, message, id, etc.)"""

    target: JsonValue
    """Target value that the scanner is expected to output."""


class Validation(BaseModel):
    """Validation for a scanner."""

    model_config = {"arbitrary_types_allowed": True}

    cases: list[ValidationCase]
    """Cases to compare scanner values against."""

    predicate: Callable[[JsonValue, JsonValue], bool] | None = Field(default=None)
    """Predicate for comparing scanner results to validation targets (defaults to equality comparison)."""

    multi_predicate: (
        Callable[[dict[str, JsonValue], dict[str, JsonValue]], dict[str, bool]] | None
    ) = Field(default=None)
    """Predicate for comparing a dict of scanner results to a dict of validation targets."""

    @field_serializer("predicate", "multi_predicate")
    def serialize_predicate(
        self, predicate: Callable[..., Any], _info: Any
    ) -> str | None:
        if predicate is None:
            return None
        pickled = dill.dumps(predicate)
        return base64.b64encode(pickled).decode("ascii")

    @field_validator("predicate", "multi_predicate", mode="before")
    @classmethod
    def deserialize_predicate(cls, v: Any) -> Callable[..., Any] | None:
        if v is None or callable(v):
            return v  # type: ignore[no-any-return]
        if isinstance(v, str):
            pickled = base64.b64decode(v.encode("ascii"))
            return dill.loads(pickled)  # type: ignore[no-any-return]
        return v  # type: ignore[no-any-return]
