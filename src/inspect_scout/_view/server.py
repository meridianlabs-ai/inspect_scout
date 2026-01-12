import os
from pathlib import Path
from typing import Any, Literal

import anyio
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import filesystem
from inspect_ai._view.fastapi_server import (
    OnlyDirAccessPolicy,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import Scope

from .._display._display import display
from ._api_v1 import v1_api_app
from ._api_v2 import v2_api_app


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that prevents caching of JS files during development."""

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)

        # We have seen sporadic caching of the core JS file in safari though I
        # wasn't able to consistently reproduce it. To be safe, disable caching
        # for all JS files for the time being
        if str(full_path).endswith(".js"):
            response.headers["cache-control"] = "no-cache, no-store, must-revalidate"
            response.headers["pragma"] = "no-cache"
            response.headers["expires"] = "0"

        return response


def view_server(
    scans: str,
    host: str,
    port: int,
    mode: Literal["default", "scans"] = "default",
    authorization: str | None = None,
    fs_options: dict[str, Any] | None = None,
) -> None:
    # get filesystem and resolve scan_dir to full path
    fs = filesystem(scans, fs_options=fs_options or {})
    if not fs.exists(scans):
        fs.mkdir(scans, True)
    scans = fs.info(scans).name

    access_policy = OnlyDirAccessPolicy(scans) if not authorization else None

    v1_api = v1_api_app(
        access_policy=access_policy,
        results_dir=scans,
        fs=fs,
    )

    v2_api = v2_api_app(
        access_policy=access_policy,
        results_dir=scans,
        fs=fs,
    )

    if authorization:
        v1_api.add_middleware(AuthorizationMiddleware, authorization=authorization)
        v2_api.add_middleware(AuthorizationMiddleware, authorization=authorization)

    app = FastAPI()
    # NOTE: order matters - Starlette matches mounts in order
    # /api/v2 must come before /api or v2 requests would route to v1
    app.mount("/api/v2", v2_api)
    app.mount("/api", v1_api)

    dist = Path(__file__).parent / "www" / "dist"
    app.mount(
        "/", NoCacheStaticFiles(directory=dist.as_posix(), html=True), name="static"
    )

    # run app
    display().print("Scout View")

    async def run_server() -> None:
        config = uvicorn.Config(app, host=host, port=port, log_config=None)
        server = uvicorn.Server(config)

        async def announce_when_ready() -> None:
            while not server.started:
                await anyio.sleep(0.05)
            # Print this for compatibility with the Inspect VSCode plugin:
            url = view_url(host, port, mode)
            display().print(
                f"======== Running on {url} ========\n(Press CTRL+C to quit)"
            )

        async with anyio.create_task_group() as tg:
            tg.start_soon(announce_when_ready)
            await server.serve()

    anyio.run(run_server)


def view_url(host: str, port: int, mode: Literal["default", "scans"]) -> str:
    """Build the view server URL."""
    mode_param = f"?mode={mode}" if mode != "default" else ""
    return f"http://{host}:{port}{mode_param}"


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
