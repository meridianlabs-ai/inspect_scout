import click
from typing_extensions import Unpack

from inspect_scout._display._display import display
from inspect_scout._init import top_level_async_init
from inspect_scout._project._project import read_project
from inspect_scout._scanresults import scan_status

from .common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_common_log_level,
)
from .scan import scan_command


@scan_command.command("status")
@click.argument("scan_location", nargs=1)
@common_options
@click.pass_context
def scan_status_command(
    ctx: click.Context,
    scan_location: str,
    **common: Unpack[CommonOptions],
) -> None:
    """Print the status of a scan."""
    # Process common options
    process_common_options(common)

    # initialize logging with the resolved log level
    top_level_async_init(
        resolve_common_log_level(ctx, common) or read_project().log_level
    )

    status = scan_status(scan_location)
    display().scan_status(status)
