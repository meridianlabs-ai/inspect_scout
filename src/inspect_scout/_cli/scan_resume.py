import click
from typing_extensions import Unpack

from inspect_scout._scan import scan_resume

from .common import CommonOptions, common_options, process_common_options


@click.command("resume")
@click.argument("scan_dir", nargs=1)
@common_options
def scan_resume_command(
    scan_dir: str,
    **common: Unpack[CommonOptions],
) -> None:
    """Resume a scan which is incomplete due to interruption or errors (errors are retried)."""
    # Process common options
    process_common_options(common)

    scan_resume(scan_dir)
