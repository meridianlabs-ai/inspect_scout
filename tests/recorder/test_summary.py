"""Tests for summary module with ValidationEntry and precision/recall metrics."""

import pytest
from inspect_scout._recorder.summary import ScannerSummary
from inspect_scout._recorder.validation import (
    ValidationEntry,
    ValidationMetrics,
    ValidationResults,
    compute_validation_metrics,
)
from inspect_scout._validation.validate import is_positive_value


class TestIsPositiveValue:
    """Tests for is_positive_value helper function."""

    def test_none_is_falsy(self) -> None:
        assert is_positive_value(None) is False

    def test_false_is_falsy(self) -> None:
        assert is_positive_value(False) is False

    def test_zero_is_falsy(self) -> None:
        assert is_positive_value(0) is False

    def test_empty_string_is_falsy(self) -> None:
        assert is_positive_value("") is False

    def test_none_string_is_falsy(self) -> None:
        assert is_positive_value("NONE") is False
        assert is_positive_value("none") is False
        assert is_positive_value("None") is False

    def test_empty_dict_is_falsy(self) -> None:
        assert is_positive_value({}) is False

    def test_empty_list_is_falsy(self) -> None:
        assert is_positive_value([]) is False

    def test_true_is_truthy(self) -> None:
        assert is_positive_value(True) is True

    def test_nonzero_is_truthy(self) -> None:
        assert is_positive_value(1) is True
        assert is_positive_value(-1) is True
        assert is_positive_value(0.5) is True

    def test_nonempty_string_is_truthy(self) -> None:
        assert is_positive_value("hello") is True
        assert is_positive_value("yes") is True

    def test_nonempty_dict_is_truthy(self) -> None:
        assert is_positive_value({"key": "value"}) is True

    def test_nonempty_list_is_truthy(self) -> None:
        assert is_positive_value([1, 2, 3]) is True


class TestValidationMetrics:
    """Tests for ValidationMetrics model."""

    def test_total(self) -> None:
        metrics = ValidationMetrics(tp=5, fp=2, tn=3, fn=1)
        assert metrics.total == 11

    def test_precision(self) -> None:
        metrics = ValidationMetrics(tp=8, fp=2, tn=0, fn=0)
        assert metrics.precision == 0.8

    def test_precision_no_positive_predictions(self) -> None:
        metrics = ValidationMetrics(tp=0, fp=0, tn=5, fn=3)
        assert metrics.precision is None

    def test_recall(self) -> None:
        metrics = ValidationMetrics(tp=8, fp=0, tn=0, fn=2)
        assert metrics.recall == 0.8

    def test_recall_no_positive_targets(self) -> None:
        metrics = ValidationMetrics(tp=0, fp=2, tn=5, fn=0)
        assert metrics.recall is None

    def test_perfect_precision_and_recall(self) -> None:
        metrics = ValidationMetrics(tp=10, fp=0, tn=5, fn=0)
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0


class TestValidationMigration:
    """Tests for migrating legacy list[bool | dict[str, bool]] to ValidationResults."""

    def test_migrate_bool_list(self) -> None:
        """Legacy list of bools should migrate to ValidationResults."""
        summary = ScannerSummary.model_validate({"validation": [True, False, True]})
        assert summary.validation is not None
        assert len(summary.validation.entries) == 3
        assert all(v.target is None for v in summary.validation.entries)
        assert summary.validation.entries[0].valid is True
        assert summary.validation.entries[1].valid is False
        assert summary.validation.entries[2].valid is True
        # No metrics since no targets
        assert summary.validation.metrics is None

    def test_migrate_dict_list(self) -> None:
        """Legacy list of dict[str, bool] should migrate to ValidationResults."""
        summary = ScannerSummary.model_validate(
            {"validation": [{"a": True, "b": False}, {"a": False, "b": True}]}
        )
        assert summary.validation is not None
        assert len(summary.validation.entries) == 2
        assert all(v.target is None for v in summary.validation.entries)
        assert summary.validation.entries[0].valid == {"a": True, "b": False}

    def test_empty_list(self) -> None:
        """Empty validation list should result in None."""
        summary = ScannerSummary.model_validate({"validation": []})
        assert summary.validation is None

    def test_none_validation(self) -> None:
        """None validation should remain None."""
        summary = ScannerSummary.model_validate({"validation": None})
        assert summary.validation is None

    def test_serialized_validation_results(self) -> None:
        """Serialized ValidationResults dict (from JSON) should be deserialized."""
        # This is what we get when loading from disk after saving
        summary = ScannerSummary.model_validate(
            {
                "validation": {
                    "entries": [
                        {"target": True, "valid": True},
                        {"target": False, "valid": True},
                    ],
                    "metrics": {"tp": 1, "fp": 0, "tn": 1, "fn": 0},
                    "metrics_by_key": None,
                }
            }
        )
        assert summary.validation is not None
        assert len(summary.validation.entries) == 2
        assert summary.validation.metrics is not None
        assert summary.validation.metrics.tp == 1
        assert summary.validation.metrics.tn == 1


