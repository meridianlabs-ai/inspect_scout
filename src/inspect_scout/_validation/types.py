import base64
from typing import Any

import dill  # type: ignore
from pydantic import BaseModel, Field, JsonValue, field_serializer, field_validator

from .predicates import PREDICATES, ValidationPredicate


class ValidationCase(BaseModel):
    """Validation case for comparing to scanner results.

    A `ValidationCase` specifies the ground truth for a scan of particular id (e.g. transcript id, message id, etc.
    """

    id: str | list[str]
    """Target id (e.g. transcript_id, message, id, etc.)"""

    target: JsonValue
    """Target value that the scanner is expected to output."""


class ValidationSet(BaseModel):
    """Validation set for a scanner."""

    model_config = {"arbitrary_types_allowed": True}

    cases: list[ValidationCase]
    """Cases to compare scanner values against."""

    predicate: ValidationPredicate | None = Field(default="eq")
    """Predicate for comparing scanner results to validation targets.

    For single-value targets, the predicate compares value to target directly.
    For dict targets, string/single-value predicates are applied to each key,
    while multi-value predicates receive the full dicts.
    """

    @field_serializer("predicate")
    def serialize_predicate(
        self, predicate: ValidationPredicate | None, _info: Any
    ) -> str | None:
        if predicate is None:
            return None
        if isinstance(predicate, str):
            return predicate  # String literals serialize as-is
        # Callable - use dill encoding
        pickled = dill.dumps(predicate)
        return base64.b64encode(pickled).decode("ascii")

    @field_validator("predicate", mode="before")
    @classmethod
    def deserialize_predicate(cls, v: Any) -> ValidationPredicate | None:
        if v is None or callable(v):
            return v  # type: ignore[no-any-return]
        if isinstance(v, str):
            # Check if it's a known predicate name
            if v in PREDICATES:
                return v  # type: ignore[return-value]
            # Try to decode as pickled callable
            try:
                pickled = base64.b64decode(v.encode("ascii"))
                return dill.loads(pickled)  # type: ignore[no-any-return]
            except Exception:
                # Return as string, will be validated later
                return v  # type: ignore[return-value]
        return v  # type: ignore[no-any-return]
