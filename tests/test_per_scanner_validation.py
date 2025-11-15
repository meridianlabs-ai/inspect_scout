"""Tests for per-scanner validation sets functionality."""

from typing import Any

import pytest
from inspect_ai.model._chat_message import ChatMessageSystem, ChatMessageUser
from inspect_scout._scan import _resolve_validation
from inspect_scout._scanjob import ScanJob
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, scanner
from inspect_scout._transcript.transcripts import Transcripts
from inspect_scout._validation import ValidationCase, ValidationSet


# Mock Transcripts for testing
class MockTranscripts(Transcripts):
    """Mock implementation of Transcripts for testing."""

    async def __aenter__(self) -> "MockTranscripts":
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,  # noqa: ARG002
    ) -> None:
        return None

    async def count(self) -> int:
        return 0

    def index(self) -> Any:
        async def empty_generator() -> Any:
            if False:
                yield

        return empty_generator()

    async def read(self, transcript: Any, content: Any) -> Any:  # noqa: ARG002
        raise NotImplementedError()

    async def snapshot(self) -> Any:
        raise NotImplementedError()


# Sample scanners for testing
@scanner(messages=["system"])
def system_scanner() -> Scanner[ChatMessageSystem]:
    """Scanner for system messages."""

    async def scan(message: ChatMessageSystem) -> Result:  # noqa: ARG001
        return Result(value={"type": "system"})

    return scan


@scanner(messages=["user"])
def user_scanner() -> Scanner[ChatMessageUser]:
    """Scanner for user messages."""

    async def scan(message: ChatMessageUser) -> Result:  # noqa: ARG001
        return Result(value={"type": "user"})

    return scan


# Tests for _resolve_validation function


def test_resolve_validation_single_set_single_scanner() -> None:
    """Single ValidationSet with single scanner should wrap to dict."""
    validation = ValidationSet(
        cases=[
            ValidationCase(id="id1", target=True),
            ValidationCase(id="id2", target=False),
        ]
    )

    scanjob = ScanJob(scanners=[("scanner1", system_scanner())])

    result = _resolve_validation(validation, scanjob)

    # Should return a dict with the scanner name
    assert isinstance(result, dict)
    assert "scanner1" in result
    assert result["scanner1"] == validation


def test_resolve_validation_single_set_multiple_scanners_raises() -> None:
    """Single ValidationSet with multiple scanners should raise ValueError."""
    validation = ValidationSet(
        cases=[
            ValidationCase(id="id1", target=True),
        ]
    )

    scanjob = ScanJob(
        scanners=[
            ("scanner1", system_scanner()),
            ("scanner2", user_scanner()),
        ]
    )

    with pytest.raises(
        ValueError,
        match="Validation sets must be specified as a dict of scanner:validation when there is more than one scanner",
    ):
        _resolve_validation(validation, scanjob)


def test_resolve_validation_dict_valid_scanner_names() -> None:
    """Dict validation with valid scanner names should pass through."""
    validation1 = ValidationSet(cases=[ValidationCase(id="id1", target=True)])
    validation2 = ValidationSet(cases=[ValidationCase(id="id2", target=False)])

    validation_dict = {
        "scanner1": validation1,
        "scanner2": validation2,
    }

    scanjob = ScanJob(
        scanners=[
            ("scanner1", system_scanner()),
            ("scanner2", user_scanner()),
        ]
    )

    result = _resolve_validation(validation_dict, scanjob)

    # Should return the same dict
    assert result == validation_dict


def test_resolve_validation_dict_invalid_scanner_name_raises() -> None:
    """Dict validation with invalid scanner name should raise ValueError."""
    validation1 = ValidationSet(cases=[ValidationCase(id="id1", target=True)])
    validation2 = ValidationSet(cases=[ValidationCase(id="id2", target=False)])

    validation_dict = {
        "scanner1": validation1,
        "invalid_scanner": validation2,
    }

    scanjob = ScanJob(scanners=[("scanner1", system_scanner())])

    with pytest.raises(
        ValueError,
        match="Validation referended scanner 'invalid_scanner' however there is no scanner of that name",
    ):
        _resolve_validation(validation_dict, scanjob)


def test_resolve_validation_dict_multiple_invalid_names_raises_for_first() -> None:
    """Dict validation should report the first invalid scanner name encountered."""
    validation_dict = {
        "invalid1": ValidationSet(cases=[ValidationCase(id="id1", target=True)]),
        "invalid2": ValidationSet(cases=[ValidationCase(id="id2", target=False)]),
    }

    scanjob = ScanJob(scanners=[("scanner1", system_scanner())])

    # Should raise for one of the invalid names (dict order may vary)
    with pytest.raises(ValueError, match="Validation referended scanner"):
        _resolve_validation(validation_dict, scanjob)


