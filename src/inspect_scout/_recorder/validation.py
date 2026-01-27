"""Validation metrics for scanner results."""

from typing import Any

from pydantic import BaseModel, Field, JsonValue, computed_field, model_validator
from typing_extensions import Self

from inspect_scout._validation.validate import is_positive_value


class ValidationEntry(BaseModel):
    """A single validation result with its target."""

    id: str | list[str]
    """ID(s) from the validation case (e.g., transcript_id)."""

    target: JsonValue
    """Expected target value."""

    valid: bool | dict[str, bool]
    """Whether validation passed."""

    @model_validator(mode="before")
    @classmethod
    def default_missing_fields(cls, data: Any) -> Any:
        """Default missing fields for legacy serialized data."""
        if isinstance(data, dict):
            if "id" not in data:
                data["id"] = ""
            if "target" not in data:
                data["target"] = None
        return data


class ValidationMetrics(BaseModel):
    """Confusion matrix counts for precision/recall."""

    tp: int = 0
    """Target truthy, validation passed."""

    fp: int = 0
    """Target falsy, validation failed."""

    tn: int = 0
    """Target falsy, validation passed."""

    fn: int = 0
    """Target truthy, validation failed."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @computed_field  # type: ignore[prop-decorator]
    @property
    def precision(self) -> float | None:
        """TP / (TP + FP). None if no positive predictions."""
        denominator = self.tp + self.fp
        if denominator == 0:
            return None
        return self.tp / denominator

    @computed_field  # type: ignore[prop-decorator]
    @property
    def recall(self) -> float | None:
        """TP / (TP + FN). None if no positive targets."""
        denominator = self.tp + self.fn
        if denominator == 0:
            return None
        return self.tp / denominator

    @computed_field  # type: ignore[prop-decorator]
    @property
    def specificity(self) -> float | None:
        """TN / (TN + FP). None if no negative targets."""
        denominator = self.tn + self.fp
        if denominator == 0:
            return None
        return self.tn / denominator

    @computed_field  # type: ignore[prop-decorator]
    @property
    def f1(self) -> float | None:
        """Harmonic mean of precision and recall."""
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def accuracy(self) -> float | None:
        """Balanced accuracy: (Recall + Specificity) / 2."""
        r, s = self.recall, self.specificity
        if r is None or s is None:
            return None
        return (r + s) / 2


class ValidationResults(BaseModel):
    """Validation entries with pre-computed metrics."""

    entries: list[ValidationEntry] = Field(default_factory=list)
    """Individual validation results."""

    metrics: ValidationMetrics | None = Field(default=None)
    """Total/aggregate metrics. None if no entries with targets."""

    metrics_by_key: dict[str, ValidationMetrics] | None = Field(default=None)
    """Per-key breakdown (only for dict-based entries). None for bool entries."""

    @classmethod
    def from_entries(cls, entries: list[ValidationEntry]) -> Self:
        """Create ValidationResults with computed metrics."""
        result = compute_validation_metrics(entries)
        if result is None:
            return cls(entries=entries)
        total, per_key = result
        return cls(entries=entries, metrics=total, metrics_by_key=per_key)


def _update_metrics(
    metrics: ValidationMetrics, target_positive: bool, valid: bool
) -> None:
    """Update confusion matrix based on target and validation result."""
    if target_positive and valid:
        metrics.tp += 1
    elif target_positive and not valid:
        metrics.fn += 1
    elif not target_positive and valid:
        metrics.tn += 1
    else:
        metrics.fp += 1


def compute_validation_metrics(
    entries: list[ValidationEntry],
) -> tuple[ValidationMetrics, dict[str, ValidationMetrics] | None] | None:
    """Compute metrics from validation entries.

    Returns (total_metrics, per_key_metrics) tuple.
    per_key_metrics is None for bool-based entries, dict for dict-based entries.
    Returns None if no entries have non-None targets.

    Note: If entries contain a mix of bool and dict `valid` values, only dict
    entries are processed (bool entries are silently skipped). This handles
    edge cases in incremental data collection but should be rare in practice.
    """
    # Filter to entries with non-None targets
    with_targets = [e for e in entries if e.target is not None]
    if not with_targets:
        return None

    # Check if any entry has dict-based valid
    has_dict_entries = any(isinstance(e.valid, dict) for e in with_targets)

    if has_dict_entries:
        # Per-key metrics
        per_key: dict[str, ValidationMetrics] = {}
        for entry in with_targets:
            target_positive = is_positive_value(entry.target)
            if isinstance(entry.valid, dict):
                for key, valid in entry.valid.items():
                    if key not in per_key:
                        per_key[key] = ValidationMetrics()
                    _update_metrics(per_key[key], target_positive, valid)

        # Total is sum of per-key
        total = ValidationMetrics()
        for m in per_key.values():
            total.tp += m.tp
            total.fp += m.fp
            total.tn += m.tn
            total.fn += m.fn
        return (total, per_key)
    else:
        # Bool entries - just total
        total = ValidationMetrics()
        for entry in with_targets:
            target_positive = is_positive_value(entry.target)
            _update_metrics(total, target_positive, entry.valid)  # type: ignore[arg-type]
        return (total, None)
