"""Tests for Condition serialization and Pydantic integration."""

from datetime import date, datetime
from typing import Literal

import pytest
from inspect_scout._transcript.columns import Condition
from inspect_scout._transcript.columns import columns as c
from pydantic import BaseModel


class TestSimpleConditionRoundTrip:
    """Test round-trip serialization of simple conditions."""

    def test_eq_string(self) -> None:
        original = c.model == "gpt-4"
        serialized = original.model_dump()

        # Check native format
        assert serialized["left"] == "model"
        assert serialized["right"] == "gpt-4"
        assert serialized["is_compound"] is False

        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_eq_int(self) -> None:
        original = c.retries == 3
        serialized = original.model_dump()

        assert serialized["right"] == 3
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_eq_float(self) -> None:
        original = c.score == 0.85
        serialized = original.model_dump()

        assert serialized["right"] == 0.85
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_eq_bool(self) -> None:
        original = c.success == True  # noqa: E712
        serialized = original.model_dump()

        assert serialized["right"] is True
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_eq_none_becomes_is_null(self) -> None:
        original = c.error == None  # noqa: E711
        serialized = original.model_dump()

        assert original.operator.name == "IS_NULL"
        assert serialized["right"] is None
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_ne(self) -> None:
        original = c.status != "failed"
        serialized = original.model_dump()

        assert original.operator.name == "NE"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_lt(self) -> None:
        original = c.score < 0.5
        serialized = original.model_dump()

        assert original.operator.name == "LT"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_le(self) -> None:
        original = c.score <= 0.5
        serialized = original.model_dump()

        assert original.operator.name == "LE"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_gt(self) -> None:
        original = c.score > 0.8
        serialized = original.model_dump()

        assert original.operator.name == "GT"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_ge(self) -> None:
        original = c.score >= 0.8
        serialized = original.model_dump()

        assert original.operator.name == "GE"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_in(self) -> None:
        original = c.model.in_(["gpt-4", "gpt-3.5", "claude-3"])
        serialized = original.model_dump()

        assert original.operator.name == "IN"
        assert serialized["right"] == ["gpt-4", "gpt-3.5", "claude-3"]
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_not_in(self) -> None:
        original = c.status.not_in(["error", "timeout"])
        serialized = original.model_dump()

        assert original.operator.name == "NOT_IN"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_like(self) -> None:
        original = c.model.like("gpt-%")
        serialized = original.model_dump()

        assert original.operator.name == "LIKE"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_not_like(self) -> None:
        original = c.model.not_like("test-%")
        serialized = original.model_dump()

        assert original.operator.name == "NOT_LIKE"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_ilike(self) -> None:
        original = c.model.ilike("%GPT%")
        serialized = original.model_dump()

        assert original.operator.name == "ILIKE"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_is_null(self) -> None:
        original = c.error.is_null()
        serialized = original.model_dump()

        assert original.operator.name == "IS_NULL"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_is_not_null(self) -> None:
        original = c.error.is_not_null()
        serialized = original.model_dump()

        assert original.operator.name == "IS_NOT_NULL"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_between(self) -> None:
        original = c.score.between(0.5, 0.9)
        serialized = original.model_dump()

        assert original.operator.name == "BETWEEN"
        assert serialized["right"] == (0.5, 0.9)

        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_not_between(self) -> None:
        original = c.score.not_between(0.0, 0.3)
        serialized = original.model_dump()

        assert original.operator.name == "NOT_BETWEEN"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")


