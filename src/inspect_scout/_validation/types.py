from typing import Any

from pydantic import BaseModel, Field, JsonValue, field_validator
from typing_extensions import Literal

from .predicates import PREDICATES, PredicateType, ValidationPredicate


class ValidationCase(BaseModel):
    """Validation case for comparing to scanner results.

    A `ValidationCase` specifies the ground truth for a scan of particular id (e.g. transcript id, message id, etc.

    Use `target` for single-value or dict validation.
    Use `labels` for validating resultsets with label-specific expectations.
    """

    id: str | list[str]
    """Target id (e.g. transcript_id, message, id, etc.)"""

    target: JsonValue | None = Field(default=None)
    """Target value that the scanner is expected to output.

    For single-value results, this is the expected value.
    For dict-valued results, this is a dict of expected values.
    """

    labels: dict[str, bool] | None = Field(default=None)
    """Label presence/absence expectations for resultset validation.

    Maps label names to boolean expectations:
    - true: expect at least one result with a positive (non-negative) value
    - false: expect no results, or all results have negative values
    """

    predicate: PredicateType | None = Field(default=None)
    """Predicate for comparing scanner result to target (e.g., 'eq', 'gte', 'contains').

    When set, this per-case predicate overrides the global predicate on ValidationSet.
    """

    split: str | None = Field(default=None)
    """Optional split name for organizing cases (e.g., 'dev', 'test', 'train')."""

    task_id: str | None = Field(default=None)
    """Optional sample identifier from the source eval log (informational only)."""

    task_repeat: int | None = Field(default=None)
    """Optional epoch/repeat number from the source eval log (informational only)."""

    @field_validator("labels", mode="before")
    @classmethod
    def coerce_labels_to_bool(cls, v: Any) -> dict[str, bool] | None:
        """Coerce label values to boolean for backwards compatibility."""
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError(f"labels must be a dict, got {type(v).__name__}")
        return {k: bool(val) for k, val in v.items()}

    def model_post_init(self, __context: Any) -> None:
        """Validate that exactly one of target or labels is set."""
        if (self.target is None) == (self.labels is None):
            raise ValueError(
                "ValidationCase must specify exactly one of 'target' or 'labels', not both or neither"
            )


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

    split: str | list[str] | None = Field(default=None)
    """Active split filter applied to this validation set (informational)."""


class RegisteredPredicateSpec(BaseModel):
    """Portable reference to a registered custom predicate."""

    kind: Literal["registered"] = "registered"
    name: str
    args: dict[str, JsonValue] = Field(default_factory=dict)
    file: str | None = None
    package_version: str | None = None


class UnavailablePredicateSpec(BaseModel):
    """Inert marker for a custom predicate unavailable during resume."""

    kind: Literal["unavailable"] = "unavailable"
    display_name: str | None = None
    reason: Literal["anonymous", "legacy"]


PredicateSpec = (
    PredicateType | RegisteredPredicateSpec | UnavailablePredicateSpec | None
)


class ValidationSetSpec(BaseModel):
    """Data-only validation set stored in portable scan specifications."""

    cases: list[ValidationCase]
    predicate: PredicateSpec = Field(default="eq")
    split: str | list[str] | None = Field(default=None)

    @field_validator("predicate", mode="before")
    @classmethod
    def legacy_predicate_marker(cls, value: Any) -> Any:
        if isinstance(value, str) and value not in PREDICATES:
            return UnavailablePredicateSpec(reason="legacy")
        return value
