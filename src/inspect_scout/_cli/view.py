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
from inspect_scout._view.network import ViewerNetworkPolicyError

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
    host: str,
    port: int,
    browser: bool | None,
    root_path: str,
    trusted_origin: tuple[str, ...],
    trusted_host: tuple[str, ...],
    unsafe_allow_unauthenticated: bool,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    process_common_options(common)

    try:
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
            root_path=root_path,
            trusted_origins=trusted_origin,
            trusted_hosts=trusted_host,
            unsafe_allow_unauthenticated=unsafe_allow_unauthenticated,
        )
    except ViewerNetworkPolicyError as ex:
        raise click.UsageError(str(ex)) from ex
