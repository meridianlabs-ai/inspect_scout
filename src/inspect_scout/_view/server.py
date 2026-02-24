import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import anyio
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from inspect_ai._util.file import filesystem
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import HTMLResponse
from starlette.types import Scope

from inspect_scout._util.constants import (
    DEFAULT_SCANS_DIR,
    DEFAULT_SERVER_HOST,
    DEFAULT_VIEW_PORT,
)
from inspect_scout._view.types import ViewConfig

from .._display._display import display
from ._api_v2 import v2_api_app


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that prevents caching of JS files during development.

    When root_path is set, injects a script tag into index.html so the
    frontend knows the base path for API requests behind a reverse proxy.
    """

    def __init__(
        self,
        *args: Any,
        root_path: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._index_html_override: str | None = None
        if root_path:
            index_path = Path(str(self.directory)) / "index.html"
            html = index_path.read_text()
            script = (
                "<script>"
                f"window.__SCOUT_BASE_PATH__={root_path!r};"
                "window.__SCOUT_DISABLE_SSE__=true;"
                "</script>"
            )
            self._index_html_override = html.replace("</head>", f"{script}</head>", 1)

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        if (
            self._index_html_override is not None
            and Path(str(full_path)).name == "index.html"
        ):
            return HTMLResponse(
                content=self._index_html_override,
                status_code=status_code,
            )

        response = super().file_response(full_path, stat_result, scope, status_code)

        # We have seen sporadic caching of the core JS file in safari though I
        # wasn't able to consistently reproduce it. To be safe, disable caching
        # for all JS files for the time being
        if str(full_path).endswith(".js"):
            response.headers["cache-control"] = "no-cache, no-store, must-revalidate"
            response.headers["pragma"] = "no-cache"
            response.headers["expires"] = "0"

        return response


def _normalize_root_path(root_path: str) -> str:
    """Extract path from a full URL and strip trailing slashes.

    If UVICORN_ROOT_PATH is set to a full URL like
    ``https://host/s/session/p/proxy/``, normalize ASGI root_path to
    just the path portion (``/s/session/p/proxy``).
    """
    if not root_path:
        return ""
    parsed = urlparse(root_path)
    if parsed.scheme:
        root_path = parsed.path
    return root_path.rstrip("/")


def view_server(
    config: ViewConfig | None = None,
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
    mode: Literal["default", "scans"] = "default",
    authorization: str | None = None,
    fs_options: dict[str, Any] | None = None,
    root_path: str = "",
) -> None:
    root_path = _normalize_root_path(root_path)

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

    dist = Path(__file__).parent / "www" / "dist"
    app.mount(
        "/",
        NoCacheStaticFiles(directory=dist.as_posix(), html=True, root_path=root_path),
        name="static",
    )

    # run app
    display().print("Scout View")

    async def run_server() -> None:
        config = uvicorn.Config(
            app, host=host, port=port, root_path=root_path, log_config=None
        )
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
