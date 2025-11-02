"""Comprehensive test suite for metadata filtering DSL."""

import pytest
from inspect_scout._transcript.metadata import (
    Column,
    LogicalOperator,
    Operator,
    SQLDialect,
)
from inspect_scout._transcript.metadata import (
    metadata as m,
)


def test_equality() -> None:
    """Test equality operator."""
    filter = m.model == "gpt-4"
    sql, params = filter.to_sql("sqlite")
    assert sql == '"model" = ?'
    assert params == ["gpt-4"]


def test_equality_with_none() -> None:
    """Test equality with None becomes IS NULL."""
    filter = m.status == None  # noqa: E711
    sql, params = filter.to_sql("sqlite")
    assert sql == '"status" IS NULL'
    assert params == []


def test_inequality() -> None:
    """Test inequality operator."""
    filter = m.score != 0.5
    sql, params = filter.to_sql("sqlite")
    assert sql == '"score" != ?'
    assert params == [0.5]


def test_inequality_with_none() -> None:
    """Test inequality with None becomes IS NOT NULL."""
    filter = m.status != None  # noqa: E711
    sql, params = filter.to_sql("sqlite")
    assert sql == '"status" IS NOT NULL'
    assert params == []


def test_comparison_operators() -> None:
    """Test <, <=, >, >= operators."""
    filters = [
        (m.score < 0.8, '"score" < ?', [0.8]),
        (m.score <= 0.8, '"score" <= ?', [0.8]),
        (m.score > 0.8, '"score" > ?', [0.8]),
        (m.score >= 0.8, '"score" >= ?', [0.8]),
    ]
    for filter, expected_sql, expected_params in filters:
        sql, params = filter.to_sql("sqlite")
        assert sql == expected_sql
        assert params == expected_params


def test_in_operator() -> None:
    """Test IN operator."""
    filter = m.model.in_(["gpt-4", "claude"])
    sql, params = filter.to_sql("sqlite")
    assert sql == '"model" IN (?, ?)'
    assert params == ["gpt-4", "claude"]


def test_in_operator_empty() -> None:
    """Test IN with empty list."""
    filter = m.model.in_([])
    sql, params = filter.to_sql("sqlite")
    assert sql == "1 = 0"  # Always false
    assert params == []


def test_not_in_operator() -> None:
    """Test NOT IN operator."""
    filter = m.model.not_in(["gpt-3.5", "davinci"])
    sql, params = filter.to_sql("sqlite")
    assert sql == '"model" NOT IN (?, ?)'
    assert params == ["gpt-3.5", "davinci"]


def test_not_in_operator_empty() -> None:
    """Test NOT IN with empty list."""
    filter = m.model.not_in([])
    sql, params = filter.to_sql("sqlite")
    assert sql == "1 = 1"  # Always true
    assert params == []


def test_like_operator() -> None:
    """Test LIKE operator."""
    filter = m.message.like("%error%")
    sql, params = filter.to_sql("sqlite")
    assert sql == '"message" LIKE ?'
    assert params == ["%error%"]


def test_not_like_operator() -> None:
    """Test NOT LIKE operator."""
    filter = m.message.not_like("%success%")
    sql, params = filter.to_sql("sqlite")
    assert sql == '"message" NOT LIKE ?'
    assert params == ["%success%"]


def test_is_null() -> None:
    """Test IS NULL."""
    filter = m.error.is_null()
    sql, params = filter.to_sql("sqlite")
    assert sql == '"error" IS NULL'
    assert params == []


def test_is_not_null() -> None:
    """Test IS NOT NULL."""
    filter = m.error.is_not_null()
    sql, params = filter.to_sql("sqlite")
    assert sql == '"error" IS NOT NULL'
    assert params == []


def test_between() -> None:
    """Test BETWEEN operator."""
    filter = m.score.between(0.3, 0.7)
    sql, params = filter.to_sql("sqlite")
    assert sql == '"score" BETWEEN ? AND ?'
    assert params == [0.3, 0.7]


def test_between_with_none_raises() -> None:
    """Test BETWEEN with None bounds raises ValueError."""
    with pytest.raises(ValueError, match="BETWEEN operator requires non-None bounds"):
        m.score.between(None, 0.7)
    with pytest.raises(ValueError, match="BETWEEN operator requires non-None bounds"):
        m.score.between(0.3, None)


def test_not_between() -> None:
    """Test NOT BETWEEN operator."""
    filter = m.score.not_between(0.3, 0.7)
    sql, params = filter.to_sql("sqlite")
    assert sql == '"score" NOT BETWEEN ? AND ?'
    assert params == [0.3, 0.7]