class TestCompoundConditionRoundTrip:
    """Test round-trip serialization of compound conditions."""

    def test_and(self) -> None:
        original = (c.model == "gpt-4") & (c.score > 0.8)
        serialized = original.model_dump()

        assert serialized["is_compound"] is True
        assert original.operator.name == "AND"
        assert serialized["left"]["is_compound"] is False
        assert serialized["right"]["is_compound"] is False

        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_or(self) -> None:
        original = (c.model == "gpt-4") | (c.model == "claude-3")
        serialized = original.model_dump()

        assert serialized["is_compound"] is True
        assert original.operator.name == "OR"

        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_not(self) -> None:
        original = ~(c.status == "error")
        serialized = original.model_dump()

        assert serialized["is_compound"] is True
        assert original.operator.name == "NOT"
        assert serialized["right"] is None

        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_nested_compound(self) -> None:
        original = ((c.model == "gpt-4") & (c.score > 0.8)) | (
            (c.model == "claude-3") & (c.score > 0.9)
        )
        serialized = original.model_dump()

        assert serialized["is_compound"] is True
        assert original.operator.name == "OR"
        assert serialized["left"]["is_compound"] is True
        assert serialized["right"]["is_compound"] is True

        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_deeply_nested(self) -> None:
        original = (
            (c.model == "gpt-4")
            & (c.score > 0.8)
            & (c.success == True)  # noqa: E712
            & (c.error == None)  # noqa: E711
        )
        serialized = original.model_dump()
        restored = Condition.model_validate(serialized)

        assert original.to_sql("sqlite") == restored.to_sql("sqlite")


class TestDateTimeSerialization:
    """Test date/datetime serialization."""

    def test_date_preserved(self) -> None:
        original = c.date > date(2024, 1, 15)
        serialized = original.model_dump()

        # Native Pydantic keeps date objects in model_dump()
        assert serialized["right"] == date(2024, 1, 15)

        restored = Condition.model_validate(serialized)
        sql, params = restored.to_sql("sqlite")
        assert params == [date(2024, 1, 15)]

    def test_datetime_preserved(self) -> None:
        original = c.created_at < datetime(2024, 6, 15, 10, 30, 0)
        serialized = original.model_dump()

        # Native Pydantic keeps datetime objects in model_dump()
        assert serialized["right"] == datetime(2024, 6, 15, 10, 30, 0)

        restored = Condition.model_validate(serialized)
        sql, params = restored.to_sql("sqlite")
        assert params == [datetime(2024, 6, 15, 10, 30, 0)]

    def test_date_in_between(self) -> None:
        original = c.date.between(date(2024, 1, 1), date(2024, 12, 31))
        serialized = original.model_dump()

        # Native Pydantic keeps the tuple with date objects
        assert serialized["right"] == (date(2024, 1, 1), date(2024, 12, 31))

        restored = Condition.model_validate(serialized)
        sql, params = restored.to_sql("sqlite")
        assert params == [date(2024, 1, 1), date(2024, 12, 31)]


class TestJsonPathColumns:
    """Test serialization with JSON path columns."""

    def test_simple_json_path(self) -> None:
        original = c["metadata.key"] == "value"
        serialized = original.model_dump()

        assert serialized["left"] == "metadata.key"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_nested_json_path(self) -> None:
        original = c["agent_args.config.timeout"] > 30
        serialized = original.model_dump()

        assert serialized["left"] == "agent_args.config.timeout"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_array_index_json_path(self) -> None:
        original = c["items[0].name"] == "first"
        serialized = original.model_dump()

        assert serialized["left"] == "items[0].name"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")


class TestEdgeCases:
    """Test edge cases in serialization."""

    def test_empty_in_list(self) -> None:
        original = c.model.in_([])
        serialized = original.model_dump()

        assert serialized["right"] == []
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_in_with_none_values(self) -> None:
        original = c.status.in_(["active", None, "pending"])
        serialized = original.model_dump()

        assert serialized["right"] == ["active", None, "pending"]
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_special_characters_in_column(self) -> None:
        original = c["user.email-address"] == "test@example.com"
        serialized = original.model_dump()

        assert serialized["left"] == "user.email-address"
        restored = Condition.model_validate(serialized)
        assert original.to_sql("sqlite") == restored.to_sql("sqlite")


