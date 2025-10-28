from pathlib import Path
from typing import Any, TypeVar, override

import anyio
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import FileSystem, filesystem
from inspect_ai._util.json import to_json_safe
from inspect_ai._view.fastapi_server import (
    AccessPolicy,
    InspectJsonResponse,
    OnlyDirAccessPolicy,
)
from inspect_scout._display._display import display
from inspect_scout._scanlist import scan_list_async
from inspect_scout._scanresults import scan_results
from starlette.status import HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR
from upath import UPath


class InspectPydanticJSONResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return to_json_safe(content)


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
        access_policy=OnlyDirAccessPolicy(results_dir), results_dir=results_dir, fs=fs
    )

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
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
    fs: FileSystem | None = None,
) -> "FastAPI":
    app = FastAPI()

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

    @app.get("/hello")
    async def hello(
        request: Request,
        header_only: str | None = Query(None, alias="header-only"),
    ) -> Response:
        return InspectJsonResponse(
            content={"hello": "world"}, media_type="application/json"
        )

    @app.get("/scans")
    async def scans(request: Request) -> Response:
        validated_results_dir = _ensure_not_none(results_dir, "results_dir is required")
        await _validate_list(request, validated_results_dir)
        scans = await scan_list_async(validated_results_dir)

        return InspectPydanticJSONResponse(
            content={"results_dir": validated_results_dir, "scans": scans},
            media_type="application/json",
        )

    # location is expected to be a path relative to the results_dir
    @app.get("/scan/{location:path}")
    async def scan(request: Request, location: str) -> Response:
        validated_results_dir = _ensure_not_none(results_dir, "results_dir is required")

        # convert to absolute path
        results_path = UPath(validated_results_dir)
        location_path = UPath(location)
        scan_path = results_path / location_path

        # validate
        await _validate_read(request, scan_path)

        # read the results and return
        result = scan_results(str(scan_path))
        return InspectPydanticJSONResponse(
            content=result, media_type="application/json"
        )

    return app
