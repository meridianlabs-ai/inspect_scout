import os
import shlex

import click
from inspect_ai._util.path import pretty_path
from rich.table import Column, Table
from typing_extensions import Unpack

from .._display import display
from .._scanlist import scan_list
from .common import CommonOptions, common_options, process_common_options
from .scan import scan_command


@scan_command.command("list")
@click.argument("scans_dir", default=os.getenv("SCOUT_SCAN_RESULTS", "./scans"))
@common_options
def scan_list_command(
    scans_dir: str,
    **common: Unpack[CommonOptions],
) -> None:
    """List the scans within the scans dir."""
    # Process common options
    process_common_options(common)

    scans = scan_list(scans_dir)

    scans = sorted(
        scan_list(scans_dir),
        key=lambda scan: scan.spec.timestamp.timestamp(),
        reverse=True,
    )

    # create table
    table = Table(
        Column("time", width=22),
        Column("scan"),
        Column("status"),
        Column("errors", justify="right"),
        box=None,
        title_style="bold",
        pad_edge=False,
        padding=(0, 1),
    )

    # populate rows
    for scan in scans:
        table.add_row(
            scan.spec.timestamp.strftime("%d-%b %H:%M:%S %Z"),
            shlex.quote(pretty_path(scan.location)),
            "complete" if scan.complete else "pending",
            str(len(scan.errors)),
        )

    # print
    display().print(table)
