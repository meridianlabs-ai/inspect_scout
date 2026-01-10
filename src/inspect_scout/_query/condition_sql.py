"""SQL serialization and parsing for Condition objects.

This module provides bidirectional conversion between Condition objects
and human-readable SQL strings with inlined values.

Features:
- Standard SQL quoting (single quotes for strings, double quotes for identifiers)
- Shorthand JSON path syntax: config.model.name instead of json_extract_string(...)
"""

from __future__ import annotations

from typing import Any, Literal, overload

from .condition import Condition, LogicalOperator, Operator
from .sql import ExecutableSQLDialect, SQLDialect, format_sql_value

# Operators that should skip type casting (they work on text or don't need values)
_SKIP_CAST_OPS = frozenset(
    {
        Operator.LIKE,
        Operator.NOT_LIKE,
        Operator.ILIKE,
        Operator.NOT_ILIKE,
        Operator.IS_NULL,
        Operator.IS_NOT_NULL,
    }
)


def _get_cast_hint(condition: Condition) -> Any:
    """Get a type hint value for casting from a condition's params."""
    if condition.operator in (Operator.BETWEEN, Operator.NOT_BETWEEN):
        return next((x for x in condition.params if x is not None), None)
    elif condition.operator in (Operator.IN, Operator.NOT_IN):
        return next((x for x in condition.params if x is not None), None)
    else:
        return condition.params[0] if condition.params else None


def _apply_json_type_cast(col: str, val: Any, dialect: ExecutableSQLDialect) -> str:
    """Apply type casting for JSON path columns based on value type and dialect."""
    if dialect == "postgres":
        if isinstance(val, bool):
            return f"({col})::text::boolean"
        if isinstance(val, int) and not isinstance(val, bool):
            return f"({col})::text::bigint"
        if isinstance(val, float):
            return f"({col})::text::double precision"
    elif dialect == "duckdb":
        if isinstance(val, bool):
            return f"({col})::BOOLEAN"
        if isinstance(val, int) and not isinstance(val, bool):
            return f"({col})::BIGINT"
        if isinstance(val, float):
            return f"({col})::DOUBLE"
    return col


def _partition_in_values(values: list[Any]) -> tuple[list[Any], bool]:
    """Partition IN/NOT IN values into non-null values and has_null flag."""
    non_null = [v for v in values if v is not None]
    has_null = any(v is None for v in values)
    return non_null, has_null


class ConditionSQLError(ValueError):
    """Base exception for condition SQL errors."""

    pass


class ConditionSQLSyntaxError(ConditionSQLError):
    """Invalid SQL syntax."""

    def __init__(self, message: str, sql: str, detail: str | None = None):
        self.sql = sql
        self.detail = detail
        full_message = f"{message}: {sql}"
        if detail:
            full_message += f" ({detail})"
        super().__init__(full_message)


class ConditionSQLUnsupportedError(ConditionSQLError):
    """Valid SQL but uses unsupported construct."""

    def __init__(self, message: str, sql: str, construct: str):
        self.sql = sql
        self.construct = construct
        super().__init__(f"{message}: {construct}")


def _condition_as_filter_sql(condition: Condition) -> str:
    """Generate a SQL-like DSL string for human editing and round-tripping.

    This produces a simplified, human-readable format that is NOT directly
    executable by any specific database. It uses shorthand syntax (e.g., dot-notation
    for JSON paths like `config.model.name`, literal `ILIKE` regardless of
    database support) designed to be parsed back via `condition_from_sql()`.

    For executable, dialect-specific SQL, use `condition_as_sql()` instead.

    WARNING: Values are inlined directly into the output string, bypassing parameterized
    query protection. Intended for display purposes where the user is supplying
    their own values.

    Args:
        condition: The Condition object to serialize.

    Returns:
        SQL-like DSL string (not executable SQL).

    Examples:
        >>> from inspect_scout._query import Column
        >>> c = Column("model")
        >>> condition_as_sql(c == "gpt-4", "filter")
        "model = 'gpt-4'"
        >>> condition_as_sql(c.in_(["a", "b"]), "filter")
        "model IN ('a', 'b')"
    """
    return _build_filter_sql(condition)


