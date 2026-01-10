"""Tests for condition_sql module - SQL serialization and parsing."""

from datetime import date, datetime

import pytest
from inspect_scout._query import (
    Column,
    Condition,
    ConditionSQLSyntaxError,
    ConditionSQLUnsupportedError,
    LogicalOperator,
    Operator,
    condition_as_sql,
    condition_from_sql,
)


class TestConditionAsSql:
    """Tests for condition_as_sql() serialization."""

    def test_simple_equality_string(self) -> None:
        c = Column("model") == "gpt-4"
        assert condition_as_sql(c, "filter") == "model = 'gpt-4'"

    def test_simple_equality_int(self) -> None:
        c = Column("count") == 42
        assert condition_as_sql(c, "filter") == "count = 42"

    def test_simple_equality_float(self) -> None:
        c = Column("score") == 0.75
        assert condition_as_sql(c, "filter") == "score = 0.75"

    def test_simple_equality_bool_true(self) -> None:
        c = Column("active") == True  # noqa: E712
        assert condition_as_sql(c, "filter") == "active = TRUE"

    def test_simple_equality_bool_false(self) -> None:
        c = Column("active") == False  # noqa: E712
        assert condition_as_sql(c, "filter") == "active = FALSE"

    def test_not_equal(self) -> None:
        c = Column("model") != "gpt-4"
        assert condition_as_sql(c, "filter") == "model != 'gpt-4'"

    def test_less_than(self) -> None:
        c = Column("score") < 0.5
        assert condition_as_sql(c, "filter") == "score < 0.5"

    def test_less_than_or_equal(self) -> None:
        c = Column("score") <= 0.5
        assert condition_as_sql(c, "filter") == "score <= 0.5"

    def test_greater_than(self) -> None:
        c = Column("score") > 0.5
        assert condition_as_sql(c, "filter") == "score > 0.5"

    def test_greater_than_or_equal(self) -> None:
        c = Column("score") >= 0.5
        assert condition_as_sql(c, "filter") == "score >= 0.5"

    def test_is_null(self) -> None:
        c = Column("model").is_null()
        assert condition_as_sql(c, "filter") == "model IS NULL"

    def test_is_not_null(self) -> None:
        c = Column("model").is_not_null()
        assert condition_as_sql(c, "filter") == "model IS NOT NULL"

    def test_in_list(self) -> None:
        c = Column("model").in_(["gpt-4", "claude-3"])
        assert condition_as_sql(c, "filter") == "model IN ('gpt-4', 'claude-3')"

    def test_not_in_list(self) -> None:
        c = Column("model").not_in(["gpt-4", "claude-3"])
        assert condition_as_sql(c, "filter") == "model NOT IN ('gpt-4', 'claude-3')"

    def test_like(self) -> None:
        c = Column("model").like("%gpt%")
        assert condition_as_sql(c, "filter") == "model LIKE '%gpt%'"

    def test_not_like(self) -> None:
        c = Column("model").not_like("%gpt%")
        assert condition_as_sql(c, "filter") == "model NOT LIKE '%gpt%'"

    def test_ilike(self) -> None:
        c = Column("model").ilike("%GPT%")
        assert condition_as_sql(c, "filter") == "model ILIKE '%GPT%'"

    def test_not_ilike(self) -> None:
        c = Column("model").not_ilike("%GPT%")
        assert condition_as_sql(c, "filter") == "model NOT ILIKE '%GPT%'"

    def test_between(self) -> None:
        c = Column("score").between(0.0, 1.0)
        assert condition_as_sql(c, "filter") == "score BETWEEN 0.0 AND 1.0"

    def test_not_between(self) -> None:
        c = Column("score").not_between(0.0, 1.0)
        assert condition_as_sql(c, "filter") == "score NOT BETWEEN 0.0 AND 1.0"

    def test_and_compound(self) -> None:
        c = (Column("model") == "gpt-4") & (Column("score") > 0.5)
        assert condition_as_sql(c, "filter") == "(model = 'gpt-4' AND score > 0.5)"

    def test_or_compound(self) -> None:
        c = (Column("model") == "gpt-4") | (Column("model") == "claude-3")
        assert (
            condition_as_sql(c, "filter") == "(model = 'gpt-4' OR model = 'claude-3')"
        )

    def test_not_compound(self) -> None:
        c = ~(Column("model") == "gpt-4")
        assert condition_as_sql(c, "filter") == "NOT (model = 'gpt-4')"

    def test_json_path(self) -> None:
        c = Column("config.model.name") == "gpt-4"
        assert condition_as_sql(c, "filter") == "config.model.name = 'gpt-4'"

    def test_json_path_nested(self) -> None:
        c = Column("config.model.params.temperature") > 0.5
        assert condition_as_sql(c, "filter") == "config.model.params.temperature > 0.5"

    def test_string_with_single_quote(self) -> None:
        c = Column("model") == "it's a test"
        assert condition_as_sql(c, "filter") == "model = 'it''s a test'"

    def test_string_with_double_quote(self) -> None:
        c = Column("model") == 'quoted "value"'
        assert condition_as_sql(c, "filter") == "model = 'quoted \"value\"'"

    def test_quoted_identifier(self) -> None:
        c = Column("special-col") == "value"
        assert condition_as_sql(c, "filter") == "\"special-col\" = 'value'"

    def test_date_value(self) -> None:
        c = Column("created") == date(2024, 1, 15)
        assert condition_as_sql(c, "filter") == "created = DATE '2024-01-15'"

    def test_datetime_value(self) -> None:
        c = Column("created") == datetime(2024, 1, 15, 10, 30, 0)
        assert (
            condition_as_sql(c, "filter") == "created = TIMESTAMP '2024-01-15T10:30:00'"
        )

    def test_complex_nested_conditions(self) -> None:
        c = ((Column("a") == 1) & (Column("b") == 2)) | (Column("c") == 3)
        assert condition_as_sql(c, "filter") == "((a = 1 AND b = 2) OR c = 3)"

    def test_null_in_in_list(self) -> None:
        """Test that NULL in IN list is handled with OR IS NULL."""
        c = Column("model").in_(["gpt-4", None, "claude-3"])
        sql = condition_as_sql(c, "filter")
        assert "IN ('gpt-4', 'claude-3')" in sql
        assert "IS NULL" in sql
        assert "OR" in sql

    def test_empty_in_list(self) -> None:
        """Test that empty IN list outputs 1 = 0."""
        c = Column("model").in_([])
        assert condition_as_sql(c, "filter") == "1 = 0"

    def test_empty_not_in_list(self) -> None:
        """Test that empty NOT IN list outputs 1 = 1."""
        c = Column("model").not_in([])
        assert condition_as_sql(c, "filter") == "1 = 1"

    def test_array_index_in_json_path(self) -> None:
        """Test array index notation in JSON paths."""
        c = Column("items[0].name") == "test"
        assert condition_as_sql(c, "filter") == "items[0].name = 'test'"

    def test_multiple_array_indices(self) -> None:
        """Test multiple array indices."""
        c = Column("data[0][1].value") == 42
        assert condition_as_sql(c, "filter") == "data[0][1].value = 42"

    def test_quoted_key_with_dot(self) -> None:
        """Test quoted key containing a dot."""
        from inspect_scout._query import Condition, Operator

        c = Condition(left='config."key.with.dot"', operator=Operator.EQ, right="value")
        assert condition_as_sql(c, "filter") == "config.\"key.with.dot\" = 'value'"


