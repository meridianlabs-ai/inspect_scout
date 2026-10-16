from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)
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
    """Portable reference to a custom predicate registered with `@validation_predicate`.

    Only the registered name and creation arguments are stored; the predicate
    is recreated from the registry when the scan is resumed.
    """

    model_config = ConfigDict(allow_inf_nan=False)

    kind: Literal["registered"] = "registered"
    """Discriminator for the predicate spec type."""

    name: str
    """Registered predicate name (prefixed with the package name if in a package)."""

    args: dict[str, JsonValue] = Field(default_factory=dict)
    """Arguments used to create the predicate (Inspect registry parameter form)."""

    file: str | None = None
    """Predicate source file (if not in a package). Loaded when the scan is resumed."""

    package_version: str | None = None
    """Predicate package version (if in a package)."""


class UnavailablePredicateSpec(BaseModel):
    """Inert marker for a custom predicate that cannot be recreated from the scan artifact.

    Written for anonymous callables (not registered with `@validation_predicate`)
    and substituted in memory for legacy serialized predicates. Resuming a scan
    with an unavailable predicate requires `predicate_overrides`.
    """

    kind: Literal["unavailable"] = "unavailable"
    """Discriminator for the predicate spec type."""

    display_name: str | None = None
    """Name of the original callable, for display only."""

    reason: Literal["anonymous", "legacy"]
    """Why the predicate is unavailable: an unregistered callable, or a legacy serialized predicate."""


PredicateSpec = (
    PredicateType | RegisteredPredicateSpec | UnavailablePredicateSpec | None
)


class ValidationSetSpec(BaseModel):
    """Data-only validation set stored in portable scan specifications (`_scan.json`).

    Unlike `ValidationSet`, the predicate is never a callable: it is a built-in
    predicate name, a `RegisteredPredicateSpec`, or an `UnavailablePredicateSpec`.
    Parsing a spec never imports or executes predicate code.
    """

    cases: list[ValidationCase]
    """Cases to compare scanner values against."""

    predicate: PredicateSpec = Field(default="eq")
    """Predicate used to compare scanner results to validation targets."""

    split: str | list[str] | None = Field(default=None)
    """Active split filter applied to this validation set (informational)."""

    @model_validator(mode="before")
    @classmethod
    def legacy_predicate_marker(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        predicate = value.get("predicate")
        if isinstance(predicate, str) and predicate not in PREDICATES:
            return {
                **value,
                "predicate": UnavailablePredicateSpec(reason="legacy"),
            }
        return value
