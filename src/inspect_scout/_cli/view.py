from logging import getLogger

import click
from inspect_ai._util.logger import warn_once
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
@click.argument("project_dir", required=False, default=None)
@click.option(
    "--workbench",
    is_flag=True,
    default=False,
    help="Launch workbench mode.",
)
@click.option(
    "-T",
    "--transcripts",
    type=str,
    default=None,
    help="Location of transcripts to view.",
    envvar="SCOUT_SCAN_TRANSCRIPTS",
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
    project_dir: str | None,
    workbench: bool,
    transcripts: str | None,
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

    # Validate: directory argument requires workbench mode
    if project_dir is not None and not workbench:
        raise click.UsageError("project_dir argument requires --workbench flag")

    if workbench:
        # Workbench mode: change to project dir, browser defaults ON
        effective_browser = browser if browser is not None else True
        view(
            project_dir=project_dir,
            transcripts=transcripts,
            scans=scans,
            host=host,
            port=port,
            browser=effective_browser,
            authorization=resolve_view_authorization(),
            workbench=True,
            log_level=common["log_level"],
        )
    else:
        effective_browser = browser if browser is not None else False
        view(
            project_dir=project_dir,
            transcripts=transcripts,
            scans=scans,
            host=host,
            port=port,
            browser=effective_browser,
            authorization=resolve_view_authorization(),
            log_level=common["log_level"],
        )
