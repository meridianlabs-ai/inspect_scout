from pathlib import Path
from typing import Any, Literal

import anyio
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import filesystem
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from inspect_scout._lfs import LFSError, resolve_lfs_directory
from inspect_scout._util.appdirs import scout_cache_dir
from inspect_scout._util.constants import (
    DEFAULT_SCANS_DIR,
    DEFAULT_SERVER_HOST,
    DEFAULT_VIEW_PORT,
)
from inspect_scout._view.types import ViewConfig

from .._display._display import display
from ._api_v2 import v2_api_app


def view_server(
    config: ViewConfig | None = None,
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
    mode: Literal["default", "scans"] = "default",
    authorization: str | None = None,
    fs_options: dict[str, Any] | None = None,
) -> None:
    # get filesystem and resolve scan_dir to full path
    config = config or ViewConfig()
    scans = config.scans_cli or config.project.scans or DEFAULT_SCANS_DIR
    fs = filesystem(scans, fs_options=fs_options or {})
    if not fs.exists(scans):
        fs.mkdir(scans, True)
    scans = fs.info(scans).name

    v2_api = v2_api_app(view_config=config)

    if authorization:
        v2_api.add_middleware(AuthorizationMiddleware, authorization=authorization)

    app = FastAPI()
    app.mount("/api/v2", v2_api)

    try:
        dist = resolve_lfs_directory(
            Path(__file__).parent / "dist",
            cache_dir=scout_cache_dir("dist"),
            repo_url="https://github.com/meridianlabs-ai/inspect_scout.git",
        )
    except LFSError as e:
        raise RuntimeError(
            f"{e}\n"
            "To fix this, either:\n"
            "  1. Install Git LFS: brew install git-lfs && git lfs install && git lfs pull\n"
            "  2. Check your network connection\n"
            "  3. Build locally: cd src/inspect_scout/_view/frontend && pnpm build"
        ) from e
    app.mount("/", StaticFiles(directory=dist.as_posix(), html=True), name="static")

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
