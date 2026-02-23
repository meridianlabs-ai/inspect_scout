import click
from typing_extensions import Unpack

from inspect_scout._scan import scan_resume

from .common import CommonOptions, common_options, process_common_options
from .scan import scan_command


@scan_command.command("resume")
@click.argument("scan_location", nargs=1)
@click.option(
    "--log-buffer",
    type=click.IntRange(min=1),
    help="Flush intermediate results to the scan directory every N transcripts. If not specified, uses the value from the original scan.",
    envvar="SCOUT_SCAN_LOG_BUFFER",
)
@common_options
def scan_resume_command(
    scan_location: str,
    log_buffer: int | None,
    **common: Unpack[CommonOptions],
) -> None:
    """Resume a scan which is incomplete due to interruption or errors (errors are retried)."""
    # Process common options
    process_common_options(common)

    scan_resume(
        scan_location,
        fail_on_error=common["fail_on_error"],
        log_buffer=log_buffer,
    )
