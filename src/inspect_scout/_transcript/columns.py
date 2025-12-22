"""Column filtering DSL for transcript queries.

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

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

# Scalar values that can be used in conditions
ScalarValue = str | int | float | bool | datetime | date | None


class SQLDialect(Enum):
    """Supported SQL dialects."""

    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    POSTGRES = "postgres"


class Operator(Enum):
    """SQL comparison operators."""

    EQ = "="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    IN = "IN"
    NOT_IN = "NOT IN"
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    ILIKE = "ILIKE"  # PostgreSQL case-insensitive LIKE
    NOT_ILIKE = "NOT ILIKE"  # PostgreSQL case-insensitive NOT LIKE
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    BETWEEN = "BETWEEN"
    NOT_BETWEEN = "NOT BETWEEN"


class LogicalOperator(Enum):
    """Logical operators for combining conditions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class Condition(BaseModel):
    """WHERE clause condition that can be combined with others."""

    left: Union[str, "Condition", None] = Field(default=None)
    """Column name (simple) or left operand (compound)."""

    operator: Union[Operator, LogicalOperator, None] = Field(default=None)
    """Comparison operator (simple) or logical operator (compound)."""

    right: Union[
        "Condition",
        list[ScalarValue],
        tuple[ScalarValue, ScalarValue],
        ScalarValue,
    ] = Field(default=None)
    """Comparison value (simple) or right operand (compound)."""

    is_compound: bool = Field(default=False)
    """True for AND/OR/NOT conditions, False for simple comparisons."""

    @property
    def params(self) -> list[ScalarValue]:
        """SQL parameters extracted from the condition for parameterized queries."""
        if self.is_compound or self.operator in (
            Operator.IS_NULL,
            Operator.IS_NOT_NULL,
        ):
            return []
        if self.operator in (Operator.IN, Operator.NOT_IN):
            return list(self.right) if isinstance(self.right, list) else []
        if self.operator in (Operator.BETWEEN, Operator.NOT_BETWEEN):
            if isinstance(self.right, tuple) and len(self.right) >= 2:
                return [self.right[0], self.right[1]]
            return []
        if self.right is not None and not isinstance(
            self.right, (Condition, list, tuple)
        ):
            return [self.right]
        return []

    def __and__(self, other: Condition) -> Condition:
        """Combine conditions with AND."""
        return Condition(
            left=self,
            operator=LogicalOperator.AND,
            right=other,
            is_compound=True,
        )

    def __or__(self, other: Condition) -> Condition:
        """Combine conditions with OR."""
        return Condition(
            left=self,
            operator=LogicalOperator.OR,
            right=other,
            is_compound=True,
        )

    def __invert__(self) -> Condition:
        """Negate a condition with NOT."""
        return Condition(
            left=self,
            operator=LogicalOperator.NOT,
            right=None,
            is_compound=True,
        )

    def to_sql(
        self,
        dialect: Union[
            SQLDialect, Literal["sqlite", "duckdb", "postgres"]
        ] = SQLDialect.SQLITE,
    ) -> tuple[str, list[Any]]:
        """Generate SQL WHERE clause and parameters.

        Args:
            dialect: Target SQL dialect (sqlite, duckdb, or postgres).

        Returns:
            Tuple of (sql_string, parameters_list).
        """
        if isinstance(dialect, str):
            dialect = SQLDialect(dialect)

        sql, params = self._build_sql(dialect)
        return sql, params

    def _build_sql(
        self, dialect: SQLDialect, param_offset: int = 0
    ) -> tuple[str, list[Any]]:
        """Recursively build SQL string and collect parameters.

        Args:
            dialect: SQL dialect to use.
            param_offset: Starting parameter position for PostgreSQL numbering.

        Returns:
            Tuple of (sql_string, parameters_list).
        """
        if self.is_compound:
            if self.operator == LogicalOperator.NOT:
                assert isinstance(self.left, Condition)
                left_sql, left_params = self.left._build_sql(dialect, param_offset)
                return f"NOT ({left_sql})", left_params
            else:
                assert isinstance(self.left, Condition)
                assert isinstance(self.right, Condition)
                assert self.operator is not None
                left_sql, left_params = self.left._build_sql(dialect, param_offset)
                # Update offset for right side based on left side parameters
                right_offset = param_offset + len(left_params)
                right_sql, right_params = self.right._build_sql(dialect, right_offset)
                return (
                    f"({left_sql} {self.operator.value} {right_sql})",
                    left_params + right_params,
                )
        else:
            # Simple condition
            assert isinstance(self.left, str)
            column = self._format_column(self.left, dialect)

            if (
                dialect == SQLDialect.POSTGRES
                and isinstance(self.left, str)
                and "." in self.left
            ):

                def _pg_cast(col: str, val: Any) -> str:
                    # PostgreSQL's ->> returns text, so we need to cast from text
                    # bool must be checked before int (bool is a subclass of int)
                    if isinstance(val, bool):
                        return f"({col})::text::boolean"
                    if isinstance(val, int) and not isinstance(val, bool):
                        return f"({col})::text::bigint"
                    if isinstance(val, float):
                        return f"({col})::text::double precision"
                    return col

                # Skip casts for operators that don't compare numerically/textually
                skip_ops = {
                    Operator.LIKE,
                    Operator.NOT_LIKE,
                    Operator.ILIKE,
                    Operator.NOT_ILIKE,
                    Operator.IS_NULL,
                    Operator.IS_NOT_NULL,
                }

                if self.operator not in skip_ops:
                    hint = None
                    if self.operator in (Operator.BETWEEN, Operator.NOT_BETWEEN):
                        # use first non-None bound as hint
                        hint = next((x for x in self.params if x is not None), None)
                    elif self.operator in (Operator.IN, Operator.NOT_IN):
                        # use first non-None value as hint for IN/NOT IN
                        hint = next((x for x in self.params if x is not None), None)
                    else:
                        hint = self.params[0] if self.params else None
                    column = _pg_cast(column, hint)

            # Add DuckDB type casting for JSON paths
            if (
                dialect == SQLDialect.DUCKDB
                and isinstance(self.left, str)
                and "." in self.left
            ):

                def _duck_cast(col: str, val: Any) -> str:
                    # DuckDB casting for type-safe comparisons
                    if isinstance(val, bool):
                        return f"({col})::BOOLEAN"
                    if isinstance(val, int) and not isinstance(val, bool):
                        return f"({col})::BIGINT"
                    if isinstance(val, float):
                        return f"({col})::DOUBLE"
                    return col

                # Apply casting for non-text operators
                skip_ops_duck = {
                    Operator.LIKE,
                    Operator.NOT_LIKE,
                    Operator.ILIKE,
                    Operator.NOT_ILIKE,
                    Operator.IS_NULL,
                    Operator.IS_NOT_NULL,
                }

                if self.operator not in skip_ops_duck:
                    hint = None
                    if self.operator in (Operator.BETWEEN, Operator.NOT_BETWEEN):
                        hint = next((x for x in self.params if x is not None), None)
                    elif self.operator in (Operator.IN, Operator.NOT_IN):
                        hint = next((x for x in self.params if x is not None), None)
                    else:
                        hint = self.params[0] if self.params else None
                    column = _duck_cast(column, hint)

            # Ensure DuckDB text operators receive VARCHAR for LIKE operations
            if (
                dialect == SQLDialect.DUCKDB
                and self.operator
                in {
                    Operator.LIKE,
                    Operator.NOT_LIKE,
                    Operator.ILIKE,
                    Operator.NOT_ILIKE,
                }
                and isinstance(self.left, str)
                and "." in self.left  # Only for JSON paths
            ):
                column = f"CAST({column} AS VARCHAR)"

            if self.operator == Operator.IS_NULL:
                return f"{column} IS NULL", []
            elif self.operator == Operator.IS_NOT_NULL:
                return f"{column} IS NOT NULL", []
            elif self.operator == Operator.IN:
                # Handle NULL values in IN list
                vals = [v for v in self.params if v is not None]
                has_null = any(v is None for v in self.params)
                n = len(vals)

                if n == 0 and not has_null:
                    return "1 = 0", []  # empty IN = always false

                sql_parts = []
                if n > 0:
                    placeholders = self._get_placeholders(n, dialect, param_offset)
                    sql_parts.append(f"{column} IN ({placeholders})")
                if has_null:
                    sql_parts.append(f"{column} IS NULL")

                sql = " OR ".join(sql_parts) if sql_parts else "1 = 0"
                if len(sql_parts) > 1:
                    sql = f"({sql})"
                return sql, vals

            elif self.operator == Operator.NOT_IN:
                # Handle NULL values in NOT IN list
                vals = [v for v in self.params if v is not None]
                has_null = any(v is None for v in self.params)
                n = len(vals)

                if n == 0 and not has_null:
                    return "1 = 1", []  # empty NOT IN = always true

                sql_parts = []
                if n > 0:
                    placeholders = self._get_placeholders(n, dialect, param_offset)
                    sql_parts.append(f"{column} NOT IN ({placeholders})")
                if has_null:
                    sql_parts.append(f"{column} IS NOT NULL")

                if not sql_parts:
                    sql = "1 = 1"
                elif len(sql_parts) == 1:
                    sql = sql_parts[0]
                else:
                    sql = f"({sql_parts[0]} AND {sql_parts[1]})"
                return sql, vals
            elif self.operator == Operator.BETWEEN:
                p1 = self._get_placeholder(param_offset, dialect)
                p2 = self._get_placeholder(param_offset + 1, dialect)
                return f"{column} BETWEEN {p1} AND {p2}", self.params
            elif self.operator == Operator.NOT_BETWEEN:
                p1 = self._get_placeholder(param_offset, dialect)
                p2 = self._get_placeholder(param_offset + 1, dialect)
                return f"{column} NOT BETWEEN {p1} AND {p2}", self.params
            elif self.operator == Operator.ILIKE:
                placeholder = self._get_placeholder(param_offset, dialect)
                if dialect == SQLDialect.POSTGRES:
                    return f"{column} ILIKE {placeholder}", self.params
                else:
                    # For SQLite and DuckDB, use LOWER() for case-insensitive comparison
                    return f"LOWER({column}) LIKE LOWER({placeholder})", self.params
            elif self.operator == Operator.NOT_ILIKE:
                placeholder = self._get_placeholder(param_offset, dialect)
                if dialect == SQLDialect.POSTGRES:
                    return f"{column} NOT ILIKE {placeholder}", self.params
                else:
                    # For SQLite and DuckDB, use LOWER() for case-insensitive comparison
                    return f"LOWER({column}) NOT LIKE LOWER({placeholder})", self.params
            else:
                assert self.operator is not None
                placeholder = self._get_placeholder(param_offset, dialect)
                return f"{column} {self.operator.value} {placeholder}", self.params

    def _esc_double(self, s: str) -> str:
        return s.replace('"', '""')

    def _esc_single(self, s: str) -> str:
        return s.replace("'", "''")

    def _needs_sqlite_jsonpath_quotes(self, key: str) -> bool:
        """Check if a key needs quotes in SQLite JSONPath."""
        # Keys need quotes if they contain anything besides alphanumeric and underscore
        return not key.replace("_", "").isalnum()

    def _escape_for_sqlite_jsonpath(self, key: str) -> str:
        """Escape a key for use in SQLite JSONPath."""
        # JSONPath is inside a single-quoted SQL string; the " chars need JSONPath escaping
        return key.replace('"', '\\"')

    def _parse_json_path(self, path: str) -> tuple[str, list[tuple[str, bool]]]:
        """Parse a JSON path supporting array indices and quoted keys.

        Returns:
            Tuple of (base_column, list of (segment, is_array_index))
        """
        if "." not in path and "[" not in path:
            return path, []

        # Identify base: everything before the first unquoted '.' or '['
        i, n, in_quotes = 0, len(path), False
        while i < n:
            ch = path[i]
            if ch == '"':
                in_quotes = not in_quotes
            elif not in_quotes and ch in ".[":
                break
            i += 1

        base = path[:i] if i > 0 else path
        rest = path[i:]
        parts: list[tuple[str, bool]] = []

        j = 0
        while j < len(rest):
            ch = rest[j]
            if ch == ".":
                # dotted key (quoted or unquoted)
                j += 1
                if j < len(rest) and rest[j] == '"':
                    # quoted key
                    j += 1
                    key_chars = []
                    while j < len(rest) and rest[j] != '"':
                        # allow \" sequences
                        if rest[j] == "\\" and j + 1 < len(rest):
                            j += 1
                        key_chars.append(rest[j])
                        j += 1
                    if j < len(rest) and rest[j] == '"':
                        j += 1  # consume closing quote
                    parts.append(("".join(key_chars), False))
                else:
                    # unquoted key
                    k = j
                    while k < len(rest) and rest[k] not in ".[":
                        k += 1
                    key = rest[j:k]
                    if key.isdigit():
                        parts.append((key, True))
                    elif key:
                        parts.append((key, False))
                    j = k
            elif ch == "[":
                # bracket index: [digits]
                k = j + 1
                while k < len(rest) and rest[k] != "]":
                    k += 1
                idx = rest[j + 1 : k]
                if idx.isdigit():
                    parts.append((idx, True))
                j = k + 1 if k < len(rest) else k  # past ']'
            else:
                j += 1

        # Handle base with bracket(s) but no dot, e.g. array[0][2]
        if "[" in base:
            bname = base.split("[", 1)[0]
            btail = base[len(bname) + 1 :]  # everything after first '['
            base = bname if bname else base
            # parse all bracket indices from the base tail
            temp_parts = []
            k = 0
            while k < len(btail):
                if btail[k].isdigit():
                    start = k
                    while k < len(btail) and btail[k].isdigit():
                        k += 1
                    temp_parts.append((btail[start:k], True))
                else:
                    k += 1
            # Insert at beginning to maintain order
            parts = temp_parts + parts

        return base, parts

    def _format_column(self, column_name: str, dialect: SQLDialect) -> str:
        # If dotted, treat as: <base_column>.<json.path.inside.it>
        if "." in column_name or "[" in column_name:
            base, path_parts = self._parse_json_path(column_name)

            if not path_parts:
                # No JSON path, just a column name that might contain a dot
                # in table.column format (not supported in current implementation)
                return f'"{self._esc_double(column_name)}"'

            if dialect == SQLDialect.SQLITE:
                # Build JSONPath like $.key[0]."user.name"
                json_path_parts = []
                for segment, is_index in path_parts:
                    if is_index:
                        json_path_parts.append(f"[{segment}]")
                    elif self._needs_sqlite_jsonpath_quotes(segment):
                        # Keys with special chars need quoting in JSONPath
                        escaped = self._escape_for_sqlite_jsonpath(segment)
                        json_path_parts.append(f'."{escaped}"')
                    else:
                        json_path_parts.append(f".{segment}")
                json_path = "$" + "".join(json_path_parts)
                return f"json_extract(\"{self._esc_double(base)}\", '{self._esc_single(json_path)}')"

            elif dialect == SQLDialect.DUCKDB:
                # Use json_extract_string to extract as VARCHAR for direct comparison
                json_path_parts = []
                for segment, is_index in path_parts:
                    if is_index:
                        json_path_parts.append(f"[{segment}]")
                    elif "." in segment:
                        # Keys with dots need quoting
                        json_path_parts.append(f'."{segment}"')
                    else:
                        json_path_parts.append(f".{segment}")
                json_path = "$" + "".join(json_path_parts)
                return f"json_extract_string(\"{self._esc_double(base)}\", '{self._esc_single(json_path)}')"

            elif dialect == SQLDialect.POSTGRES:
                result = f'"{self._esc_double(base)}"'
                for i, (segment, is_index) in enumerate(path_parts):
                    op = "->>" if i == len(path_parts) - 1 else "->"
                    if is_index:
                        # Array index: use unquoted integer
                        result = f"{result}{op}{segment}"
                    else:
                        # Object key: use quoted string
                        result = f"{result}{op}'{self._esc_single(segment)}'"
                return result

        # Simple (non-JSON) column
        return f'"{self._esc_double(column_name)}"'

    def _get_placeholder(self, position: int, dialect: SQLDialect) -> str:
        """Get parameter placeholder for the dialect.

        Args:
            position: Zero-based position in the parameter array.
            dialect: SQL dialect to use.
        """
        if dialect == SQLDialect.POSTGRES:
            return f"${position + 1}"  # PostgreSQL uses 1-based indexing
        else:  # SQLite and DuckDB use ?
            return "?"

    def _get_placeholders(
        self, count: int, dialect: SQLDialect, offset: int = 0
    ) -> str:
        """Get multiple parameter placeholders for the dialect.

        Args:
            count: Number of placeholders to generate.
            dialect: SQL dialect to use.
            offset: Zero-based starting position in the parameter array.
        """
        if dialect == SQLDialect.POSTGRES:
            # PostgreSQL uses 1-based $1, $2, $3, etc.
            return ", ".join([f"${offset + i + 1}" for i in range(count)])
        else:  # SQLite and DuckDB use ?
            return ", ".join(["?" for _ in range(count)])


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


