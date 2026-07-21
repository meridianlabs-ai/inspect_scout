"""Tests for label-based validation of resultsets."""

import json
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result, Scanner, scanner
from inspect_scout._scanresults import _expand_resultset_rows
from inspect_scout._transcript.types import Transcript
from inspect_scout._validation.validate import _validate_labels, is_positive_value
from inspect_scout._validation.validation import validation_set

# Test data location
LOGS_DIR = Path(__file__).parent.parent / "examples" / "scanner" / "logs"

# Test transcript ID for integration tests
TEST_TRANSCRIPT_ID = "test-transcript-123"


def create_test_transcript() -> Transcript:
    """Create a simple test transcript with a known ID."""
    return Transcript(
        transcript_id=TEST_TRANSCRIPT_ID,
        source_type="test",
        source_id="test-source",
        source_uri="test://source",
        messages=[
            ChatMessageUser(content="Hello, can you help me?"),
        ],
        metadata={},
    )


@scanner(name="multi_finding_scanner", messages="all")
def multi_finding_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns multiple findings per transcript."""

    async def scan_transcript(transcript: Transcript) -> list[Result]:
        # Return different findings based on transcript ID
        if len(transcript.transcript_id) % 3 == 0:
            # Return deception and jailbreak
            return [
                Result(label="deception", value=True, explanation="Found deception"),
                Result(label="jailbreak", value=True, explanation="Found jailbreak"),
            ]

        elif len(transcript.transcript_id) % 3 == 1:
            # Return only deception
            return [
                Result(label="deception", value=True, explanation="Found deception"),
            ]

        else:
            # Return no findings (all false/absent)
            return []

    return scan_transcript


def test_csv_label_parsing() -> None:
    """Test parsing CSV with label_* columns."""
    csv_content = """id,label_deception,label_jailbreak
transcript-1,true,false
transcript-2,false,true"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()

        vset = validation_set(f.name)

        # Check that we have 2 cases
        assert len(vset.cases) == 2

        # Check first case
        case1 = vset.cases[0]
        assert case1.id == "transcript-1"
        assert case1.labels is not None
        assert case1.labels == {"deception": True, "jailbreak": False}
        assert case1.target is None

        # Check second case
        case2 = vset.cases[1]
        assert case2.id == "transcript-2"
        assert case2.labels is not None
        assert case2.labels == {"deception": False, "jailbreak": True}

    Path(f.name).unlink()


def test_yaml_label_parsing() -> None:
    """Test parsing YAML with labels: key."""
    yaml_content = """
- id: transcript-1
  labels:
    deception: true
    jailbreak: false
- id: transcript-2
  labels:
    deception: false
    jailbreak: true
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        vset = validation_set(f.name)

        # Check that we have 2 cases
        assert len(vset.cases) == 2

        # Check first case
        case1 = vset.cases[0]
        assert case1.id == "transcript-1"
        assert case1.labels is not None
        assert case1.labels == {"deception": True, "jailbreak": False}

    Path(f.name).unlink()


def test_label_validation_basic() -> None:
    """Test basic label-based validation format is stored correctly."""
    # This test validates that label-based ValidationCases can be created
    # Integration with scan is tested in other tests
    val_df = pd.DataFrame(
        [
            {"id": "test-id", "label_deception": True, "label_jailbreak": False},
        ]
    )

    vset = validation_set(val_df)
    assert len(vset.cases) == 1
    case = vset.cases[0]
    assert case.labels is not None
    assert case.labels == {"deception": True, "jailbreak": False}
    assert case.target is None


# ============================================================================
# Tests for label validation presentation in results DataFrames
# (_expand_resultset_rows / _handle_label_validation)
# ============================================================================


def _resultset_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a scanner-results-shaped DataFrame of resultset rows.

    Each row dict has: transcript_id, results (list of result dicts),
    target (validation target), result (validation result).
    """
    return pd.DataFrame(
        [
            {
                "transcript_id": row["transcript_id"],
                "value": json.dumps(row["results"]),
                "value_type": "resultset",
                "validation_target": json.dumps(row["target"]),
                "validation_result": json.dumps(row["result"]),
            }
            for row in rows
        ]
    )


