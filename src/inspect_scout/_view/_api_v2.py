import io
from typing import Any, Iterable, TypeVar, Union, get_args, get_origin

import pyarrow.ipc as pa_ipc
from duckdb import InvalidInputException
from fastapi import FastAPI, HTTPException, Path, Request, Response
from fastapi.responses import StreamingResponse
from inspect_ai._util.file import FileSystem
from inspect_ai._util.json import JsonChange
from inspect_ai._view.fastapi_server import AccessPolicy
from inspect_ai.event._event import Event
from inspect_ai.model import ChatMessage
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from inspect_scout._project._project import project
from inspect_scout._util.constants import DEFAULT_SCANS_DIR

from .._query import Column, Query
from .._recorder.recorder import Status as RecorderStatus
from .._scanjobs.factory import scan_jobs_view
from .._scanresults import (
    scan_results_arrow_async,
    scan_results_df_async,
)
from .._transcript.database.factory import transcripts_view
from .._transcript.types import Transcript, TranscriptContent
from .._validation.types import ValidationCase
from ._api_v2_helpers import (
    build_pagination_context,
    build_scans_cursor,
    build_transcripts_cursor,
)
from ._api_v2_types import (
    AppConfig,
    ScansRequest,
    ScansResponse,
    ScanStatus,
    TranscriptsRequest,
    TranscriptsResponse,
)
from ._server_common import (
    InspectPydanticJSONResponse,
    decode_base64url,
)

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()

API_VERSION = "2.0.0-alpha"


def v2_api_app(
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
) -> FastAPI:
    """Create V2 API FastAPI app.

    WARNING: This is an ALPHA API. Expect breaking changes without notice.
    Do not depend on this API for production use.
    """
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
                ("ChatMessage", ChatMessage),
                ("ValidationCase", ValidationCase),
                ("Event", Event),
                ("JsonChange", JsonChange),
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
        transcripts = project().transcripts
        transcripts = (
            UPath(transcripts).resolve().as_uri() if transcripts is not None else None
        )
        # resolve scans uri
        scans = UPath(project().scans or DEFAULT_SCANS_DIR).resolve().as_uri()
        return AppConfig(
            transcripts_dir=transcripts,
            scans_dir=scans,
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
            return await view.read(infos[0], content)

    @app.post(
        "/scans",
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

        next_cursor = None
        if (
            body
            and body.pagination
            and len(results) == body.pagination.limit
            and results
        ):
            edge = results[-1] if body.pagination.direction == "forward" else results[0]
            next_cursor = build_scans_cursor(edge, ctx.order_columns)

        return ScansResponse(items=results, total_count=count, next_cursor=next_cursor)

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