class TestComputeValidationMetrics:
    """Tests for compute_validation_metrics function."""

    def test_no_validations(self) -> None:
        """No validations should return None."""
        assert compute_validation_metrics([]) is None

    def test_legacy_data_no_targets(self) -> None:
        """Legacy data (all target=None) should return None."""
        validations = [
            ValidationEntry(target=None, valid=True),
            ValidationEntry(target=None, valid=False),
        ]
        assert compute_validation_metrics(validations) is None

    def test_basic_metrics(self) -> None:
        """Basic metrics computation with mixed targets."""
        validations = [
            # TP: target truthy, valid true
            ValidationEntry(target=True, valid=True),
            ValidationEntry(target="yes", valid=True),
            # FN: target truthy, valid false
            ValidationEntry(target=True, valid=False),
            # FP: target falsy, valid false
            ValidationEntry(target=False, valid=False),
            # TN: target falsy, valid true
            ValidationEntry(target=None, valid=True),  # Legacy entry, excluded
            ValidationEntry(target=False, valid=True),
        ]
        result = compute_validation_metrics(validations)
        assert result is not None
        metrics, per_key = result
        assert per_key is None  # Bool entries have no per-key metrics
        # Only entries with non-None targets counted: 5 entries
        # TP=2, FN=1, FP=1, TN=1
        assert metrics.tp == 2
        assert metrics.fn == 1
        assert metrics.fp == 1
        assert metrics.tn == 1
        # precision = 2/(2+1) = 0.666...
        assert metrics.precision == pytest.approx(2 / 3)
        # recall = 2/(2+1) = 0.666...
        assert metrics.recall == pytest.approx(2 / 3)

    def test_dict_valid_per_key_metrics(self) -> None:
        """Dict valid entries should produce per-key metrics."""
        validations = [
            ValidationEntry(target=True, valid={"a": True, "b": False}),
            ValidationEntry(target=True, valid={"a": True, "b": True}),
            ValidationEntry(target=False, valid={"a": True, "b": True}),
        ]
        result = compute_validation_metrics(validations)
        assert result is not None
        metrics, per_key = result
        assert per_key is not None
        # Per-key: a: TP=2, TN=1; b: TP=1, FN=1, TN=1
        assert per_key["a"].tp == 2
        assert per_key["a"].tn == 1
        assert per_key["b"].tp == 1
        assert per_key["b"].fn == 1
        assert per_key["b"].tn == 1
        # Total is sum of per-key
        assert metrics.tp == 3  # 2 from a, 1 from b
        assert metrics.fn == 1  # 0 from a, 1 from b
        assert metrics.tn == 2  # 1 from a, 1 from b

    def test_mixed_with_legacy(self) -> None:
        """Mixed entries with some legacy (target=None) are handled correctly."""
        validations = [
            # Legacy entries - excluded
            ValidationEntry(target=None, valid=True),
            ValidationEntry(target=None, valid=False),
            # New entries - included
            ValidationEntry(target=True, valid=True),  # TP
            ValidationEntry(target=False, valid=True),  # TN
        ]
        result = compute_validation_metrics(validations)
        assert result is not None
        metrics, per_key = result
        assert per_key is None
        assert metrics.total == 2
        assert metrics.tp == 1
        assert metrics.tn == 1
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0


class TestValidationResults:
    """Tests for ValidationResults model."""

    def test_from_entries_with_bool(self) -> None:
        """from_entries should compute metrics for bool entries."""
        entries = [
            ValidationEntry(target=True, valid=True),
            ValidationEntry(target=False, valid=True),
        ]
        results = ValidationResults.from_entries(entries)
        assert len(results.entries) == 2
        assert results.metrics is not None
        assert results.metrics.tp == 1
        assert results.metrics.tn == 1
        assert results.metrics_by_key is None

    def test_from_entries_with_dict(self) -> None:
        """from_entries should compute per-key metrics for dict entries."""
        entries = [
            ValidationEntry(target=True, valid={"a": True, "b": False}),
            ValidationEntry(target=False, valid={"a": True, "b": True}),
        ]
        results = ValidationResults.from_entries(entries)
        assert len(results.entries) == 2
        assert results.metrics is not None
        assert results.metrics_by_key is not None
        assert "a" in results.metrics_by_key
        assert "b" in results.metrics_by_key

    def test_from_entries_no_targets(self) -> None:
        """from_entries with legacy data should have no metrics."""
        entries = [
            ValidationEntry(target=None, valid=True),
            ValidationEntry(target=None, valid=False),
        ]
        results = ValidationResults.from_entries(entries)
        assert len(results.entries) == 2
        assert results.metrics is None
        assert results.metrics_by_key is None