def conditions_as_filter(conditions: list[Condition] | None) -> list[str] | None:
    if conditions is not None:
        return [_condition_as_filter_sql(c) for c in conditions]
    else:
        return None


# ---------------------------------------------------------------------------
# condition_as_sql: dialect-specific SQL generation with parameterized queries
# ---------------------------------------------------------------------------


@overload
def condition_as_sql(
    condition: Condition,
    dialect: Literal["filter"],
) -> str: ...


@overload
def condition_as_sql(
    condition: Condition,
    dialect: Literal["sqlite", "duckdb", "postgres"] = ...,
) -> tuple[str, list[Any]]: ...


def condition_as_sql(
    condition: Condition,
    dialect: SQLDialect = "sqlite",
) -> str | tuple[str, list[Any]]:
    """Generate SQL WHERE clause and parameters.

    Args:
        condition: The Condition object to serialize.
        dialect: Target SQL dialect. Use "filter" for human-readable DSL string
            with inlined values (for display/editing). Use "sqlite", "duckdb", or
            "postgres" for executable SQL with parameterized queries.

    Returns:
        If dialect="filter": SQL-like DSL string with values inlined.
        Otherwise: Tuple of (sql_string, parameters_list).
    """
    if dialect == "filter":
        return _condition_as_filter_sql(condition)
    sql, params = _build_parameterized_sql(condition, dialect)
    return (sql, params)


def _build_parameterized_sql(
    condition: Condition,
    dialect: Literal["sqlite", "duckdb", "postgres"],
    param_offset: int = 0,
) -> tuple[str, list[Any]]:
    """Build dialect-specific SQL with parameter placeholders.

    Args:
        condition: The Condition object to serialize.
        dialect: SQL dialect to use.
        param_offset: Starting parameter position for PostgreSQL numbering.

    Returns:
        Tuple of (sql_string, parameters_list).
    """
    if condition.is_compound:
        if condition.operator == LogicalOperator.NOT:
            assert isinstance(condition.left, Condition)
            left_sql, left_params = _build_parameterized_sql(
                condition.left,
                dialect,
                param_offset,
            )
            return f"NOT ({left_sql})", left_params
        else:
            assert isinstance(condition.left, Condition)
            assert isinstance(condition.right, Condition)
            assert condition.operator is not None
            left_sql, left_params = _build_parameterized_sql(
                condition.left,
                dialect,
                param_offset,
            )
            # Update offset for right side based on left side parameters
            right_offset = param_offset + len(left_params)
            right_sql, right_params = _build_parameterized_sql(
                condition.right,
                dialect,
                right_offset,
            )
            return (
                f"({left_sql} {condition.operator.value} {right_sql})",
                left_params + right_params,
            )
    else:
        # Simple condition
        assert isinstance(condition.left, str)
        column = _format_column_for_dialect(condition.left, dialect)
        is_json_path = "." in condition.left

        # Apply type casting for JSON paths (postgres/duckdb only)
        if is_json_path and dialect in ("postgres", "duckdb"):
            if condition.operator not in _SKIP_CAST_OPS:
                hint = _get_cast_hint(condition)
                column = _apply_json_type_cast(column, hint, dialect)

        # DuckDB LIKE operators need VARCHAR cast for JSON paths
        if (
            dialect == "duckdb"
            and is_json_path
            and condition.operator
            in {Operator.LIKE, Operator.NOT_LIKE, Operator.ILIKE, Operator.NOT_ILIKE}
        ):
            column = f"CAST({column} AS VARCHAR)"

        if condition.operator == Operator.IS_NULL:
            return f"{column} IS NULL", []
        elif condition.operator == Operator.IS_NOT_NULL:
            return f"{column} IS NOT NULL", []
        elif condition.operator == Operator.IN:
            vals, has_null = _partition_in_values(list(condition.params))
            if not vals and not has_null:
                return "1 = 0", []  # empty IN = always false
            sql_parts = []
            if vals:
                placeholders = _get_placeholders(len(vals), dialect, param_offset)
                sql_parts.append(f"{column} IN ({placeholders})")
            if has_null:
                sql_parts.append(f"{column} IS NULL")
            sql = " OR ".join(sql_parts)
            if len(sql_parts) > 1:
                sql = f"({sql})"
            return sql, vals

        elif condition.operator == Operator.NOT_IN:
            vals, has_null = _partition_in_values(list(condition.params))
            if not vals and not has_null:
                return "1 = 1", []  # empty NOT IN = always true
            sql_parts = []
            if vals:
                placeholders = _get_placeholders(len(vals), dialect, param_offset)
                sql_parts.append(f"{column} NOT IN ({placeholders})")
            if has_null:
                sql_parts.append(f"{column} IS NOT NULL")
            sql = " AND ".join(sql_parts) if len(sql_parts) > 1 else sql_parts[0]
            if len(sql_parts) > 1:
                sql = f"({sql})"
            return sql, vals
        elif condition.operator == Operator.BETWEEN:
            p1 = _get_placeholder(param_offset, dialect)
            p2 = _get_placeholder(param_offset + 1, dialect)
            return f"{column} BETWEEN {p1} AND {p2}", list(condition.params)
        elif condition.operator == Operator.NOT_BETWEEN:
            p1 = _get_placeholder(param_offset, dialect)
            p2 = _get_placeholder(param_offset + 1, dialect)
            return f"{column} NOT BETWEEN {p1} AND {p2}", list(condition.params)
        elif condition.operator == Operator.ILIKE:
            placeholder = _get_placeholder(param_offset, dialect)
            if dialect == "postgres":
                return f"{column} ILIKE {placeholder}", list(condition.params)
            # For SQLite and DuckDB, use LOWER() for case-insensitive comparison
            return f"LOWER({column}) LIKE LOWER({placeholder})", list(condition.params)
        elif condition.operator == Operator.NOT_ILIKE:
            placeholder = _get_placeholder(param_offset, dialect)
            if dialect == "postgres":
                return f"{column} NOT ILIKE {placeholder}", list(condition.params)
            # For SQLite and DuckDB, use LOWER() for case-insensitive comparison
            return f"LOWER({column}) NOT LIKE LOWER({placeholder})", list(
                condition.params
            )
        else:
            assert condition.operator is not None
            placeholder = _get_placeholder(param_offset, dialect)
            return f"{column} {condition.operator.value} {placeholder}", list(
                condition.params
            )


