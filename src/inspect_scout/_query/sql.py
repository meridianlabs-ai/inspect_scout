from __future__ import annotations

from collections.abc import Collection
from datetime import date, datetime
from typing import Any, Literal

ExecutableSQLDialect = Literal["sqlite", "duckdb", "postgres"]
SQLDialect = ExecutableSQLDialect | Literal["filter"]


class UnknownColumnError(ValueError):
    """A query selected a column that is not present in the active schema."""

    def __init__(self, column: str) -> None:
        self.column = column
        super().__init__(f"Unknown column: {column!r}")


def escape_identifier(identifier: str) -> str:
    """Escape one SQL identifier without adding quotes."""
    if "\x00" in identifier:
        raise ValueError("SQL identifiers cannot contain NUL characters")
    return identifier.replace('"', '""')


def quote_identifier(identifier: str) -> str:
    """Quote one SQL identifier."""
    return f'"{escape_identifier(identifier)}"'


def quote_qualified_identifier(*identifiers: str) -> str:
    """Quote already-separated components of a qualified SQL identifier."""
    return ".".join(quote_identifier(identifier) for identifier in identifiers)


def validate_column(column: str, available_columns: Collection[str]) -> str:
    """Require a caller-selected top-level column to exist in a schema."""
    if column not in available_columns:
        raise UnknownColumnError(column)
    return column


def format_sql_value(value: Any) -> str:
    """Format a Python value as SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        return f"TIMESTAMP '{value.isoformat()}'"
    if isinstance(value, date):
        return f"DATE '{value.isoformat()}'"
    if isinstance(value, str):
        return f"'{value.replace(chr(39), chr(39) + chr(39))}'"
    return str(value)
