from __future__ import annotations

from enum import Enum


class SQLDialect(Enum):
    """Supported SQL dialects."""

    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    POSTGRES = "postgres"