def _escape_identifier(s: str) -> str:
    """Escape an identifier for use in double quotes."""
    return s.replace('"', '""')


def _escape_single_quotes(s: str) -> str:
    """Escape single quotes for SQL string literals by doubling them."""
    return s.replace("'", "''")


def _escape_for_sqlite_jsonpath(key: str) -> str:
    """Escape a key for use in SQLite JSONPath."""
    # JSONPath is inside a single-quoted SQL string; the " chars need JSONPath escaping
    return key.replace('"', '\\"')


def _parse_json_path(path: str) -> tuple[str, list[tuple[str, bool]]]:
    """Parse a JSON path into base column and segments.

    Uses SQL standard doubled-quote escaping ("") for quoted identifiers.

    Args:
        path: JSON path like "config.model.name" or "items[0].value"

    Returns:
        Tuple of (base_column, list of (segment, is_array_index))
    """
    if "." not in path and "[" not in path:
        return path, []

    segments: list[tuple[str, bool]] = []
    i = 0
    n = len(path)
    base: str | None = None

    while i < n:
        ch = path[i]

        if ch == "[":
            # Array index
            j = i + 1
            while j < n and path[j] != "]":
                j += 1
            index = path[i + 1 : j]
            segments.append((index, True))
            i = j + 1
            if i < n and path[i] == ".":
                i += 1

        elif ch == '"':
            # Quoted identifier - handle doubled quotes ("") as escape
            j = i + 1
            key_chars: list[str] = []
            while j < n:
                if path[j] == '"':
                    if j + 1 < n and path[j + 1] == '"':
                        key_chars.append('"')
                        j += 2
                    else:
                        break
                else:
                    key_chars.append(path[j])
                    j += 1
            segment = "".join(key_chars)
            if base is None:
                base = segment
            else:
                segments.append((segment, False))
            i = j + 1
            if i < n and path[i] == ".":
                i += 1

        elif ch == ".":
            i += 1

        else:
            # Unquoted identifier
            j = i
            while j < n and path[j] not in '.[]"':
                j += 1
            if j > i:
                segment = path[i:j]
                if base is None:
                    base = segment
                else:
                    segments.append((segment, False))
            i = j
            if i < n and path[i] == ".":
                i += 1

    return base or path, segments


