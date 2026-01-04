"""Scout viewer launcher."""

from inspect_ai._util.path import chdir

from inspect_scout._cli.common import resolve_view_authorization

from .view import view


def scout_workbench(
    project_dir: str | None = None,
    host: str = "127.0.0.1",
    port: int = 7576,
    browser: bool | None = None,
    log_level: str = "warning",
) -> None:
    """Launch the scout viewer for a project.

    Args:
        project_dir: Project directory containing scout.yaml. Defaults to cwd.
        host: TCP/IP host for the view server.
        port: Port for the view server.
        browser: Open in web browser. Defaults to True for workbench mode.
        log_level: Log level for the server.
    """
    # Default to current directory
    if project_dir is None:
        project_dir = "."

    # Change to project directory for duration of view server
    with chdir(project_dir):
        view(
            results_dir=None,
            host=host,
            port=port,
            browser=browser if browser is not None else True,
            authorization=resolve_view_authorization(),
            workbench=True,
            log_level=log_level,
        )
