import click
from typing_extensions import Unpack

from inspect_scout._scan import scan_resume

from .common import CommonOptions, common_options, process_common_options
from .scan import scan_command


@scan_command.command("resume")
@click.argument("scan_location", nargs=1)
@common_options
@click.pass_context
def scan_resume_command(
    ctx: click.Context,
    scan_location: str,
    **common: Unpack[CommonOptions],
) -> None:
    """Resume a scan which is incomplete due to interruption or errors (errors are retried)."""
    # Process common options
    process_common_options(common)

    status = scan_resume(scan_location, fail_on_error=common["fail_on_error"])

    # exit non-zero when the user asked us to fail on error and the scan
    # didn't complete cleanly
    if common["fail_on_error"] and not status.complete:
        ctx.exit(1)
