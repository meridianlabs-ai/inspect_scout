from typing import Any, Literal

from .._recorder.recorder import Status
from .._transcript.columns import Condition, Operator
from .._transcript.types import TranscriptInfo
from ._api_v2_types import OrderBy


def ensure_tiebreaker(
    order_by: OrderBy | list[OrderBy] | None,
) -> list[tuple[str, Literal["ASC", "DESC"]]]:
    """Ensure sort order has transcript_id as final tiebreaker.

    Returns list of (column, direction) tuples with directions in uppercase.
    If order_by is None, returns [("transcript_id", "ASC")].
    If transcript_id already in sort, don't add duplicate.
    """
    if order_by is None:
        return [("transcript_id", "ASC")]

    order_bys = order_by if isinstance(order_by, list) else [order_by]
    # Already uppercase from Pydantic model
    columns = [(ob.column, ob.direction) for ob in order_bys]

    if any(col == "transcript_id" for col, _ in columns):
        return columns

    return columns + [("transcript_id", "ASC")]


def cursor_to_condition(
    cursor: dict[str, Any],
    order_columns: list[tuple[str, Literal["ASC", "DESC"]]],
    direction: Literal["forward", "backward"],
) -> Condition:
    """Convert cursor to SQL condition for keyset pagination.

    For lexicographic ordering with columns (c1, c2, c3), generates:
    forward+ASC:  (c1 > v1) OR (c1 = v1 AND c2 > v2) OR (c1 = v1 AND c2 = v2 AND c3 > v3)
    forward+DESC: (c1 < v1) OR (c1 = v1 AND c2 < v2) OR ...
    backward flips the comparison operators.
    """

    def get_operator(
        sort_dir: Literal["ASC", "DESC"], pag_dir: Literal["forward", "backward"]
    ) -> Operator:
        want_greater = (pag_dir == "forward" and sort_dir == "ASC") or (
            pag_dir == "backward" and sort_dir == "DESC"
        )
        return Operator.GT if want_greater else Operator.LT

    # Build OR'd conditions for lexicographic comparison
    or_conditions: list[Condition] = []

    for i in range(len(order_columns)):
        and_conditions: list[Condition] = []

        # Equality conditions for all preceding columns
        for j in range(i):
            col_name, _ = order_columns[j]
            cursor_val = cursor.get(col_name)
            # Match Python behavior: None -> ""
            cursor_val = "" if cursor_val is None else cursor_val
            and_conditions.append(
                Condition(left=col_name, operator=Operator.EQ, right=cursor_val)
            )

        # Comparison condition for current column
        col_name, sort_dir = order_columns[i]
        cursor_val = cursor.get(col_name)
        cursor_val = "" if cursor_val is None else cursor_val
        op = get_operator(sort_dir, direction)
        and_conditions.append(Condition(left=col_name, operator=op, right=cursor_val))

        # Combine with AND
        combined = and_conditions[0]
        for cond in and_conditions[1:]:
            combined = combined & cond
        or_conditions.append(combined)

    # Combine all with OR
    result = or_conditions[0]
    for cond in or_conditions[1:]:
        result = result | cond

    return result


def build_cursor(
    transcript: TranscriptInfo,
    order_columns: list[tuple[str, Literal["ASC", "DESC"]]],
) -> dict[str, Any]:
    """Build cursor from transcript using sort columns."""
    cursor: dict[str, Any] = {}
    for column, _ in order_columns:
        cursor[column] = getattr(transcript, column, None)
    return cursor


def reverse_order_columns(
    order_columns: list[tuple[str, Literal["ASC", "DESC"]]],
) -> list[tuple[str, Literal["ASC", "DESC"]]]:
    """Reverse direction of all order columns."""
    return [
        (col, "DESC" if direction == "ASC" else "ASC")
        for col, direction in order_columns
    ]


def ensure_scan_tiebreaker(
    order_by: OrderBy | list[OrderBy] | None,
) -> list[tuple[str, Literal["ASC", "DESC"]]]:
    """Ensure sort order has scan_id as final tiebreaker.

    Returns list of (column, direction) tuples with directions in uppercase.
    If order_by is None, returns [("scan_id", "ASC")].
    If scan_id already in sort, don't add duplicate.
    """
    if order_by is None:
        return [("scan_id", "ASC")]

    order_bys = order_by if isinstance(order_by, list) else [order_by]
    columns = [(ob.column, ob.direction) for ob in order_bys]

    if any(col == "scan_id" for col, _ in columns):
        return columns

    return columns + [("scan_id", "ASC")]


def build_scan_cursor(
    status: Status,
    order_columns: list[tuple[str, Literal["ASC", "DESC"]]],
) -> dict[str, Any]:
    """Build cursor from Status using sort columns.

    Maps column names to values from Status object:
    - scan_id, scan_name, timestamp -> status.spec.*
    - complete, location -> status.*
    - scanners, model -> derived from spec
    """
    cursor: dict[str, Any] = {}
    for column, _ in order_columns:
        if column == "scan_id":
            cursor[column] = status.spec.scan_id
        elif column == "scan_name":
            cursor[column] = status.spec.scan_name
        elif column == "timestamp":
            cursor[column] = status.spec.timestamp.isoformat() if status.spec.timestamp else None
        elif column == "complete":
            cursor[column] = status.complete
        elif column == "location":
            cursor[column] = status.location
        elif column == "scanners":
            cursor[column] = ",".join(status.spec.scanners.keys()) if status.spec.scanners else ""
        elif column == "model":
            model = status.spec.model
            cursor[column] = getattr(model, "model", None) or str(model) if model else None
        else:
            cursor[column] = None
    return cursor
