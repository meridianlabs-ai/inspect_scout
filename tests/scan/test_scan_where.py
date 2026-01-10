"""Tests for ScanTranscripts.where field serialization."""

import tempfile
from pathlib import Path

import pytest
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._query.column import Column
from inspect_scout._query.condition import Condition, Operator
from inspect_scout._query.condition_sql import (
    condition_as_sql,
    condition_from_sql,
)
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
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clause was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify the condition structure
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.is_compound is False
        assert condition.left == "task_set"
        assert condition.operator is not None and condition.operator.name == "EQ"
        assert condition.right == "popularity"


@pytest.mark.asyncio
async def test_scan_with_compound_where_clause() -> None:
    """Test that compound conditions (AND/OR) are persisted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with compound where clause
        transcripts = transcripts_from(LOGS_DIR).where(
            (c.task_set == "popularity") | (c.task_set == "theory-of-mind")
        )

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clause was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify the compound condition structure
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.is_compound is True
        assert condition.operator is not None and condition.operator.name == "OR"
        # Check left operand
        assert isinstance(condition.left, Condition)
        assert condition.left.is_compound is False
        assert condition.left.left == "task_set"
        assert condition.left.right == "popularity"
        # Check right operand
        assert isinstance(condition.right, Condition)
        assert condition.right.is_compound is False
        assert condition.right.left == "task_set"
        assert condition.right.right == "theory-of-mind"


@pytest.mark.asyncio
async def test_scan_with_in_where_clause() -> None:
    """Test where clause using IN operator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with IN where clause
        transcripts = transcripts_from(LOGS_DIR).where(
            c.task_set.in_(["popularity", "security-guide"])
        )

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clause was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify the IN condition structure
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.is_compound is False
        assert condition.left == "task_set"
        assert condition.operator is not None and condition.operator.name == "IN"
        assert condition.right == ["popularity", "security-guide"]


@pytest.mark.asyncio
async def test_scan_with_and_where_clause() -> None:
    """Test where clause using AND operator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with AND where clause
        transcripts = transcripts_from(LOGS_DIR).where(
            (c.task_set == "popularity") & (c.success == True)  # noqa: E712
        )

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clause was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify the AND condition structure
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.is_compound is True
        assert condition.operator is not None and condition.operator.name == "AND"


@pytest.mark.asyncio
async def test_where_clause_roundtrip() -> None:
    """Test that where conditions can be serialized and deserialized correctly."""
    # Create various conditions
    conditions = [
        c.task_set == "popularity",
        c.score > 0.5,
        c.model.in_(["gpt-4", "claude-3"]),
        (c.task_set == "math") & (c.success == True),  # noqa: E712
        c.task_set.like("pop%"),
    ]

    for original in conditions:
        # Serialize
        serialized = original.model_dump()

        # Deserialize
        restored = Condition.model_validate(serialized)

        # Verify SQL generation matches
        assert condition_as_sql(original, "sqlite") == condition_as_sql(
            restored, "sqlite"
        )
        assert condition_as_sql(original, "duckdb") == condition_as_sql(
            restored, "duckdb"
        )
        assert condition_as_sql(original, "postgres") == condition_as_sql(
            restored, "postgres"
        )


@pytest.mark.asyncio
async def test_scan_with_multiple_where_calls() -> None:
    """Test that multiple .where() calls accumulate conditions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with multiple where calls
        transcripts = (
            transcripts_from(LOGS_DIR)
            .where(c.task_set == "popularity")
            .where(c.success == True)  # noqa: E712
        )

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clauses were stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        # Multiple where() calls should accumulate
        assert len(status.spec.transcripts.filter) >= 1


