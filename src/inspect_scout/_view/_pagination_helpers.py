"""Shared pagination helpers for V2 API routers."""

from dataclasses import dataclass
from functools import reduce
from typing import Any, Literal

from .._query import Operator
from .._query.condition import Condition
from .._query.order_by import OrderBy
from ._api_v2_types import PaginatedRequest


def ensure_tiebreaker(
    order_by: OrderBy | list[OrderBy] | None,
    tiebreaker_col: str,
) -> list[OrderBy]:
    """Ensure sort order has tiebreaker column as final element."""
    if order_by is None:
        return [OrderBy(tiebreaker_col, "ASC")]

    order_bys = order_by if isinstance(order_by, list) else [order_by]
    columns = [OrderBy(ob.column, ob.direction) for ob in order_bys]

    if any(ob.column == tiebreaker_col for ob in columns):
        return columns

    return columns + [OrderBy(tiebreaker_col, "ASC")]


def cursor_to_condition(
    cursor: dict[str, Any],
    order_columns: list[OrderBy],
    direction: Literal["forward", "backward"],
) -> Condition:
    """Convert cursor to SQL condition for keyset pagination."""

    def get_operator(
        sort_dir: Literal["ASC", "DESC"], pag_dir: Literal["forward", "backward"]
    ) -> Operator:
        want_greater = (pag_dir == "forward" and sort_dir == "ASC") or (
            pag_dir == "backward" and sort_dir == "DESC"
        )
        return Operator.GT if want_greater else Operator.LT

    def build_and_condition(prefix_count: int, ob: OrderBy) -> Condition:
        """Build AND condition: equality on prefix columns plus comparison on current."""
        eq_conditions = [
            Condition(
                left=order_columns[j].column,
                operator=Operator.EQ,
                right=cursor.get(order_columns[j].column),
            )
            for j in range(prefix_count)
        ]
        cmp_condition = Condition(
            left=ob.column,
            operator=get_operator(ob.direction, direction),
            right=cursor.get(ob.column),
        )
        all_conditions = eq_conditions + [cmp_condition]
        return reduce(lambda a, b: a & b, all_conditions)

    or_conditions = [
        build_and_condition(i, order_columns[i]) for i in range(len(order_columns))
    ]
    return reduce(lambda a, b: a | b, or_conditions)


def reverse_order_columns(order_columns: list[OrderBy]) -> list[OrderBy]:
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
    global_filters: list[Condition] | None = None,
) -> PaginationContext:
    """Build pagination context from request body."""
    filter_conditions: list[Condition] = (
        global_filters.copy() if global_filters else []
    )
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
