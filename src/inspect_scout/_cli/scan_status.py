import click
from typing_extensions import Unpack

from inspect_scout._display._display import display
from inspect_scout._scanresults import scan_status

from .common import CommonOptions, common_options, process_common_options
from .scan import scan_command


@scan_command.command("status")
@click.argument("scan_location", nargs=1)
@common_options
def scan_status_command(
    scan_location: str,
    **common: Unpack[CommonOptions],
) -> None:
    """Print the status of a scan."""
    # Process common options
    process_common_options(common)

    status = scan_status(scan_location)
    display().scan_status(status)
