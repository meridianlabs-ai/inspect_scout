import logging

from inspect_ai._view.view import view_acquire_port
from inspect_scout._util.appdirs import scout_data_dir
from inspect_scout._view.server import view_server

logger = logging.getLogger(__name__)

DEFAULT_VIEW_PORT = 7576
DEFAULT_SERVER_HOST = "127.0.0.1"


def view(
    results_dir: str,
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
) -> None:
    # acquire the port
    view_acquire_port(scout_data_dir("view"), DEFAULT_VIEW_PORT)

    # start the server
    view_server(
        results_dir=results_dir,
        host=host,
        port=port,
    )
