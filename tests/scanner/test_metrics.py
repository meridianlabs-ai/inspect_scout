"""Tests for scanner metrics feature."""

import tempfile
import time
from pathlib import Path

import pytest
from inspect_ai._util.registry import registry_info
from inspect_ai.scorer import mean, stderr
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._scanner.metrics import (
    MetricsAccumulator,
    as_score_value,
    metrics_accumulators,
    metrics_for_scanner,
)
from inspect_scout._scanner.scanner import SCANNER_METRICS
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout._util.throttle import throttle

# Test data location
LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


# =============================================================================
# Unit Tests: Throttle Decorator
# =============================================================================


def test_throttle_first_call_always_executes() -> None:
    """First call to throttled function should always execute."""
    call_count = 0

    @throttle(10)  # 10 second throttle - won't expire during test
    def tracked_func() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    result = tracked_func()
    assert result == 1
    assert call_count == 1


def test_throttle_returns_cached_result_within_interval() -> None:
    """Calls within throttle interval should return cached result."""
    call_count = 0

    @throttle(10)  # 10 second throttle
    def tracked_func() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    result1 = tracked_func()
    result2 = tracked_func()
    result3 = tracked_func()

    assert result1 == 1
    assert result2 == 1  # Cached
    assert result3 == 1  # Cached
    assert call_count == 1  # Only called once


def test_throttle_calls_function_after_interval() -> None:
    """Function should be called again after throttle interval expires."""
    call_count = 0

    @throttle(0.1)  # 100ms throttle
    def tracked_func() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    result1 = tracked_func()
    assert result1 == 1
    assert call_count == 1

    # Wait for throttle to expire
    time.sleep(0.15)

    result2 = tracked_func()
    assert result2 == 2
    assert call_count == 2


# =============================================================================
# Unit Tests: as_score_value
# =============================================================================


def test_as_score_value_numeric_int() -> None:
    """Integer values should pass through unchanged."""
    assert as_score_value(42) == 42


def test_as_score_value_numeric_float() -> None:
    """Float values should pass through unchanged."""
    assert as_score_value(3.14) == 3.14


def test_as_score_value_bool() -> None:
    """Boolean values should pass through unchanged."""
    assert as_score_value(True) is True
    assert as_score_value(False) is False


def test_as_score_value_string() -> None:
    """String values should pass through unchanged."""
    assert as_score_value("correct") == "correct"


def test_as_score_value_list_of_scalars() -> None:
    """List of scalar values should pass through unchanged."""
    result = as_score_value([1, 2, 3])
    assert result == [1, 2, 3]


def test_as_score_value_list_with_nested() -> None:
    """List with nested structures should serialize non-scalars to JSON."""
    result = as_score_value([1, {"nested": "dict"}, 3])
    assert isinstance(result, list)
    assert result[0] == 1
    assert isinstance(result[1], str)  # Serialized to JSON string
    assert result[2] == 3


def test_as_score_value_dict_of_scalars() -> None:
    """Dict with scalar values should pass through unchanged."""
    result = as_score_value({"a": 1, "b": "test", "c": True})
    assert result == {"a": 1, "b": "test", "c": True}


def test_as_score_value_dict_with_nested() -> None:
    """Dict with nested structures should serialize non-scalars to JSON."""
    result = as_score_value({"a": 1, "b": {"nested": "dict"}})
    assert isinstance(result, dict)
    assert result["a"] == 1
    assert isinstance(result["b"], str)  # Serialized to JSON string


def test_as_score_value_none_raises() -> None:
    """None values should raise AssertionError."""
    with pytest.raises(AssertionError):
        as_score_value(None)


# =============================================================================
# Unit Tests: MetricsAccumulator
# =============================================================================


def test_metrics_accumulator_add_result_numeric() -> None:
    """MetricsAccumulator should accumulate numeric results."""
    accumulator = MetricsAccumulator(scanner="test", metrics=[mean()])
    accumulator.add_result(5)
    accumulator.add_result(10)
    accumulator.add_result(15)

    assert len(accumulator._scores) == 3


def test_metrics_accumulator_add_result_skips_none() -> None:
    """MetricsAccumulator should skip None values."""
    accumulator = MetricsAccumulator(scanner="test", metrics=[mean()])
    accumulator.add_result(5)
    accumulator.add_result(None)
    accumulator.add_result(10)

    assert len(accumulator._scores) == 2


