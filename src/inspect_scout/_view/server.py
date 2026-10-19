import logging
import os
import secrets
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import anyio
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from inspect_ai._lfs import LFSError, resolve_lfs_directory
from inspect_ai._util.event_loop_monitor import event_loop_monitor
from inspect_ai._util.file import filesystem
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import HTMLResponse
from starlette.types import ASGIApp, Scope

from inspect_scout._util.appdirs import scout_cache_dir
from inspect_scout._util.constants import (
    DEFAULT_SCANS_DIR,
    DEFAULT_SERVER_HOST,
    DEFAULT_VIEW_PORT,
)
from inspect_scout._view.network import (
    BrowserOriginMiddleware,
    HostValidationMiddleware,
    ViewerNetworkPolicy,
    resolve_viewer_network_policy,
    unsafe_network_warning,
)
from inspect_scout._view.notify import notify_lifespan
from inspect_scout._view.types import ViewConfig

from .._display._display import display
from ._api_v2 import v2_api_app
from ._csp import (
    SecurityHeadersMiddleware,
    inline_script_source,
    read_content_security_policy,
)

_IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
_DIST_DIR = Path(__file__).parent / "dist"
_REPO_URL = "https://github.com/meridianlabs-ai/inspect_scout.git"

logger = logging.getLogger(__name__)


def _base_path_script(root_path: str) -> str:
    """The inline script that tells the frontend its base path behind a proxy."""
    return (
        f"window.__SCOUT_BASE_PATH__={root_path!r};window.__SCOUT_DISABLE_SSE__=true;"
    )


