import logging
import webbrowser
from typing import Any

from inspect_ai._util.path import chdir
from inspect_ai._view.view import view_acquire_port

from inspect_scout._project import project
from inspect_scout._scan import top_level_async_init
from inspect_scout._util.appdirs import scout_data_dir
from inspect_scout._util.constants import DEFAULT_SCANS_DIR
from inspect_scout._view.server import view_server, view_url

logger = logging.getLogger(__name__)

DEFAULT_VIEW_PORT = 7576
DEFAULT_SERVER_HOST = "127.0.0.1"


def view(
    project_dir: str | None = None,
    transcripts: str | None = None,
    scans: str | None = None,
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
    browser: bool = False,
    authorization: str | None = None,
    log_level: str | None = None,
    workbench: bool = False,
    fs_options: dict[str, Any] | None = None,
) -> None:
    with chdir(project_dir or "."):
        # top level init
        top_level_async_init(log_level, transcripts=transcripts, scans=scans)

        # acquire the port
        view_acquire_port(scout_data_dir("view"), port)

        # open browser if requested
        if browser:
            webbrowser.open(view_url(host, port, workbench))

        # start the server
        view_server(
            scans=project().scans or DEFAULT_SCANS_DIR,
            host=host,
            port=port,
            authorization=authorization,
            workbench=workbench,
            fs_options=fs_options,
        )