def test_metrics_accumulator_compute_metrics_with_mean() -> None:
    """MetricsAccumulator should compute mean correctly."""
    accumulator = MetricsAccumulator(scanner="test_scanner", metrics=[mean()])
    accumulator.add_result(2)
    accumulator.add_result(4)
    accumulator.add_result(6)

    metrics = accumulator.compute_metrics()

    # The metrics dict structure is {scorer_name: {metric_name: value}}
    assert "test_scanner" in metrics
    assert "mean" in metrics["test_scanner"]
    assert metrics["test_scanner"]["mean"] == 4.0  # (2+4+6)/3


def test_metrics_accumulator_compute_metrics_multiple() -> None:
    """MetricsAccumulator should compute multiple metrics."""
    accumulator = MetricsAccumulator(scanner="test_scanner", metrics=[mean(), stderr()])
    for i in range(10):
        accumulator.add_result(i)

    metrics = accumulator.compute_metrics()

    assert "test_scanner" in metrics
    assert "mean" in metrics["test_scanner"]
    assert "stderr" in metrics["test_scanner"]


def test_metrics_accumulator_compute_metrics_throttled() -> None:
    """Throttled compute should return cached result within interval."""
    accumulator = MetricsAccumulator(scanner="test", metrics=[mean()])
    accumulator.add_result(10)

    # First call computes
    metrics1 = accumulator.compute_metrics_throttled()

    # Add more data
    accumulator.add_result(20)

    # Second call should return cached (within 3s throttle)
    metrics2 = accumulator.compute_metrics_throttled()

    # Both should have same mean (10) since second call is throttled
    assert metrics1["test"]["mean"] == metrics2["test"]["mean"]


# =============================================================================
# Unit Tests: Helper Functions
# =============================================================================


def test_metrics_for_scanner_returns_none_when_no_metrics() -> None:
    """metrics_for_scanner should return None for scanners without metrics."""

    @scanner(messages="all")
    def no_metrics_scanner() -> Scanner[Transcript]:
        async def scan_fn(transcript: Transcript) -> Result:
            return Result(value=True)

        return scan_fn

    instance = no_metrics_scanner()
    result = metrics_for_scanner(instance)
    assert result is None


def test_metrics_for_scanner_returns_metrics() -> None:
    """metrics_for_scanner should return metrics for scanners with metrics."""

    @scanner(messages="all", metrics=[mean()])
    def with_metrics_scanner() -> Scanner[Transcript]:
        async def scan_fn(transcript: Transcript) -> Result:
            return Result(value=5)

        return scan_fn

    instance = with_metrics_scanner()
    result = metrics_for_scanner(instance)
    assert result is not None
    assert len(result) == 1


def test_metrics_accumulators_creates_for_scanners_with_metrics() -> None:
    """metrics_accumulators should only create accumulators for scanners with metrics."""

    @scanner(messages="all", metrics=[mean()])
    def with_metrics() -> Scanner[Transcript]:
        async def scan_fn(transcript: Transcript) -> Result:
            return Result(value=5)

        return scan_fn

    @scanner(messages="all")
    def without_metrics() -> Scanner[Transcript]:
        async def scan_fn(transcript: Transcript) -> Result:
            return Result(value=True)

        return scan_fn

    scanners = {
        "with_metrics": with_metrics(),
        "without_metrics": without_metrics(),
    }

    accumulators = metrics_accumulators(scanners)

    assert "with_metrics" in accumulators
    assert "without_metrics" not in accumulators


# =============================================================================
# Integration Tests: Scanner Decorator with Metrics
# =============================================================================


def test_scanner_decorator_stores_metrics_in_registry() -> None:
    """Scanner decorator should store metrics in registry metadata."""

    @scanner(messages="all", metrics=[mean()])
    def metrics_scanner() -> Scanner[Transcript]:
        async def scan_fn(transcript: Transcript) -> Result:
            return Result(value=5)

        return scan_fn

    instance = metrics_scanner()
    info = registry_info(instance)

    assert SCANNER_METRICS in info.metadata
    assert info.metadata[SCANNER_METRICS] is not None