class TestConditionFromSql:
    """Tests for condition_from_sql() parsing."""

    def test_parse_simple_equality_string(self) -> None:
        c = condition_from_sql("model = 'gpt-4'")
        assert c.left == "model"
        assert c.operator == Operator.EQ
        assert c.right == "gpt-4"

    def test_parse_simple_equality_int(self) -> None:
        c = condition_from_sql("count = 42")
        assert c.left == "count"
        assert c.operator == Operator.EQ
        assert c.right == 42

    def test_parse_simple_equality_float(self) -> None:
        c = condition_from_sql("score = 0.75")
        assert c.left == "score"
        assert c.operator == Operator.EQ
        assert c.right == 0.75

    def test_parse_bool_true(self) -> None:
        c = condition_from_sql("active = TRUE")
        assert c.left == "active"
        assert c.operator == Operator.EQ
        assert c.right is True

    def test_parse_bool_false(self) -> None:
        c = condition_from_sql("active = FALSE")
        assert c.left == "active"
        assert c.operator == Operator.EQ
        assert c.right is False

    def test_parse_not_equal(self) -> None:
        c = condition_from_sql("model != 'gpt-4'")
        assert c.operator == Operator.NE

    def test_parse_less_than(self) -> None:
        c = condition_from_sql("score < 0.5")
        assert c.operator == Operator.LT

    def test_parse_less_than_or_equal(self) -> None:
        c = condition_from_sql("score <= 0.5")
        assert c.operator == Operator.LE

    def test_parse_greater_than(self) -> None:
        c = condition_from_sql("score > 0.5")
        assert c.operator == Operator.GT

    def test_parse_greater_than_or_equal(self) -> None:
        c = condition_from_sql("score >= 0.5")
        assert c.operator == Operator.GE

    def test_parse_is_null(self) -> None:
        c = condition_from_sql("model IS NULL")
        assert c.left == "model"
        assert c.operator == Operator.IS_NULL

    def test_parse_is_not_null(self) -> None:
        c = condition_from_sql("model IS NOT NULL")
        assert c.operator == Operator.IS_NOT_NULL

    def test_parse_in_list(self) -> None:
        c = condition_from_sql("model IN ('gpt-4', 'claude-3')")
        assert c.left == "model"
        assert c.operator == Operator.IN
        assert c.right == ["gpt-4", "claude-3"]

    def test_parse_not_in_list(self) -> None:
        c = condition_from_sql("model NOT IN ('gpt-4', 'claude-3')")
        assert c.operator == Operator.NOT_IN

    def test_parse_like(self) -> None:
        c = condition_from_sql("model LIKE '%gpt%'")
        assert c.left == "model"
        assert c.operator == Operator.LIKE
        assert c.right == "%gpt%"

    def test_parse_not_like(self) -> None:
        c = condition_from_sql("model NOT LIKE '%gpt%'")
        assert c.operator == Operator.NOT_LIKE

    def test_parse_ilike(self) -> None:
        c = condition_from_sql("model ILIKE '%GPT%'")
        assert c.operator == Operator.ILIKE

    def test_parse_not_ilike(self) -> None:
        c = condition_from_sql("model NOT ILIKE '%GPT%'")
        assert c.operator == Operator.NOT_ILIKE

    def test_parse_between(self) -> None:
        c = condition_from_sql("score BETWEEN 0.0 AND 1.0")
        assert c.left == "score"
        assert c.operator == Operator.BETWEEN
        assert c.right == (0.0, 1.0)

    def test_parse_and_conjunction(self) -> None:
        c = condition_from_sql("model = 'gpt-4' AND score > 0.5")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.AND

    def test_parse_or_conjunction(self) -> None:
        c = condition_from_sql("model = 'gpt-4' OR model = 'claude-3'")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.OR

    def test_parse_json_path(self) -> None:
        c = condition_from_sql("config.model.name = 'gpt-4'")
        assert c.left == "config.model.name"
        assert c.right == "gpt-4"

    def test_parse_quoted_identifier(self) -> None:
        c = condition_from_sql('"special-col" = 42')
        assert c.left == "special-col"
        assert c.right == 42

    def test_parse_string_with_escaped_quote(self) -> None:
        c = condition_from_sql("model = 'it''s a test'")
        assert c.right == "it's a test"

    def test_parse_parenthesized(self) -> None:
        c = condition_from_sql("(model = 'gpt-4') AND (score > 0.5)")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.AND


