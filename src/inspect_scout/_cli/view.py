from logging import getLogger
from typing import Literal

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
    "--mode",
    type=click.Choice(("default", "scans")),
    default="default",
    help="View display mode.",
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
    transcripts: str | None,
    scans: str | None,
    mode: Literal["default", "scans"],
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

    view(
        project_dir=project_dir,
        transcripts=transcripts,
        scans=scans,
        host=host,
        port=port,
        browser=browser is True,
        mode=mode,
        authorization=resolve_view_authorization(),
        log_level=common["log_level"],
    )
