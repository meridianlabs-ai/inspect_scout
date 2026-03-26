"""Scans REST API endpoints."""

import asyncio
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from typing import Any, Iterable

import anyio
import pyarrow.ipc as pa_ipc
from duckdb import InvalidInputException
from fastapi import APIRouter, HTTPException, Path, Request, Response
from fastapi import Query as QueryParam
from fastapi.responses import StreamingResponse
from inspect_ai._util.file import file
from send2trash import send2trash
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from .._query import Query, ScalarValue
from .._query.order_by import OrderBy
from .._recorder.active_scans_store import ActiveScanInfo, active_scans_store
from .._recorder.factory import scan_recorder_for_location
from .._scanjob_config import ScanJobConfig
from .._scanjobs.duckdb import scan_jobs_view
from .._scanresults import scan_results_arrow_async, scan_results_df_async
from ._api_v2_types import (
    ActiveScansResponse,
    DistinctRequest,
    ScannerInputResponse,
    ScanRow,
    ScansRequest,
    ScansResponse,
    ScanStatus,
)
from ._pagination_helpers import build_pagination_context
from ._server_common import InspectPydanticJSONResponse, decode_base64url
from .invalidationTopics import notify_topics

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()


def _build_scan_zip(scan_path: UPath) -> Response:
    """Build a zip archive of all files in a scan directory."""
    if not scan_path.exists():
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Scan not found: {scan_path}",
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for child in scan_path.iterdir():
            if child.is_file():
                with file(child.as_posix(), "rb") as f:
                    zf.writestr(child.name, f.read())

    scan_id = scan_path.name
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{scan_id}.zip"',
        },
    )


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
                    scan_row
                    async for scan_row in view.select(
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

        next_cursor = None
        if (
            body
            and body.pagination
            and len(results) == body.pagination.limit
            and results
        ):
            edge = results[-1] if body.pagination.direction == "forward" else results[0]
            next_cursor = _build_scans_cursor(edge, ctx.order_columns)

        return ScansResponse(items=results, total_count=count, next_cursor=next_cursor)

    @router.post(
        "/scans/{dir}/distinct",
        summary="Get distinct column values",
        description="Returns distinct values for a column, optionally filtered.",
    )
    async def scans_distinct(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        body: DistinctRequest | None = None,
    ) -> list[ScalarValue]:
        """Get distinct values for a column."""
        scans_dir = decode_base64url(dir)
        if body is None:
            return []
        async with await scan_jobs_view(scans_dir) as view:
            return await view.distinct(body.column, body.filter)

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
        description="Returns detailed status and metadata for a single scan. "
        "Send Accept: application/zip to download the scan directory as a zip archive.",
        responses={
            200: {
                "content": {
                    "application/zip": {
                        "description": "Zip archive of the scan directory "
                        "when Accept: application/zip is sent.",
                    },
                },
            }
        },
    )
    async def scan(
        request: Request,
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
    ) -> ScanStatus | Response:
        """Get detailed status for a single scan.

        Content negotiation: returns JSON by default, or a zip archive
        when the client sends Accept: application/zip.
        """
        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

        accept = request.headers.get("accept", "")
        if "application/zip" in accept:
            return await anyio.to_thread.run_sync(lambda: _build_scan_zip(scan_path))

        try:
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
        except FileNotFoundError as err:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scan not found: {scan_path}",
            ) from err

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
                exclude_columns=["input", "scan_events"],
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
        response_model=ScannerInputResponse,
        summary="Get scanner input for a specific result",
        description="Returns a JSON envelope with input, input_type, and input_data "
        "(EventsData pools for condensed events, or null).",
        deprecated=True,
    )
    async def scanner_input(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
        scanner: str = Path(description="Scanner name"),
        uuid: str = Path(description="UUID of the specific result row"),
    ) -> Response:
        """Retrieve scanner input as a JSON envelope.

        Returns ``{"input_type": ..., "input": ..., "input_data": ...}``
        where ``input`` and ``input_data`` are raw JSON from parquet —
        no server-side parsing or re-encoding.
        """
        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

        result = await scan_results_arrow_async(str(scan_path))
        if scanner not in result.scanners:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scanner '{scanner}' not found in scan results",
            )

        fields = result.get_fields(
            scanner, "uuid", uuid, ["input", "input_type", "input_data"]
        )

        # `input` and `input_data` are pre-serialized JSON strings in the parquet
        # columns. The call to `.get_fields()` does `.as_py()` which returns a Python
        # `str` from Arrow's `large_string`. This means that `fields["input"]` is
        # a python `str`. They both pass straight through as raw JSON fragments
        # — no parsing, no re-encoding, no extra copies beyond Arrow → Python str.
        # Obviously, there's no type safety here — `response_model`` is for OpenAPI
        # schema only.

        return Response(
            content=(
                '{"input_type":'
                + json.dumps(fields["input_type"])
                + ',"input":'
                + (fields["input"] or "null")
                + ',"input_data":'
                + (fields["input_data"] or "null")
                + "}"
            ),
            media_type="application/json",
        )

    _FIELDS_ALLOWLIST: frozenset[str] = frozenset(
        {"input", "input_type", "input_data", "scan_events"}
    )
    _PLAIN_VALUE_FIELDS: frozenset[str] = frozenset({"input_type"})

    @router.get(
        "/scans/{dir}/{scan}/{scanner}/{uuid}/fields",
        summary="Get specific fields for a result row",
        description="Returns requested fields as a JSON object. "
        "Allowed fields: input, input_type, input_data, scan_events. "
        "Pass a comma-separated list via the `fields` query parameter.",
    )
    async def scanner_fields(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
        scanner: str = Path(description="Scanner name"),
        uuid: str = Path(description="UUID of the specific result row"),
        fields: str | None = QueryParam(
            default=None,
            description="Comma-separated list of field names to return",
        ),
    ) -> Response:
        """Retrieve specific fields for a result row as a JSON object.

        Fields ``input``, ``input_data``, and ``scan_events`` are pre-serialized
        JSON strings in parquet — passed through raw without re-encoding.
        ``input_type`` is a plain scalar and is serialized with ``json.dumps``.
        """
        if not fields:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Missing required query parameter: fields",
            )

        requested = list(dict.fromkeys(f.strip() for f in fields.split(",") if f.strip()))
        unknown = set(requested) - _FIELDS_ALLOWLIST
        if unknown:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Unknown field(s): {sorted(unknown)}. "
                f"Allowed: {sorted(_FIELDS_ALLOWLIST)}",
            )

        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

        result = await scan_results_arrow_async(str(scan_path))
        if scanner not in result.scanners:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scanner '{scanner}' not found in scan results",
            )

        try:
            row = result.get_fields(scanner, "uuid", uuid, requested)
        except (KeyError, ValueError) as err:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No row found for uuid: {uuid}",
            ) from err

        # Build raw JSON manually to avoid re-parsing pre-serialized JSON fields.
        parts: list[str] = []
        for field in requested:
            raw = row[field]
            # Convert pyarrow scalars to native Python values.
            value = raw.as_py() if hasattr(raw, "as_py") else raw
            if value is None:
                serialized = "null"
            elif field in _PLAIN_VALUE_FIELDS:
                serialized = json.dumps(value)
            else:
                # Pre-serialized JSON string — pass through raw.
                serialized = value
            parts.append(json.dumps(field) + ":" + serialized)

        return Response(
            content="{" + ",".join(parts) + "}",
            media_type="application/json",
        )

    @router.delete(
        "/scans/{dir}/{scan}",
        status_code=204,
        summary="Delete a scan",
        description="Deletes a scan directory. Returns 409 Conflict if scan is active.",
    )
    async def delete_scan(
        dir: str = Path(description="Scans directory (base64url-encoded)"),
        scan: str = Path(description="Scan path (base64url-encoded)"),
    ) -> None:
        """Delete a scan directory."""
        scans_dir = decode_base64url(dir)
        scan_path = UPath(scans_dir) / decode_base64url(scan)

        # Check if scan exists
        if not scan_path.exists():
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )

        # Check if scan is active (prevent deletion of running scans)
        scan_location_str = str(scan_path)
        with active_scans_store() as store:
            active_scans = store.read_all()
            for active_info in active_scans.values():
                if active_info.location == scan_location_str:
                    raise HTTPException(
                        status_code=HTTP_409_CONFLICT,
                        detail=f"Cannot delete active scan: {active_info.scan_id}",
                    )

        send2trash(scan_path.path)

        # Notify clients to invalidate scan caches
        await notify_topics(["scans"])

    return router


def _build_scans_cursor(
    row: ScanRow,
    order_columns: list[OrderBy],
) -> dict[str, Any]:
    """Build cursor from ScanRow using sort columns."""
    cursor: dict[str, Any] = {}
    for ob in order_columns:
        column = ob.column
        value = getattr(row, column, None)
        # Handle timestamp serialization
        if column == "timestamp" and value is not None:
            cursor[column] = value.isoformat()
        else:
            cursor[column] = value
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
