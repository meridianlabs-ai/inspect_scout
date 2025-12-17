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
from ._api_v1 import v1_api_router
from ._api_v2 import v2_api_router


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

    access_policy = OnlyDirAccessPolicy(results_dir) if not authorization else None

    v1_router = v1_api_router(
        access_policy=access_policy,
        results_dir=results_dir,
        fs=fs,
    )

    v2_router = v2_api_router(
        access_policy=access_policy,
        results_dir=results_dir,
        fs=fs,
    )

    app = FastAPI()

    if authorization:
        app.add_middleware(AuthorizationMiddleware, authorization=authorization)

    # v2 has prefix="/v2" built-in, so both mount at /api
    app.include_router(v2_router, prefix="/api")
    app.include_router(v1_router, prefix="/api")

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