def _format_column_for_dialect(column_name: str, dialect: SQLDialect) -> str:
    """Format a column reference for the target SQL dialect.

    Handles JSON path syntax (config.model.name) per dialect:
    - sqlite: json_extract("col", '$.path')
    - duckdb: json_extract_string("col", '$.path')
    - postgres: "col"->'path'->>'leaf'
    """
    # If dotted, treat as: <base_column>.<json.path.inside.it>
    if "." in column_name or "[" in column_name:
        base, path_parts = _parse_json_path(column_name)

        if not path_parts:
            # No JSON path, just a column name that might contain a dot
            # in table.column format (not supported in current implementation)
            return f'"{_escape_identifier(column_name)}"'

        if dialect == "sqlite":
            # Build JSONPath like $.key[0]."user.name"
            json_path_parts = []
            for segment, is_index in path_parts:
                if is_index:
                    json_path_parts.append(f"[{segment}]")
                elif not segment.replace("_", "").isalnum():
                    # Keys with special chars need quoting in JSONPath
                    escaped = _escape_for_sqlite_jsonpath(segment)
                    json_path_parts.append(f'."{escaped}"')
                else:
                    json_path_parts.append(f".{segment}")
            json_path = "$" + "".join(json_path_parts)
            return f"json_extract(\"{_escape_identifier(base)}\", '{_escape_single_quotes(json_path)}')"

        elif dialect == "duckdb":
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
            return f"json_extract_string(\"{_escape_identifier(base)}\", '{_escape_single_quotes(json_path)}')"

        elif dialect == "postgres":
            result = f'"{_escape_identifier(base)}"'
            for i, (segment, is_index) in enumerate(path_parts):
                op = "->>" if i == len(path_parts) - 1 else "->"
                if is_index:
                    # Array index: use unquoted integer
                    result = f"{result}{op}{segment}"
                else:
                    # Object key: use quoted string
                    result = f"{result}{op}'{_escape_single_quotes(segment)}'"
            return result

    # Simple (non-JSON) column
    return f'"{_escape_identifier(column_name)}"'


def _get_placeholder(position: int, dialect: SQLDialect) -> str:
    """Get parameter placeholder for the dialect.

    Args:
        position: Zero-based position in the parameter array.
        dialect: SQL dialect to use.
    """
    if dialect == "postgres":
        return f"${position + 1}"  # PostgreSQL uses 1-based indexing
    else:  # SQLite and DuckDB use ?
        return "?"


def _get_placeholders(count: int, dialect: SQLDialect, offset: int = 0) -> str:
    """Get multiple parameter placeholders for the dialect.

    Args:
        count: Number of placeholders to generate.
        dialect: SQL dialect to use.
        offset: Zero-based starting position in the parameter array.
    """
    if dialect == "postgres":
        # PostgreSQL uses 1-based $1, $2, $3, etc.
        return ", ".join([f"${offset + i + 1}" for i in range(count)])
    else:  # SQLite and DuckDB use ?
        return ", ".join(["?" for _ in range(count)])


