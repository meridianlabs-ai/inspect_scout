import os

import click
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
)
from inspect_scout._util.constants import DEFAULT_SERVER_HOST

from .._view.view import view


@click.command("view")
@click.option(
    "--results",
    type=str,
    default="./scans",
    help="Location to read scan results from.",
    envvar="SCOUT_SCAN_RESULTS",
)
@click.option(
    "--host",
    default=DEFAULT_SERVER_HOST,
    help="Tcp/Ip host",
)
@click.option(
    "--port",
    type=int,
    default=7576,
    help="Port to use for the view server.",
    envvar="SCOUT_VIEW_PORT",
)
@common_options
def view_command(
    results: str,
    host: str,
    port: int,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    # commonm options
    process_common_options(common)

    # resolve optional auth token
    INSPECT_VIEW_AUTHORIZATION_TOKEN = "INSPECT_VIEW_AUTHORIZATION_TOKEN"
    authorization = os.environ.get(INSPECT_VIEW_AUTHORIZATION_TOKEN, None)
    if authorization:
        del os.environ[INSPECT_VIEW_AUTHORIZATION_TOKEN]
        os.unsetenv(INSPECT_VIEW_AUTHORIZATION_TOKEN)

    # run view
    view(
        results,
        host=host,
        port=port,
        authorization=authorization,
        log_level=common["log_level"],
    )