def test_and_operator() -> None:
    """Test AND operator."""
    filter = (m.model == "gpt-4") & (m.score > 0.8)
    sql, params = filter.to_sql("sqlite")
    assert sql == '("model" = ? AND "score" > ?)'
    assert params == ["gpt-4", 0.8]


def test_or_operator() -> None:
    """Test OR operator."""
    filter = (m.status == "error") | (m.retries > 3)
    sql, params = filter.to_sql("sqlite")
    assert sql == '("status" = ? OR "retries" > ?)'
    assert params == ["error", 3]


def test_not_operator() -> None:
    """Test NOT operator."""
    filter = ~(m.enabled == True)  # noqa: E712
    sql, params = filter.to_sql("sqlite")
    assert sql == 'NOT ("enabled" = ?)'
    assert params == [True]


def test_complex_combination() -> None:
    """Test complex logical combinations."""
    filter = ((m.model == "gpt-4") & (m.score > 0.8)) | (
        (m.model == "claude") & (m.score > 0.7)
    )
    sql, params = filter.to_sql("sqlite")
    assert sql == '(("model" = ? AND "score" > ?) OR ("model" = ? AND "score" > ?))'
    assert params == ["gpt-4", 0.8, "claude", 0.7]


def test_sqlite_json_path() -> None:
    """Test SQLite json_extract for dotted paths."""
    filter = m["config.temperature"] > 0.5
    sql, params = filter.to_sql("sqlite")
    assert sql == "json_extract(\"config\", '$.temperature') > ?"
    assert params == [0.5]


def test_postgres_json_path() -> None:
    """Test PostgreSQL arrow operators for dotted paths."""
    filter = m["config.temperature"] > 0.5
    sql, params = filter.to_sql("postgres")
    # Should include cast for numeric comparison
    assert "config\"->>'temperature'" in sql
    assert "::text::double precision" in sql
    assert params == [0.5]


def test_duckdb_json_path() -> None:
    """Test DuckDB json_extract for dotted paths."""
    filter = m["config.model.name"] == "gpt-4"
    sql, params = filter.to_sql("duckdb")
    # Now uses json_extract for better compatibility
    assert "json_extract" in sql
    assert "$.model.name" in sql
    assert params == ["gpt-4"]


def test_deep_nesting() -> None:
    """Test deeply nested JSON paths."""
    filter = m["a.b.c.d.e"] == 42
    sql, params = filter.to_sql("sqlite")
    assert "json_extract" in sql
    assert "$.b.c.d.e" in sql
    assert params == [42]


def test_ilike_postgres() -> None:
    """Test ILIKE in PostgreSQL."""
    filter = m.name.ilike("%test%")
    sql, params = filter.to_sql("postgres")
    assert sql == '"name" ILIKE $1'
    assert params == ["%test%"]


def test_ilike_sqlite() -> None:
    """Test ILIKE fallback in SQLite."""
    filter = m.name.ilike("%test%")
    sql, params = filter.to_sql("sqlite")
    assert sql == 'LOWER("name") LIKE LOWER(?)'
    assert params == ["%test%"]


def test_ilike_duckdb() -> None:
    """Test ILIKE fallback in DuckDB."""
    filter = m.name.ilike("%test%")
    sql, params = filter.to_sql("duckdb")
    assert sql == 'LOWER("name") LIKE LOWER(?)'
    assert params == ["%test%"]


def test_not_ilike_postgres() -> None:
    """Test NOT ILIKE in PostgreSQL."""
    filter = m.name.not_ilike("%test%")
    sql, params = filter.to_sql("postgres")
    assert sql == '"name" NOT ILIKE $1'
    assert params == ["%test%"]


def test_not_ilike_fallback() -> None:
    """Test NOT ILIKE fallback."""
    filter = m.name.not_ilike("%test%")
    sql, params = filter.to_sql("sqlite")
    assert sql == 'LOWER("name") NOT LIKE LOWER(?)'
    assert params == ["%test%"]


def test_postgres_single_param() -> None:
    """Test single parameter uses $1."""
    filter = m.model == "gpt-4"
    sql, params = filter.to_sql("postgres")
    assert sql == '"model" = $1'
    assert params == ["gpt-4"]


def test_postgres_multiple_params() -> None:
    """Test multiple parameters use $1, $2, etc."""
    filter = (m.model == "gpt-4") & (m.score > 0.8)
    sql, params = filter.to_sql("postgres")
    assert "$1" in sql and "$2" in sql
    assert params == ["gpt-4", 0.8]


def test_postgres_in_params() -> None:
    """Test IN clause parameters."""
    filter = m.model.in_(["a", "b", "c"])
    sql, params = filter.to_sql("postgres")
    assert sql == '"model" IN ($1, $2, $3)'
    assert params == ["a", "b", "c"]