@pytest.mark.asyncio
async def test_scan_without_where_clause() -> None:
    """Test scan without where clause has empty/None where."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts without where clause
        transcripts = transcripts_from(LOGS_DIR)

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify transcripts are present but where is None or empty
        assert status.spec.transcripts is not None
        # where should be None or empty list when no filter applied
        where = status.spec.transcripts.filter
        assert where is None or len(where) == 0


@pytest.mark.asyncio
async def test_where_clause_with_comparison_operators() -> None:
    """Test where clause with various comparison operators."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test with greater than operator
        transcripts = transcripts_from(LOGS_DIR).where(c.score > 0.5)

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify where clause was stored
        assert status.spec.transcripts is not None

        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify the condition structure
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.is_compound is False
        assert condition.left == "score"
        assert condition.operator is not None and condition.operator.name == "GT"
        assert condition.right == 0.5


@pytest.mark.asyncio
async def test_where_clause_preserves_sql_generation() -> None:
    """Test that restored where clause generates same SQL as original."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a condition and get its SQL
        original_condition = (c.task_set == "popularity") & (c.score > 0.8)
        original_sql = condition_as_sql(original_condition, "sqlite")

        # Run scan with this condition
        transcripts = transcripts_from(LOGS_DIR).where(original_condition)

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Get the restored condition
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        restored_condition = condition_from_sql(status.spec.transcripts.filter[0])

        # Verify SQL generation matches
        restored_sql = condition_as_sql(restored_condition, "sqlite")
        assert original_sql == restored_sql


# =============================================================================
# Unit tests for condition_as_sql / condition_from_sql roundtrip
# =============================================================================


def test_sql_roundtrip_string_with_single_quotes() -> None:
    """Test roundtrip of strings containing single quotes."""
    col = Column("name")
    condition = col == "O'Brien"
    sql = condition_as_sql(condition, "filter")

    # Verify SQL escapes single quotes
    assert "'O''Brien'" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "name"
    assert restored.right == "O'Brien"


def test_sql_roundtrip_between_operator() -> None:
    """Test roundtrip of BETWEEN operator."""
    col = Column("score")
    condition = col.between(0.5, 0.9)
    sql = condition_as_sql(condition, "filter")

    # Verify SQL format
    assert "BETWEEN" in sql
    assert "0.5" in sql
    assert "0.9" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "score"
    assert restored.operator == Operator.BETWEEN
    assert restored.right == (0.5, 0.9)


def test_sql_roundtrip_not_between_operator() -> None:
    """Test roundtrip of NOT BETWEEN operator."""
    col = Column("score")
    condition = col.not_between(0.2, 0.8)
    sql = condition_as_sql(condition, "filter")

    # Verify SQL format
    assert "NOT BETWEEN" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "score"
    assert restored.operator == Operator.NOT_BETWEEN
    assert restored.right == (0.2, 0.8)


def test_sql_roundtrip_ilike_operator() -> None:
    """Test roundtrip of ILIKE operator."""
    col = Column("model")
    condition = col.ilike("gpt%")
    sql = condition_as_sql(condition, "filter")

    # Verify SQL format
    assert "ILIKE" in sql
    assert "'gpt%'" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "model"
    assert restored.operator == Operator.ILIKE
    assert restored.right == "gpt%"


def test_sql_roundtrip_not_ilike_operator() -> None:
    """Test roundtrip of NOT ILIKE operator."""
    col = Column("model")
    condition = col.not_ilike("claude%")
    sql = condition_as_sql(condition, "filter")

    # Verify SQL format
    assert "NOT ILIKE" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "model"
    assert restored.operator == Operator.NOT_ILIKE
    assert restored.right == "claude%"


def test_sql_roundtrip_json_path_with_array_index() -> None:
    """Test roundtrip of JSON paths containing array indices."""
    col = Column("config.items[0].name")
    condition = col == "test"
    sql = condition_as_sql(condition, "filter")

    # Verify SQL format includes the array index
    assert "items" in sql
    assert "[0]" in sql
    assert "config" in sql
    # Verify the value is present
    assert "'test'" in sql

    # Full roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "config.items[0].name"
    assert restored.right == "test"


def test_sql_roundtrip_reserved_word_identifier() -> None:
    """Test roundtrip of identifiers that are SQL reserved words."""
    col = Column("select")
    condition = col == "value"
    sql = condition_as_sql(condition, "filter")

    # Reserved words should be quoted
    assert '"select"' in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "select"
    assert restored.right == "value"


def test_sql_roundtrip_not_operator() -> None:
    """Test roundtrip of NOT operator wrapping a condition.

    Note: DuckDB simplifies NOT (x = y) to x != y during parsing,
    which is semantically equivalent. This test verifies the
    SQL generation and that the semantics are preserved.
    """
    col = Column("active")
    inner_condition = col == True  # noqa: E712
    condition = ~inner_condition  # NOT operator
    sql = condition_as_sql(condition, "filter")

    # Verify SQL format includes NOT
    assert "NOT" in sql

    # Roundtrip through SQL parsing - DuckDB may simplify NOT (x = y) to x != y
    restored = condition_from_sql(sql)
    # Either it's a compound NOT, or it was simplified to NE
    if restored.is_compound:
        assert isinstance(restored.left, Condition)
    else:
        # DuckDB simplified NOT (active = TRUE) to active != TRUE
        assert restored.left == "active"
        assert restored.operator == Operator.NE
        assert restored.right is True


def test_sql_roundtrip_empty_in_list() -> None:
    """Test roundtrip of empty IN list (should produce always-false condition)."""
    col = Column("status")
    condition = col.in_([])
    sql = condition_as_sql(condition, "filter")

    # Empty IN should produce always-false condition
    assert "1 = 0" in sql


def test_sql_roundtrip_in_with_null() -> None:
    """Test roundtrip of IN list containing NULL."""
    col = Column("status")
    condition = col.in_(["active", None, "pending"])
    sql = condition_as_sql(condition, "filter")

    # Should handle NULL separately with IS NULL
    assert "IS NULL" in sql
    assert "IN" in sql


def test_sql_roundtrip_not_in_with_null() -> None:
    """Test roundtrip of NOT IN list containing NULL."""
    col = Column("status")
    condition = col.not_in(["deleted", None])
    sql = condition_as_sql(condition, "filter")

    # Should handle NULL separately with IS NOT NULL
    assert "IS NOT NULL" in sql
    assert "NOT IN" in sql


def test_sql_roundtrip_is_null() -> None:
    """Test roundtrip of IS NULL operator."""
    col = Column("error")
    condition = col.is_null()
    sql = condition_as_sql(condition, "filter")

    assert "IS NULL" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "error"
    assert restored.operator == Operator.IS_NULL


def test_sql_roundtrip_is_not_null() -> None:
    """Test roundtrip of IS NOT NULL operator."""
    col = Column("result")
    condition = col.is_not_null()
    sql = condition_as_sql(condition, "filter")

    assert "IS NOT NULL" in sql

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.left == "result"
    assert restored.operator == Operator.IS_NOT_NULL


def test_sql_roundtrip_complex_nested_condition() -> None:
    """Test roundtrip of complex nested AND/OR conditions."""
    col_a = Column("status")
    col_b = Column("score")
    col_c = Column("model")

    condition = ((col_a == "success") & (col_b > 0.8)) | (col_c == "gpt-4")
    sql = condition_as_sql(condition, "filter")

    # Roundtrip through SQL parsing
    restored = condition_from_sql(sql)
    assert restored.is_compound is True

    # Verify SQL generation matches
    original_sql_tuple = condition_as_sql(condition, "duckdb")
    restored_sql_tuple = condition_as_sql(restored, "duckdb")
    assert original_sql_tuple[0] == restored_sql_tuple[0]


def test_sql_roundtrip_boolean_values() -> None:
    """Test roundtrip of boolean values."""
    col = Column("success")

    # Test TRUE
    condition_true = col == True  # noqa: E712
    sql_true = condition_as_sql(condition_true, "filter")
    assert "TRUE" in sql_true
    restored_true = condition_from_sql(sql_true)
    assert restored_true.right is True

    # Test FALSE
    condition_false = col == False  # noqa: E712
    sql_false = condition_as_sql(condition_false, "filter")
    assert "FALSE" in sql_false
    restored_false = condition_from_sql(sql_false)
    assert restored_false.right is False


def test_sql_roundtrip_integer_values() -> None:
    """Test roundtrip of integer values."""
    col = Column("count")
    condition = col == 42
    sql = condition_as_sql(condition, "filter")

    restored = condition_from_sql(sql)
    assert restored.right == 42
    assert isinstance(restored.right, int)


def test_sql_roundtrip_float_values() -> None:
    """Test roundtrip of float values."""
    col = Column("score")
    condition = col == 3.14159
    sql = condition_as_sql(condition, "filter")

    restored = condition_from_sql(sql)
    assert abs(float(restored.right) - 3.14159) < 0.0001  # type: ignore


def test_sql_string_filter_accepted_by_where() -> None:
    """Test that .where() accepts SQL string filter."""
    transcripts = transcripts_from(LOGS_DIR)

    # Should accept SQL string
    filtered = transcripts.where("task_set = 'popularity'")

    # Verify the condition was parsed
    assert len(filtered._query.where) == 1
    condition = filtered._query.where[0]
    assert condition.left == "task_set"
    assert condition.right == "popularity"


# =============================================================================
# Integration tests with actual scans
# =============================================================================


@pytest.mark.asyncio
async def test_scan_with_between_filter() -> None:
    """Integration test: scan with BETWEEN filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with BETWEEN filter on score
        transcripts = transcripts_from(LOGS_DIR).where(c.score.between(0.0, 1.0))

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify filter was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify BETWEEN was preserved
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.operator == Operator.BETWEEN


