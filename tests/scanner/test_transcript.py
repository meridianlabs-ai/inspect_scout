"""Comprehensive tests for the _transcript module."""

import uuid
from typing import Any, Literal, cast

import pandas as pd
import pytest
import pytest_asyncio
from inspect_scout import columns as c
from inspect_scout._query import Query
from inspect_scout._query.order_by import OrderBy
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.types import TranscriptInfo


def create_test_dataframe(num_samples: int = 10) -> pd.DataFrame:
    """Create a test DataFrame with sample data for testing."""
    data = []
    for i in range(num_samples):
        data.append(
            {
                "sample_id": f"sample_{uuid.uuid4().hex[:8]}",
                "id": f"id_{i:03d}",
                "epoch": 1,
                "eval_id": f"eval_{uuid.uuid4().hex[:8]}",  # Add eval_id
                "log": f"/path/to/log_{i:03d}.json",
                "model": ["gpt-4", "gpt-3.5-turbo", "claude"][i % 3],
                "score": 0.5 + (i % 10) * 0.05,  # 0.5 to 0.95
                "status": ["success", "error", "timeout"][i % 3],
                "retries": i % 4,
                "temperature": 0.7 + (i % 5) * 0.1,
                "max_tokens": 1000 + (i % 5) * 500,
                "dataset": ["train", "test", "validation"][i % 3],
                "run_date": f"2024-01-{(i % 28) + 1:02d}",
                "duration_seconds": 10 + i * 5,
                "token_count": 500 + i * 100,
                "error_message": "timeout error" if i % 3 == 2 else None,
            }
        )
    return pd.DataFrame(data)


@pytest_asyncio.fixture
async def db() -> Any:
    """Create and connect to a test database."""
    df = create_test_dataframe(20)
    db = EvalLogTranscriptsView(df)
    await db.connect()
    yield db
    await db.disconnect()


# ============================================================================
# Metadata Filtering DSL Tests
# ============================================================================


def test_simple_equality() -> None:
    """Test simple equality conditions."""
    condition = c.model == "gpt-4"
    sql, params = condition.to_sql("sqlite")
    assert sql == '"model" = ?'
    assert params == ["gpt-4"]


def test_comparison_operators() -> None:
    """Test all comparison operators."""
    # Greater than
    condition = c.score > 0.8
    sql, params = condition.to_sql("sqlite")
    assert sql == '"score" > ?'
    assert params == [0.8]

    # Less than or equal
    condition = c.retries <= 3
    sql, params = condition.to_sql("sqlite")
    assert sql == '"retries" <= ?'
    assert params == [3]

    # Not equal
    condition = c.status != "error"
    sql, params = condition.to_sql("sqlite")
    assert sql == '"status" != ?'
    assert params == ["error"]


def test_in_operator() -> None:
    """Test IN and NOT IN operators."""
    condition = c.model.in_(["gpt-4", "claude"])
    sql, params = condition.to_sql("sqlite")
    assert sql == '"model" IN (?, ?)'
    assert params == ["gpt-4", "claude"]

    condition = c.status.not_in(["error", "timeout"])
    sql, params = condition.to_sql("sqlite")
    assert sql == '"status" NOT IN (?, ?)'
    assert params == ["error", "timeout"]


def test_empty_in_operator() -> None:
    """Test empty IN and NOT IN operators."""
    # Empty IN should always be false (nothing can be in an empty set)
    condition = c.model.in_([])
    sql, params = condition.to_sql("sqlite")
    assert sql == "1 = 0"  # Always false
    assert params == []

    # Empty NOT IN should always be true (everything is not in an empty set)
    condition = c.status.not_in([])
    sql, params = condition.to_sql("sqlite")
    assert sql == "1 = 1"  # Always true
    assert params == []

    # Test with other dialects too
    condition = c.model.in_([])
    sql, params = condition.to_sql("postgres")
    assert sql == "1 = 0"
    assert params == []

    condition = c.status.not_in([])
    sql, params = condition.to_sql("duckdb")
    assert sql == "1 = 1"
    assert params == []


def test_null_operators() -> None:
    """Test NULL and NOT NULL operators."""
    condition = c.error_message.is_null()
    sql, params = condition.to_sql("sqlite")
    assert sql == '"error_message" IS NULL'
    assert params == []

    condition = c.error_message.is_not_null()
    sql, params = condition.to_sql("sqlite")
    assert sql == '"error_message" IS NOT NULL'
    assert params == []


