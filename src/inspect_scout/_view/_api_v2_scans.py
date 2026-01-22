"""Scans REST API endpoints."""

import asyncio
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable, Literal, TypeVar

import pyarrow.ipc as pa_ipc
from duckdb import InvalidInputException
from fastapi import APIRouter, HTTPException, Path, Request, Response
from fastapi.responses import StreamingResponse
from inspect_ai._util.file import FileSystem
from inspect_ai._view.fastapi_server import AccessPolicy
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from .._query import Operator, Query
from .._query.condition import Condition as ConditionType
from .._query.order_by import OrderBy
from .._recorder.active_scans_store import ActiveScanInfo, active_scans_store
from .._recorder.factory import scan_recorder_for_location
from .._recorder.recorder import Status as RecorderStatus
from .._scanjob_config import ScanJobConfig
from .._scanjobs.factory import scan_jobs_view
from .._scanresults import scan_results_arrow_async, scan_results_df_async
from ._api_v2_types import (
    ActiveScansResponse,
    PaginatedRequest,
    ScansRequest,
    ScansResponse,
    ScanStatus,
    ScanStatusWithActiveInfo,
)
from ._server_common import InspectPydanticJSONResponse, decode_base64url

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()


# --- Pagination helpers ---


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


def _build_scans_cursor(
    status: RecorderStatus,
    order_columns: list[OrderBy],
) -> dict[str, Any]:
    """Build cursor from Status using sort columns."""
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
) -> _PaginationContext:
    """Build pagination context from request body."""
    filter_conditions: list[ConditionType] = []
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


# --- Subprocess helpers (from _run_scan_helpers.py) ---


def _tee_pipe(
    pipe: io.BufferedReader, dest: io.TextIOWrapper, accumulator: list[bytes]
) -> None:
    """Read from pipe, write to dest, and accumulate."""
    for line in pipe:
        dest.buffer.write(line)
        dest.buffer.flush()
        accumulator.append(line)
    pipe.close()