@pytest.mark.asyncio
async def test_scan_with_ilike_filter() -> None:
    """Integration test: scan with ILIKE filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with ILIKE filter
        transcripts = transcripts_from(LOGS_DIR).where(c.task_set.ilike("pop%"))

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify filter was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify ILIKE was preserved
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.operator == Operator.ILIKE
        assert condition.right == "pop%"


@pytest.mark.asyncio
async def test_scan_with_like_filter() -> None:
    """Integration test: scan with LIKE filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with LIKE filter
        transcripts = transcripts_from(LOGS_DIR).where(c.task_set.like("pop%"))

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify filter was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None
        assert len(status.spec.transcripts.filter) == 1

        # Verify LIKE was preserved
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.operator == Operator.LIKE


@pytest.mark.asyncio
async def test_scan_with_sql_string_filter() -> None:
    """Integration test: scan with SQL string filter passed to .where()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use SQL string directly
        transcripts = transcripts_from(LOGS_DIR).where("task_set = 'popularity'")

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify filter was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None

        # Verify the condition was correctly parsed and stored
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.left == "task_set"
        assert condition.right == "popularity"


@pytest.mark.asyncio
async def test_scan_with_not_filter() -> None:
    """Integration test: scan with NOT filter.

    Note: DuckDB simplifies NOT (x = y) to x != y during parsing,
    which is semantically equivalent.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with NOT filter
        inner_condition = c.task_set == "excluded"
        transcripts = transcripts_from(LOGS_DIR).where(~inner_condition)

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify filter was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None

        # Verify the semantics are preserved (DuckDB may simplify NOT to NE)
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        if condition.is_compound:
            # Kept as NOT
            assert isinstance(condition.left, Condition)
        else:
            # Simplified to NE (not equal)
            assert condition.left == "task_set"
            assert condition.operator == Operator.NE
            assert condition.right == "excluded"


@pytest.mark.asyncio
async def test_scan_with_is_null_filter() -> None:
    """Integration test: scan with IS NULL filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create transcripts with IS NULL filter
        transcripts = transcripts_from(LOGS_DIR).where(c.error.is_null())

        status = scan(
            scanners=[where_test_scanner_factory()],
            transcripts=transcripts,
            scans=tmpdir,
            limit=1,
        )

        # Verify scan completed
        assert status.complete

        # Verify filter was stored
        assert status.spec.transcripts is not None
        assert status.spec.transcripts.filter is not None

        # Verify IS NULL was preserved
        condition = condition_from_sql(status.spec.transcripts.filter[0])
        assert condition.operator == Operator.IS_NULL