def test_none_comparison() -> None:
    """Test that == None and != None map to IS NULL and IS NOT NULL."""
    # == None should map to IS NULL
    condition = c.error_message == None  # noqa: E711
    sql, params = condition.to_sql("sqlite")
    assert sql == '"error_message" IS NULL'
    assert params == []

    # != None should map to IS NOT NULL
    condition = c.error_message != None  # noqa: E711
    sql, params = condition.to_sql("sqlite")
    assert sql == '"error_message" IS NOT NULL'
    assert params == []

    # Test with other dialects
    condition = c.status == None  # noqa: E711
    sql, params = condition.to_sql("postgres")
    assert sql == '"status" IS NULL'
    assert params == []

    condition = c.status != None  # noqa: E711
    sql, params = condition.to_sql("duckdb")
    assert sql == '"status" IS NOT NULL'
    assert params == []

    # Combined with other conditions
    condition = (c.model == "gpt-4") & (c.error == None)  # noqa: E711
    sql, params = condition.to_sql("sqlite")
    assert sql == '("model" = ? AND "error" IS NULL)'
    assert params == ["gpt-4"]


def test_like_operator() -> None:
    """Test LIKE and NOT LIKE operators."""
    condition = c.error_message.like("%timeout%")
    sql, params = condition.to_sql("sqlite")
    assert sql == '"error_message" LIKE ?'
    assert params == ["%timeout%"]

    condition = c.log.not_like("/tmp/%")
    sql, params = condition.to_sql("sqlite")
    assert sql == '"log" NOT LIKE ?'
    assert params == ["/tmp/%"]


def test_ilike_operator() -> None:
    """Test ILIKE and NOT ILIKE operators for case-insensitive matching."""
    # PostgreSQL - native ILIKE support
    condition = c.error_message.ilike("%TIMEOUT%")
    sql, params = condition.to_sql("postgres")
    assert sql == '"error_message" ILIKE $1'
    assert params == ["%TIMEOUT%"]

    condition = c.log.not_ilike("/TMP/%")
    sql, params = condition.to_sql("postgres")
    assert sql == '"log" NOT ILIKE $1'
    assert params == ["/TMP/%"]

    # SQLite - should use LOWER() for case-insensitivity
    condition = c.error_message.ilike("%TIMEOUT%")
    sql, params = condition.to_sql("sqlite")
    assert sql == 'LOWER("error_message") LIKE LOWER(?)'
    assert params == ["%TIMEOUT%"]

    condition = c.log.not_ilike("/TMP/%")
    sql, params = condition.to_sql("sqlite")
    assert sql == 'LOWER("log") NOT LIKE LOWER(?)'
    assert params == ["/TMP/%"]

    # DuckDB - should also use LOWER() for case-insensitivity
    condition = c.status.ilike("SUCCESS%")
    sql, params = condition.to_sql("duckdb")
    assert sql == 'LOWER("status") LIKE LOWER(?)'
    assert params == ["SUCCESS%"]

    condition = c.model.not_ilike("%GPT%")
    sql, params = condition.to_sql("duckdb")
    assert sql == 'LOWER("model") NOT LIKE LOWER(?)'
    assert params == ["%GPT%"]

    # Test with JSON paths too
    condition = c["metadata.message"].ilike("%Error%")
    sql, params = condition.to_sql("postgres")
    assert sql == """"metadata"->>'message' ILIKE $1"""
    assert params == ["%Error%"]

    # SQLite with JSON path
    condition = c["metadata.message"].ilike("%Error%")
    sql, params = condition.to_sql("sqlite")
    assert sql == """LOWER(json_extract("metadata", '$.message')) LIKE LOWER(?)"""
    assert params == ["%Error%"]

    # DuckDB with JSON path - now uses json_extract_string with VARCHAR cast
    condition = c["metadata.message"].ilike("%Error%")
    sql, params = condition.to_sql("duckdb")
    assert (
        sql
        == """LOWER(CAST(json_extract_string("metadata", '$.message') AS VARCHAR)) LIKE LOWER(?)"""
    )
    assert params == ["%Error%"]


