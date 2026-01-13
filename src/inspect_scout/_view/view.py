import logging
import webbrowser
from typing import Any, Literal

from inspect_ai._util.path import chdir
from inspect_ai._view.view import view_acquire_port

from inspect_scout._project._project import read_project
from inspect_scout._scan import top_level_async_init
from inspect_scout._util.appdirs import scout_data_dir
from inspect_scout._util.constants import DEFAULT_SERVER_HOST, DEFAULT_VIEW_PORT
from inspect_scout._view.server import view_server, view_url
from inspect_scout._view.types import ViewConfig

logger = logging.getLogger(__name__)


def view(
    project_dir: str | None = None,
    transcripts: str | None = None,
    scans: str | None = None,
    mode: Literal["default", "scans"] = "default",
    host: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_VIEW_PORT,
    browser: bool = False,
    authorization: str | None = None,
    log_level: str | None = None,
    fs_options: dict[str, Any] | None = None,
) -> None:
    with chdir(project_dir or "."):
        # top level init
        project = read_project()
        top_level_async_init(log_level, project=project)

        # acquire the port
        view_acquire_port(scout_data_dir("view"), port)

        # open browser if requested
        if browser:
            webbrowser.open(view_url(host, port, mode))

        # start the server
        view_server(
            config=ViewConfig(
                project=project,
                transcripts=transcripts,
                scans=scans,
            ),
            host=host,
            port=port,
            mode=mode,
            authorization=authorization,
            fs_options=fs_options,
        )