def _build_filter_sql(condition: Condition) -> str:
    """Build SQL for the filter DSL (human-readable, values inlined)."""
    if condition.is_compound:
        if condition.operator == LogicalOperator.NOT:
            assert isinstance(condition.left, Condition)
            left_sql = _build_filter_sql(condition.left)
            return f"NOT ({left_sql})"
        else:
            assert isinstance(condition.left, Condition)
            assert isinstance(condition.right, Condition)
            assert condition.operator is not None
            left_sql = _build_filter_sql(condition.left)
            right_sql = _build_filter_sql(condition.right)
            return f"({left_sql} {condition.operator.value} {right_sql})"
    else:
        # Simple condition
        assert isinstance(condition.left, str)
        column = _format_filter_column(condition.left)

        if condition.operator == Operator.IS_NULL:
            return f"{column} IS NULL"
        elif condition.operator == Operator.IS_NOT_NULL:
            return f"{column} IS NOT NULL"
        elif condition.operator == Operator.IN:
            values = condition.right if isinstance(condition.right, list) else []
            non_null_values, has_null = _partition_in_values(values)
            if not non_null_values and not has_null:
                return "1 = 0"  # Empty IN = always false
            sql_parts = []
            if non_null_values:
                formatted = ", ".join(format_sql_value(v) for v in non_null_values)
                sql_parts.append(f"{column} IN ({formatted})")
            if has_null:
                sql_parts.append(f"{column} IS NULL")
            sql = " OR ".join(sql_parts)
            return f"({sql})" if len(sql_parts) > 1 else sql

        elif condition.operator == Operator.NOT_IN:
            values = condition.right if isinstance(condition.right, list) else []
            non_null_values, has_null = _partition_in_values(values)
            if not non_null_values and not has_null:
                return "1 = 1"  # Empty NOT IN = always true
            sql_parts = []
            if non_null_values:
                formatted = ", ".join(format_sql_value(v) for v in non_null_values)
                sql_parts.append(f"{column} NOT IN ({formatted})")
            if has_null:
                sql_parts.append(f"{column} IS NOT NULL")
            sql = " AND ".join(sql_parts)
            return f"({sql})" if len(sql_parts) > 1 else sql
        elif condition.operator == Operator.BETWEEN:
            if isinstance(condition.right, tuple) and len(condition.right) >= 2:
                low = format_sql_value(condition.right[0])
                high = format_sql_value(condition.right[1])
                return f"{column} BETWEEN {low} AND {high}"
            return f"{column} BETWEEN NULL AND NULL"
        elif condition.operator == Operator.NOT_BETWEEN:
            if isinstance(condition.right, tuple) and len(condition.right) >= 2:
                low = format_sql_value(condition.right[0])
                high = format_sql_value(condition.right[1])
                return f"{column} NOT BETWEEN {low} AND {high}"
            return f"{column} NOT BETWEEN NULL AND NULL"
        elif condition.operator == Operator.LIKE:
            return f"{column} LIKE {format_sql_value(condition.right)}"
        elif condition.operator == Operator.NOT_LIKE:
            return f"{column} NOT LIKE {format_sql_value(condition.right)}"
        elif condition.operator == Operator.ILIKE:
            return f"{column} ILIKE {format_sql_value(condition.right)}"
        elif condition.operator == Operator.NOT_ILIKE:
            return f"{column} NOT ILIKE {format_sql_value(condition.right)}"
        else:
            assert condition.operator is not None
            return f"{column} {condition.operator.value} {format_sql_value(condition.right)}"


def _format_filter_column(column_name: str) -> str:
    """Format a column for the filter DSL (human-readable, not executable).

    Simple columns are output unquoted if they don't need quoting.
    JSON paths use dot notation: config.model.name
    Array indices use bracket notation: items[0].name
    """
    # Check if column needs quoting (has special characters)
    if "." not in column_name and "[" not in column_name:
        # Simple column - quote only if needed
        if _needs_quoting(column_name):
            return f'"{_escape_identifier(column_name)}"'
        return column_name

    # JSON path - parse and format each segment
    segments = _parse_json_path_segments(column_name)
    result_parts: list[str] = []

    for segment, is_array_index in segments:
        if is_array_index:
            # Array index - use bracket notation
            result_parts.append(f"[{segment}]")
        else:
            # Object key - use dot notation (with quoting if needed)
            if _needs_quoting(segment):
                result_parts.append(f'"{_escape_identifier(segment)}"')
            else:
                result_parts.append(segment)

    # Join with dots, but not before array indices
    result = ""
    for i, part in enumerate(result_parts):
        if i == 0:
            result = part
        elif part.startswith("["):
            result += part  # No dot before array index
        else:
            result += "." + part
    return result


