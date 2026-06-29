import click
from typing_extensions import Unpack

from inspect_scout._scan import scan_complete

from .common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_common_log_level,
)
from .scan import scan_command


@scan_command.command("complete")
@click.argument("scan_location", nargs=1)
@common_options
@click.pass_context
def scan_complete_command(
    ctx: click.Context,
    scan_location: str,
    **common: Unpack[CommonOptions],
) -> None:
    """Complete a scan which is incomplete due to errors (errors are not retried)."""
    # Process common options
    process_common_options(common)

    scan_complete(scan_location, log_level=resolve_common_log_level(ctx, common))
