"""Transcripts REST API endpoints."""

from dataclasses import dataclass
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Path, Request
from inspect_ai._view.fastapi_server import AccessPolicy
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_413_CONTENT_TOO_LARGE,
)

from .._project._project import read_project
from .._query import Column, Operator, Query, ScalarValue
from .._query.condition import Condition as ConditionType
from .._query.condition_sql import condition_from_sql
from .._query.order_by import OrderBy
from .._transcript.database.factory import transcripts_view
from .._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
    TranscriptTooLargeError,
)
from ._api_v2_types import (
    DistinctRequest,
    PaginatedRequest,
    TranscriptsRequest,
    TranscriptsResponse,
)
from ._server_common import InspectPydanticJSONResponse, decode_base64url

MAX_TRANSCRIPT_BYTES = 350 * 1024 * 1024  # 350MB


# --- Pagination helpers (from _api_v2_helpers.py) ---


def _ensure_tiebreaker(
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


def _cursor_to_condition(
    cursor: dict[str, Any],
    order_columns: list[OrderBy],
    direction: Literal["forward", "backward"],
) -> ConditionType:
    """Convert cursor to SQL condition for keyset pagination."""

    def get_operator(
        sort_dir: Literal["ASC", "DESC"], pag_dir: Literal["forward", "backward"]
    ) -> Operator:
        want_greater = (pag_dir == "forward" and sort_dir == "ASC") or (
            pag_dir == "backward" and sort_dir == "DESC"
        )
        return Operator.GT if want_greater else Operator.LT

    or_conditions: list[ConditionType] = []

    for i in range(len(order_columns)):
        and_conditions: list[ConditionType] = []

        for j in range(i):
            col_name = order_columns[j].column
            cursor_val = cursor.get(col_name)
            cursor_val = "" if cursor_val is None else cursor_val
            and_conditions.append(
                ConditionType(left=col_name, operator=Operator.EQ, right=cursor_val)
            )

        ob = order_columns[i]
        col_name = ob.column
        sort_dir = ob.direction
        cursor_val = cursor.get(col_name)
        cursor_val = "" if cursor_val is None else cursor_val
        op = get_operator(sort_dir, direction)
        and_conditions.append(
            ConditionType(left=col_name, operator=op, right=cursor_val)
        )

        combined = and_conditions[0]
        for cond in and_conditions[1:]:
            combined = combined & cond
        or_conditions.append(combined)

    result = or_conditions[0]
    for cond in or_conditions[1:]:
        result = result | cond

    return result


def _reverse_order_columns(order_columns: list[OrderBy]) -> list[OrderBy]:
    """Reverse direction of all order columns."""
    return [
        OrderBy(ob.column, "DESC" if ob.direction == "ASC" else "ASC")
        for ob in order_columns
    ]


def _build_transcripts_cursor(
    transcript: TranscriptInfo,
    order_columns: list[OrderBy],
) -> dict[str, Any]:
    """Build cursor from transcript using sort columns."""
    cursor: dict[str, Any] = {}
    for ob in order_columns:
        column = ob.column
        cursor[column] = getattr(transcript, column, None)
    return cursor


@dataclass
class _PaginationContext:
    """Context for paginated queries."""

    filter_conditions: list[ConditionType]
    conditions: list[ConditionType]
    order_columns: list[OrderBy]
    db_order_columns: list[OrderBy]
    limit: int | None
    needs_reverse: bool


def _build_pagination_context(
    body: PaginatedRequest | None,
    tiebreaker_col: str,
    global_filters: list[ConditionType] | None = None,
) -> _PaginationContext:
    """Build pagination context from request body."""
    filter_conditions: list[ConditionType] = (
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
        order_columns = _ensure_tiebreaker(order_by, tiebreaker_col)

        db_order_columns = order_columns
        if pagination.direction == "backward" and not pagination.cursor:
            db_order_columns = _reverse_order_columns(order_columns)
            needs_reverse = True

        if pagination.cursor:
            conditions.append(
                _cursor_to_condition(
                    pagination.cursor, order_columns, pagination.direction
                )
            )

        limit = pagination.limit
    elif body and body.order_by:
        order_bys = (
            body.order_by if isinstance(body.order_by, list) else [body.order_by]
        )
        db_order_columns = [OrderBy(ob.column, ob.direction) for ob in order_bys]

    return _PaginationContext(
        filter_conditions=filter_conditions,
        conditions=conditions,
        order_columns=order_columns,
        db_order_columns=db_order_columns,
        limit=limit,
        needs_reverse=needs_reverse,
    )


# --- Project filters helper (from _transcripts_helpers.py) ---


def _get_project_filters() -> list[ConditionType]:
    project = read_project()
    return [
        condition_from_sql(f)
        for f in (
            project.filter if isinstance(project.filter, list) else [project.filter]
        )
        if f
    ]


# --- Router factory ---


def create_transcripts_router(
    access_policy: AccessPolicy | None = None,
) -> APIRouter:
    """Create transcripts API router.

    Args:
        access_policy: Optional access policy for read/list/delete operations.

    Returns:
        Configured APIRouter with transcripts endpoints.
    """
    router = APIRouter(tags=["transcripts"])

    async def _validate_read(request: Request, file: str) -> None:
        if access_policy is not None:
            if not await access_policy.can_read(request, file):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    @router.post(
        "/transcripts/{dir}",
        summary="List transcripts",
        description="Returns transcripts from specified directory. "
        "Optional filter condition uses SQL-like DSL. Optional order_by for sorting results. "
        "Optional pagination for cursor-based pagination.",
    )
    async def transcripts(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        body: TranscriptsRequest | None = None,
    ) -> TranscriptsResponse:
        """Filter transcript metadata from the transcripts directory."""
        transcripts_dir = decode_base64url(dir)

        try:
            ctx = _build_pagination_context(
                body, "transcript_id", _get_project_filters()
            )

            async with transcripts_view(transcripts_dir) as view:
                count = await view.count(Query(where=ctx.filter_conditions or []))
                results = [
                    t
                    async for t in view.select(
                        Query(
                            where=ctx.conditions or [],
                            limit=ctx.limit,
                            order_by=ctx.db_order_columns or [],
                        )
                    )
                ]

            if ctx.needs_reverse:
                results = list(reversed(results))

            next_cursor = None
            if (
                body
                and body.pagination
                and len(results) == body.pagination.limit
                and results
            ):
                edge = (
                    results[-1]
                    if body.pagination.direction == "forward"
                    else results[0]
                )
                next_cursor = _build_transcripts_cursor(edge, ctx.order_columns)

            return TranscriptsResponse(
                items=results, total_count=count, next_cursor=next_cursor
            )
        except FileNotFoundError:
            return TranscriptsResponse(items=[], total_count=0, next_cursor=None)

    @router.get(
        "/transcripts/{dir}/{id}",
        response_model=Transcript,
        response_class=InspectPydanticJSONResponse,
        summary="Get transcript",
        description="Returns a single transcript with full content (messages and events).",
    )
    async def transcript(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        id: str = Path(description="Transcript ID"),
    ) -> Transcript:
        """Get a single transcript by ID."""
        transcripts_dir = decode_base64url(dir)

        async with transcripts_view(transcripts_dir) as view:
            condition = Column("transcript_id") == id
            infos = [info async for info in view.select(Query(where=[condition]))]
            if not infos:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Transcript not found"
                )

            content = TranscriptContent(messages="all", events="all")
            try:
                return await view.read(
                    infos[0], content, max_bytes=MAX_TRANSCRIPT_BYTES
                )
            except TranscriptTooLargeError as e:
                raise HTTPException(
                    status_code=HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"Transcript too large: {e.size} bytes exceeds {e.max_size} limit",
                ) from None

    @router.post(
        "/transcripts/{dir}/distinct",
        summary="Get distinct column values",
        description="Returns distinct values for a column, optionally filtered.",
    )
    async def transcripts_distinct(
        dir: str = Path(description="Transcripts directory (base64url-encoded)"),
        body: DistinctRequest | None = None,
    ) -> list[ScalarValue]:
        """Get distinct values for a column."""
        transcripts_dir = decode_base64url(dir)
        if body is None:
            return []
        async with transcripts_view(transcripts_dir) as view:
            return await view.distinct(body.column, body.filter)

    return router
