"""Convert DuckDB JSON AST to Condition objects.

This module handles the conversion of DuckDB's json_serialize_sql() output
into Condition objects for the query DSL.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .condition import Condition, LogicalOperator, Operator, ScalarValue


def convert_from_select(ast: dict[str, Any]) -> Condition:
    """Convert a SELECT statement AST, extracting the WHERE clause.

    Args:
        ast: The full AST from json_serialize_sql()

    Returns:
        Condition representing the WHERE clause
    """
    # Navigate to WHERE clause
    # AST structure: {"statements": [{"node": {"type": "SELECT_NODE", ...}}]}
    statements = ast.get("statements", [])
    if not statements:
        raise ValueError("No statements in AST")

    stmt = statements[0]
    node = stmt.get("node", {})

    # Find WHERE clause
    where_clause = node.get("where_clause")
    if where_clause is None:
        raise ValueError("No WHERE clause found in AST")

    return _convert_expression(where_clause)


def _convert_expression(node: dict[str, Any]) -> Condition:
    """Convert an expression node to a Condition."""
    node_class = node.get("class", "")
    node_type = node.get("type", "")

    # Handle comparison expressions
    if node_class == "COMPARISON":
        return _convert_comparison(node)

    # Handle conjunctions (AND/OR)
    if node_class == "CONJUNCTION":
        return _convert_conjunction(node)

    # Handle operators (NOT, IS NULL, etc.)
    if node_class == "OPERATOR":
        return _convert_operator(node)

    # Handle function calls (LIKE, ILIKE via ~~ operators)
    if node_class == "FUNCTION":
        return _convert_function(node)

    # Handle BETWEEN expressions
    if node_class == "BETWEEN":
        return _convert_between(node)

    raise ValueError(f"Unsupported expression class: {node_class}, type: {node_type}")


def _convert_comparison(node: dict[str, Any]) -> Condition:
    """Convert a comparison expression."""
    comp_type = node.get("type", "")

    # DuckDB uses left/right for binary comparisons
    left_node = node.get("left")
    right_node = node.get("right")

    # Some nodes use children array instead
    children = node.get("children", [])
    if left_node is None and children:
        left_node = children[0] if len(children) > 0 else None
        right_node = children[1] if len(children) > 1 else None

    if left_node is None:
        raise ValueError("Comparison missing left operand")

    # Extract column name (may be json_extract_string)
    column = _extract_column(left_node)

    # Map comparison type to operator
    operator_map = {
        "COMPARE_EQUAL": Operator.EQ,
        "COMPARE_NOTEQUAL": Operator.NE,
        "COMPARE_LESSTHAN": Operator.LT,
        "COMPARE_LESSTHANOREQUALTO": Operator.LE,
        "COMPARE_GREATERTHAN": Operator.GT,
        "COMPARE_GREATERTHANOREQUALTO": Operator.GE,
        "COMPARE_IN": Operator.IN,
        "COMPARE_NOT_IN": Operator.NOT_IN,
        "COMPARE_BETWEEN": Operator.BETWEEN,
        "COMPARE_NOT_BETWEEN": Operator.NOT_BETWEEN,
    }

    operator = operator_map.get(comp_type)
    if operator is None:
        raise ValueError(f"Unsupported comparison type: {comp_type}")

    # Handle special cases
    if operator in (Operator.IN, Operator.NOT_IN):
        # IN/NOT IN have a list of values
        if right_node is None:
            raise ValueError("IN/NOT IN missing values")
        values = _extract_in_values(right_node)
        return Condition(left=column, operator=operator, right=values)

    if operator in (Operator.BETWEEN, Operator.NOT_BETWEEN):
        # BETWEEN has upper and lower bounds
        upper = node.get("upper")
        lower = node.get("lower")
        if upper is not None and lower is not None:
            low = _extract_value(lower)
            high = _extract_value(upper)
            return Condition(left=column, operator=operator, right=(low, high))
        # Fallback to children if upper/lower not present
        if len(children) >= 3:
            low = _extract_value(children[1])
            high = _extract_value(children[2])
            return Condition(left=column, operator=operator, right=(low, high))
        raise ValueError("BETWEEN requires upper and lower bounds")

    # Standard comparison
    if right_node is None:
        raise ValueError("Comparison missing right operand")
    value = _extract_value(right_node)
    return Condition(left=column, operator=operator, right=value)


def _convert_conjunction(node: dict[str, Any]) -> Condition:
    """Convert AND/OR conjunction."""
    conj_type = node.get("type", "")
    children = node.get("children", [])

    if len(children) < 2:
        raise ValueError(
            f"Conjunction requires at least 2 children, got {len(children)}"
        )

    operator_map = {
        "CONJUNCTION_AND": LogicalOperator.AND,
        "CONJUNCTION_OR": LogicalOperator.OR,
    }

    operator = operator_map.get(conj_type)
    if operator is None:
        raise ValueError(f"Unsupported conjunction type: {conj_type}")

    # Convert children
    left = _convert_expression(children[0])
    right = _convert_expression(children[1])

    # If more than 2 children, chain them
    result = Condition(left=left, operator=operator, right=right, is_compound=True)

    for i in range(2, len(children)):
        child = _convert_expression(children[i])
        result = Condition(
            left=result, operator=operator, right=child, is_compound=True
        )

    return result


def _convert_operator(node: dict[str, Any]) -> Condition:
    """Convert operator expressions (NOT, IS NULL, IN, etc.)."""
    op_type = node.get("type", "")
    children = node.get("children", [])

    if op_type == "OPERATOR_NOT":
        if len(children) < 1:
            raise ValueError("NOT requires at least 1 child")
        # Check if this is NOT wrapping a BETWEEN - convert to NOT_BETWEEN
        child_node = children[0]
        if child_node.get("class") == "BETWEEN":
            # This is NOT BETWEEN - handle as NOT_BETWEEN operator
            input_node = child_node.get("input")
            lower_node = child_node.get("lower")
            upper_node = child_node.get("upper")

            if input_node and lower_node and upper_node:
                column = _extract_column(input_node)
                low = _extract_value(lower_node)
                high = _extract_value(upper_node)
                return Condition(
                    left=column, operator=Operator.NOT_BETWEEN, right=(low, high)
                )
        # Regular NOT expression
        child = _convert_expression(children[0])
        return Condition(
            left=child, operator=LogicalOperator.NOT, right=None, is_compound=True
        )

    if op_type == "OPERATOR_IS_NULL":
        if len(children) < 1:
            raise ValueError("IS NULL requires at least 1 child")
        column = _extract_column(children[0])
        return Condition(left=column, operator=Operator.IS_NULL, right=None)

    if op_type == "OPERATOR_IS_NOT_NULL":
        if len(children) < 1:
            raise ValueError("IS NOT NULL requires at least 1 child")
        column = _extract_column(children[0])
        return Condition(left=column, operator=Operator.IS_NOT_NULL, right=None)

    # DuckDB puts IN/NOT IN under OPERATOR class
    if op_type == "COMPARE_IN":
        if len(children) < 1:
            raise ValueError("IN requires at least 1 child")
        column = _extract_column(children[0])
        values = [_extract_value(c) for c in children[1:]]
        return Condition(left=column, operator=Operator.IN, right=values)

    if op_type == "COMPARE_NOT_IN":
        if len(children) < 1:
            raise ValueError("NOT IN requires at least 1 child")
        column = _extract_column(children[0])
        values = [_extract_value(c) for c in children[1:]]
        return Condition(left=column, operator=Operator.NOT_IN, right=values)

    raise ValueError(f"Unsupported operator type: {op_type}")


def _convert_function(node: dict[str, Any]) -> Condition:
    """Convert function calls (LIKE, ILIKE patterns)."""
    func_name = node.get("function_name", "")
    children = node.get("children", [])

    # DuckDB represents LIKE as ~~ function
    like_map = {
        "~~": Operator.LIKE,
        "!~~": Operator.NOT_LIKE,
        "~~*": Operator.ILIKE,
        "!~~*": Operator.NOT_ILIKE,
    }

    operator = like_map.get(func_name)
    if operator is not None:
        if len(children) < 2:
            raise ValueError(f"LIKE function requires 2 children, got {len(children)}")
        column = _extract_column(children[0])
        pattern = _extract_value(children[1])
        return Condition(left=column, operator=operator, right=pattern)

    # Check for json_extract_string being used as a column
    # This shouldn't happen in WHERE context, but handle it
    from .condition_sql import ConditionSQLUnsupportedError

    raise ConditionSQLUnsupportedError(
        "Unsupported function in filter expression",
        "",
        func_name,
    )


def _convert_between(node: dict[str, Any]) -> Condition:
    """Convert BETWEEN expression."""
    node_type = node.get("type", "")

    # BETWEEN uses input, lower, upper fields
    input_node = node.get("input")
    lower_node = node.get("lower")
    upper_node = node.get("upper")

    if input_node is None or lower_node is None or upper_node is None:
        raise ValueError("BETWEEN requires input, lower, and upper")

    column = _extract_column(input_node)
    low = _extract_value(lower_node)
    high = _extract_value(upper_node)

    # Determine operator based on type
    if node_type == "COMPARE_NOT_BETWEEN":
        operator = Operator.NOT_BETWEEN
    else:
        operator = Operator.BETWEEN

    return Condition(left=column, operator=operator, right=(low, high))


def _extract_column(node: dict[str, Any]) -> str:
    """Extract column name from a node.

    Handles:
    - Simple column references
    - json_extract_string function calls (converts back to dot notation)
    - STRUCT_EXTRACT operators (DuckDB's representation of field access)
    - ARRAY_EXTRACT operators (DuckDB's representation of array indexing)
    """
    node_class = node.get("class", "")
    node_type = node.get("type", "")

    if node_class == "COLUMN_REF":
        # Simple column reference - may have multiple parts (e.g., config.items)
        column_names = node.get("column_names", [])
        if column_names:
            # Join all parts with dots for multi-part column references
            return ".".join(str(name) for name in column_names)
        raise ValueError("COLUMN_REF missing column_names")

    if node_class == "FUNCTION":
        func_name = node.get("function_name", "")
        if func_name == "json_extract_string":
            # Convert back to dot notation
            children = node.get("children", [])
            if len(children) >= 2:
                base = _extract_column(children[0])
                path = _extract_value(children[1])
                if isinstance(path, str) and path.startswith("$."):
                    # Remove $. prefix and join with base
                    json_path = path[2:]  # Remove $.
                    return f"{base}.{json_path}"
            raise ValueError("Invalid json_extract_string arguments")
        else:
            # Unsupported function in column position
            from .condition_sql import ConditionSQLUnsupportedError

            raise ConditionSQLUnsupportedError(
                "Functions in column position are not supported",
                "",
                func_name,
            )

    # Handle STRUCT_EXTRACT (DuckDB's representation of .field access)
    if node_class == "OPERATOR" and node_type == "STRUCT_EXTRACT":
        children = node.get("children", [])
        if len(children) >= 2:
            base = _extract_column(children[0])
            field = _extract_value(children[1])
            if isinstance(field, str):
                return f"{base}.{field}"
        raise ValueError("Invalid STRUCT_EXTRACT structure")

    # Handle ARRAY_EXTRACT (DuckDB's representation of [index] access)
    if node_class == "OPERATOR" and node_type == "ARRAY_EXTRACT":
        children = node.get("children", [])
        if len(children) >= 2:
            base = _extract_column(children[0])
            index = _extract_value(children[1])
            if isinstance(index, int):
                return f"{base}[{index}]"
            elif isinstance(index, str):
                # String index is object key access (e.g., config['items'])
                return f"{base}.{index}"
        raise ValueError("Invalid ARRAY_EXTRACT structure")

    # Handle cast expressions - extract the inner value
    if node_class == "CAST":
        child = node.get("child")
        if child is not None:
            return _extract_column(child)
        children = node.get("children", [])
        if children:
            return _extract_column(children[0])

    raise ValueError(f"Cannot extract column from {node_class}/{node_type}")


def _extract_value(node: dict[str, Any]) -> ScalarValue:
    """Extract a scalar value from a constant node."""
    node_class = node.get("class", "")
    node_type = node.get("type", "")

    if node_class == "CONSTANT":
        value_info = node.get("value", {})
        type_info = value_info.get("type", {})
        value_type = type_info.get("id", "")
        value = value_info.get("value")

        # Handle different value types
        if value_type == "NULL" or value is None or value_info.get("is_null"):
            return None
        if value_type == "BOOLEAN":
            return bool(value)
        if value_type in ("INTEGER", "BIGINT", "SMALLINT", "TINYINT", "HUGEINT"):
            return int(value)
        if value_type in ("FLOAT", "DOUBLE"):
            return float(value)
        if value_type == "DECIMAL":
            # DECIMAL stores value as integer with scale
            # e.g., 0.5 is stored as value=5, scale=1
            type_details = type_info.get("type_info", {})
            scale: int = type_details.get("scale", 0)
            int_val: int = int(value) if value is not None else 0
            if scale > 0:
                result: float = float(int_val) / (10**scale)
                return result
            return float(int_val)
        if value_type == "VARCHAR":
            return str(value)
        if value_type == "DATE":
            if isinstance(value, str):
                return date.fromisoformat(value)
            elif isinstance(value, date):
                return value
            return None
        if value_type in (
            "TIMESTAMP",
            "TIMESTAMP_NS",
            "TIMESTAMP_MS",
            "TIMESTAMP_S",
        ):
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            elif isinstance(value, datetime):
                return value
            return None

        # Default: convert to string or None
        if value is not None:
            return str(value)
        return None

    # Handle cast expressions
    if node_class == "CAST":
        # Check if this is a boolean cast
        cast_type = node.get("cast_type", {}).get("id", "")
        child = node.get("child")
        if child is None:
            # Fallback to children array
            children = node.get("children", [])
            child = children[0] if children else None

        if child is not None:
            if cast_type == "BOOLEAN":
                # Boolean TRUE/FALSE is cast from VARCHAR "t"/"f"
                child_value = _extract_value(child)
                if child_value == "t":
                    return True
                elif child_value == "f":
                    return False
                # Try to interpret as boolean
                if isinstance(child_value, str):
                    return child_value.lower() in ("true", "t", "1", "yes")
                return bool(child_value)
            if cast_type == "DATE":
                # DATE cast from VARCHAR string
                child_value = _extract_value(child)
                if isinstance(child_value, str):
                    return date.fromisoformat(child_value)
                elif isinstance(child_value, date):
                    return child_value
                return None
            if cast_type in (
                "TIMESTAMP",
                "TIMESTAMP_NS",
                "TIMESTAMP_MS",
                "TIMESTAMP_S",
                "TIMESTAMP WITH TIME ZONE",
            ):
                # TIMESTAMP cast from VARCHAR string
                child_value = _extract_value(child)
                if isinstance(child_value, str):
                    return datetime.fromisoformat(child_value)
                elif isinstance(child_value, datetime):
                    return child_value
                return None
            # For other casts, extract the child value
            return _extract_value(child)

    # Provide helpful error for common mistakes
    if node_class == "COLUMN_REF":
        column_names = node.get("column_names", [])
        column_name = column_names[-1] if column_names else "unknown"
        from .condition_sql import ConditionSQLSyntaxError

        raise ConditionSQLSyntaxError(
            "Expected a value but found a column reference. "
            "Did you use double quotes for a string? "
            "Use single quotes for strings: 'value' not \"value\"",
            "",
            f'found column "{column_name}" where a value was expected',
        )

    raise ValueError(f"Cannot extract value from {node_class}/{node_type}")


def _extract_in_values(node: dict[str, Any]) -> list[ScalarValue]:
    """Extract values from an IN list node."""
    # IN lists can be represented different ways
    node_class = node.get("class", "")

    if node_class == "CONSTANT":
        # Single value - wrap in list
        return [_extract_value(node)]

    if node_class == "FUNCTION" and node.get("function_name") == "list_value":
        # List of values
        children = node.get("children", [])
        return [_extract_value(child) for child in children]

    # Try to extract children as values
    children = node.get("children", [])
    if children:
        return [_extract_value(child) for child in children]

    raise ValueError(f"Cannot extract IN values from {node_class}")