def test_resolve_validation_dict_partial_invalid_names_raises() -> None:
    """Dict validation with mix of valid and invalid names should raise."""
    validation_dict = {
        "scanner1": ValidationSet(cases=[ValidationCase(id="id1", target=True)]),
        "invalid_scanner": ValidationSet(
            cases=[ValidationCase(id="id2", target=False)]
        ),
    }

    scanjob = ScanJob(scanners=[("scanner1", system_scanner())])

    with pytest.raises(ValueError, match="Validation referended scanner"):
        _resolve_validation(validation_dict, scanjob)


def test_resolve_validation_empty_validation_dict() -> None:
    """Empty validation dict should be valid."""
    validation_dict: dict[str, ValidationSet] = {}

    scanjob = ScanJob(scanners=[("scanner1", system_scanner())])

    result = _resolve_validation(validation_dict, scanjob)

    assert result == {}


def test_resolve_validation_single_empty_validation_set() -> None:
    """Single ValidationSet with empty cases should work."""
    validation = ValidationSet(cases=[])

    scanjob = ScanJob(scanners=[("scanner1", system_scanner())])

    result = _resolve_validation(validation, scanjob)

    assert isinstance(result, dict)
    assert "scanner1" in result
    assert len(result["scanner1"].cases) == 0


# Tests for Transcripts.for_validation with dict input


def test_for_validation_dict_single_scanner() -> None:
    """for_validation should handle dict with single scanner."""
    validation_dict = {
        "scanner1": ValidationSet(
            cases=[
                ValidationCase(id="id1", target=True),
                ValidationCase(id="id2", target=False),
            ]
        )
    }

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation_dict)

    assert len(filtered._where) == 1

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?, ?)'
    assert params == ["id1", "id2"]


def test_for_validation_dict_multiple_scanners() -> None:
    """for_validation should merge IDs from multiple scanners."""
    validation_dict = {
        "scanner1": ValidationSet(
            cases=[
                ValidationCase(id="id1", target=True),
                ValidationCase(id="id2", target=False),
            ]
        ),
        "scanner2": ValidationSet(
            cases=[
                ValidationCase(id="id3", target=True),
                ValidationCase(id="id4", target=False),
            ]
        ),
    }

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation_dict)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should merge all IDs from both scanners
    assert sql == '"sample_id" IN (?, ?, ?, ?)'
    assert set(params) == {"id1", "id2", "id3", "id4"}


def test_for_validation_dict_overlapping_ids() -> None:
    """for_validation should deduplicate overlapping IDs from multiple scanners."""
    validation_dict = {
        "scanner1": ValidationSet(
            cases=[
                ValidationCase(id="id1", target=True),
                ValidationCase(id="id2", target=False),
            ]
        ),
        "scanner2": ValidationSet(
            cases=[
                ValidationCase(id="id2", target=True),  # Duplicate
                ValidationCase(id="id3", target=False),
            ]
        ),
    }

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation_dict)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should deduplicate id2
    assert sql == '"sample_id" IN (?, ?, ?)'
    assert set(params) == {"id1", "id2", "id3"}


def test_for_validation_dict_with_list_ids() -> None:
    """for_validation should handle list IDs in dict validation."""
    validation_dict = {
        "scanner1": ValidationSet(
            cases=[
                ValidationCase(id=["id1", "id2"], target=True),
            ]
        ),
        "scanner2": ValidationSet(
            cases=[
                ValidationCase(id="id3", target=False),
            ]
        ),
    }

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation_dict)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    assert sql == '"sample_id" IN (?, ?, ?)'
    assert set(params) == {"id1", "id2", "id3"}


def test_for_validation_dict_empty_validation_sets() -> None:
    """for_validation should handle empty validation sets in dict."""
    validation_dict = {
        "scanner1": ValidationSet(cases=[]),
        "scanner2": ValidationSet(cases=[]),
    }

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation_dict)

    condition = filtered._where[0]
    sql, params = condition.to_sql("sqlite")

    # Should result in empty IN clause
    assert sql == "1 = 0"
    assert params == []


def test_for_validation_preserves_order_across_scanners() -> None:
    """for_validation should preserve order when merging from multiple scanners."""
    validation_dict = {
        "scanner1": ValidationSet(
            cases=[
                ValidationCase(id="id_c", target=True),
                ValidationCase(id="id_a", target=False),
            ]
        ),
        "scanner2": ValidationSet(
            cases=[
                ValidationCase(id="id_b", target=True),
                ValidationCase(id="id_a", target=False),  # Duplicate
            ]
        ),
    }

    transcripts = MockTranscripts()
    filtered = transcripts.for_validation(validation_dict)

    condition = filtered._where[0]
    _sql, params = condition.to_sql("sqlite")

    # Should have all unique IDs in order of first appearance
    assert len(params) == 3
    # id_a appears in scanner1 first
    assert "id_c" in params
    assert "id_a" in params
    assert "id_b" in params
