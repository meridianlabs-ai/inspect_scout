import pytest
from inspect_scout._query import Query, UnknownColumnError
from inspect_scout._query.order_by import OrderBy
from inspect_scout._query.sql import quote_identifier


def test_quote_identifier_escapes_embedded_quotes() -> None:
    assert quote_identifier('column"; SELECT 1; --') == ('"column""; SELECT 1; --"')


def test_order_by_requires_connected_schema() -> None:
    query = Query(order_by=[OrderBy("model", "ASC")])

    with pytest.raises(ValueError, match="available_columns"):
        query.to_sql_suffix("duckdb")


def test_order_by_rejects_unknown_column() -> None:
    query = Query(order_by=[OrderBy('model"; SELECT 1; --', "ASC")])

    with pytest.raises(UnknownColumnError):
        query.to_sql_suffix("duckdb", available_columns={"model"})


def test_order_by_quotes_valid_column() -> None:
    query = Query(order_by=[OrderBy('model"name', "DESC")])

    suffix, params, register_shuffle = query.to_sql_suffix(
        "duckdb", available_columns={'model"name'}
    )

    assert suffix == ' ORDER BY "model""name" DESC'
    assert params == []
    assert register_shuffle is None


def test_order_by_rejects_unknown_direction() -> None:
    query = Query(order_by=[OrderBy("model", "ASC")])
    query.order_by[0].direction = "ASC; SELECT 1"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="Unsupported order direction"):
        query.to_sql_suffix("duckdb", available_columns={"model"})
