import json
from pathlib import Path
from typing import Any, Protocol, override

import anyio
from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import filesystem
from inspect_scout._display._display import display
from starlette.status import (
    HTTP_403_FORBIDDEN,
)


class AccessPolicy(Protocol):
    async def can_read(self, request: Request, file: str) -> bool: ...

    async def can_delete(self, request: Request, file: str) -> bool: ...

    async def can_list(self, request: Request, dir: str) -> bool: ...


class OnlyLogDirAccessPolicy(AccessPolicy):
    def __init__(self, log_dir: str) -> None:
        super().__init__()
        self.log_dir = log_dir

    def _validate_log_dir(self, file: str) -> bool:
        return file.startswith(self.log_dir) and ".." not in file

    async def can_read(self, request: Request, file: str) -> bool:
        return self._validate_log_dir(file)

    async def can_delete(self, request: Request, file: str) -> bool:
        return self._validate_log_dir(file)

    async def can_list(self, request: Request, dir: str) -> bool:
        return self._validate_log_dir(dir)


def view_server(
    results_dir: str,
    host: str,
    port: int,
    authorization: str | None = None,
    fs_options: dict[str, Any] = {},
) -> None:
    # get filesystem and resolve scan_dir to full path
    fs = filesystem(results_dir)
    if not fs.exists(results_dir):
        fs.mkdir(results_dir, True)
    results_dir = fs.info(results_dir).name

    api = view_server_app(
        access_policy=OnlyLogDirAccessPolicy(results_dir),
        results_dir=results_dir,
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


class InspectJsonResponse(JSONResponse):
    """Like the standard starlette JSON, but allows NaN."""

    @override
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


def view_server_app(
    access_policy: AccessPolicy | None = None,
    results_dir: str | None = None,
) -> "FastAPI":
    app = FastAPI()

    async def _validate_read(request: Request, file: str) -> None:
        if access_policy is not None:
            if not await access_policy.can_read(request, file):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    async def _validate_delete(request: Request, file: str) -> None:
        if access_policy is not None:
            if not await access_policy.can_delete(request, file):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    async def _validate_list(request: Request, file: str) -> None:
        if access_policy is not None:
            if not await access_policy.can_list(request, file):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

    @app.get("/hello")
    async def hello(
        request: Request,
        header_only: str | None = Query(None, alias="header-only"),
    ) -> Response:
        return InspectJsonResponse(
            content={"hello": "world"}, media_type="application/json"
        )

    return app
