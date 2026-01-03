import logging
from typing import Any

from inspect_ai._view.view import view_acquire_port

from inspect_scout._project import init_project, project
from inspect_scout._scan import top_level_async_init
from inspect_scout._util.appdirs import scout_data_dir
from inspect_scout._view.server import view_server

logger = logging.getLogger(__name__)

DEFAULT_VIEW_PORT = 7576
DEFAULT_SERVER_HOST = "127.0.0.1"


def view(
    results_dir: str | None = None,
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
    authorization: str | None = None,
    log_level: str | None = None,
    fs_options: dict[str, Any] | None = None,
) -> None:
    # Initialize project from cwd (always reinitialize to support multiple projects)
    init_project()

    proj = project()

    # Use project defaults for results_dir and log_level
    effective_results_dir = results_dir or proj.results or "./scans"
    effective_log_level = log_level or proj.log_level

    top_level_async_init(effective_log_level)

    # acquire the port
    view_acquire_port(scout_data_dir("view"), port)

    # start the server
    view_server(
        results_dir=effective_results_dir,
        host=host,
        port=port,
        authorization=authorization,
        fs_options=fs_options,
    )
