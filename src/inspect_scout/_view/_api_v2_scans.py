"""Scans REST API endpoints."""

import asyncio
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterable

import pyarrow.ipc as pa_ipc
from duckdb import InvalidInputException
from fastapi import APIRouter, HTTPException, Path, Response
from fastapi.responses import StreamingResponse
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from .._query import Query
from .._query.order_by import OrderBy
from .._recorder.active_scans_store import ActiveScanInfo, active_scans_store
from .._recorder.factory import scan_recorder_for_location
from .._recorder.recorder import Status as RecorderStatus
from .._scanjob_config import ScanJobConfig
from .._scanjobs.factory import scan_jobs_view
from .._scanresults import scan_results_arrow_async, scan_results_df_async
from ._api_v2_types import (
    ActiveScansResponse,
    ScansRequest,
    ScansResponse,
    ScanStatus,
    ScanStatusWithActiveInfo,
)
from ._pagination_helpers import build_pagination_context
from ._server_common import InspectPydanticJSONResponse, decode_base64url

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()


def create_scans_router(
    streaming_batch_size: int = 1024,
) -> APIRouter:
    """Create scans API router.

    Args:
        streaming_batch_size: Batch size for Arrow IPC streaming.

    Returns:
        Configured APIRouter with scans endpoints.
    """
    router = APIRouter(tags=["scans"])

    @router.post(
        "/scans/{dir}",
        response_class=InspectPydanticJSONResponse,
        summary="List scans",
        description="Returns scans from specified directory. "
        "Optional filter condition uses SQL-like DSL. Optional order_by for sorting results. "
        "Optional pagination for cursor-based pagination.",
    )
    async def scans(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        body: ScansRequest | None = None,
    ) -> ScansResponse:
        """Filter scan jobs from the scans directory."""
        scans_dir = decode_base64url(dir)

        ctx = build_pagination_context(body, "scan_id")

        try:
            async with await scan_jobs_view(scans_dir) as view:
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
        "/scans/{dir}/{scan}",
        response_model=ScanStatus,
        response_class=InspectPydanticJSONResponse,
        summary="Get scan status",
        description="Returns detailed status and metadata for a single scan.",
    )
    async def scan(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
    ) -> ScanStatus:
        """Get detailed status for a single scan."""
        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

        recorder_status_with_df = await scan_results_df_async(
            str(scan_path), rows="transcripts"
        )

        if recorder_status_with_df.spec.transcripts:
            recorder_status_with_df.spec.transcripts = (
                recorder_status_with_df.spec.transcripts.model_copy(
                    update={"data": None}
                )
            )

        return recorder_status_with_df

    @router.get(
        "/scans/{dir}/{scan}/{scanner}",
        summary="Get scanner dataframe containing results for all transcripts",
        description="Streams scanner results as Arrow IPC format with LZ4 compression. "
        "Excludes input column for efficiency; use the input endpoint for input text.",
    )
    async def scan_df(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
        scanner: str = Path(description="Scanner name"),
    ) -> Response:
        """Stream scanner results as Arrow IPC with LZ4 compression."""
        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

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
        "/scans/{dir}/{scan}/{scanner}/{uuid}/input",
        summary="Get scanner input for a specific transcript",
        description="Returns the original input text for a specific scanner result. "
        "The input type is returned in the X-Input-Type response header.",
    )
    async def scanner_input(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
        scanner: str = Path(description="Scanner name"),
        uuid: str = Path(description="UUID of the specific result row"),
    ) -> Response:
        """Retrieve original input text for a scanner result."""
        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

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


# --- Private helpers ---


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
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="scout_scan_config_", delete=False
    )
    try:
        with f:
            f.write(config.model_dump_json(exclude_none=True))

        proc = subprocess.Popen(
            ["scout", "scan", f.name],
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

        return proc, f.name, stdout_lines, stderr_lines
    except Exception:
        os.unlink(f.name)
        raise


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