def test_scanner_decorator_metrics_with_dict_syntax() -> None:
    """Scanner decorator should accept dict metrics syntax for labeled results."""

    @scanner(messages="all", metrics=[{"*": [mean(), stderr()]}])
    def labeled_scanner() -> Scanner[Transcript]:
        async def scan_fn(transcript: Transcript) -> Result:
            return Result(value=5, label="category_a")

        return scan_fn

    instance = labeled_scanner()
    info = registry_info(instance)

    assert SCANNER_METRICS in info.metadata
    metrics = info.metadata[SCANNER_METRICS]
    assert metrics is not None
    # Should be a list containing a dict
    assert isinstance(metrics, list)
    assert len(metrics) == 1
    assert isinstance(metrics[0], dict)


# =============================================================================
# End-to-End Tests: Full Scan with Metrics
# =============================================================================


@scanner(name="numeric_metrics_scanner", messages="all", metrics=[mean()])
def numeric_metrics_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns deterministic numeric values for metric testing."""

    async def scan_transcript(transcript: Transcript) -> Result:
        # Return a deterministic value based on transcript ID
        # Using abs() and modulo to get consistent values 1-10
        value = (abs(hash(transcript.transcript_id)) % 10) + 1
        return Result(
            value=value,
            explanation=f"Numeric value: {value}",
        )

    return scan_transcript


@scanner(name="no_metrics_comparison_scanner", messages="all")
def no_metrics_comparison_scanner_factory() -> Scanner[Transcript]:
    """Scanner without metrics for comparison testing."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=True,
            explanation="Simple boolean result",
        )

    return scan_transcript


def test_scan_with_numeric_scanner_metrics() -> None:
    """Test full scan pipeline with a scanner that has mean() metric."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[numeric_metrics_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=3,
            display="none",
        )

        # Verify scan completed
        assert status.complete
        assert status.location is not None

        # Verify summary has metrics
        summary = status.summary
        scanner_summary = summary.scanners["numeric_metrics_scanner"]

        # Metrics should be computed
        assert scanner_summary.metrics is not None
        assert "numeric_metrics_scanner" in scanner_summary.metrics
        assert "mean" in scanner_summary.metrics["numeric_metrics_scanner"]

        # Mean should be a reasonable value (between 1 and 10)
        mean_value = scanner_summary.metrics["numeric_metrics_scanner"]["mean"]
        assert 1.0 <= mean_value <= 10.0


def test_scan_with_multiple_scanners_mixed_metrics() -> None:
    """Test scan with multiple scanners, some with metrics and some without."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[
                numeric_metrics_scanner_factory(),
                no_metrics_comparison_scanner_factory(),
            ],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=2,
            display="none",
        )

        # Verify scan completed
        assert status.complete

        # Verify summary
        summary = status.summary

        # Scanner with metrics should have metrics
        with_metrics = summary.scanners["numeric_metrics_scanner"]
        assert with_metrics.metrics is not None

        # Scanner without metrics should not have metrics
        without_metrics = summary.scanners["no_metrics_comparison_scanner"]
        assert without_metrics.metrics is None


def test_scan_metrics_values_are_correct() -> None:
    """Test that computed metrics match expected values."""

    # Create a scanner with known, predictable outputs
    @scanner(name="predictable_scanner", messages="all", metrics=[mean()])
    def predictable_scanner_factory() -> Scanner[Transcript]:
        """Scanner that returns the same value for all transcripts."""

        async def scan_transcript(transcript: Transcript) -> Result:
            return Result(value=5)  # Always returns 5

        return scan_transcript

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[predictable_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=3,
            display="none",
        )

        assert status.complete

        # Since all values are 5, mean should be exactly 5
        metrics = status.summary.scanners["predictable_scanner"].metrics
        assert metrics is not None
        assert metrics["predictable_scanner"]["mean"] == 5.0


def test_scan_metrics_with_multiple_metrics() -> None:
    """Test scanner with multiple metrics (mean and stderr)."""

    @scanner(name="multi_metrics_scanner", messages="all", metrics=[mean(), stderr()])
    def multi_metrics_scanner_factory() -> Scanner[Transcript]:
        """Scanner with multiple metrics."""

        async def scan_transcript(transcript: Transcript) -> Result:
            value = (abs(hash(transcript.transcript_id)) % 10) + 1
            return Result(value=value)

        return scan_transcript

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[multi_metrics_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            scans=tmpdir,
            limit=5,
            display="none",
        )

        assert status.complete

        metrics = status.summary.scanners["multi_metrics_scanner"].metrics
        assert metrics is not None
        assert "mean" in metrics["multi_metrics_scanner"]
        assert "stderr" in metrics["multi_metrics_scanner"]
