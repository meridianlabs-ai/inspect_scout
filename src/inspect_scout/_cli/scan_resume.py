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
    """Resume a scan which is incomplete due to interruption or errors (errors are retried).

    Resuming runs code the scan names: it imports the scanner and validation
    predicate source files recorded in the scan, builds its scanners,
    predicates, model and model roles (including base URLs and model args)
    from values in the scan, and reads transcripts from the locations the scan
    records. Only resume scans you trust.
    """
    # Process common options
    process_common_options(ctx, common)

    status = scan_resume(
        scan_location,
        log_level=common["log_level"],
        fail_on_error=common["fail_on_error"],
    )

    # exit non-zero when the user asked us to fail on error and the scan
    # didn't complete cleanly
    if common["fail_on_error"] and not status.complete:
        ctx.exit(1)
