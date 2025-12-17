import base64
import io
from dataclasses import dataclass
from typing import Iterable, Literal, TypeVar

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as pa_ipc
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from inspect_ai._util.file import FileSystem
from inspect_ai._view.fastapi_server import (
    AccessPolicy,
    FileMappingPolicy,
)
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from upath import UPath

from .._recorder.recorder import Status
from .._recorder.summary import Summary
from .._scanlist import scan_list_async
from .._scanner.result import Error
from .._scanresults import (
    remove_scan_results,
    scan_results_arrow_async,
    scan_results_df_async,
)
from .._scanspec import ScanSpec
from ._server_common import InspectPydanticJSONResponse


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


def v1_api_app(
    mapping_policy: FileMappingPolicy | None = None,
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
    streaming_batch_size: int = 1024,
) -> FastAPI:
    """Create V1 API FastAPI app (deprecated)."""
    app = FastAPI(
        title="Inspect Scout Viewer API (Deprecated)",
        description="⚠️ **DEPRECATED**: This API is deprecated. Use /api/v2 instead.",
    )

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

    @app.get("/scans", deprecated=True)
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

    @app.get("/scanner_df_input/{scan:path}", deprecated=True)
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

    @app.get("/scanner_df/{scan:path}", deprecated=True)
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

    @app.get("/scan/{scan:path}", deprecated=True)
    async def scan(
        request: Request,
        scan: str,
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

        # clear the transcript data
        if result.spec.transcripts:
            result.spec.transcripts = result.spec.transcripts.model_copy(
                update={"data": None}
            )

        # create the status
        status = Status(
            complete=result.complete,
            spec=result.spec,
            location=await _unmap_file(request, result.location),
            summary=result.summary,
            errors=result.errors,
        )

        return InspectPydanticJSONResponse(
            content=status, media_type="application/json"
        )

    @app.get("/scan-delete/{scan:path}", deprecated=True)
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