def test_between_operator() -> None:
    """Test BETWEEN and NOT BETWEEN operators."""
    condition = c.score.between(0.5, 0.9)
    sql, params = condition.to_sql("sqlite")
    assert sql == '"score" BETWEEN ? AND ?'
    assert params == [0.5, 0.9]

    condition = c.retries.not_between(1, 3)
    sql, params = condition.to_sql("sqlite")
    assert sql == '"retries" NOT BETWEEN ? AND ?'
    assert params == [1, 3]


def test_between_with_null_bounds() -> None:
    """Test that BETWEEN properly handles NULL bounds."""
    # NULL in lower bound should raise ValueError
    with pytest.raises(ValueError, match="BETWEEN operator requires non-None bounds"):
        c.score.between(None, 0.9)

    # NULL in upper bound should raise ValueError
    with pytest.raises(ValueError, match="BETWEEN operator requires non-None bounds"):
        c.score.between(0.5, None)

    # NULL in both bounds should raise ValueError
    with pytest.raises(ValueError, match="BETWEEN operator requires non-None bounds"):
        c.score.between(None, None)

    # Same for NOT BETWEEN
    with pytest.raises(
        ValueError, match="NOT BETWEEN operator requires non-None bounds"
    ):
        c.retries.not_between(None, 3)

    with pytest.raises(
        ValueError, match="NOT BETWEEN operator requires non-None bounds"
    ):
        c.retries.not_between(1, None)

    with pytest.raises(
        ValueError, match="NOT BETWEEN operator requires non-None bounds"
    ):
        c.retries.not_between(None, None)


def test_logical_operators() -> None:
    """Test AND, OR, and NOT logical operators."""
    # AND
    condition = (c.model == "gpt-4") & (c.score > 0.8)
    sql, params = condition.to_sql("sqlite")
    assert sql == '("model" = ? AND "score" > ?)'
    assert params == ["gpt-4", 0.8]

    # OR
    condition = (c.status == "error") | (c.retries > 2)
    sql, params = condition.to_sql("sqlite")
    assert sql == '("status" = ? OR "retries" > ?)'
    assert params == ["error", 2]

    # NOT
    condition = ~(c.model == "gpt-3.5-turbo")
    sql, params = condition.to_sql("sqlite")
    assert sql == 'NOT ("model" = ?)'
    assert params == ["gpt-3.5-turbo"]


def test_complex_nested_conditions() -> None:
    """Test complex nested conditions."""
    condition = (
        ((c.model == "gpt-4") & (c.score > 0.8))
        | ((c.model == "claude") & (c.score > 0.7))
    ) & ~(c.error_message.is_not_null())

    sql, params = condition.to_sql("sqlite")
    assert "AND" in sql
    assert "OR" in sql
    assert "NOT" in sql
    assert len(params) == 4


def test_bracket_notation() -> None:
    """Test bracket notation for column access."""
    condition = c["custom_field"] > 100
    sql, params = condition.to_sql("sqlite")
    assert sql == '"custom_field" > ?'
    assert params == [100]


def test_nested_json_paths() -> None:
    """Test nested JSON path extraction with proper escaping."""
    # Simple nested path
    condition = c["metadata.config.temperature"] > 0.7

    # SQLite
    sql, params = condition.to_sql("sqlite")
    assert sql == "json_extract(\"metadata\", '$.config.temperature') > ?"
    assert params == [0.7]

    # DuckDB - now uses json_extract_string with type casting
    sql, params = condition.to_sql("duckdb")
    assert (
        sql == "(json_extract_string(\"metadata\", '$.config.temperature'))::DOUBLE > ?"
    )
    assert params == [0.7]

    # PostgreSQL - should use ->> for last element AND cast from text for numeric comparison
    sql, params = condition.to_sql("postgres")
    assert (
        sql == """("metadata"->'config'->>'temperature')::text::double precision > $1"""
    )
    assert params == [0.7]


def test_column_name_escaping() -> None:
    """Test that column names with special characters are properly escaped."""
    # Column name with double quotes
    condition = c['col"umn'] == "value"
    sql, params = condition.to_sql("sqlite")
    assert sql == '"col""umn" = ?'
    assert params == ["value"]

    # JSON path with single quotes - now gets quoted in SQLite due to special chars
    condition = c["metadata.key'with'quotes"] == "value"
    sql, params = condition.to_sql("sqlite")
    assert sql == """json_extract("metadata", '$."key''with''quotes"') = ?"""
    assert params == ["value"]

    # DuckDB - uses json_extract_string
    sql, params = condition.to_sql("duckdb")
    assert sql == """json_extract_string("metadata", '$.key''with''quotes') = ?"""
    assert params == ["value"]