class TestRoundtrip:
    """Tests for roundtrip conversion: condition -> SQL -> condition."""

    @pytest.mark.parametrize(
        "condition",
        [
            # Basic equality
            Column("model") == "gpt-4",
            Column("count") == 42,
            Column("active") == True,  # noqa: E712
            Column("active") == False,  # noqa: E712
            # All comparison operators
            Column("model") != "gpt-4",
            Column("score") < 0.5,
            Column("score") <= 0.5,
            Column("score") > 0.5,
            Column("score") >= 0.5,
            # NULL operators
            Column("model").is_null(),
            Column("model").is_not_null(),
            # IN operators
            Column("model").in_(["a", "b", "c"]),
            Column("model").not_in(["a", "b"]),
            # LIKE operators
            Column("model").like("%test%"),
            Column("model").not_like("%test%"),
            Column("model").ilike("%TEST%"),
            Column("model").not_ilike("%TEST%"),
            # BETWEEN operators
            Column("score").between(0.0, 1.0),
            Column("score").not_between(0.0, 1.0),
            # Date/datetime
            Column("created") == date(2024, 1, 15),
            Column("created") == datetime(2024, 1, 15, 10, 30, 0),
        ],
        ids=[
            "equality_string",
            "equality_int",
            "bool_true",
            "bool_false",
            "not_equal",
            "less_than",
            "less_than_or_equal",
            "greater_than",
            "greater_than_or_equal",
            "is_null",
            "is_not_null",
            "in_list",
            "not_in_list",
            "like",
            "not_like",
            "ilike",
            "not_ilike",
            "between",
            "not_between",
            "date_value",
            "datetime_value",
        ],
    )
    def test_simple_roundtrip(self, condition: Condition) -> None:
        """Test that simple conditions survive roundtrip."""
        sql = condition_as_sql(condition, "filter")
        restored = condition_from_sql(sql)
        # Compare by re-serializing (accounts for normalization)
        assert condition_as_sql(restored, "filter") == sql

    def test_and_roundtrip(self) -> None:
        original = (Column("model") == "gpt-4") & (Column("score") > 0.5)
        sql = condition_as_sql(original, "filter")
        restored = condition_from_sql(sql)
        assert condition_as_sql(restored, "filter") == sql

    def test_or_roundtrip(self) -> None:
        original = (Column("model") == "gpt-4") | (Column("model") == "claude-3")
        sql = condition_as_sql(original, "filter")
        restored = condition_from_sql(sql)
        assert condition_as_sql(restored, "filter") == sql

    def test_not_roundtrip(self) -> None:
        """Test NOT operator roundtrip.

        Note: DuckDB optimizes NOT (a = b) to a != b, so we verify
        semantic equivalence rather than structural equivalence.
        """
        original = ~(Column("model") == "gpt-4")
        sql = condition_as_sql(original, "filter")  # "NOT (model = 'gpt-4')"
        restored = condition_from_sql(sql)
        # DuckDB optimizes to model != 'gpt-4' which is semantically equivalent
        assert restored.left == "model"
        assert restored.operator == Operator.NE
        assert restored.right == "gpt-4"

    def test_complex_not_roundtrip(self) -> None:
        """Test complex NOT expression roundtrip."""
        original = ~((Column("a") == 1) & (Column("b") == 2))
        sql = condition_as_sql(original, "filter")
        restored = condition_from_sql(sql)
        assert condition_as_sql(restored, "filter") == sql

    def test_json_path_roundtrip(self) -> None:
        original = Column("config.model.name") == "gpt-4"
        sql = condition_as_sql(original, "filter")
        restored = condition_from_sql(sql)
        assert restored.left == "config.model.name"
        assert restored.right == "gpt-4"

    def test_quoted_identifier_roundtrip(self) -> None:
        """Test quoted identifier roundtrip."""
        original = Column("special-col") == "value"
        sql = condition_as_sql(original, "filter")
        restored = condition_from_sql(sql)
        assert restored.left == "special-col"
        assert restored.right == "value"


