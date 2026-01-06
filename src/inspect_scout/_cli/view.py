import click
from inspect_ai._util.path import chdir
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_view_authorization,
    view_options,
)

from .._view.view import view


@click.command("view")
@click.argument("directory", required=False, default=None)
@click.option(
    "--workbench",
    is_flag=True,
    default=False,
    help="Launch workbench mode.",
)
@click.option(
    "--results",
    type=str,
    default=None,
    hidden=True,  # Deprecated
    envvar="SCOUT_SCAN_RESULTS",
)
@view_options
@common_options
def view_command(
    directory: str | None,
    workbench: bool,
    results: str | None,
    host: str,
    port: int,
    browser: bool | None,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    process_common_options(common)

    # --results forces non-workbench mode (deprecated option)
    if results is not None:
        workbench = False

    # Validate: directory argument requires workbench mode
    if directory is not None and not workbench:
        raise click.UsageError("Directory argument requires --workbench flag")

    if workbench:
        # Workbench mode: change to project dir, browser defaults ON
        project_dir = directory or "."
        effective_browser = browser if browser is not None else True
        with chdir(project_dir):
            view(
                results_dir=None,
                host=host,
                port=port,
                browser=effective_browser,
                authorization=resolve_view_authorization(),
                workbench=True,
                log_level=common["log_level"],
            )
    else:
        # Non-workbench mode: browser defaults OFF
        effective_browser = browser if browser is not None else False
        view(
            results,
            host=host,
            port=port,
            browser=effective_browser,
            authorization=resolve_view_authorization(),
            log_level=common["log_level"],
        )
