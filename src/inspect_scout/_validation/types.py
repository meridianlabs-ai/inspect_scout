import base64
from typing import Any, Callable, TypeAlias, TypeVar, Union

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


VT = TypeVar("VT", bound=JsonValue)

ValidationPredicate: TypeAlias = Union[
    Callable[[VT, VT], bool],
    Callable[[dict[str, JsonValue], dict[str, JsonValue]], dict[str, bool]],
]
"""Validation function use to compare scanner result to target.

Can either be a function that compares single values and returns a `bool`,
or compares `dict` of values and returns `dict[str,bool]`.
"""


class Validation(BaseModel):
    """Validation for a scanner."""

    model_config = {"arbitrary_types_allowed": True}

    cases: list[ValidationCase]
    """Cases to compare scanner values against."""

    predicate: ValidationPredicate[JsonValue] | None = Field(default=None)
    """Predicate for comparing scanner results to validation targets.

    Defaults to an equality based comparison.
    """

    @field_serializer("predicate")
    def serialize_predicate(
        self, predicate: ValidationPredicate[JsonValue] | None, _info: Any
    ) -> str | None:
        if predicate is None:
            return None
        pickled = dill.dumps(predicate)
        return base64.b64encode(pickled).decode("ascii")

    @field_validator("predicate", mode="before")
    @classmethod
    def deserialize_predicate(cls, v: Any) -> ValidationPredicate[JsonValue] | None:
        if v is None or callable(v):
            return v  # type: ignore[no-any-return]
        if isinstance(v, str):
            pickled = base64.b64decode(v.encode("ascii"))
            return dill.loads(pickled)  # type: ignore[no-any-return]
        return v  # type: ignore[no-any-return]