def test_postgres_json_type_casting() -> None:
    """Test that PostgreSQL properly casts JSON values for comparisons."""
    # Integer comparison - should cast from text to bigint
    condition = c["metadata.retries"] > 3
    sql, params = condition.to_sql("postgres")
    assert sql == """("metadata"->>'retries')::text::bigint > $1"""
    assert params == [3]

    # Float comparison - should cast from text to double precision
    condition = c["metadata.score"] >= 0.75
    sql, params = condition.to_sql("postgres")
    assert sql == """("metadata"->>'score')::text::double precision >= $1"""
    assert params == [0.75]

    # Boolean comparison - should cast from text to boolean
    condition = c["metadata.enabled"] == True  # noqa: E712
    sql, params = condition.to_sql("postgres")
    assert sql == """("metadata"->>'enabled')::text::boolean = $1"""
    assert params == [True]

    condition = c["metadata.flag"] != False  # noqa: E712
    sql, params = condition.to_sql("postgres")
    assert sql == """("metadata"->>'flag')::text::boolean != $1"""
    assert params == [False]

    # BETWEEN with numeric values - should cast from text
    condition = c["metadata.score"].between(0.5, 0.9)
    sql, params = condition.to_sql("postgres")
    assert sql == """("metadata"->>'score')::text::double precision BETWEEN $1 AND $2"""
    assert params == [0.5, 0.9]

    # String comparison - no cast needed
    condition = c["metadata.status"] == "active"
    sql, params = condition.to_sql("postgres")
    assert sql == """"metadata"->>'status' = $1"""
    assert params == ["active"]

    # LIKE operator - should NOT cast (string operation)
    condition = c["metadata.message"].like("%error%")
    sql, params = condition.to_sql("postgres")
    assert sql == """"metadata"->>'message' LIKE $1"""
    assert params == ["%error%"]

    # IN operator - should NOT cast
    condition = c["metadata.status"].in_(["active", "pending"])
    sql, params = condition.to_sql("postgres")
    assert sql == """"metadata"->>'status' IN ($1, $2)"""
    assert params == ["active", "pending"]

    # IS NULL - should NOT cast
    condition = c["metadata.optional"].is_null()
    sql, params = condition.to_sql("postgres")
    assert sql == """"metadata"->>'optional' IS NULL"""
    assert params == []

    # Deep nested paths with casting
    condition = c["metadata.config.max_retries"] < 10
    sql, params = condition.to_sql("postgres")
    assert sql == """("metadata"->'config'->>'max_retries')::text::bigint < $1"""
    assert params == [10]


def test_postgres_casting_with_none() -> None:
    """Test PostgreSQL casting handles None values correctly."""
    # Comparison with None should not crash the casting logic
    condition = c["metadata.field"] == None  # noqa: E711
    sql, params = condition.to_sql("postgres")
    assert sql == """"metadata"->>'field' IS NULL"""
    assert params == []


def test_postgres_double_cast_correctness() -> None:
    """Test that the double cast (::text::type) works correctly for PostgreSQL JSON extraction."""
    # The ->> operator returns text, so we need ::text::type casting

    # Test with various types to ensure the double cast is correct
    test_cases = [
        (c["config.retry_count"] > 5, int, "bigint", 5),
        (c["settings.threshold"] < 0.95, float, "double precision", 0.95),
        (c["flags.enabled"] == True, bool, "boolean", True),  # noqa: E712
        (c["options.active"] != False, bool, "boolean", False),  # noqa: E712
    ]

    for condition, val_type, pg_type, expected_val in test_cases:
        sql, params = condition.to_sql("postgres")
        # Should have ::text:: in the middle for the double cast
        assert "::text::" in sql, f"Missing ::text:: in SQL for {val_type}: {sql}"
        assert f"::text::{pg_type}" in sql, f"Expected ::text::{pg_type} in SQL: {sql}"
        assert params == [expected_val]

    # Verify text comparison doesn't get double cast
    condition = c["metadata.name"] == "test"
    sql, params = condition.to_sql("postgres")
    assert "::text::" not in sql  # String comparison shouldn't have type casting
    assert params == ["test"]