class TestLabelValidationExpansion:
    """Label validation presentation is scoped per resultset row.

    That is, per transcript/case, matching how it is computed at scan time
    by _validate_labels().
    """

    def test_one_row_per_transcript_label_pair(self) -> None:
        """Regression test for whole-frame scoping (worked example in PR #545).

        t1 truly contains deception (scanner finds it: true positive) and no
        phishing (scanner stays silent: true negative). t2 is clean but the
        scanner reports phishing (false positive) and stays silent on
        deception (true negative). The DataFrame must surface all four
        judgments as rows -- the whole-frame present_labels computation
        yielded zero synthetic rows here because each label appeared
        somewhere in the frame.
        """
        df = _resultset_df(
            [
                {
                    "transcript_id": "t1",
                    "results": [{"label": "deception", "value": "found"}],
                    "target": {"deception": True, "phishing": False},
                    "result": {"deception": True, "phishing": True},
                },
                {
                    "transcript_id": "t2",
                    "results": [{"label": "phishing", "value": "found"}],
                    "target": {"deception": False, "phishing": False},
                    "result": {"deception": True, "phishing": False},
                },
            ]
        )

        expanded = _expand_resultset_rows(df)

        rows = {
            (row["transcript_id"], row["label"]): (
                row["value"],
                row["validation_result"],
            )
            for _, row in expanded.iterrows()
        }
        assert rows == {
            ("t1", "deception"): ("found", True),  # true positive
            ("t1", "phishing"): (False, True),  # synthetic true negative
            ("t2", "phishing"): ("found", False),  # false positive
            ("t2", "deception"): (False, True),  # synthetic true negative
        }

        # synthetic rows carry a boolean value type
        synthetic = expanded[
            (expanded["transcript_id"] == "t1") & (expanded["label"] == "phishing")
        ]
        assert synthetic.iloc[0]["value_type"] == "boolean"

        # internal bookkeeping column doesn't leak
        assert not any(col.startswith("_resultset") for col in expanded.columns)

    def test_synthetic_rows_without_stored_validation_result(self) -> None:
        """A label-based target alone drives synthesis.

        If a row's validation_result is missing (e.g. a scan error), its
        expected-absent labels still get synthetic rows, with a None
        validation result.
        """
        df = _resultset_df(
            [
                {
                    "transcript_id": "t1",
                    "results": [{"label": "deception", "value": "found"}],
                    "target": {"deception": True, "phishing": False},
                    "result": None,
                }
            ]
        )

        expanded = _expand_resultset_rows(df)

        phishing = expanded[expanded["label"] == "phishing"]
        assert len(phishing) == 1
        assert phishing.iloc[0]["value"] == False  # noqa: E712
        assert pd.isna(phishing.iloc[0]["validation_result"])

        # the real row's validation_result is left as stored
        deception = expanded[expanded["label"] == "deception"]
        assert deception.iloc[0]["validation_result"] == "null"

    def test_synthetic_rows_for_empty_resultset(self) -> None:
        """An empty resultset still yields synthetic true-negative rows."""
        df = _resultset_df(
            [
                {
                    "transcript_id": "t1",
                    "results": [],
                    "target": {"phishing": False},
                    "result": {"phishing": True},
                }
            ]
        )

        expanded = _expand_resultset_rows(df)

        assert len(expanded) == 1
        row = expanded.iloc[0]
        assert row["transcript_id"] == "t1"
        assert row["label"] == "phishing"
        assert row["value"] == False  # noqa: E712
        assert row["validation_result"] == True  # noqa: E712

    def test_synthetic_rows_use_each_rows_own_target(self) -> None:
        """Each transcript gets synthetic rows for its own expected labels."""
        df = _resultset_df(
            [
                {
                    "transcript_id": "t1",
                    "results": [],
                    "target": {"alpha": False},
                    "result": {"alpha": True},
                },
                {
                    "transcript_id": "t2",
                    "results": [],
                    "target": {"beta": False},
                    "result": {"beta": True},
                },
            ]
        )

        expanded = _expand_resultset_rows(df)

        labels_by_transcript = expanded.set_index("transcript_id")["label"]
        assert labels_by_transcript["t1"] == "alpha"
        assert labels_by_transcript["t2"] == "beta"

    def test_scalar_validation_rows_unaffected(self) -> None:
        """Non-label (scalar target) validation is left untouched."""
        df = _resultset_df(
            [
                {
                    "transcript_id": "t1",
                    "results": [{"label": "x", "value": "found"}],
                    "target": True,
                    "result": True,
                }
            ]
        )

        expanded = _expand_resultset_rows(df)

        assert len(expanded) == 1
        # validation_result stays as stored (JSON scalar), no synthetic rows
        assert expanded.iloc[0]["validation_result"] == "true"

    def test_label_rows_handled_even_when_first_row_is_scalar(self) -> None:
        """Label validation applies per row, not gated on the frame's first row."""
        df = _resultset_df(
            [
                {
                    "transcript_id": "t1",
                    "results": [{"label": "x", "value": "found"}],
                    "target": True,
                    "result": True,
                },
                {
                    "transcript_id": "t2",
                    "results": [],
                    "target": {"phishing": False},
                    "result": {"phishing": True},
                },
            ]
        )

        expanded = _expand_resultset_rows(df)

        t2_rows = expanded[expanded["transcript_id"] == "t2"]
        assert len(t2_rows) == 1
        assert t2_rows.iloc[0]["label"] == "phishing"
        assert t2_rows.iloc[0]["validation_result"] == True  # noqa: E712


# ============================================================================
# Tests for is_positive_value helper function
# ============================================================================