def _parse_json_path_segments(path: str) -> list[tuple[str, bool]]:
    """Parse a JSON path into segments with type information.

    Returns list of (segment, is_array_index) tuples including the base.
    Delegates to _parse_json_path for actual parsing.
    """
    base, segments = _parse_json_path(path)
    # Include base as first segment (not an array index)
    return [(base, False)] + segments


def _needs_quoting(identifier: str) -> bool:
    """Check if an identifier needs quoting."""
    if not identifier:
        return True
    # Identifiers need quoting if they:
    # - Start with a digit
    # - Contain non-alphanumeric characters (except underscore)
    # - Are SQL reserved words (simplified check)
    if identifier[0].isdigit():
        return True
    if not all(c.isalnum() or c == "_" for c in identifier):
        return True
    # Check for common SQL reserved words
    reserved = {
        "select",
        "from",
        "where",
        "and",
        "or",
        "not",
        "in",
        "like",
        "between",
        "is",
        "null",
        "true",
        "false",
        "order",
        "by",
        "limit",
        "offset",
        "group",
        "having",
        "join",
        "left",
        "right",
        "inner",
        "outer",
        "on",
        "as",
        "case",
        "when",
        "then",
        "else",
        "end",
    }
    if identifier.lower() in reserved:
        return True
    return False


def condition_from_sql(sql: str) -> Condition:
    """Parse SQL expression into Condition.

    Args:
        sql: SQL expression (without WHERE keyword)

    Returns:
        Condition object representing the parsed expression.

    Raises:
        ConditionSQLSyntaxError: Invalid SQL syntax
        ConditionSQLUnsupportedError: Valid SQL but unsupported construct

    Examples:
        >>> c = condition_from_sql("model = 'gpt-4'")
        >>> c.left
        'model'
        >>> c.right
        'gpt-4'
    """
    # Import here to avoid circular imports
    from ._ast_converter import convert_from_select

    # Pre-process: convert JSON path shorthand to json_extract_string
    processed_sql = _preprocess_json_paths(sql)

    # Parse using DuckDB
    import duckdb

    try:
        # Wrap in SELECT statement to parse as expression
        full_sql = f"SELECT * FROM __t WHERE {processed_sql}"
        result = duckdb.execute(
            f"SELECT json_serialize_sql('{_escape_sql_string(full_sql)}')"
        ).fetchone()
        if result is None:
            raise ConditionSQLSyntaxError("Failed to parse SQL", sql)

        import json

        ast = json.loads(result[0])

        # Check for parse errors
        if ast.get("error"):
            raise ConditionSQLSyntaxError(
                "SQL syntax error",
                sql,
                ast.get("error_message", "Unknown error"),
            )

        # Extract WHERE clause from AST
        return convert_from_select(ast)

    except duckdb.Error as e:
        raise ConditionSQLSyntaxError("DuckDB parse error", sql, str(e)) from e


def _escape_sql_string(s: str) -> str:
    """Escape a string for use inside SQL single quotes."""
    return s.replace("'", "''")