def test_no_casting_for_non_json_columns() -> None:
    """Test that regular columns don't get cast in PostgreSQL."""
    # Regular column with integer - no casting
    condition = c.retries > 3
    sql, params = condition.to_sql("postgres")
    assert sql == '"retries" > $1'
    assert params == [3]

    # Regular column with float - no casting
    condition = c.score >= 0.75
    sql, params = condition.to_sql("postgres")
    assert sql == '"score" >= $1'
    assert params == [0.75]


def test_deep_nested_paths() -> None:
    """Test deeply nested JSON paths."""
    condition = c["metadata.level1.level2.level3.value"] > 10

    # SQLite
    sql, params = condition.to_sql("sqlite")
    assert sql == "json_extract(\"metadata\", '$.level1.level2.level3.value') > ?"
    assert params == [10]

    # DuckDB - uses json_extract_string with type casting
    sql, params = condition.to_sql("duckdb")
    assert (
        sql
        == "(json_extract_string(\"metadata\", '$.level1.level2.level3.value'))::BIGINT > ?"
    )
    assert params == [10]

    # PostgreSQL - should cast from text to integer for numeric comparison
    sql, params = condition.to_sql("postgres")
    assert (
        sql
        == """("metadata"->'level1'->'level2'->'level3'->>'value')::text::bigint > $1"""
    )
    assert params == [10]


def test_postgres_parameter_numbering() -> None:
    """Test that PostgreSQL parameter numbering is correct (1-based)."""
    # Single parameter - should be $1
    condition = c.score > 0.5
    sql, params = condition.to_sql("postgres")
    assert sql == '"score" > $1'
    assert params == [0.5]

    # BETWEEN - should be $1 and $2
    condition = c.score.between(0.3, 0.7)
    sql, params = condition.to_sql("postgres")
    assert sql == '"score" BETWEEN $1 AND $2'
    assert params == [0.3, 0.7]

    # IN with multiple values - should be $1, $2, $3
    condition = c.model.in_(["gpt-4", "claude", "gemini"])
    sql, params = condition.to_sql("postgres")
    assert sql == '"model" IN ($1, $2, $3)'
    assert params == ["gpt-4", "claude", "gemini"]

    # Combined conditions - parameters should be numbered sequentially
    condition = (c.score > 0.5) & (c.retries < 3)
    sql, params = condition.to_sql("postgres")
    assert sql == '("score" > $1 AND "retries" < $2)'
    assert params == [0.5, 3]

    # Complex with BETWEEN in combination
    condition = (c.model == "gpt-4") & (c.score.between(0.3, 0.7))
    sql, params = condition.to_sql("postgres")
    assert sql == '("model" = $1 AND "score" BETWEEN $2 AND $3)'
    assert params == ["gpt-4", 0.3, 0.7]

    # Multiple IN clauses
    condition = (c.model.in_(["gpt-4", "claude"])) & (
        c.status.in_(["success", "pending"])
    )
    sql, params = condition.to_sql("postgres")
    assert sql == '("model" IN ($1, $2) AND "status" IN ($3, $4))'
    assert params == ["gpt-4", "claude", "success", "pending"]

    # Complex nested with all types
    condition = ((c.model == "gpt-4") & (c.score.between(0.3, 0.7))) | (
        (c.status.in_(["error", "timeout"])) & (c.retries > 2)
    )
    sql, params = condition.to_sql("postgres")
    # Should have parameters $1, $2, $3, $4, $5, $6
    assert "$1" in sql and "$2" in sql and "$3" in sql
    assert "$4" in sql and "$5" in sql and "$6" in sql
    assert len(params) == 6
    assert params == ["gpt-4", 0.3, 0.7, "error", "timeout", 2]


# ============================================================================
# TranscriptDB Tests
# ============================================================================


@pytest.mark.asyncio
async def test_connect_disconnect() -> None:
    """Test database connection and disconnection."""
    df = create_test_dataframe(5)
    db = EvalLogTranscriptsView(df)

    # Connect
    await db.connect()
    assert db._conn is not None

    # Disconnect
    await db.disconnect()
    # Can't check if connection is closed in SQLite, but no error is good


@pytest.mark.asyncio
async def test_select_all(db: EvalLogTranscriptsView) -> None:
    """Test querying all records."""
    results = [item async for item in db.select(Query())]
    assert len(results) == 20

    # Check that each result is a TranscriptInfo
    for result in results:
        assert isinstance(result, TranscriptInfo)
        assert result.transcript_id.startswith("sample_")
        assert result.source_uri
        assert result.source_uri.startswith("/path/to/log_")
        assert isinstance(result.metadata, dict)


