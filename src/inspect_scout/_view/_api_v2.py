import asyncio
import inspect
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
from functools import reduce
from pathlib import Path as PathlibPath
from typing import (
    Any,
    Callable,
    Iterable,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

import pyarrow.ipc as pa_ipc
from duckdb import InvalidInputException
from fastapi import FastAPI, Header, HTTPException, Path, Request, Response
from fastapi.responses import StreamingResponse
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import FileSystem
from inspect_ai._util.json import JsonChange
from inspect_ai._util.registry import registry_find, registry_info
from inspect_ai._view.fastapi_server import AccessPolicy
from inspect_ai.event._event import Event
from inspect_ai.model import ChatMessage, Content
from inspect_ai.util import json_schema
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_412_PRECONDITION_FAILED,
    HTTP_413_CONTENT_TOO_LARGE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from .._llm_scanner.params import LlmScannerParams
from .._project._project import (
    EtagMismatchError,
    read_project,
    read_project_config_with_etag,
    write_project_config,
)
from .._project.types import ProjectConfig
from .._query import Column, Condition, Query, ScalarValue, condition_as_sql
from .._recorder.active_scans_store import ActiveScanInfo, active_scans_store
from .._recorder.factory import scan_recorder_for_location
from .._recorder.recorder import Status as RecorderStatus
from .._scanjob_config import ScanJobConfig
from .._scanjobs.factory import scan_jobs_view
from .._scanresults import (
    scan_results_arrow_async,
    scan_results_df_async,
)
from .._transcript.database.factory import transcripts_view
from .._transcript.types import Transcript, TranscriptContent, TranscriptTooLargeError
from .._util.constants import DEFAULT_SCANS_DIR
from .._validation.types import ValidationCase
from .._view.types import ViewConfig
from ._api_v2_helpers import (
    build_pagination_context,
    build_scans_cursor,
    build_transcripts_cursor,
)
from ._api_v2_types import (
    ActiveScansResponse,
    AppConfig,
    DistinctRequest,
    ScannerInfo,
    ScannerParam,
    ScannersResponse,
    ScansRequest,
    ScansResponse,
    ScanStatus,
    ScanStatusWithActiveInfo,
    TranscriptsRequest,
    TranscriptsResponse,
)
from ._server_common import (
    InspectPydanticJSONResponse,
    decode_base64url,
)
from ._validation_api import create_validation_router

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()

API_VERSION = "2.0.0-alpha"

MAX_TRANSCRIPT_BYTES = 350 * 1024 * 1024  # 350MB


def v2_api_app(
    view_config: ViewConfig | None = None,
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
) -> FastAPI:
    """Create V2 API FastAPI app.

    WARNING: This is an ALPHA API. Expect breaking changes without notice.
    Do not depend on this API for production use.
    """
    view_config = view_config or ViewConfig()

    app = FastAPI(
        title="Inspect Scout Viewer API",
        version=API_VERSION,
    )

    # Remove implied and noisy 422 responses from OpenAPI schema
    def custom_openapi() -> dict[str, Any]:
        if not app.openapi_schema:
            from fastapi._compat import v2
            from fastapi.openapi.utils import get_openapi

            from ._server_common import CustomJsonSchemaGenerator

            # Monkey-patch custom schema generator for response-oriented schemas
            v2.GenerateJsonSchema = CustomJsonSchemaGenerator  # type: ignore

            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                routes=app.routes,
            )
            for path in openapi_schema.get("paths", {}).values():
                for operation in path.values():
                    if isinstance(operation, dict):
                        operation.get("responses", {}).pop("422", None)

            # Force additional types into schema even if not referenced by endpoints.
            # Format: list of (schema_name, type) tuples.
            # - For Union types (type aliases): creates a oneOf schema with the
            #   given name, plus schemas for each member type. Python type aliases
            #   don't preserve their name at runtime, so we must provide it explicitly.
            # - For Pydantic models: creates a schema with the given name.
            extra_schemas = [
                ("Content", Content),
                ("ChatMessage", ChatMessage),
                ("ValidationCase", ValidationCase),
                ("Event", Event),
                ("JsonChange", JsonChange),
                ("LlmScannerParams", LlmScannerParams),
            ]
            ref_template = "#/components/schemas/{model}"
            schemas = openapi_schema.setdefault("components", {}).setdefault(
                "schemas", {}
            )
            for name, t in extra_schemas:
                if get_origin(t) is Union:
                    # Union type: create oneOf schema and add member schemas
                    members = get_args(t)
                    for m in members:
                        schema = m.model_json_schema(
                            ref_template=ref_template,
                            schema_generator=CustomJsonSchemaGenerator,
                        )
                        schemas.update(schema.get("$defs", {}))
                        schemas[m.__name__] = {
                            k: v for k, v in schema.items() if k != "$defs"
                        }
                    schemas[name] = {
                        "oneOf": [
                            {"$ref": f"#/components/schemas/{m.__name__}"}
                            for m in members
                        ]
                    }
                elif hasattr(t, "model_json_schema"):
                    # Pydantic model: add directly
                    schema = t.model_json_schema(
                        ref_template=ref_template,
                        schema_generator=CustomJsonSchemaGenerator,
                    )
                    schemas.update(schema.get("$defs", {}))
                    schemas[name] = {k: v for k, v in schema.items() if k != "$defs"}

            app.openapi_schema = openapi_schema
        return app.openapi_schema

    # Include validation router
    app.include_router(create_validation_router(PathlibPath.cwd(), access_policy))

    app.openapi = custom_openapi  # type: ignore[method-assign]

    async def _validate_read(request: Request, file: str | UPath) -> None:
        if access_policy is not None:
            if not await access_policy.can_read(request, str(file)):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    async def _validate_delete(request: Request, file: str | UPath) -> None:
        if access_policy is not None:
            if not await access_policy.can_delete(request, str(file)):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    async def _validate_list(request: Request, file: str | UPath) -> None:
        if access_policy is not None:
            if not await access_policy.can_list(request, str(file)):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    T = TypeVar("T")

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

    @app.get(
        "/config",
        response_model=AppConfig,
        response_class=InspectPydanticJSONResponse,
        summary="Get application configuration",
        description="Returns app config including transcripts and scans directories.",
    )
    async def config(request: Request) -> AppConfig:
        """Return application configuration."""
        project = read_project()
        transcripts = view_config.transcripts or project.transcripts
        scans = view_config.scans or project.scans or DEFAULT_SCANS_DIR
        return AppConfig(
            home_dir=UPath(PathlibPath.home()).resolve().as_uri(),
            project_dir=UPath(PathlibPath.cwd()).resolve().as_uri(),
            transcripts_dir=UPath(transcripts).resolve().as_uri()
            if transcripts is not None
            else None,
            scans_dir=UPath(scans).resolve().as_uri(),
        )

    @app.get(
        "/scanners",
        response_model=ScannersResponse,
        response_class=InspectPydanticJSONResponse,
        summary="List available scanners",
        description="Returns info about all registered scanners.",
    )
    async def scanners() -> ScannersResponse:
        """Return info about all registered scanner factories."""

        def param_schema(p: inspect.Parameter) -> dict[str, Any]:
            if p.annotation == inspect.Parameter.empty:
                return {"type": "any"}
            return json_schema(p.annotation).model_dump(exclude_none=True)

        scanner_objs = registry_find(lambda info: info.type == "scanner")
        items = [
            ScannerInfo(
                name=registry_info(s).name,
                version=registry_info(s).metadata.get("scanner_version", 0),
                description=s.__doc__.split("\n")[0] if s.__doc__ else None,
                params=[
                    ScannerParam(
                        name=p.name,
                        schema=param_schema(p),
                        required=p.default == inspect.Parameter.empty,
                        default=(
                            p.default if p.default != inspect.Parameter.empty else None
                        ),
                    )
                    for p in inspect.signature(
                        cast(Callable[..., Any], s)
                    ).parameters.values()
                ],
            )
            for s in scanner_objs
        ]
        return ScannersResponse(items=items)

    @app.get(
        "/project/config",
        response_model=ProjectConfig,
        response_class=InspectPydanticJSONResponse,
        summary="Get project configuration",
        description="Returns the project configuration from scout.yaml. "
        "The ETag header contains a hash of the file for conditional updates.",
    )
    async def get_project_config() -> Response:
        """Return project configuration with ETag header."""
        config, etag = read_project_config_with_etag()

        return InspectPydanticJSONResponse(
            content=config,
            headers={"ETag": f'"{etag}"'},
        )

    @app.put(
        "/project/config",
        response_model=ProjectConfig,
        response_class=InspectPydanticJSONResponse,
        summary="Update project configuration",
        description="Updates the project configuration in scout.yaml while preserving "
        "comments and formatting. Optionally include If-Match header with current ETag for "
        "optimistic concurrency control. Omit If-Match to force save.",
    )
    async def put_project_config(
        config: ProjectConfig,
        if_match: str | None = Header(
            default=None,
            description="ETag from GET request (optional, omit to force save)",
        ),
    ) -> Response:
        """Update project configuration with comment preservation."""
        # Parse the If-Match header (may be quoted), None means force save
        expected_etag = if_match.strip('"') if if_match else None

        try:
            updated_config, new_etag = write_project_config(config, expected_etag)
        except FileNotFoundError:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Project config file (scout.yaml) not found",
            ) from None
        except EtagMismatchError:
            raise HTTPException(
                status_code=HTTP_412_PRECONDITION_FAILED,
                detail="Config file has been modified. Please refresh and try again.",
            ) from None
        except PrerequisiteError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from None

        return InspectPydanticJSONResponse(
            content=updated_config,
            headers={"ETag": f'"{new_etag}"'},
        )

    @app.post(
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
            ctx = build_pagination_context(body, "transcript_id")

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
                next_cursor = build_transcripts_cursor(edge, ctx.order_columns)

            return TranscriptsResponse(
                items=results, total_count=count, next_cursor=next_cursor
            )
        except FileNotFoundError:
            return TranscriptsResponse(items=[], total_count=0, next_cursor=None)

    @app.get(
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

    @app.post(
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

    @app.post(
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

        ctx = build_pagination_context(body, "scan_id")

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
            # This will be raised when there are not scans in validated_results_dir
            return ScansResponse(items=[], total_count=0)

        if ctx.needs_reverse:
            results = list(reversed(results))

        # Enrich results with active scan info
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
            next_cursor = build_scans_cursor(edge, ctx.order_columns)

        return ScansResponse(
            items=enriched_results, total_count=count, next_cursor=next_cursor
        )

    @app.get(
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

    @app.post(
        "/code",
        summary="Code endpoint",
    )
    async def code(
        body: Condition | list[Condition],
    ) -> dict[str, str]:
        """Process condition."""
        filter_sql = condition_as_sql(
            reduce(lambda a, b: a & b, body) if isinstance(body, list) else body,
            "filter",
        )
        return {
            "python": f"transcripts.where({filter_sql!r})",
            "filter": filter_sql,
        }

    @app.post(
        "/startscan",
        response_model=ScanStatus,
        response_class=InspectPydanticJSONResponse,
        summary="Run llm_scanner",
        description="Runs a scan using llm_scanner with the provided ScanJobConfig.",
    )
    async def run_llm_scanner(body: ScanJobConfig) -> ScanStatus:
        """Run an llm_scanner scan via subprocess."""
        # Spawn subprocess with unadulterated config
        proc, temp_path, _stdout_lines, stderr_lines = _spawn_scan_subprocess(body)
        pid = proc.pid

        # Wait for scan to register in active_scans_store
        active_info = await _wait_for_active_scan(pid)

        # Clean up temp file - subprocess has read it if registered
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        if active_info is None:
            exit_code = proc.poll()
            if exit_code is not None:
                # Give threads a moment to finish reading
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

        # Get status from recorder using location from active_info
        return await scan_recorder_for_location(active_info.location).status(
            active_info.location
        )

    @app.get(
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

        # read the results and return
        recorder_status_with_df = await scan_results_df_async(
            str(scan_path), rows="transcripts"
        )

        # clear the transcript data
        if recorder_status_with_df.spec.transcripts:
            recorder_status_with_df.spec.transcripts = (
                recorder_status_with_df.spec.transcripts.model_copy(
                    update={"data": None}
                )
            )

        return await _to_rest_scan(request, recorder_status_with_df, _running_scans)

    @app.get(
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

            # Convert dataframe to Arrow IPC format with LZ4 compression
            # LZ4 provides good compression with fast decompression and
            # has native js codecs for the client
            #
            # Note that it was _much_ faster to compress vs gzip
            # with only a moderate loss in compression ratio
            # (e.g. 40% larger in exchange for ~20x faster compression)
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

                        # Flush whatever the writer just appended
                        data = buf.getvalue()
                        if data:
                            yield data
                            buf.seek(0)
                            buf.truncate(0)

                # Footer / EOS marker
                remaining = buf.getvalue()
                if remaining:
                    yield remaining

        return StreamingResponse(
            content=stream_as_arrow_ipc(),
            media_type="application/vnd.apache.arrow.stream; codecs=lz4",
        )

    @app.get(
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

        # Return raw input as body with inputType in header (more efficient for large text)
        return Response(
            content=input_value,
            media_type="text/plain",
            headers={"X-Input-Type": input_type or ""},
        )

    return app


# JUST FOR TESTING
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
    """Spawn a subprocess to run the scan.

    Args:
        config: The scan job configuration

    Returns:
        Tuple of (Popen object, temp config file path, stdout_lines, stderr_lines)
        stdout_lines and stderr_lines accumulate as subprocess runs.
    """
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
    """Wait for an active scan to appear for the given PID.

    Args:
        pid: The subprocess PID to monitor
        timeout_seconds: Max time to wait
        poll_interval: Time between polls

    Returns:
        ActiveScanInfo if found, None on timeout
    """
    start = time.time()

    while time.time() - start < timeout_seconds:
        with active_scans_store() as store:
            info = store.read_by_pid(pid)
            if info is not None:
                return info
        await asyncio.sleep(poll_interval)

    return None


async def _run_scan_background(config: ScanJobConfig, location: str) -> None:
    # import inspect_scout._display._display as display_module
    from inspect_scout._scan import scan_async

    # original_display = display_module._display

    await scan_async(scanners=config)
    # try:
    #     display_module._display = None
    # finally:
    #     display_module._display = original_display
