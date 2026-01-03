"""Column filtering DSL for database queries.

This module provides a pythonic DSL for building WHERE clauses
to filter columns in SQLite, DuckDB, and PostgreSQL databases.

Usage:
    from inspect_scout import columns as c

    # Simple conditions
    filter = c.model == "gpt-4"
    filter = c["custom_field"] > 100

    # Combined conditions
    filter = (c.model == "gpt-4") & (c.score > 0.8)
    filter = (c.status == "error") | (c.retries > 3)

    # Generate SQL
    sql, params = filter.to_sql("sqlite")  # or "duckdb" or "postgres"
"""

from __future__ import annotations

from typing import Any

from inspect_scout._query.condition import Condition, Operator

# Rebuild model to resolve forward references for recursive type
Condition.model_rebuild()


class Column:
    """Database column with comparison operators.

    Supports various predicate functions including `like()`, `not_like()`, `between()`, etc.
    Additionally supports standard python equality and comparison operators (e.g. `==`, '>`, etc.
    """

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: Any) -> Condition:  # type: ignore[override]
        """Equal to."""
        return Condition(
            left=self.name,
            operator=Operator.IS_NULL if other is None else Operator.EQ,
            right=None if other is None else other,
        )

    def __ne__(self, other: Any) -> Condition:  # type: ignore[override]
        """Not equal to."""
        return Condition(
            left=self.name,
            operator=Operator.IS_NOT_NULL if other is None else Operator.NE,
            right=None if other is None else other,
        )

    def __lt__(self, other: Any) -> Condition:
        """Less than."""
        return Condition(left=self.name, operator=Operator.LT, right=other)

    def __le__(self, other: Any) -> Condition:
        """Less than or equal to."""
        return Condition(left=self.name, operator=Operator.LE, right=other)

    def __gt__(self, other: Any) -> Condition:
        """Greater than."""
        return Condition(left=self.name, operator=Operator.GT, right=other)

    def __ge__(self, other: Any) -> Condition:
        """Greater than or equal to."""
        return Condition(left=self.name, operator=Operator.GE, right=other)

    def in_(self, values: list[Any]) -> Condition:
        """Check if value is in a list."""
        return Condition(left=self.name, operator=Operator.IN, right=values)

    def not_in(self, values: list[Any]) -> Condition:
        """Check if value is not in a list."""
        return Condition(left=self.name, operator=Operator.NOT_IN, right=values)

    def like(self, pattern: str) -> Condition:
        """SQL LIKE pattern matching (case-sensitive)."""
        return Condition(left=self.name, operator=Operator.LIKE, right=pattern)

    def not_like(self, pattern: str) -> Condition:
        """SQL NOT LIKE pattern matching (case-sensitive)."""
        return Condition(left=self.name, operator=Operator.NOT_LIKE, right=pattern)

    def ilike(self, pattern: str) -> Condition:
        """PostgreSQL ILIKE pattern matching (case-insensitive).

        Note: For SQLite and DuckDB, this will use LIKE with LOWER() for case-insensitivity.
        """
        return Condition(left=self.name, operator=Operator.ILIKE, right=pattern)

    def not_ilike(self, pattern: str) -> Condition:
        """PostgreSQL NOT ILIKE pattern matching (case-insensitive).

        Note: For SQLite and DuckDB, this will use NOT LIKE with LOWER() for case-insensitivity.
        """
        return Condition(left=self.name, operator=Operator.NOT_ILIKE, right=pattern)

    def is_null(self) -> Condition:
        """Check if value is NULL."""
        return Condition(left=self.name, operator=Operator.IS_NULL, right=None)

    def is_not_null(self) -> Condition:
        """Check if value is not NULL."""
        return Condition(left=self.name, operator=Operator.IS_NOT_NULL, right=None)

    def between(self, low: Any, high: Any) -> Condition:
        """Check if value is between two values.

        Args:
            low: Lower bound (inclusive). If None, raises ValueError.
            high: Upper bound (inclusive). If None, raises ValueError.

        Raises:
            ValueError: If either bound is None.
        """
        if low is None or high is None:
            raise ValueError("BETWEEN operator requires non-None bounds")
        return Condition(left=self.name, operator=Operator.BETWEEN, right=(low, high))

    def not_between(self, low: Any, high: Any) -> Condition:
        """Check if value is not between two values.

        Args:
            low: Lower bound (inclusive). If None, raises ValueError.
            high: Upper bound (inclusive). If None, raises ValueError.

        Raises:
            ValueError: If either bound is None.
        """
        if low is None or high is None:
            raise ValueError("NOT BETWEEN operator requires non-None bounds")
        return Condition(
            left=self.name, operator=Operator.NOT_BETWEEN, right=(low, high)
        )
