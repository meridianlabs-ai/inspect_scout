import hashlib
import io
from typing import Any, Iterable, TypeVar, Union, get_args, get_origin

import pyarrow.ipc as pa_ipc
from fastapi import FastAPI, Header, HTTPException, Path, Query, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from inspect_ai._util.file import FileSystem
from inspect_ai._view.fastapi_server import AccessPolicy
from inspect_ai.model import ChatMessage
from starlette.status import (
    HTTP_304_NOT_MODIFIED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from .._recorder.recorder import Status as RecorderStatus
from .._scanlist import scan_list_async
from .._scanresults import (
    scan_results_arrow_async,
    scan_results_df_async,
)
from .._transcript.columns import Column
from .._transcript.factory import transcripts_from
from .._transcript.types import Transcript, TranscriptContent
from .._validation.types import ValidationCase
from ._api_v2_helpers import (
    _apply_cursor_pagination,
    _build_cursor,
    _ensure_tiebreaker,
    _has_more_results,
)
from ._api_v2_types import (
    OrderBy,
    RestScanStatus,
    TranscriptsRequest,
    TranscriptsResponse,
)
from ._server_common import (
    InspectPydanticJSONResponse,
    decode_base64url,
    default_transcripts_dir,
)

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()

API_VERSION = "2.0.0-alpha"


def _compute_scans_etag(scans_location: str) -> str | None:
    """Compute ETag from API version and _summary.json mtimes."""
    try:
        scans_dir = UPath(scans_location)
        mtimes = sorted(
            (d.name, (d / "_summary.json").stat().st_mtime)
            for d in scans_dir.rglob("scan_id=*")
            if d.is_dir() and (d / "_summary.json").exists()
        )
        return hashlib.md5(
            f"{API_VERSION}:{scans_location}:{mtimes}".encode()
        ).hexdigest()
    except Exception:
        return None


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
            from fastapi.openapi.utils import get_openapi

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
                        schema = m.model_json_schema(ref_template=ref_template)
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
                    schema = t.model_json_schema(ref_template=ref_template)
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
    ) -> RestScanStatus:
        return scan

    @app.get(
        "/transcripts-dir",
        response_class=PlainTextResponse,
        summary="Get default transcripts directory",
        description="Returns the default directory path where transcripts are stored.",
    )
    async def transcripts_dir(request: Request) -> str:
        """Return default transcripts directory path."""
        return await default_transcripts_dir()

    @app.get(
        "/scans-dir",
        response_class=PlainTextResponse,
        summary="Get default scans directory",
        description="Returns the default directory path where scans are stored.",
    )
    async def scans_dir(request: Request) -> str:
        """Return default scans directory path."""
        return _ensure_not_none(results_dir, "results_dir is not configured")

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
            transcripts_query = transcripts_from(transcripts_dir)
            if body and body.filter:
                transcripts_query = transcripts_query.where(body.filter)

            # Push order_by to database layer
            # When pagination used, apply tiebreaker. Otherwise just apply user's order_by.
            use_pagination = body and body.pagination
            if use_pagination:
                # Determine order with tiebreaker
                order_by = body.order_by if body else None
                if not order_by:
                    order_by = OrderBy(column="transcript_id", direction="ASC")
                order_columns = _ensure_tiebreaker(order_by)

                # Apply to database query
                for col, direction in order_columns:
                    transcripts_query = transcripts_query.order_by(
                        Column(col), direction
                    )
            elif body and body.order_by:
                # No pagination - just apply user's order_by
                order_bys = (
                    body.order_by
                    if isinstance(body.order_by, list)
                    else [body.order_by]
                )
                for ob in order_bys:
                    transcripts_query = transcripts_query.order_by(
                        Column(ob.column), ob.direction
                    )

            async with transcripts_query.reader() as tr:
                results = [t async for t in tr.index()]

            # Apply pagination if requested
            if use_pagination:
                assert body and body.pagination  # type narrowing
                paginated = _apply_cursor_pagination(
                    results, body.pagination, order_columns
                )

                # Build next cursor if more results exist
                next_cursor = None
                if _has_more_results(results, paginated, body.pagination):
                    if body.pagination.direction == "forward":
                        next_cursor = _build_cursor(paginated[-1], order_columns)
                    else:
                        next_cursor = _build_cursor(paginated[0], order_columns)

                return TranscriptsResponse(items=paginated, next_cursor=next_cursor)

            # No pagination - return all results
            return TranscriptsResponse(items=results, next_cursor=None)
        except FileNotFoundError:
            return TranscriptsResponse(items=[], next_cursor=None)

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

        transcripts_query = transcripts_from(transcripts_dir).where(
            Column("transcript_id") == id
        )

        async with transcripts_query.reader() as reader:
            infos = [info async for info in reader.index()]
            if not infos:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Transcript not found"
                )

            content = TranscriptContent(messages="all", events="all")
            return await reader.read(infos[0], content)

    @app.get(
        "/scans",
        response_model=list[RestScanStatus],
        response_class=InspectPydanticJSONResponse,
        summary="List scans",
        description="Returns all scans in the results directory. Supports ETag caching.",
    )
    async def scans(
        request: Request,
        response: Response,
        query_results_dir: str | None = Query(
            None,
            alias="results_dir",
            description="Results directory containing scans. Required if not configured server-side.",
            examples=["/path/to/results"],
        ),
        if_none_match: str | None = Header(
            None,
            alias="If-None-Match",
            include_in_schema=False,
        ),
    ) -> list[RestScanStatus] | Response:
        """List all scans with ETag-based caching support."""
        validated_results_dir = _ensure_not_none(
            query_results_dir or results_dir, "results_dir is required"
        )
        await _validate_list(request, validated_results_dir)

        if etag := _compute_scans_etag(validated_results_dir):
            if if_none_match and if_none_match.strip('"') == etag:
                return Response(
                    status_code=HTTP_304_NOT_MODIFIED, headers={"ETag": f'"{etag}"'}
                )
            response.headers["ETag"] = f'"{etag}"'

        return [
            await _to_rest_scan(request, scan, _running_scans)
            for scan in await scan_list_async(validated_results_dir)
        ]

    @app.get(
        "/scans/{scan}",
        response_model=RestScanStatus,
        response_class=InspectPydanticJSONResponse,
        summary="Get scan status",
        description="Returns detailed status and metadata for a single scan.",
    )
    async def scan(
        request: Request,
        scan: str = Path(description="Scan path (base64url-encoded)"),
    ) -> RestScanStatus:
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
