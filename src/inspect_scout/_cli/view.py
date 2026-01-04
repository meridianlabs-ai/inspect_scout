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


@click.command("view")
@click.option(
    "--results",
    type=str,
    default=None,
    help="Location to read scan results from. Defaults to project results or './scans'.",
    envvar="SCOUT_SCAN_RESULTS",
)
@view_options
@common_options
def view_command(
    results: str | None,
    host: str,
    port: int,
    browser: bool | None,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    process_common_options(common)

    view(
        results,
        host=host,
        port=port,
        browser=browser if browser is not None else False,
        authorization=resolve_view_authorization(),
        log_level=common["log_level"],
    )