class Columns:
    """Entry point for building filter expressions.

    ::: {.callout-note}
    Note that the `Columns` class is available only in the development version of Inspect Scout. Install the development version from GitHub with:

    ```python
    pip install git+https://github.com/meridianlabs-ai/inspect_scout
    ```
    :::

    Supports both dot notation and bracket notation for accessing columns:

    ```python
    from inspect_scout import columns as c

    c.column_name
    c["column_name"]
    c["nested.json.path"]
    ```
    """

    @property
    def transcript_id(self) -> Column:
        """Globally unique identifier for transcript."""
        return Column("transcript_id")

    @property
    def source_type(self) -> Column:
        """Type of transcript source (e.g. "eval_log", "weave", etc.)."""
        return Column("source_type")

    @property
    def source_id(self) -> Column:
        """Globally unique identifier of transcript source (e.g. 'eval_id' in Inspect logs)."""
        return Column("source_id")

    @property
    def source_uri(self) -> Column:
        """URI for source data (e.g. full path to the Inspect log file or weave op)."""
        return Column("source_uri")

    @property
    def date(self) -> Column:
        """Date transcript was created."""
        return Column("date")

    @property
    def task_set(self) -> Column:
        """Set from which transcript task was drawn (e.g. benchmark name)."""
        return Column("task_set")

    @property
    def task_id(self) -> Column:
        """Identifier for task (e.g. dataset sample id)."""
        return Column("task_id")

    @property
    def task_repeat(self) -> Column:
        """Repeat for a given task id within a task set (e.g. epoch)."""
        return Column("task_repeat")

    @property
    def agent(self) -> Column:
        """Agent name."""
        return Column("agent")

    @property
    def agent_args(self) -> Column:
        """Agent args."""
        return Column("agent_args")

    @property
    def model(self) -> Column:
        """Model used for eval."""
        return Column("model")

    @property
    def model_options(self) -> Column:
        """Generation options for model."""
        return Column("model_options")

    @property
    def score(self) -> Column:
        """Headline score value."""
        return Column("score")

    @property
    def success(self) -> Column:
        """Reduction of 'score' to True/False sucess."""
        return Column("success")

    @property
    def total_time(self) -> Column:
        """Total execution time."""
        return Column("total_time")

    @property
    def error(self) -> Column:
        """Error that halted exeuction."""
        return Column("error")

    @property
    def limit(self) -> Column:
        """Limit that halted execution."""
        return Column("limit")

    def __getattr__(self, name: str) -> Column:
        """Access columns using dot notation."""
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        return Column(name)

    def __getitem__(self, name: str) -> Column:
        """Access columns using bracket notation."""
        return Column(name)


columns = Columns()
"""Column selector for where expressions.

Typically aliased to a more compact expression (e.g. `c`)
for use in queries). For example:

```python
from inspect_scout import columns as c
filter = c.model == "gpt-4"
filter = (c.task_set == "math") & (c.epochs > 1)
```
"""
