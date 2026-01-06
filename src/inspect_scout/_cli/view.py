from logging import getLogger

import click
from inspect_ai._util.logger import warn_once
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

logger = getLogger(__name__)


@click.command("view")
@click.argument("directory", required=False, default=None)
@click.option(
    "--workbench",
    is_flag=True,
    default=False,
    help="Launch workbench mode.",
)
@click.option(
    "--scans",
    type=str,
    default=None,
    help="Location of scan results to view.",
    envvar="SCOUT_SCAN_SCANS",
)
@click.option(
    "--results",
    type=str,
    default=None,
    hidden=True,
    envvar="SCOUT_SCAN_RESULTS",
)
@view_options
@common_options
def view_command(
    directory: str | None,
    workbench: bool,
    scans: str | None,
    results: str | None,
    host: str,
    port: int,
    browser: bool | None,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    process_common_options(common)

    # Handle deprecated --results option
    if results is not None:
        warn_once(
            logger, "CLI option '--results' is deprecated, please use '--scans' instead"
        )
        if scans is not None:
            raise click.UsageError("Cannot specify both --scans and --results")
        scans = results

    # --scans forces non-workbench mode
    if scans is not None:
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
                scans=None,
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
            scans,
            host=host,
            port=port,
            browser=effective_browser,
            authorization=resolve_view_authorization(),
            log_level=common["log_level"],
        )