@pytest.mark.asyncio
async def test_select_with_filter(db: EvalLogTranscriptsView) -> None:
    """Test querying with filters."""
    # Filter by model
    results = [item async for item in db.select(Query(where=[c.model == "gpt-4"]))]
    for result in results:
        assert result.model == "gpt-4"

    # Filter by score range
    results = [item async for item in db.select(Query(where=[c.score > 0.7]))]
    for result in results:
        assert cast(float, result.score) > 0.7


@pytest.mark.asyncio
async def test_select_with_multiple_conditions(db: EvalLogTranscriptsView) -> None:
    """Test querying with multiple conditions."""
    conditions = [c.model == "gpt-4", c.score > 0.6]
    results = [item async for item in db.select(Query(where=conditions))]

    for result in results:
        assert result.model == "gpt-4"
        assert cast(float, result.score) > 0.6


@pytest.mark.asyncio
async def test_select_with_limit(db: EvalLogTranscriptsView) -> None:
    """Test querying with limit."""
    results = [item async for item in db.select(Query(limit=5))]
    assert len(results) == 5

    # With filter and limit
    results = [
        item async for item in db.select(Query(where=[c.model == "gpt-4"], limit=2))
    ]
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_count_method_all(db: EvalLogTranscriptsView) -> None:
    """Test count() method with no filter."""
    count = await db.count(Query())
    assert count == 20


@pytest.mark.asyncio
async def test_count_method_with_where(db: EvalLogTranscriptsView) -> None:
    """Test count() method with filter condition."""
    count = await db.count(Query(where=[c.model == "gpt-4"]))
    # gpt-4 is one of 3 models, so expect ~7 results
    assert count > 0


@pytest.mark.asyncio
async def test_select_with_shuffle(db: EvalLogTranscriptsView) -> None:
    """Test querying with shuffle."""
    # Get results without shuffle
    results1 = [item async for item in db.select(Query(limit=10))]
    ids1 = [r.transcript_id for r in results1]

    # Get results with shuffle (seed=42)
    results2 = [item async for item in db.select(Query(limit=10, shuffle=42))]
    ids2 = [r.transcript_id for r in results2]

    # Results should be different order (very unlikely to be same)
    assert ids1 != ids2

    # Get results with same seed - should be same order
    results3 = [item async for item in db.select(Query(limit=10, shuffle=42))]
    ids3 = [r.transcript_id for r in results3]
    assert ids2 == ids3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "column,direction,extractor,reverse",
    [
        (c.score.name, "ASC", lambda r: cast(float, r.score), False),
        (c.score.name, "DESC", lambda r: cast(float, r.score), True),
        (c.model.name, "ASC", lambda r: r.model, False),
        (c.model.name, "DESC", lambda r: r.model, True),
    ],
)
async def test_select_with_order_by_single_column(
    db: EvalLogTranscriptsView,
    column: str,
    direction: Literal["ASC", "DESC"],
    extractor: Any,
    reverse: bool,
) -> None:
    """Test ordering by single column with various directions."""
    results = [
        item async for item in db.select(Query(order_by=[OrderBy(column, direction)]))
    ]
    values = [extractor(r) for r in results if extractor(r) is not None]
    assert values == sorted(values, reverse=reverse)


@pytest.mark.asyncio
async def test_select_with_order_by_chaining(db: EvalLogTranscriptsView) -> None:
    """Test ordering with multiple columns (tie-breaking)."""
    # Order by model ASC, then score DESC
    results = [
        item
        async for item in db.select(
            Query(
                order_by=[OrderBy(c.model.name, "ASC"), OrderBy(c.score.name, "DESC")]
            )
        )
    ]

    # Group by model and verify scores are descending within each model
    from itertools import groupby

    for _model, group in groupby(results, key=lambda r: r.model):
        scores = [cast(float, r.score) for r in group]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "where_clause,limit,expected_min_results",
    [
        ([c.model == "gpt-4"], None, 1),
        ([], 5, 5),
    ],
)
async def test_order_by_with_where_and_limit(
    db: EvalLogTranscriptsView,
    where_clause: list[Any],
    limit: int | None,
    expected_min_results: int,
) -> None:
    """Test combining where clause and limit with order_by."""
    results = [
        item
        async for item in db.select(
            Query(
                where=where_clause,
                order_by=[OrderBy(c.score.name, "ASC")],
                limit=limit,
            )
        )
    ]

    # Verify results match expectations
    if where_clause:
        for result in results:
            assert result.model == "gpt-4"
    if limit:
        assert len(results) == expected_min_results

    # Verify ordering
    scores = [cast(float, r.score) for r in results]
    assert scores == sorted(scores)