class TestIsPositiveValue:
    """Tests for the is_positive_value helper function."""

    def test_negative_values(self) -> None:
        """Test that negative values are correctly identified."""
        # Explicit negatives
        assert is_positive_value(None) is False
        assert is_positive_value(False) is False
        assert is_positive_value(0) is False
        assert is_positive_value("") is False
        assert is_positive_value("NONE") is False
        assert is_positive_value("none") is False
        assert is_positive_value("None") is False
        assert is_positive_value({}) is False
        assert is_positive_value([]) is False

    def test_positive_values(self) -> None:
        """Test that positive values are correctly identified."""
        # Explicit positives
        assert is_positive_value(True) is True
        assert is_positive_value(1) is True
        assert is_positive_value(-1) is True
        assert is_positive_value(0.5) is True
        assert is_positive_value("hello") is True
        assert is_positive_value("false") is True  # String "false" is NOT False
        assert is_positive_value({"key": "value"}) is True
        assert is_positive_value([1, 2, 3]) is True
        assert is_positive_value({"confidence": 0.9}) is True


# ============================================================================
# Tests for _validate_labels function with boolean logic
# ============================================================================


class TestValidateLabelsBoolean:
    """Tests for _validate_labels with boolean presence/absence logic."""

    @pytest.mark.asyncio
    async def test_expect_true_with_positive_result_passes(self) -> None:
        """labels: {foo: true} with positive results -> pass."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[{"label": "foo", "value": True}],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is True

    @pytest.mark.asyncio
    async def test_expect_true_with_no_results_fails(self) -> None:
        """labels: {foo: true} with no results -> fail."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[],  # Empty resultset
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is False

    @pytest.mark.asyncio
    async def test_expect_true_with_only_negative_results_fails(self) -> None:
        """labels: {foo: true} with only negative results -> fail."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[
                {"label": "foo", "value": False},
                {"label": "foo", "value": None},
                {"label": "foo", "value": 0},
            ],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is False

    @pytest.mark.asyncio
    async def test_expect_false_with_no_results_passes(self) -> None:
        """labels: {foo: false} with no results -> pass."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[],  # Empty resultset
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": False}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is True

    @pytest.mark.asyncio
    async def test_expect_false_with_negative_results_passes(self) -> None:
        """labels: {foo: false} with negative results -> pass."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[
                {"label": "foo", "value": False},
                {"label": "foo", "value": None},
            ],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": False}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is True

    @pytest.mark.asyncio
    async def test_expect_false_with_any_positive_result_fails(self) -> None:
        """labels: {foo: false} with any positive result -> fail."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[
                {"label": "foo", "value": False},
                {"label": "foo", "value": True},  # One positive!
            ],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": False}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is False

    @pytest.mark.asyncio
    async def test_non_empty_dict_treated_as_positive(self) -> None:
        """Non-empty dict/list values treated as positive."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[{"label": "foo", "value": {"confidence": 0.9}}],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is True

    @pytest.mark.asyncio
    async def test_empty_dict_treated_as_negative(self) -> None:
        """Empty dict {} treated as negative."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[{"label": "foo", "value": {}}],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is False

    @pytest.mark.asyncio
    async def test_empty_list_treated_as_negative(self) -> None:
        """Empty list [] treated as negative."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[{"label": "foo", "value": []}],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is False

    @pytest.mark.asyncio
    async def test_non_empty_list_treated_as_positive(self) -> None:
        """Non-empty list treated as positive."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[{"label": "foo", "value": [1, 2, 3]}],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {"foo": True}

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["foo"] is True

    def test_backwards_compat_non_boolean_coercion(self) -> None:
        """Backwards compat: non-boolean values coerced to boolean at ValidationCase level."""
        from inspect_scout._validation.types import ValidationCase

        # Non-boolean truthy value should be coerced to True
        case_truthy = ValidationCase(id="test", labels={"foo": 1})  # type: ignore[dict-item]
        assert case_truthy.labels is not None
        assert case_truthy.labels["foo"] is True

        # Non-boolean falsy value should be coerced to False
        case_falsy = ValidationCase(id="test", labels={"foo": 0})  # type: ignore[dict-item]
        assert case_falsy.labels is not None
        assert case_falsy.labels["foo"] is False

        # String "true" should be coerced to True
        case_str = ValidationCase(id="test", labels={"foo": "true"})  # type: ignore[dict-item]
        assert case_str.labels is not None
        assert case_str.labels["foo"] is True

        # Empty string should be coerced to False
        case_empty = ValidationCase(id="test", labels={"foo": ""})  # type: ignore[dict-item]
        assert case_empty.labels is not None
        assert case_empty.labels["foo"] is False

    @pytest.mark.asyncio
    async def test_multiple_labels(self) -> None:
        """Test validation with multiple labels."""
        from inspect_scout._validation.types import ValidationSet

        result = Result(
            type="resultset",
            value=[
                {"label": "deception", "value": True},
                {"label": "jailbreak", "value": False},
            ],
        )
        validation = ValidationSet(cases=[])
        labels: dict[str, bool] = {
            "deception": True,
            "jailbreak": False,
            "phishing": False,
        }

        validation_results = await _validate_labels(validation, result, labels, None)
        assert validation_results["deception"] is True  # Has positive value
        assert (
            validation_results["jailbreak"] is True
        )  # Has negative value, expected false
        assert validation_results["phishing"] is True  # Missing label, expected false