class TestPydanticIntegration:
    """Test Condition as a field type in Pydantic models."""

    def test_condition_field(self) -> None:
        class QueryConfig(BaseModel):
            filter: Condition

        config = QueryConfig(filter=c.model == "gpt-4")
        json_str = config.model_dump_json()
        config2 = QueryConfig.model_validate_json(json_str)

        assert config.filter.to_sql("sqlite") == config2.filter.to_sql("sqlite")

    def test_optional_condition_field(self) -> None:
        class QueryConfig(BaseModel):
            filter: Condition | None = None

        # With value
        config = QueryConfig(filter=c.score > 0.5)
        json_str = config.model_dump_json()
        config2 = QueryConfig.model_validate_json(json_str)
        assert config.filter is not None
        assert config2.filter is not None
        assert config.filter.to_sql("sqlite") == config2.filter.to_sql("sqlite")

        # Without value
        config_empty = QueryConfig()
        json_str_empty = config_empty.model_dump_json()
        config_empty2 = QueryConfig.model_validate_json(json_str_empty)
        assert config_empty2.filter is None

    def test_list_condition_field(self) -> None:
        class QueryConfig(BaseModel):
            filters: list[Condition] = []

        config = QueryConfig(
            filters=[
                c.model == "gpt-4",
                c.score > 0.8,
                (c.success == True) & (c.error == None),  # noqa: E711, E712
            ]
        )
        json_str = config.model_dump_json()
        config2 = QueryConfig.model_validate_json(json_str)

        assert len(config2.filters) == 3
        for orig, restored in zip(config.filters, config2.filters, strict=True):
            assert orig.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_dict_condition_field(self) -> None:
        class QueryConfig(BaseModel):
            named_filters: dict[str, Condition] = {}

        config = QueryConfig(
            named_filters={
                "high_score": c.score > 0.9,
                "gpt_models": c.model.like("gpt-%"),
            }
        )
        json_str = config.model_dump_json()
        config2 = QueryConfig.model_validate_json(json_str)

        assert len(config2.named_filters) == 2
        for name in config.named_filters:
            orig = config.named_filters[name]
            restored = config2.named_filters[name]
            assert orig.to_sql("sqlite") == restored.to_sql("sqlite")

    def test_model_dump_produces_dict(self) -> None:
        class QueryConfig(BaseModel):
            filter: Condition

        config = QueryConfig(filter=c.model == "gpt-4")
        dumped = config.model_dump()

        assert isinstance(dumped["filter"], dict)
        assert dumped["filter"]["is_compound"] is False

    def test_condition_passthrough(self) -> None:
        """Test that passing a Condition object directly works."""

        class QueryConfig(BaseModel):
            filter: Condition

        condition = c.model == "gpt-4"
        config = QueryConfig(filter=condition)

        assert config.filter is condition


class TestDialectRoundTrip:
    """Test that serialized conditions work across all SQL dialects."""

    @pytest.mark.parametrize("dialect", ["sqlite", "duckdb", "postgres"])
    def test_simple_condition_all_dialects(
        self, dialect: Literal["sqlite", "duckdb", "postgres"]
    ) -> None:
        original = c.model == "gpt-4"
        serialized = original.model_dump()
        restored = Condition.model_validate(serialized)

        assert original.to_sql(dialect) == restored.to_sql(dialect)

    @pytest.mark.parametrize("dialect", ["sqlite", "duckdb", "postgres"])
    def test_compound_condition_all_dialects(
        self, dialect: Literal["sqlite", "duckdb", "postgres"]
    ) -> None:
        original = (c.model == "gpt-4") & (c.score > 0.8)
        serialized = original.model_dump()
        restored = Condition.model_validate(serialized)

        assert original.to_sql(dialect) == restored.to_sql(dialect)

    @pytest.mark.parametrize("dialect", ["sqlite", "duckdb", "postgres"])
    def test_in_condition_all_dialects(
        self, dialect: Literal["sqlite", "duckdb", "postgres"]
    ) -> None:
        original = c.model.in_(["gpt-4", "claude-3"])
        serialized = original.model_dump()
        restored = Condition.model_validate(serialized)

        assert original.to_sql(dialect) == restored.to_sql(dialect)