def _preprocess_json_paths(sql: str) -> str:
    """Convert JSON path shorthand to json_extract_string function calls.

    Transforms: config.model.name = 'gpt-4'
    Into: json_extract_string("config", '$.model.name') = 'gpt-4'

    Handles:
    - Simple paths: col.path.field
    - Quoted identifiers: "col".path or col."path.with.dot"
    - Skips function calls: func.name() is not converted
    """
    # This regex matches identifier chains that look like JSON paths
    # Pattern: identifier(.identifier)+ not followed by (
    # We need to be careful not to match:
    # - Function calls: func()
    # - Things inside strings
    # - Already-converted json_extract_string calls

    result = []
    i = 0
    n = len(sql)

    while i < n:
        # Skip string literals
        if sql[i] == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2  # Escaped quote
                    else:
                        j += 1
                        break
                else:
                    j += 1
            result.append(sql[i:j])
            i = j
            continue

        # Skip already-converted json_extract_string calls
        if sql[i:].lower().startswith("json_extract_string"):
            # Find the closing parenthesis
            j = i + len("json_extract_string")
            if j < n and sql[j] == "(":
                paren_depth = 1
                j += 1
                while j < n and paren_depth > 0:
                    if sql[j] == "(":
                        paren_depth += 1
                    elif sql[j] == ")":
                        paren_depth -= 1
                    elif sql[j] == "'":
                        # Skip string inside function
                        j += 1
                        while j < n:
                            if sql[j] == "'":
                                if j + 1 < n and sql[j + 1] == "'":
                                    j += 2
                                else:
                                    break
                            else:
                                j += 1
                    j += 1
                result.append(sql[i:j])
                i = j
                continue

        # Try to match an identifier (possibly quoted)
        match = _match_identifier_chain(sql, i)
        if match:
            ident_chain, end_pos = match
            # Check if followed by ( - if so, it's a function call
            next_non_space = end_pos
            while next_non_space < n and sql[next_non_space] in " \t":
                next_non_space += 1
            if next_non_space < n and sql[next_non_space] == "(":
                # Function call - don't convert
                result.append(sql[i:end_pos])
                i = end_pos
            elif "." in ident_chain or "[" in ident_chain:
                # JSON path - convert to json_extract_string
                parts = _parse_identifier_chain(ident_chain)
                if len(parts) > 1:
                    base = parts[0]
                    path = "$." + ".".join(parts[1:])
                    # Quote base if needed
                    if _needs_quoting(base.strip('"')):
                        base_quoted = f'"{_escape_identifier(base.strip(chr(34)))}"'
                    else:
                        base_quoted = f'"{base}"'
                    result.append(f"json_extract_string({base_quoted}, '{path}')")
                    i = end_pos
                else:
                    result.append(sql[i:end_pos])
                    i = end_pos
            else:
                result.append(sql[i:end_pos])
                i = end_pos
        else:
            result.append(sql[i])
            i += 1

    return "".join(result)


def _match_identifier_chain(sql: str, start: int) -> tuple[str, int] | None:
    """Match an identifier chain starting at position start.

    Returns (matched_string, end_position) or None if no match.
    """
    n = len(sql)
    i = start

    # Must start with identifier character or quote
    if i >= n:
        return None
    if not (sql[i].isalpha() or sql[i] == "_" or sql[i] == '"'):
        return None

    parts = []

    while i < n:
        # Match one identifier (quoted or unquoted)
        if sql[i] == '"':
            # Quoted identifier - handle doubled quotes ("") as escape
            j = i + 1
            while j < n:
                if sql[j] == '"':
                    # Check for doubled quote (escaped)
                    if j + 1 < n and sql[j + 1] == '"':
                        j += 2  # Skip both quotes
                    else:
                        break  # End of quoted identifier
                else:
                    j += 1
            if j < n:
                j += 1  # Include closing quote
            parts.append(sql[i:j])
            i = j
        elif sql[i].isalpha() or sql[i] == "_":
            # Unquoted identifier
            j = i
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            parts.append(sql[i:j])
            i = j
        else:
            break

        # Check for dot continuation
        if i < n and sql[i] == ".":
            parts.append(".")
            i += 1
            # Must be followed by identifier
            if i >= n or not (sql[i].isalpha() or sql[i] == "_" or sql[i] == '"'):
                # Trailing dot - include it but stop
                break
        else:
            break

    if not parts:
        return None

    matched = "".join(parts)
    return (matched, start + len(matched))


def _parse_identifier_chain(chain: str) -> list[str]:
    """Split a dotted identifier chain like 'config.model.name' into parts."""
    parts: list[str] = []
    i = 0
    n = len(chain)

    while i < n:
        if chain[i] == ".":
            i += 1
            continue
        elif chain[i] == '"':
            # Quoted identifier
            j = i + 1
            while j < n and chain[j] != '"':
                j += 1
            parts.append(chain[i + 1 : j])  # Without quotes
            i = j + 1 if j < n else j
        elif chain[i].isalpha() or chain[i] == "_":
            j = i
            while j < n and (chain[j].isalnum() or chain[j] == "_"):
                j += 1
            parts.append(chain[i:j])
            i = j
        else:
            i += 1

    return parts
