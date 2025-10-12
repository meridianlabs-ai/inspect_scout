import click
from typing_extensions import Unpack

from inspect_scout._scan import scan_complete

from .common import CommonOptions, common_options, process_common_options


@click.command("complete")
@click.argument("scan_dir", nargs=1)
@common_options
def scan_complete_command(
    scan_dir: str,
    **common: Unpack[CommonOptions],
) -> None:
    """Complete a scan which is incomplete due to errors (errors are not retried)."""
    # Process common options
    process_common_options(common)

    scan_complete(scan_dir)