class TestErrorHandling:
    """Tests for error handling."""

    def test_syntax_error_incomplete(self) -> None:
        with pytest.raises(ConditionSQLSyntaxError):
            condition_from_sql("model = ")

    def test_syntax_error_invalid(self) -> None:
        with pytest.raises(ConditionSQLSyntaxError):
            condition_from_sql("SELECT * FROM foo")

    def test_unsupported_function(self) -> None:
        with pytest.raises(ConditionSQLUnsupportedError):
            condition_from_sql("UPPER(model) = 'GPT-4'")

    def test_double_quotes_for_string_helpful_error(self) -> None:
        """Test that double quotes for strings gives a helpful error message."""
        with pytest.raises(ConditionSQLSyntaxError) as exc_info:
            condition_from_sql('model = "gpt-4"')
        assert "single quotes" in str(exc_info.value).lower()
        assert "double quotes" in str(exc_info.value).lower()


class TestEdgeCases:
    """Tests for edge cases and SQL variations."""

    def test_negative_integer(self) -> None:
        """Test parsing negative integers."""
        c = condition_from_sql("count > -10")
        assert c.left == "count"
        assert c.operator == Operator.GT
        assert c.right == -10

    def test_negative_float(self) -> None:
        """Test parsing negative floats."""
        c = condition_from_sql("score > -0.5")
        assert c.left == "score"
        assert c.operator == Operator.GT
        assert c.right == -0.5

    def test_not_equal_ansi(self) -> None:
        """Test parsing <> operator (ANSI SQL not equal)."""
        c = condition_from_sql("model <> 'gpt-4'")
        assert c.left == "model"
        assert c.operator == Operator.NE
        assert c.right == "gpt-4"

    def test_empty_string(self) -> None:
        """Test parsing empty string."""
        c = condition_from_sql("model = ''")
        assert c.left == "model"
        assert c.operator == Operator.EQ
        assert c.right == ""

    def test_lowercase_keywords(self) -> None:
        """Test parsing lowercase SQL keywords."""
        c = condition_from_sql("model = 'test' and score > 0.5")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.AND

    def test_mixed_case_keywords(self) -> None:
        """Test parsing mixed case SQL keywords."""
        c = condition_from_sql("model = 'test' And score > 0.5")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.AND

    def test_deeply_nested_parentheses(self) -> None:
        """Test parsing deeply nested parentheses."""
        c = condition_from_sql("(((model = 'gpt-4')))")
        assert c.left == "model"
        assert c.operator == Operator.EQ
        assert c.right == "gpt-4"

    def test_extra_whitespace(self) -> None:
        """Test parsing with extra whitespace."""
        c = condition_from_sql("  model   =   'gpt-4'  ")
        assert c.left == "model"
        assert c.right == "gpt-4"

    def test_in_with_single_value(self) -> None:
        """Test IN with single value."""
        c = condition_from_sql("model IN ('gpt-4')")
        assert c.left == "model"
        assert c.operator == Operator.IN
        assert c.right == ["gpt-4"]

    def test_in_with_integers(self) -> None:
        """Test IN with integer values."""
        c = condition_from_sql("count IN (1, 2, 3)")
        assert c.left == "count"
        assert c.operator == Operator.IN
        assert c.right == [1, 2, 3]

    def test_between_integers(self) -> None:
        """Test BETWEEN with integer values."""
        c = condition_from_sql("count BETWEEN 10 AND 20")
        assert c.left == "count"
        assert c.operator == Operator.BETWEEN
        assert c.right == (10, 20)

    def test_complex_and_or_chain(self) -> None:
        """Test complex AND/OR chain."""
        c = condition_from_sql("(a = 1 AND b = 2) OR (c = 3 AND d = 4)")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.OR

    def test_not_in_values(self) -> None:
        """Test NOT IN parsing."""
        c = condition_from_sql("model NOT IN ('a', 'b', 'c')")
        assert c.left == "model"
        assert c.operator == Operator.NOT_IN
        assert c.right == ["a", "b", "c"]

    def test_not_between_values(self) -> None:
        """Test NOT BETWEEN parsing."""
        c = condition_from_sql("score NOT BETWEEN 0.0 AND 1.0")
        assert c.left == "score"
        assert c.operator == Operator.NOT_BETWEEN
        assert c.right == (0.0, 1.0)

    def test_parse_not_expression_optimized(self) -> None:
        """Test that NOT (a = b) is optimized to a != b by DuckDB."""
        c = condition_from_sql("NOT (model = 'gpt-4')")
        # DuckDB optimizes NOT (a = b) to a != b
        assert c.left == "model"
        assert c.operator == Operator.NE
        assert c.right == "gpt-4"

    def test_parse_not_compound(self) -> None:
        """Test parsing NOT on compound expression (can't be optimized)."""
        c = condition_from_sql("NOT (model = 'gpt-4' AND score > 0.5)")
        assert c.is_compound is True
        assert c.operator == LogicalOperator.NOT

    def test_string_with_special_chars(self) -> None:
        """Test string with various special characters."""
        c = condition_from_sql("model = 'test@123!#$%'")
        assert c.right == "test@123!#$%"

    def test_unicode_string(self) -> None:
        """Test unicode string."""
        c = condition_from_sql("model = 'модель'")
        assert c.right == "модель"

    def test_date_parsing(self) -> None:
        """Test DATE literal parsing."""
        c = condition_from_sql("created = DATE '2024-01-15'")
        assert c.left == "created"
        assert c.operator == Operator.EQ
        assert c.right == date(2024, 1, 15)

    def test_timestamp_parsing(self) -> None:
        """Test TIMESTAMP literal parsing."""
        c = condition_from_sql("created = TIMESTAMP '2024-01-15T10:30:00'")
        assert c.left == "created"
        assert c.operator == Operator.EQ
        assert c.right == datetime(2024, 1, 15, 10, 30, 0)


class TestConditionAsSqlParameterized:
    """Tests for condition_as_sql() with parameterized queries."""

    def test_default_is_parameterized(self) -> None:
        """By default, to_sql returns parameterized SQL."""
        c = Column("count") == 42
        sql, params = condition_as_sql(c)
        assert sql == '"count" = ?'
        assert params == [42]