def test_postgres_between_params() -> None:
    """Test BETWEEN parameters."""
    filter = m.score.between(0.3, 0.7)
    sql, params = filter.to_sql("postgres")
    assert sql == '"score" BETWEEN $1 AND $2'
    assert params == [0.3, 0.7]


def test_postgres_cast_for_integer_comparison() -> None:
    """Test casting JSON to integer for comparison."""
    filter = m["config.max_tokens"] > 100
    sql, params = filter.to_sql("postgres")
    assert "::text::bigint" in sql
    assert params == [100]


def test_postgres_cast_for_float_comparison() -> None:
    """Test casting JSON to float for comparison."""
    filter = m["config.temperature"] > 0.5
    sql, params = filter.to_sql("postgres")
    assert "::text::double precision" in sql
    assert params == [0.5]


def test_postgres_cast_for_boolean_comparison() -> None:
    """Test casting JSON to boolean for comparison."""
    filter = m["config.enabled"] == True  # noqa: E712
    sql, params = filter.to_sql("postgres")
    assert "::text::boolean" in sql
    assert params == [True]


def test_postgres_no_cast_for_string_comparison() -> None:
    """Test no casting for string comparison."""
    filter = m["config.model"] == "gpt-4"
    sql, params = filter.to_sql("postgres")
    assert "::text::bigint" not in sql
    assert "::text::double" not in sql
    assert "::text::boolean" not in sql
    assert params == ["gpt-4"]


def test_postgres_no_cast_for_like_operator() -> None:
    """Test no casting for LIKE operator."""
    filter = m["config.message"].like("%error%")
    sql, params = filter.to_sql("postgres")
    assert "::" not in sql or "->>" in sql  # No type casting
    assert params == ["%error%"]


def test_postgres_cast_for_between_operator() -> None:
    """Test casting for BETWEEN operator."""
    filter = m["config.score"].between(0.3, 0.7)
    sql, params = filter.to_sql("postgres")
    assert "::text::double precision" in sql
    assert params == [0.3, 0.7]


def test_double_quote_in_column_name() -> None:
    """Test escaping double quotes in column names."""
    col = Column('col"with"quotes')
    filter = col == "value"
    sql, params = filter.to_sql("sqlite")
    assert sql == '"col""with""quotes" = ?'
    assert params == ["value"]


def test_single_quote_in_json_path_sqlite() -> None:
    """Test escaping single quotes in JSON paths for SQLite."""
    col = Column("data.key'with'quotes")
    filter = col == "value"
    sql, params = filter.to_sql("sqlite")
    assert "key''with''quotes" in sql
    assert params == ["value"]


def test_single_quote_in_json_path_postgres() -> None:
    """Test escaping single quotes in JSON paths for PostgreSQL."""
    col = Column("data.key'with'quotes")
    filter = col == "value"
    sql, params = filter.to_sql("postgres")
    assert "key''with''quotes" in sql
    assert params == ["value"]


def test_bracket_notation_simple() -> None:
    """Test bracket notation for simple columns."""
    filter = m["model"] == "gpt-4"
    sql, params = filter.to_sql("sqlite")
    assert sql == '"model" = ?'
    assert params == ["gpt-4"]


def test_bracket_notation_json_path() -> None:
    """Test bracket notation for JSON paths."""
    filter = m["config.temperature"] > 0.5
    sql, params = filter.to_sql("sqlite")
    assert "json_extract" in sql
    assert params == [0.5]


def test_enum_values() -> None:
    """Test enum value strings."""
    assert Operator.EQ.value == "="
    assert Operator.NE.value == "!="
    assert LogicalOperator.AND.value == "AND"
    assert LogicalOperator.OR.value == "OR"


def test_dialect_enum() -> None:
    """Test SQLDialect enum values."""
    assert SQLDialect.SQLITE.value == "sqlite"
    assert SQLDialect.DUCKDB.value == "duckdb"
    assert SQLDialect.POSTGRES.value == "postgres"


def test_underscore_attribute_raises() -> None:
    """Test that accessing underscore attributes raises AttributeError."""
    with pytest.raises(AttributeError):
        _ = m._private


def test_dialect_string_conversion() -> None:
    """Test converting string to SQLDialect enum."""
    filter = m.test == "value"
    sql1, _ = filter.to_sql("sqlite")
    sql2, _ = filter.to_sql(SQLDialect.SQLITE)
    assert sql1 == sql2


def test_complex_nested_conditions() -> None:
    """Test deeply nested logical conditions."""
    filter = ~(((m.a == 1) & (m.b == 2)) | ((m.c == 3) & (m.d == 4)))
    sql, params = filter.to_sql("sqlite")
    assert sql.startswith("NOT (")
    assert params == [1, 2, 3, 4]