@pytest.mark.asyncio
async def test_shuffle_deterministic(db: EvalLogTranscriptsView) -> None:
    """Test that shuffle with same seed produces deterministic order."""
    # Get results with shuffle
    results1 = [item async for item in db.select(Query(shuffle=42, limit=10))]
    ids1 = [r.transcript_id for r in results1]

    # Get results with same shuffle seed - should be same order
    results2 = [item async for item in db.select(Query(shuffle=42, limit=10))]
    ids2 = [r.transcript_id for r in results2]
    assert ids1 == ids2

    # Get results without shuffle - should be different
    results3 = [
        item
        async for item in db.select(
            Query(order_by=[OrderBy(c.score.name, "ASC")], limit=10)
        )
    ]
    ids3 = [r.transcript_id for r in results3]
    assert ids1 != ids3  # Shuffled vs ordered should differ


@pytest.mark.asyncio
async def test_order_by_empty_results(db: EvalLogTranscriptsView) -> None:
    """Test order_by on empty result set."""
    results = [
        item
        async for item in db.select(
            Query(
                where=[c.model == "nonexistent"],
                order_by=[OrderBy(c.score.name, "ASC")],
            )
        )
    ]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_complex_queries(db: EvalLogTranscriptsView) -> None:
    """Test complex queries with multiple operators."""
    # Complex condition
    conditions = [
        (c.model.in_(["gpt-4", "claude"])) & (c.score > 0.6),
        c.error_message.is_null(),
    ]

    results = [item async for item in db.select(Query(where=conditions))]
    for result in results:
        assert result.model in ["gpt-4", "claude"]
        assert cast(float, result.score) > 0.6
        assert result.metadata.get("error_message") is None


@pytest.mark.asyncio
async def test_metadata_extraction(db: EvalLogTranscriptsView) -> None:
    """Test that metadata is properly extracted."""
    results = [item async for item in db.select(Query(limit=1))]
    assert len(results) == 1

    result = results[0]
    metadata = result.metadata

    # Check expected metadata fields
    assert result.model
    assert result.score
    assert "status" in metadata
    assert "retries" in metadata


@pytest.mark.asyncio
async def test_none_comparison_in_db(db: EvalLogTranscriptsView) -> None:
    """Test that == None and != None work correctly in database queries."""
    # Using == None (should behave same as is_null())
    results_eq_none = [
        item
        async for item in db.select(
            Query(where=[c.error_message == None])  # noqa: E711
        )
    ]
    results_is_null = [
        item async for item in db.select(Query(where=[c.error_message.is_null()]))
    ]
    assert len(results_eq_none) == len(results_is_null)

    # Using != None (should behave same as is_not_null())
    results_ne_none = [
        item
        async for item in db.select(
            Query(where=[c.error_message != None])  # noqa: E711
        )
    ]
    results_is_not_null = [
        item async for item in db.select(Query(where=[c.error_message.is_not_null()]))
    ]
    assert len(results_ne_none) == len(results_is_not_null)

    # Verify they partition all records
    assert len(results_eq_none) + len(results_ne_none) == 20


@pytest.mark.asyncio
async def test_null_value_handling(db: EvalLogTranscriptsView) -> None:
    """Test handling of NULL values in metadata."""
    # Query for null error_message
    results = [
        item async for item in db.select(Query(where=[c.error_message.is_null()]))
    ]

    for result in results:
        # NULL values should not appear in metadata dict
        assert (
            "error_message" not in result.metadata
            or result.metadata["error_message"] is None
        )

    # Query for non-null error_message
    results = [
        item async for item in db.select(Query(where=[c.error_message.is_not_null()]))
    ]

    for result in results:
        assert result.metadata.get("error_message") is not None


# ============================================================================
# Transcripts API Tests
# ============================================================================


# ============================================================================
# Edge Cases Tests
# ============================================================================


