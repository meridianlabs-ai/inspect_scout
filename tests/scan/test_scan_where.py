"""Tests for ScanTranscripts.where field serialization."""

import tempfile
from pathlib import Path
from typing import Any

import pytest

from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._transcript.columns import columns as c
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

# Test data location - use recorder logs which have multiple task_sets
LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


@scanner(name="where_test_scanner", messages="all")
def where_test_scanner_factory() -> Scanner[Transcript]:
    """Minimal scanner for testing where clause persistence."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True, explanation="test")

    return scan_transcript


@pytest.mark.asyncio
async def test_scan_with_simple_where_clause() -> None:
    """Test that a simple where clause is persisted in the scan spec."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with where clause
        transcripts = transcripts_from(LOGS_DIR).where(c.task_set == "popularity")

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            results=tmpdir,
            limit=1,
            max_processes=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clause was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.conditions is not None
        assert len(status.spec.transcripts.conditions) == 1

        # Verify the condition structure (now stored as dict)
        condition: dict[str, Any] = status.spec.transcripts.conditions[0]
        assert condition["is_compound"] is False
        assert condition["left"] == "task_set"
        assert condition["operator"] == "="  # EQ operator value
        assert condition["right"] == "popularity"


# def test_scan_with_compound_where_clause() -> None:
#     """Test that compound conditions (AND/OR) are persisted."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create transcripts with compound where clause
#         transcripts = transcripts_from(LOGS_DIR).where(
#             (c.task_set == "popularity") | (c.task_set == "theory-of-mind")
#         )

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Verify where clause was stored
#         assert status.spec.transcripts is not None
#         assert status.spec.transcripts.conditions is not None
#         assert len(status.spec.transcripts.conditions) == 1

#         # Verify the compound condition structure (now stored as dict)
#         condition: dict[str, Any] = status.spec.transcripts.conditions[0]
#         assert condition["is_compound"] is True
#         assert condition["operator"] == "OR"  # OR operator value
#         # Check left operand
#         assert isinstance(condition["left"], dict)
#         assert condition["left"]["is_compound"] is False
#         assert condition["left"]["left"] == "task_set"
#         assert condition["left"]["right"] == "popularity"
#         # Check right operand
#         assert isinstance(condition["right"], dict)
#         assert condition["right"]["is_compound"] is False
#         assert condition["right"]["left"] == "task_set"
#         assert condition["right"]["right"] == "theory-of-mind"


# def test_scan_with_in_where_clause() -> None:
#     """Test where clause using IN operator."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create transcripts with IN where clause
#         transcripts = transcripts_from(LOGS_DIR).where(
#             c.task_set.in_(["popularity", "security-guide"])
#         )

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Verify where clause was stored
#         assert status.spec.transcripts is not None
#         assert status.spec.transcripts.conditions is not None
#         assert len(status.spec.transcripts.conditions) == 1

#         # Verify the IN condition structure (now stored as dict)
#         condition: dict[str, Any] = status.spec.transcripts.conditions[0]
#         assert condition["is_compound"] is False
#         assert condition["left"] == "task_set"
#         assert condition["operator"] == "IN"  # IN operator value
#         assert condition["right"] == ["popularity", "security-guide"]


# def test_scan_with_and_where_clause() -> None:
#     """Test where clause using AND operator."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create transcripts with AND where clause
#         transcripts = transcripts_from(LOGS_DIR).where(
#             (c.task_set == "popularity") & (c.success == True)  # noqa: E712
#         )

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Verify where clause was stored
#         assert status.spec.transcripts is not None
#         assert status.spec.transcripts.conditions is not None
#         assert len(status.spec.transcripts.conditions) == 1

#         # Verify the AND condition structure (now stored as dict)
#         condition: dict[str, Any] = status.spec.transcripts.conditions[0]
#         assert condition["is_compound"] is True
#         assert condition["operator"] == "AND"  # AND operator value


# def test_where_clause_roundtrip() -> None:
#     """Test that where conditions can be serialized and deserialized correctly."""
#     # Create various conditions
#     conditions = [
#         c.task_set == "popularity",
#         c.score > 0.5,
#         c.model.in_(["gpt-4", "claude-3"]),
#         (c.task_set == "math") & (c.success == True),  # noqa: E712
#         c.task_set.like("pop%"),
#     ]

#     for original in conditions:
#         # Serialize
#         serialized = original.model_dump()

#         # Deserialize
#         restored = Condition.model_validate(serialized)

#         # Verify SQL generation matches
#         assert original.to_sql("sqlite") == restored.to_sql("sqlite")
#         assert original.to_sql("duckdb") == restored.to_sql("duckdb")
#         assert original.to_sql("postgres") == restored.to_sql("postgres")


# def test_scan_with_multiple_where_calls() -> None:
#     """Test that multiple .where() calls accumulate conditions."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create transcripts with multiple where calls
#         transcripts = (
#             transcripts_from(LOGS_DIR)
#             .where(c.task_set == "popularity")
#             .where(c.success == True)  # noqa: E712
#         )

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Verify where clauses were stored
#         assert status.spec.transcripts is not None
#         assert status.spec.transcripts.conditions is not None
#         # Multiple where() calls should accumulate
#         assert len(status.spec.transcripts.conditions) >= 1


# def test_scan_without_where_clause() -> None:
#     """Test scan without where clause has empty/None where."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create transcripts without where clause
#         transcripts = transcripts_from(LOGS_DIR)

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Verify transcripts are present but where is None or empty
#         assert status.spec.transcripts is not None
#         # where should be None or empty list when no filter applied
#         where = status.spec.transcripts.conditions
#         assert where is None or len(where) == 0


# def test_where_clause_with_comparison_operators() -> None:
#     """Test where clause with various comparison operators."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Test with greater than operator
#         transcripts = transcripts_from(LOGS_DIR).where(c.score > 0.5)

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Verify where clause was stored
#         assert status.spec.transcripts is not None
#         assert status.spec.transcripts.conditions is not None
#         assert len(status.spec.transcripts.conditions) == 1

#         # Verify the condition structure (now stored as dict)
#         condition: dict[str, Any] = status.spec.transcripts.conditions[0]
#         assert condition["is_compound"] is False
#         assert condition["left"] == "score"
#         assert condition["operator"] == ">"  # GT operator value
#         assert condition["right"] == 0.5


# def test_where_clause_preserves_sql_generation() -> None:
#     """Test that restored where clause generates same SQL as original."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create a condition and get its SQL
#         original_condition = (c.task_set == "popularity") & (c.score > 0.8)
#         original_sql = original_condition.to_sql("sqlite")

#         # Run scan with this condition
#         transcripts = transcripts_from(LOGS_DIR).where(original_condition)

#         status = scan(
#             scanners=[where_test_scanner_factory()],
#             transcripts=transcripts,
#             results=tmpdir,
#             limit=1,
#             max_processes=1,
#         )

#         # Verify scan completed
#         assert status.complete

#         # Get the stored condition dict and restore to Condition object
#         assert status.spec.transcripts is not None
#         assert status.spec.transcripts.conditions is not None
#         condition_dict: dict[str, Any] = status.spec.transcripts.conditions[0]
#         restored_condition = Condition.model_validate(condition_dict)

#         # Verify SQL generation matches
#         restored_sql = restored_condition.to_sql("sqlite")
#         assert original_sql == restored_sql