# Tests for issues that need fixes (currently would fail)
def test_postgres_in_with_json_casting() -> None:
    """Test IN operator with JSON path needs casting in Postgres."""
    filter = m["config.level"].in_([1, 2, 3])
    sql, params = filter.to_sql("postgres")
    # Should cast JSON text to integer for IN comparison
    assert "::text::bigint" in sql
    assert "IN ($1, $2, $3)" in sql
    assert params == [1, 2, 3]


def test_array_index_sqlite() -> None:
    """Test array indexing in SQLite JSON paths."""
    filter = m["data.items.0.name"] == "first"
    sql, params = filter.to_sql("sqlite")
    # Should generate json_extract("data", '$.items[0].name') not $.items.0.name
    assert "$.items[0].name" in sql
    assert params == ["first"]


def test_array_index_postgres() -> None:
    """Test array indexing in PostgreSQL."""
    filter = m["data.items.0.name"] == "first"
    sql, params = filter.to_sql("postgres")
    # Should use ->0 not ->'0' for array index
    assert "->0" in sql
    assert "->'0'" not in sql
    assert params == ["first"]


def test_key_with_dot_sqlite() -> None:
    """Test JSON key containing dot in SQLite."""
    filter = m['data."user.name"'] == "alice"
    sql, params = filter.to_sql("sqlite")
    # Should treat "user.name" as single key
    assert '$."user.name"' in sql or "user.name" in sql
    assert params == ["alice"]


def test_in_with_null_values() -> None:
    """Test IN operator with NULL in the list."""
    filter = m.status.in_(["active", None, "pending"])
    sql, params = filter.to_sql("sqlite")
    # Should handle NULL separately: (status IN (?, ?) OR status IS NULL)
    assert "IS NULL" in sql
    assert params == ["active", "pending"]  # None filtered out


def test_duckdb_json_extract_function() -> None:
    """Test DuckDB uses json_extract for better compatibility."""
    filter = m["config.level"] > 5
    sql, params = filter.to_sql("duckdb")
    # Should use json_extract for VARCHAR columns containing JSON
    assert "json_extract" in sql
    assert params == [5]


def test_duckdb_json_type_casting() -> None:
    """Test DuckDB casts JSON values for type-safe comparisons."""
    filter = m["config.threshold"] > 0.5
    sql, params = filter.to_sql("duckdb")
    # Should cast to DOUBLE for numeric comparison
    assert "::DOUBLE" in sql
    assert params == [0.5]


def test_bracket_notation_array_access() -> None:
    """Test bracket notation for array access."""
    filter = m["items[0].name"] == "first"
    sql, params = filter.to_sql("sqlite")
    # items is the column, [0].name is the path within it
    assert "$[0].name" in sql
    assert params == ["first"]


def test_multiple_brackets() -> None:
    """Test multiple bracket indices."""
    filter = m["data[0][2].value"] == 42
    sql, params = filter.to_sql("sqlite")
    assert "[0][2]" in sql
    assert params == [42]


def test_base_only_bracket() -> None:
    """Test bracket notation without dots."""
    filter = m["array[1]"] == "test"
    sql, params = filter.to_sql("sqlite")
    # array is the column, [1] is the path
    assert "$[1]" in sql
    assert params == ["test"]


def test_sqlite_key_with_hyphen() -> None:
    """Test SQLite JSONPath with hyphenated keys."""
    filter = m["data.user-name"] == "alice"
    sql, params = filter.to_sql("sqlite")
    # Hyphenated keys should be quoted
    assert '"user-name"' in sql
    assert params == ["alice"]


def test_sqlite_key_with_space() -> None:
    """Test SQLite JSONPath with spaces in keys."""
    filter = m['data."user name"'] == "bob"
    sql, params = filter.to_sql("sqlite")
    assert '"user name"' in sql
    assert params == ["bob"]


def test_duckdb_like_with_json_path() -> None:
    """Test DuckDB casts JSON to VARCHAR for LIKE operations."""
    filter = m["config.message"].like("%error%")
    sql, params = filter.to_sql("duckdb")
    # Should cast to VARCHAR for text comparison
    assert "CAST(" in sql and "AS VARCHAR)" in sql
    assert params == ["%error%"]


def test_duckdb_ilike_with_json_path() -> None:
    """Test DuckDB casts JSON to VARCHAR for ILIKE operations."""
    filter = m["config.message"].ilike("%ERROR%")
    sql, params = filter.to_sql("duckdb")
    # Should cast to VARCHAR and use LOWER
    assert "CAST(" in sql and "AS VARCHAR)" in sql
    assert "LOWER" in sql
    assert params == ["%ERROR%"]
