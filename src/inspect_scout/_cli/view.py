from logging import getLogger
from typing import Literal

import click
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
)
@click.option(
    "--scans",
    type=str,
    default=None,
    help="Location of scan results to view.",
)
@click.option(
    "--mode",
    type=click.Choice(("default", "scans")),
    default="default",
    help="View display mode.",
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
