import logging
from typing import Any

from inspect_ai._view.view import view_acquire_port

from inspect_scout._scan import top_level_async_init
from inspect_scout._util.appdirs import scout_data_dir
from inspect_scout._view.server import view_server

logger = logging.getLogger(__name__)

DEFAULT_VIEW_PORT = 7576
DEFAULT_SERVER_HOST = "127.0.0.1"


def view(
    results_dir: str,
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
    authorization: str | None = None,
    log_level: str | None = None,
    fs_options: dict[str, Any] | None = None,
) -> None:
    top_level_async_init(log_level)

    # acquire the port
    view_acquire_port(scout_data_dir("view"), port)

    # start the server
    view_server(
        results_dir=results_dir,
        host=host,
        port=port,
        authorization=authorization,
        fs_options=fs_options,
    )
