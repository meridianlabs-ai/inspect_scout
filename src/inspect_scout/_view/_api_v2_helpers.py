from dataclasses import dataclass
from typing import Any, Literal

from .._query import Operator
from .._query.condition import Condition
from .._query.order_by import OrderBy
from .._recorder.recorder import Status
from .._transcript.types import TranscriptInfo
from ._api_v2_types import PaginatedRequest


def ensure_tiebreaker(
    order_by: OrderBy | list[OrderBy] | None,
    tiebreaker_col: str,
) -> list[OrderBy]:
    """Ensure sort order has tiebreaker column as final element.

    Returns list of (column, direction) tuples with directions in uppercase.
    If order_by is None, returns [(tiebreaker_col, "ASC")].
    If tiebreaker_col already in sort, don't add duplicate.
    """
    if order_by is None:
        return [OrderBy(tiebreaker_col, "ASC")]

    order_bys = order_by if isinstance(order_by, list) else [order_by]
    # Already uppercase from Pydantic model
    columns = [OrderBy(ob.column, ob.direction) for ob in order_bys]

    if any(ob.column == tiebreaker_col for ob in columns):
        return columns

    return columns + [OrderBy(tiebreaker_col, "ASC")]


def cursor_to_condition(
    cursor: dict[str, Any],
    order_columns: list[OrderBy],
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
            col_name = order_columns[j].column
            cursor_val = cursor.get(col_name)
            # Match Python behavior: None -> ""
            cursor_val = "" if cursor_val is None else cursor_val
            and_conditions.append(
                Condition(left=col_name, operator=Operator.EQ, right=cursor_val)
            )

        # Comparison condition for current column
        ob = order_columns[i]
        col_name = ob.column
        sort_dir = ob.direction
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


def build_transcripts_cursor(
    transcript: TranscriptInfo,
    order_columns: list[OrderBy],
) -> dict[str, Any]:
    """Build cursor from transcript using sort columns."""
    cursor: dict[str, Any] = {}
    for ob in order_columns:
        column = ob.column
        cursor[column] = getattr(transcript, column, None)
    return cursor


def reverse_order_columns(
    order_columns: list[OrderBy],
) -> list[OrderBy]:
    """Reverse direction of all order columns."""
    return [
        OrderBy(ob.column, "DESC" if ob.direction == "ASC" else "ASC")
        for ob in order_columns
    ]


@dataclass
class PaginationContext:
    """Context for paginated queries."""

    filter_conditions: list[Condition]
    conditions: list[Condition]
    order_columns: list[OrderBy]
    db_order_columns: list[OrderBy]
    limit: int | None
    needs_reverse: bool


def build_pagination_context(
    body: PaginatedRequest | None,
    tiebreaker_col: str,
) -> PaginationContext:
    """Build pagination context from request body."""
    filter_conditions: list[Condition] = []
    if body and body.filter:
        filter_conditions.append(body.filter)

    conditions = filter_conditions.copy()
    use_pagination = body is not None and body.pagination is not None
    db_order_columns: list[OrderBy] = []
    order_columns: list[OrderBy] = []
    limit: int | None = None
    needs_reverse = False

    if use_pagination:
        assert body is not None and body.pagination is not None
        pagination = body.pagination

        order_by = body.order_by or OrderBy(column=tiebreaker_col, direction="ASC")
        order_columns = ensure_tiebreaker(order_by, tiebreaker_col)

        db_order_columns = order_columns
        if pagination.direction == "backward" and not pagination.cursor:
            db_order_columns = reverse_order_columns(order_columns)
            needs_reverse = True

        if pagination.cursor:
            conditions.append(
                cursor_to_condition(
                    pagination.cursor, order_columns, pagination.direction
                )
            )

        limit = pagination.limit
    elif body and body.order_by:
        order_bys = (
            body.order_by if isinstance(body.order_by, list) else [body.order_by]
        )
        db_order_columns = [OrderBy(ob.column, ob.direction) for ob in order_bys]

    return PaginationContext(
        filter_conditions=filter_conditions,
        conditions=conditions,
        order_columns=order_columns,
        db_order_columns=db_order_columns,
        limit=limit,
        needs_reverse=needs_reverse,
    )


def build_scans_cursor(
    status: Status,
    order_columns: list[OrderBy],
) -> dict[str, Any]:
    """Build cursor from Status using sort columns.

    Maps column names to values from Status object:
    - scan_id, scan_name, timestamp -> status.spec.*
    - complete, location -> status.*
    - scanners, model -> derived from spec
    """
    cursor: dict[str, Any] = {}
    for ob in order_columns:
        column = ob.column
        if column == "scan_id":
            cursor[column] = status.spec.scan_id
        elif column == "scan_name":
            cursor[column] = status.spec.scan_name
        elif column == "timestamp":
            cursor[column] = (
                status.spec.timestamp.isoformat() if status.spec.timestamp else None
            )
        elif column == "complete":
            cursor[column] = status.complete
        elif column == "location":
            cursor[column] = status.location
        elif column == "scanners":
            cursor[column] = (
                ",".join(status.spec.scanners.keys()) if status.spec.scanners else ""
            )
        elif column == "model":
            model = status.spec.model
            cursor[column] = (
                getattr(model, "model", None) or str(model) if model else None
            )
        else:
            cursor[column] = None
    return cursor
