from pathlib import Path
from typing import Any

import anyio
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import filesystem
from inspect_ai._view.fastapi_server import (
    OnlyDirAccessPolicy,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .._display._display import display
from ._api_v1 import v1_api_app
from ._api_v2 import v2_api_app


def view_server(
    scans: str,
    host: str,
    port: int,
    authorization: str | None = None,
    workbench: bool = False,
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
    app.mount("/", StaticFiles(directory=dist.as_posix(), html=True), name="static")

    # run app
    title = "Scout" if workbench else "Scout View"
    display().print(f"{title}: {scans}")

    async def run_server() -> None:
        config = uvicorn.Config(app, host=host, port=port, log_config=None)
        server = uvicorn.Server(config)

        async def announce_when_ready() -> None:
            while not server.started:
                await anyio.sleep(0.05)
            # Print this for compatibility with the Inspect VSCode plugin:
            url = view_url(host, port, workbench)
            display().print(
                f"======== Running on {url} ========\n(Press CTRL+C to quit)"
            )

        async with anyio.create_task_group() as tg:
            tg.start_soon(announce_when_ready)
            await server.serve()

    anyio.run(run_server)


def view_url(host: str, port: int, workbench: bool = False) -> str:
    """Build the view server URL."""
    workbench_param = "?workbench=1" if workbench else ""
    return f"http://{host}:{port}{workbench_param}"


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
