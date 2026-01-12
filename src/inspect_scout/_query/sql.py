from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

ExecutableSQLDialect = Literal["sqlite", "duckdb", "postgres"]
SQLDialect = ExecutableSQLDialect | Literal["filter"]


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