@pytest.mark.asyncio
async def test_empty_dataframe() -> None:
    """Test with empty DataFrame."""
    df = pd.DataFrame(columns=["sample_id", "id", "epoch", "eval_id", "log"])
    db = EvalLogTranscriptsView(df)
    await db.connect()

    results = [item async for item in db.select(Query())]
    assert len(results) == 0

    await db.disconnect()


@pytest.mark.asyncio
async def test_missing_required_columns() -> None:
    """Test error handling when required columns are missing."""
    # DataFrame with all required columns but one has None
    df = pd.DataFrame(
        {
            "sample_id": [None],  # Missing sample_id value
            "id": "myid",
            "epoch": 1,
            "eval_id": ["eval_123"],
            "log": ["/path/to/log.json"],
            "model": ["gpt-4"],
        }
    )

    db = EvalLogTranscriptsView(df)
    await db.connect()

    # Should raise error when trying to query
    with pytest.raises(ValueError, match="Missing required fields"):
        [item async for item in db.select(Query())]

    await db.disconnect()


@pytest.mark.asyncio
async def test_empty_in_clause_in_db(db: Any) -> None:
    """Test that empty IN/NOT IN work correctly in actual queries."""
    # Empty IN should return no results
    results = [item async for item in db.select(Query(where=[c.model.in_([])]))]
    assert len(results) == 0  # Always false, no results

    # Empty NOT IN should return all results
    results = [item async for item in db.select(Query(where=[c.model.not_in([])]))]
    assert len(results) == 20  # Always true, all results

    # Combined with other conditions
    results = [
        item
        async for item in db.select(
            Query(
                where=[
                    c.score > 0.5,
                    c.status.not_in(
                        []
                    ),  # This is always true, shouldn't affect results
                ]
            )
        )
    ]
    # Should be same as just c.score > 0.5
    results_without = [item async for item in db.select(Query(where=[c.score > 0.5]))]
    assert len(results) == len(results_without)


@pytest.mark.asyncio
async def test_large_in_clause() -> None:
    """Test IN clause with many values."""
    df = create_test_dataframe(100)
    db = EvalLogTranscriptsView(df)
    await db.connect()

    # Create a large list of values
    large_list = [f"model_{i}" for i in range(50)]
    large_list.append("gpt-4")  # Include one that exists

    results = [item async for item in db.select(Query(where=[c.model.in_(large_list)]))]

    # Should find some results
    assert len(results) > 0

    await db.disconnect()


# ============================================================================
# transcript_ids() Tests
# ============================================================================


@pytest.mark.asyncio
async def test_transcript_ids_all(db: EvalLogTranscriptsView) -> None:
    """Test transcript_ids returns all IDs."""
    ids = await db.transcript_ids(Query())
    assert len(ids) == 20
    assert all(isinstance(k, str) for k in ids.keys())
    assert all(v is None or isinstance(v, str) for v in ids.values())


@pytest.mark.asyncio
async def test_transcript_ids_with_filter(db: EvalLogTranscriptsView) -> None:
    """Test transcript_ids with where filter."""
    ids = await db.transcript_ids(Query(where=[c.model == "gpt-4"]))
    # gpt-4 appears every 3rd item (indices 0, 3, 6, ...) in 20 items = ~7
    assert 0 < len(ids) < 20
    for tid in ids.keys():
        # Verify filtered IDs match select results
        results = [item async for item in db.select(Query(where=[c.model == "gpt-4"]))]
        result_ids = {r.transcript_id for r in results}
        assert tid in result_ids


@pytest.mark.asyncio
async def test_transcript_ids_with_limit(db: EvalLogTranscriptsView) -> None:
    """Test transcript_ids respects limit."""
    ids = await db.transcript_ids(Query(limit=5))
    assert len(ids) == 5


@pytest.mark.asyncio
async def test_transcript_ids_with_shuffle(db: EvalLogTranscriptsView) -> None:
    """Test transcript_ids with deterministic shuffle."""
    ids1 = await db.transcript_ids(Query(shuffle=42))
    ids2 = await db.transcript_ids(Query(shuffle=42))
    ids3 = await db.transcript_ids(Query(shuffle=99))

    # Same seed = same order
    assert list(ids1.keys()) == list(ids2.keys())
    # Different seed = different order (with high probability)
    assert list(ids1.keys()) != list(ids3.keys())


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
