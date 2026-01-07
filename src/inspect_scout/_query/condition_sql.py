"""SQL serialization and parsing for Condition objects.

This module provides bidirectional conversion between Condition objects
and human-readable SQL strings with inlined values.

Features:
- Standard SQL quoting (single quotes for strings, double quotes for identifiers)
- Shorthand JSON path syntax: config.model.name instead of json_extract_string(...)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .condition import Condition, LogicalOperator, Operator


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


def condition_as_sql(condition: Condition) -> str:
    """Generate SQL with values inlined (human-readable).

    Uses shorthand JSON path syntax: config.model.name = 'gpt-4'

    Args:
        condition: The Condition object to serialize.

    Returns:
        SQL string with values inlined.

    Examples:
        >>> from inspect_scout._query import Column
        >>> c = Column("model")
        >>> condition_as_sql(c == "gpt-4")
        "model = 'gpt-4'"
        >>> condition_as_sql(c.in_(["a", "b"]))
        "model IN ('a', 'b')"
    """
    return _build_sql(condition)


def conditions_as_filter(conditions: list[Condition] | None) -> list[str] | None:
    if conditions is not None:
        return [condition_as_sql(c) for c in conditions]
    else:
        return None


def _build_sql(condition: Condition) -> str:
    """Recursively build SQL string from condition."""
    if condition.is_compound:
        if condition.operator == LogicalOperator.NOT:
            assert isinstance(condition.left, Condition)
            left_sql = _build_sql(condition.left)
            return f"NOT ({left_sql})"
        else:
            assert isinstance(condition.left, Condition)
            assert isinstance(condition.right, Condition)
            assert condition.operator is not None
            left_sql = _build_sql(condition.left)
            right_sql = _build_sql(condition.right)
            return f"({left_sql} {condition.operator.value} {right_sql})"
    else:
        # Simple condition
        assert isinstance(condition.left, str)
        column = _format_column(condition.left)

        if condition.operator == Operator.IS_NULL:
            return f"{column} IS NULL"
        elif condition.operator == Operator.IS_NOT_NULL:
            return f"{column} IS NOT NULL"
        elif condition.operator == Operator.IN:
            values = condition.right if isinstance(condition.right, list) else []
            # Handle NULL values specially - NULL in IN doesn't work as expected
            non_null_values = [v for v in values if v is not None]
            has_null = any(v is None for v in values)

            if not non_null_values and not has_null:
                return "1 = 0"  # Empty IN = always false

            sql_parts = []
            if non_null_values:
                formatted = ", ".join(_format_value(v) for v in non_null_values)
                sql_parts.append(f"{column} IN ({formatted})")
            if has_null:
                sql_parts.append(f"{column} IS NULL")

            if len(sql_parts) == 1:
                return sql_parts[0]
            return f"({' OR '.join(sql_parts)})"

        elif condition.operator == Operator.NOT_IN:
            values = condition.right if isinstance(condition.right, list) else []
            # Handle NULL values specially
            non_null_values = [v for v in values if v is not None]
            has_null = any(v is None for v in values)

            if not non_null_values and not has_null:
                return "1 = 1"  # Empty NOT IN = always true

            sql_parts = []
            if non_null_values:
                formatted = ", ".join(_format_value(v) for v in non_null_values)
                sql_parts.append(f"{column} NOT IN ({formatted})")
            if has_null:
                sql_parts.append(f"{column} IS NOT NULL")

            if len(sql_parts) == 1:
                return sql_parts[0]
            return f"({' AND '.join(sql_parts)})"
        elif condition.operator == Operator.BETWEEN:
            if isinstance(condition.right, tuple) and len(condition.right) >= 2:
                low = _format_value(condition.right[0])
                high = _format_value(condition.right[1])
                return f"{column} BETWEEN {low} AND {high}"
            return f"{column} BETWEEN NULL AND NULL"
        elif condition.operator == Operator.NOT_BETWEEN:
            if isinstance(condition.right, tuple) and len(condition.right) >= 2:
                low = _format_value(condition.right[0])
                high = _format_value(condition.right[1])
                return f"{column} NOT BETWEEN {low} AND {high}"
            return f"{column} NOT BETWEEN NULL AND NULL"
        elif condition.operator == Operator.LIKE:
            return f"{column} LIKE {_format_value(condition.right)}"
        elif condition.operator == Operator.NOT_LIKE:
            return f"{column} NOT LIKE {_format_value(condition.right)}"
        elif condition.operator == Operator.ILIKE:
            return f"{column} ILIKE {_format_value(condition.right)}"
        elif condition.operator == Operator.NOT_ILIKE:
            return f"{column} NOT ILIKE {_format_value(condition.right)}"
        else:
            assert condition.operator is not None
            return (
                f"{column} {condition.operator.value} {_format_value(condition.right)}"
            )


def _format_column(column_name: str) -> str:
    """Format column name, using shorthand for JSON paths.

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

    Returns list of (segment, is_array_index) tuples.
    Handles:
    - Simple dotted paths: config.model.name
    - Array indices: items[0].name
    - Quoted keys: config."key.with.dot"
    """
    segments: list[tuple[str, bool]] = []
    i = 0
    n = len(path)

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
            # Skip trailing dot if present
            if i < n and path[i] == ".":
                i += 1

        elif ch == '"':
            # Quoted identifier - handle doubled quotes ("") as escape
            j = i + 1
            key_chars: list[str] = []
            while j < n:
                if path[j] == '"':
                    # Check for doubled quote (escaped)
                    if j + 1 < n and path[j + 1] == '"':
                        key_chars.append('"')  # Add single quote to result
                        j += 2  # Skip both quotes
                    else:
                        break  # End of quoted identifier
                else:
                    key_chars.append(path[j])
                    j += 1
            segments.append(("".join(key_chars), False))
            i = j + 1
            # Skip trailing dot if present
            if i < n and path[i] == ".":
                i += 1

        elif ch == ".":
            # Skip leading/consecutive dots
            i += 1

        else:
            # Unquoted identifier
            j = i
            while j < n and path[j] not in '.[]"':
                j += 1
            if j > i:
                segments.append((path[i:j], False))
            i = j
            # Skip trailing dot if present
            if i < n and path[i] == ".":
                i += 1

    return segments


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


def _escape_identifier(identifier: str) -> str:
    """Escape an identifier for use in double quotes."""
    return identifier.replace('"', '""')


def _format_value(value: Any) -> str:
    """Format a Python value as SQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(value, datetime):
        return f"TIMESTAMP '{value.isoformat()}'"
    if isinstance(value, date):
        return f"DATE '{value.isoformat()}'"
    # Fallback for other types
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


# Placeholder for condition_from_sql - will be implemented next
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
    """Parse an identifier chain into its parts."""
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
