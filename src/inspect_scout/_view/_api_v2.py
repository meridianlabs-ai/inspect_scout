import hashlib
import io
from typing import Iterable, TypeVar

import pyarrow.ipc as pa_ipc
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from inspect_ai._util.file import FileSystem
from inspect_ai._view.fastapi_server import AccessPolicy
from starlette.status import (
    HTTP_304_NOT_MODIFIED,
    HTTP_400_BAD_REQUEST,
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
from .._transcript.factory import transcripts_from
from .._transcript.types import TranscriptInfo
from ._api_v2_types import RestScanStatus, ScansRestResponse
from ._server_common import InspectPydanticJSONResponse, default_transcripts_dir

# TODO: temporary simulation tracking currently running scans (by location path)
_running_scans: set[str] = set()


def _compute_scans_etag(scans_location: str) -> str | None:
    """Compute ETag from scan_summary.json mtimes. Returns None on error."""
    try:
        scans_dir = UPath(scans_location)
        mtimes = sorted(
            (d.name, (d / "scan_summary.json").stat().st_mtime)
            for d in scans_dir.rglob("scan_id=*")
            if d.is_dir() and (d / "scan_summary.json").exists()
        )
        return hashlib.md5(str(mtimes).encode()).hexdigest()
    except Exception:
        return None


def v2_api_app(
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
) -> "FastAPI":
    """Create V2 API FastAPI app.

    WARNING: This is an ALPHA API. Expect breaking changes without notice.
    Do not depend on this API for production use.
    """
    app = FastAPI(
        title="Inspect Scout Viewer API",
        version="2.0.0-alpha",
    )

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

    @app.get("/transcripts-dir", response_class=PlainTextResponse)
    async def transcripts_dir(
        request: Request,
    ) -> str:
        return await default_transcripts_dir()

    @app.get("/transcripts")
    async def transcripts(
        request_transcripts_dir: str | None = Query(None, alias="dir"),
    ) -> list[TranscriptInfo]:
        transcripts_dir = request_transcripts_dir or await default_transcripts_dir()
        try:
            async with transcripts_from(transcripts_dir).reader() as tr:
                return [t async for t in tr.index()]
        except FileNotFoundError:
            return []

    @app.get(
        "/scans",
        response_model=ScansRestResponse,
        response_class=InspectPydanticJSONResponse,
        responses={
            HTTP_304_NOT_MODIFIED: {"description": "Not Modified"},
            HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        },
    )
    async def scans(
        request: Request,
        response: Response,
        query_results_dir: str | None = Query(None, alias="results_dir"),
        if_none_match: str | None = Header(None, alias="If-None-Match"),
    ) -> ScansRestResponse | Response:
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

        return ScansRestResponse(
            results_dir=validated_results_dir,
            scans=[
                await _to_rest_scan(request, scan, _running_scans)
                for scan in await scan_list_async(validated_results_dir)
            ],
        )

    @app.get("/scanner_df_input/{scan:path}")
    async def scanner_input(
        request: Request,
        scan: str,
        query_scanner: str | None = Query(None, alias="scanner"),
        query_uuid: str | None = Query(None, alias="uuid"),
    ) -> Response:
        if query_scanner is None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="scanner query parameter is required",
            )

        if query_uuid is None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="uuid query parameter is required",
            )

        # convert to absolute path
        scan_path = UPath(scan)
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        # validate
        await _validate_read(request, scan_path)

        # get the result
        result = await scan_results_arrow_async(str(scan_path))

        # ensure we have the data (404 if not)
        if query_scanner not in result.scanners:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scanner '{query_scanner}' not found in scan results",
            )

        input_value = result.get_field(
            query_scanner, "uuid", query_uuid, "input"
        ).as_py()
        input_type = result.get_field(
            query_scanner, "uuid", query_uuid, "input_type"
        ).as_py()

        # Return raw input as body with inputType in header (more efficient for large text)
        return Response(
            content=input_value,
            media_type="text/plain",
            headers={"X-Input-Type": input_type or ""},
        )

    @app.get("/scanner_df/{scan:path}")
    async def scan_df(
        request: Request,
        scan: str,
        query_scanner: str | None = Query(None, alias="scanner"),
    ) -> Response:
        if query_scanner is None:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="scanner query parameter is required",
            )

        # convert to absolute path
        scan_path = UPath(scan)
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        # validate
        await _validate_read(request, scan_path)

        # get the result
        result = await scan_results_arrow_async(str(scan_path))

        # ensure we have the data (404 if not)
        if query_scanner not in result.scanners:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Scanner '{query_scanner}' not found in scan results",
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
                query_scanner,
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
        "/scan/{scan:path}",
        response_model=RestScanStatus,
        response_class=InspectPydanticJSONResponse,
        responses={
            HTTP_403_FORBIDDEN: {"description": "Forbidden"},
            HTTP_404_NOT_FOUND: {"description": "Not Found"},
        },
    )
    async def scan(
        request: Request,
        scan: str,
    ) -> RestScanStatus:
        # convert to absolute path
        scan_path = UPath(scan)
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        # validate
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

    return app