def _spawn_scan_subprocess(
    config: ScanJobConfig,
) -> tuple[subprocess.Popen[bytes], str, list[bytes], list[bytes]]:
    """Spawn a subprocess to run the scan."""
    fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="scout_scan_config_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(config.model_dump_json(exclude_none=True))
    except Exception:
        os.close(fd)
        os.unlink(temp_path)
        raise

    proc = subprocess.Popen(
        ["scout", "scan", temp_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    stdout_lines: list[bytes] = []
    stderr_lines: list[bytes] = []

    assert proc.stdout is not None
    assert proc.stderr is not None

    threading.Thread(
        target=_tee_pipe, args=(proc.stdout, sys.stdout, stdout_lines), daemon=True
    ).start()
    threading.Thread(
        target=_tee_pipe, args=(proc.stderr, sys.stderr, stderr_lines), daemon=True
    ).start()

    return proc, temp_path, stdout_lines, stderr_lines


async def _wait_for_active_scan(
    pid: int,
    timeout_seconds: float = 10.0,
    poll_interval: float = 0.5,
) -> ActiveScanInfo | None:
    """Wait for an active scan to appear for the given PID."""
    start = time.time()

    while time.time() - start < timeout_seconds:
        with active_scans_store() as store:
            info = store.read_by_pid(pid)
            if info is not None:
                return info
        await asyncio.sleep(poll_interval)

    return None


# --- Router factory ---


T = TypeVar("T")


def create_scans_router(
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
) -> APIRouter:
    """Create scans API router.

    Args:
        access_policy: Optional access policy for read/list/delete operations.
        results_dir: Directory containing scan results.
        fs: FileSystem instance for file operations.
        streaming_batch_size: Batch size for Arrow IPC streaming.

    Returns:
        Configured APIRouter with scans endpoints.
    """
    router = APIRouter(tags=["scans"])

    async def _validate_read(request: Request, file: str | UPath) -> None:
        if access_policy is not None:
            if not await access_policy.can_read(request, str(file)):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    async def _validate_list(request: Request, file: str | UPath) -> None:
        if access_policy is not None:
            if not await access_policy.can_list(request, str(file)):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    def _ensure_not_none(
        value: T | None, error_message: str = "Required value is None"
    ) -> T:
        """Raises HTTPException if value is None, otherwise returns the non-None value."""
        if value is None:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message
            )
        return value

    async def _to_rest_scan(
        request: Request, scan: RecorderStatus, running_scans: set[str]
    ) -> ScanStatus:
        return scan

    @router.post(
        "/scans",
        response_class=InspectPydanticJSONResponse,
        summary="List scans",
        description="Returns scans from the results directory. "
        "Optional filter condition uses SQL-like DSL. Optional order_by for sorting results. "
        "Optional pagination for cursor-based pagination.",
    )
    async def scans(
        request: Request,
        body: ScansRequest | None = None,
    ) -> ScansResponse:
        """Filter scan jobs from the results directory."""
        validated_results_dir = _ensure_not_none(results_dir, "results_dir is required")
        await _validate_list(request, validated_results_dir)

        ctx = _build_pagination_context(body, "scan_id")

        try:
            async with await scan_jobs_view(validated_results_dir) as view:
                count = await view.count(Query(where=ctx.filter_conditions or []))
                results = [
                    status
                    async for status in view.select(
                        Query(
                            where=ctx.conditions or [],
                            limit=ctx.limit,
                            order_by=ctx.db_order_columns or [],
                        )
                    )
                ]
        except InvalidInputException:
            return ScansResponse(items=[], total_count=0)

        if ctx.needs_reverse:
            results = list(reversed(results))

        with active_scans_store() as store:
            active_scans_map = store.read_all()

        enriched_results = [
            ScanStatusWithActiveInfo(
                complete=status.complete,
                spec=status.spec,
                location=status.location,
                summary=status.summary,
                errors=status.errors,
                active_scan_info=active_scans_map.get(status.spec.scan_id),
            )
            for status in results
        ]

        next_cursor = None
        if (
            body
            and body.pagination
            and len(enriched_results) == body.pagination.limit
            and enriched_results
        ):
            edge = (
                enriched_results[-1]
                if body.pagination.direction == "forward"
                else enriched_results[0]
            )
            next_cursor = _build_scans_cursor(edge, ctx.order_columns)

        return ScansResponse(
            items=enriched_results, total_count=count, next_cursor=next_cursor
        )

    @router.get(
        "/scans/active",
        response_model=ActiveScansResponse,
        response_class=InspectPydanticJSONResponse,
        summary="Get active scans",
        description="Returns info on all currently running scans.",
    )
    async def active_scans() -> ActiveScansResponse:
        """Get info on all active scans from the KV store."""
        with active_scans_store() as store:
            return ActiveScansResponse(items=store.read_all())

    @router.post(
        "/startscan",
        response_model=ScanStatus,
        response_class=InspectPydanticJSONResponse,
        summary="Run llm_scanner",
        description="Runs a scan using llm_scanner with the provided ScanJobConfig.",
    )
    async def run_llm_scanner(body: ScanJobConfig) -> ScanStatus:
        """Run an llm_scanner scan via subprocess."""
        proc, temp_path, _stdout_lines, stderr_lines = _spawn_scan_subprocess(body)
        pid = proc.pid

        active_info = await _wait_for_active_scan(pid)

        if os.path.exists(temp_path):
            os.unlink(temp_path)

        if active_info is None:
            exit_code = proc.poll()
            if exit_code is not None:
                proc.wait(timeout=1)
                stderr = b"".join(stderr_lines)
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Scan subprocess exited with code {exit_code}: {error_msg}",
                )
            else:
                proc.terminate()
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Scan subprocess failed to register within timeout",
                )

        return await scan_recorder_for_location(active_info.location).status(
            active_info.location
        )

    @router.get(
        "/scans/{scan}",
        response_model=ScanStatus,
        response_class=InspectPydanticJSONResponse,
        summary="Get scan status",
        description="Returns detailed status and metadata for a single scan.",
    )
    async def scan(
        request: Request,
        scan: str = Path(description="Scan path (base64url-encoded)"),
    ) -> ScanStatus:
        """Get detailed status for a single scan."""
        scan_path = UPath(decode_base64url(scan))
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        await _validate_read(request, scan_path)

        recorder_status_with_df = await scan_results_df_async(
            str(scan_path), rows="transcripts"
        )

        if recorder_status_with_df.spec.transcripts:
            recorder_status_with_df.spec.transcripts = (
                recorder_status_with_df.spec.transcripts.model_copy(
                    update={"data": None}
                )
            )

        return await _to_rest_scan(request, recorder_status_with_df, _running_scans)

    @router.get(
        "/scans/{scan}/{scanner}",
        summary="Get scanner dataframe containing results for all transcripts",
        description="Streams scanner results as Arrow IPC format with LZ4 compression. "
        "Excludes input column for efficiency; use the input endpoint for input text.",
    )
    async def scan_df(
        request: Request,
        scan: str = Path(description="Scan path (base64url-encoded)"),
        scanner: str = Path(description="Scanner name"),
    ) -> Response:
        """Stream scanner results as Arrow IPC with LZ4 compression."""
        scan_path = UPath(decode_base64url(scan))
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        await _validate_read(request, scan_path)

        result = await scan_results_arrow_async(str(scan_path))
        if scanner not in result.scanners:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scanner '{scanner}' not found in scan results",
            )

        def stream_as_arrow_ipc() -> Iterable[bytes]:
            buf = io.BytesIO()

            with result.reader(
                scanner,
                streaming_batch_size=streaming_batch_size,
                exclude_columns=["input"],
            ) as reader:
                with pa_ipc.new_stream(
                    buf,
                    reader.schema,
                    options=pa_ipc.IpcWriteOptions(compression="lz4"),
                ) as writer:
                    for batch in reader:
                        writer.write_batch(batch)

                        data = buf.getvalue()
                        if data:
                            yield data
                            buf.seek(0)
                            buf.truncate(0)

                remaining = buf.getvalue()
                if remaining:
                    yield remaining

        return StreamingResponse(
            content=stream_as_arrow_ipc(),
            media_type="application/vnd.apache.arrow.stream; codecs=lz4",
        )

    @router.get(
        "/scans/{scan}/{scanner}/{uuid}/input",
        summary="Get scanner input for a specific transcript",
        description="Returns the original input text for a specific scanner result. "
        "The input type is returned in the X-Input-Type response header.",
    )
    async def scanner_input(
        request: Request,
        scan: str = Path(description="Scan path (base64url-encoded)"),
        scanner: str = Path(description="Scanner name"),
        uuid: str = Path(description="UUID of the specific result row"),
    ) -> Response:
        """Retrieve original input text for a scanner result."""
        scan_path = UPath(decode_base64url(scan))
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        await _validate_read(request, scan_path)

        result = await scan_results_arrow_async(str(scan_path))
        if scanner not in result.scanners:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scanner '{scanner}' not found in scan results",
            )

        input_value = result.get_field(scanner, "uuid", uuid, "input").as_py()
        input_type = result.get_field(scanner, "uuid", uuid, "input_type").as_py()

        return Response(
            content=input_value,
            media_type="text/plain",
            headers={"X-Input-Type": input_type or ""},
        )

    return router
