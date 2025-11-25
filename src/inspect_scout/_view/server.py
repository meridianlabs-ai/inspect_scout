import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, TypeVar

import anyio
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as pa_ipc
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import FileSystem, filesystem
from inspect_ai._util.json import to_json_safe
from inspect_ai._view.fastapi_server import (
    AccessPolicy,
    FileMappingPolicy,
    OnlyDirAccessPolicy,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from typing_extensions import override
from upath import UPath

from inspect_scout._display._display import display
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanlist import scan_list_async
from inspect_scout._scanresults import (
    remove_scan_results,
    scan_results_arrow_async,
    scan_results_df_async,
)
from inspect_scout._scanspec import ScanSpec

from .._scanner.result import Error


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)


@dataclass
class IPCDataFrame:
    """Data frame serialized as Arrow IPC format."""

    format: Literal["arrow.feather"] = "arrow.feather"
    """Type of serialized data frame."""

    version: int = 2
    """Version of serialization format."""

    encoding: Literal["base64"] = "base64"
    """Encoding of serialized data frame."""

    data: str | None = None
    """Data frame serialized as Arrow IPC format."""

    row_count: int | None = None
    """Number of rows in data frame."""

    column_names: list[str] | None = None
    """List of column names in data frame."""


@dataclass
class IPCSerializableResults(Status):
    """Scan results as serialized data frames."""

    scanners: dict[str, IPCDataFrame]
    """Dict of scanner name to serialized data frame."""

    def __init__(
        self,
        complete: bool,
        spec: ScanSpec,
        location: str,
        summary: Summary,
        errors: list[Error],
        scanners: dict[str, IPCDataFrame],
    ) -> None:
        super().__init__(complete, spec, location, summary, errors)
        self.scanners = scanners


def df_to_ipc(df: pd.DataFrame) -> IPCDataFrame:
    table = pa.Table.from_pandas(df, preserve_index=False)

    buf = io.BytesIO()
    with pa_ipc.new_stream(buf, table.schema) as writer:
        writer.write_table(table)

    payload = base64.b64encode(buf.getvalue()).decode("ascii")
    return IPCDataFrame(
        data=payload,
        row_count=int(len(df)),
        column_names=[str(c) for c in df.columns],
    )


def view_server(
    results_dir: str,
    host: str,
    port: int,
    authorization: str | None = None,
    fs_options: dict[str, Any] | None = None,
) -> None:
    # get filesystem and resolve scan_dir to full path
    fs = filesystem(results_dir, fs_options=fs_options or {})
    if not fs.exists(results_dir):
        fs.mkdir(results_dir, True)
    results_dir = fs.info(results_dir).name

    api = view_server_app(
        access_policy=OnlyDirAccessPolicy(results_dir) if not authorization else None,
        results_dir=results_dir,
        fs=fs,
    )

    if authorization:
        api.add_middleware(AuthorizationMiddleware, authorization=authorization)

    app = FastAPI()
    app.mount("/api", api)

    dist = Path(__file__).parent / "www" / "dist"
    app.mount("/", StaticFiles(directory=dist.as_posix(), html=True), name="static")

    # run app
    display().print(f"Scout View: {results_dir}")

    async def run_server() -> None:
        config = uvicorn.Config(app, host=host, port=port, log_config=None)
        server = uvicorn.Server(config)

        async def announce_when_ready() -> None:
            while not server.started:
                await anyio.sleep(0.05)
            # Print this for compatibility with the Inspect VSCode plugin:
            display().print(
                f"======== Running on http://{host}:{port} ========\n"
                "(Press CTRL+C to quit)"
            )

        async with anyio.create_task_group() as tg:
            tg.start_soon(announce_when_ready)
            await server.serve()

    anyio.run(run_server)


def view_server_app(
    mapping_policy: FileMappingPolicy | None = None,
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
) -> "FastAPI":
    app = FastAPI()

    async def _map_file(request: Request, file: str) -> str:
        if mapping_policy is not None:
            return await mapping_policy.map(request, file)
        return file

    async def _unmap_file(request: Request, file: str) -> str:
        if mapping_policy is not None:
            return await mapping_policy.unmap(request, file)
        return file

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

    @app.get("/scans")
    async def scans(
        request: Request,
        query_results_dir: str | None = Query(None, alias="results_dir"),
    ) -> Response:
        validated_results_dir = _ensure_not_none(
            query_results_dir or results_dir, "results_dir is required"
        )
        await _validate_list(request, validated_results_dir)
        scans = await scan_list_async(await _map_file(request, validated_results_dir))
        for scan in scans:
            scan.location = await _unmap_file(request, scan.location)

        return InspectPydanticJSONResponse(
            content={"results_dir": validated_results_dir, "scans": scans},
            media_type="application/json",
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
        scan_path = UPath(await _map_file(request, scan))
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
                query_scanner, streaming_batch_size=streaming_batch_size
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

    @app.get("/scan/{scan:path}")
    async def scan(
        request: Request,
        scan: str,
        status_only: bool | None = Query(None, alias="status_only"),
    ) -> Response:
        # convert to absolute path
        scan_path = UPath(await _map_file(request, scan))
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        # validate
        await _validate_read(request, scan_path)

        # read the results and return
        result = await scan_results_df_async(str(scan_path), rows="transcripts")

        # convert the dataframes to their serializable form (omit
        # if status_only is true)
        serializable_scanners: dict[str, IPCDataFrame] = {}
        if not status_only:
            for scanner in result.scanners:
                df = result.scanners[scanner]
                serializable_scanners[scanner] = df_to_ipc(df)

        # clear the transcript data
        if result.spec.transcripts:
            result.spec.transcripts = result.spec.transcripts.model_copy(
                update={"data": None}
            )

        # create the serializable result
        serializable_result = IPCSerializableResults(
            complete=result.complete,
            spec=result.spec,
            location=await _unmap_file(request, result.location),
            summary=result.summary,
            errors=result.errors,
            scanners=serializable_scanners,
        )

        return InspectPydanticJSONResponse(
            content=serializable_result, media_type="application/json"
        )

    @app.get("/scan-delete/{scan:path}")
    async def scan_delete(request: Request, scan: str) -> Response:
        # convert to absolute path
        scan_path = UPath(await _map_file(request, scan))
        if not scan_path.is_absolute():
            validated_results_dir = _ensure_not_none(
                results_dir, "results_dir is required"
            )
            results_path = UPath(validated_results_dir)
            scan_path = results_path / scan_path

        await _validate_delete(request, scan_path)

        remove_scan_results(scan_path.as_posix())

        return InspectPydanticJSONResponse(content=True, media_type="application/json")

    return app


class AuthorizationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, authorization: str) -> None:
        super().__init__(app)
        self.authorization = authorization

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        auth_header = request.headers.get("authorization", None)
        if auth_header != self.authorization:
            return Response("Unauthorized", status_code=401)
        return await call_next(request)