class _ScoutStaticFiles(StaticFiles):
    """StaticFiles with runtime config injection and cache headers.

    Hashed assets under ``assets/`` are served with immutable cache headers.
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
            script = f"<script>{_base_path_script(root_path)}</script>"
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
        if "/assets/" in str(full_path):
            response.headers["cache-control"] = _IMMUTABLE_CACHE
        else:
            response.headers["cache-control"] = "no-cache"
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
    trusted_origins: tuple[str, ...] = (),
    trusted_hosts: tuple[str, ...] = (),
    unsafe_allow_unauthenticated: bool = False,
    network_policy: ViewerNetworkPolicy | None = None,
) -> None:
    network_policy = network_policy or resolve_viewer_network_policy(
        bind_host=host,
        port=port,
        trusted_hosts=trusted_hosts,
        trusted_origins=trusted_origins,
        authorization=authorization,
        unsafe_allow_unauthenticated=unsafe_allow_unauthenticated,
        root_path=root_path,
    )
    root_path = _normalize_root_path(root_path)

    # get filesystem and resolve scan_dir to full path
    config = config or ViewConfig()
    scans = config.scans_cli or config.project.scans or DEFAULT_SCANS_DIR
    fs = filesystem(scans, fs_options=fs_options or {})
    if not fs.exists(scans):
        fs.mkdir(scans, True)
    scans = fs.info(scans).name

    # ensure we've resolved the dist directory
    directory = _resolve_dist_directory()

    app = standalone_view_app(
        view_config=config,
        network_policy=network_policy,
        root_path=root_path,
        directory=directory,
    )

    # run app
    display().print("Scout View")
    warning = unsafe_network_warning(network_policy)
    if warning:
        logger.warning(warning)

    async def run_server() -> None:
        config = uvicorn.Config(
            app,
            host=network_policy.bind_host,
            port=network_policy.port,
            root_path=root_path,
            log_config=None,
        )
        server = uvicorn.Server(config)

        async def announce_when_ready() -> None:
            while not server.started:
                await anyio.sleep(0.05)
            # Print this for compatibility with the Inspect VSCode plugin:
            url = view_url(network_policy.bind_host, network_policy.port, mode)
            display().print(
                f"======== Running on {url} ========\n(Press CTRL+C to quit)"
            )

        async with anyio.create_task_group() as tg:
            tg.start_soon(announce_when_ready)
            await server.serve()

    anyio.run(run_server)


def standalone_view_app(
    *,
    view_config: ViewConfig | None,
    network_policy: ViewerNetworkPolicy,
    root_path: str = "",
    directory: Path | None = None,
) -> ASGIApp:
    root_path = _normalize_root_path(root_path)
    directory = directory or _resolve_dist_directory()
    return _view_app(
        v2_api_app(view_config=view_config, dist_path=directory),
        directory,
        root_path,
        network_policy,
    )


def _view_app(
    v2_api: FastAPI,
    directory: Path,
    root_path: str,
    network_policy: ViewerNetworkPolicy,
) -> ASGIApp:
    """The view server's app: the API under `/api/v2` and the viewer at `/`.

    The viewer's files are served with the dist's Content-Security-Policy,
    which also allows the base-path script the server injects behind a proxy.
    Every response forbids framing.
    """
    content_security_policy = read_content_security_policy(
        directory,
        extra_script_sources=(
            (inline_script_source(_base_path_script(root_path)),) if root_path else ()
        ),
    )

    app = FastAPI(lifespan=notify_lifespan)

    if os.getenv("SCOUT_VIEW_EVENT_LOOP_MONITOR", "false").lower() in (
        "true",
        "1",
        "yes",
    ):

        async def log_and_monitor(
            request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            method, path = request.method, request.url.path
            print(f"-> {method} {path}", flush=True)
            async with event_loop_monitor():
                response = await call_next(request)
            print(f"<- {method} {path} {response.status_code}", flush=True)
            return response

        app.middleware("http")(log_and_monitor)

    app.mount("/api/v2", BrowserOriginMiddleware(v2_api, network_policy))

    app.mount(
        "/",
        _ScoutStaticFiles(
            directory=directory.as_posix(),
            html=True,
            root_path=root_path,
        ),
        name="static",
    )

    if network_policy.authorization:
        app.add_middleware(
            AuthorizationMiddleware,
            authorization=network_policy.authorization,
        )

    protected_app: ASGIApp = HostValidationMiddleware(app, network_policy)
    # Wraps the whole app so responses from FastAPI's error handler and the
    # host check get the headers too.
    return SecurityHeadersMiddleware(
        protected_app,
        content_security_policy=content_security_policy,
        viewer_policy_exempt_mounts=("/api/v2",),
    )


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
        if auth_header is None or not secrets.compare_digest(
            auth_header.encode(), self.authorization.encode()
        ):
            return Response("Unauthorized", status_code=401)
        return await call_next(request)


def _resolve_dist_directory() -> Path:
    """Resolve the frontend dist directory, downloading LFS objects if needed.

    To test without Git LFS (simulates a user without LFS installed)::

        # Enter test state — discard LFS content, leave pointer stubs
        git lfs uninstall
        GIT_LFS_SKIP_SMUDGE=1 git rm --cached -r src/inspect_scout/_view/dist
        GIT_LFS_SKIP_SMUDGE=1 git reset --hard
        # WARNING: git reset --hard discards uncommitted changes

        # Verify — LFS files should be ~130-byte pointer stubs
        head -1 src/inspect_scout/_view/dist/index.html
        # Expected: "version https://git-lfs.github.com/spec/v1"

        # Restore
        git lfs install
        git lfs pull
    """
    # The LFS module logs download progress at INFO, but scout's default log
    # display level is WARNING. Add a temporary handler so users see download
    # activity during startup.
    lfs_logger = logging.getLogger("inspect_ai._lfs")
    prev_level = lfs_logger.level
    lfs_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    lfs_logger.addHandler(handler)
    try:
        result = resolve_lfs_directory(
            _DIST_DIR,
            cache_dir=scout_cache_dir("dist"),
            repo_url=_REPO_URL,
        )
        if result != _DIST_DIR:
            display().print(f"Serving static data from {result}")

        return result
    except LFSError as e:
        raise RuntimeError(
            f"{e}\n"
            "To fix this, either:\n"
            "  1. Install Git LFS: brew install git-lfs && git lfs install && git lfs pull\n"
            "  2. Build locally: cd src/inspect_scout/_view/ts-mono && pnpm build"
        ) from e
    finally:
        lfs_logger.removeHandler(handler)
        lfs_logger.setLevel(prev_level)
