from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Callable

from .condition import Condition
from .order_by import OrderBy
from .sql import SQLDialect


@dataclass
class Query:
    """Selection criteria for transcripts."""

    where: list[Condition] = field(default_factory=list)
    """Where clauses for query."""

    limit: int | None = None
    """Limit on total results form query."""

    shuffle: bool | int = False
    """Shuffle results randomly (use with limit to take random draws).

    Shuffle is implemented as ORDER BY shuffle_hash(col), ensuring it happens
    before limit—critical for random sampling (otherwise limit would select
    the same N rows, then shuffle them). Cannot be combined with order_by.
    """

    order_by: list[OrderBy] = field(default_factory=list)
    """Column names and directions for ordering (ASC/DESC)."""

    def to_sql_suffix(
        self,
        dialect: SQLDialect,
        shuffle_column: str | None = None,
    ) -> tuple[str, list[Any], Callable[[Any], None] | None]:
        """Generate SQL suffix (WHERE + ORDER BY + LIMIT).

        Args:
            dialect: SQL dialect for placeholders.
            shuffle_column: Column for shuffle ORDER BY (required if self.shuffle is set).

        Returns:
            (sql_suffix, params, register_shuffle)
            - sql_suffix: SQL string with WHERE/ORDER BY/LIMIT clauses
            - params: Parameter values for placeholders
            - register_shuffle: If shuffle is set, function(conn) that registers the
              shuffle_hash UDF. Caller must invoke before executing. None if no shuffle.
        """
        parts: list[str] = []
        params: list[Any] = []

        # WHERE clause
        if self.where:
            condition = (
                self.where[0]
                if len(self.where) == 1
                else reduce(lambda a, b: a & b, self.where)
            )
            where_sql, where_params = condition.to_sql(dialect)
            parts.append(f" WHERE {where_sql}")
            params.extend(where_params)

        # ORDER BY clause
        order_by_clauses: list[str] = []
        register_shuffle: Callable[[Any], None] | None = None

        if self.shuffle:
            assert shuffle_column is not None, (
                "shuffle_column required when shuffle is set"
            )
            assert not self.order_by, (
                "order_by is not meaningful when shuffle is enabled"
            )
            seed = 0 if self.shuffle is True else self.shuffle
            order_by_clauses.append(f"shuffle_hash({shuffle_column})")
            register_shuffle = _make_shuffle_registrar(dialect, seed)
        else:
            for ob in self.order_by:
                order_by_clauses.append(f'"{ob.column}" {ob.direction}')

        if order_by_clauses:
            parts.append(" ORDER BY " + ", ".join(order_by_clauses))

        # LIMIT clause
        if self.limit is not None:
            placeholder = (
                "$" + str(len(params) + 1) if dialect == SQLDialect.POSTGRES else "?"
            )
            parts.append(f" LIMIT {placeholder}")
            params.append(self.limit)

        return "".join(parts), params, register_shuffle


def _make_shuffle_registrar(dialect: SQLDialect, seed: int) -> Callable[[Any], None]:
    """Create a function that registers the shuffle_hash UDF on a connection.

    Args:
        dialect: SQL dialect (determines registration API).
        seed: Random seed for deterministic shuffling.

    Returns:
        Function that takes a connection and registers the UDF.
    """

    def shuffle_hash(value: str) -> str:
        """Compute deterministic hash for shuffling."""
        content = f"{value}:{seed}"
        return hashlib.sha256(content.encode()).hexdigest()

    def register(conn: Any) -> None:
        if dialect == SQLDialect.SQLITE:
            conn.create_function("shuffle_hash", 1, shuffle_hash)
        elif dialect == SQLDialect.DUCKDB:
            # Remove existing function first (DuckDB doesn't support replace)
            try:
                conn.remove_function("shuffle_hash")
            except Exception:
                pass  # Function may not exist
            conn.create_function("shuffle_hash", shuffle_hash)
        else:
            raise ValueError(f"Shuffle not supported for dialect: {dialect}")

    return register
