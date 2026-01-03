from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from .sql import SQLDialect

# Scalar values that can be used in conditions
ScalarValue = str | int | float | bool | datetime | date | None


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
