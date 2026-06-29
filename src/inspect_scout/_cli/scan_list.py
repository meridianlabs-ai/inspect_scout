import shlex

import click
from rich.table import Column, Table
from typing_extensions import Unpack

from inspect_scout._display.util import terminal_path
from inspect_scout._project._project import read_project

from .._display import display
from .._scan import top_level_async_init
from .._scanlist import scan_list
from .common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_common_log_level,
)
from .scan import scan_command


@scan_command.command("list")
@click.argument("scans_dir", default="")
@common_options
@click.pass_context
def scan_list_command(
    ctx: click.Context,
    scans_dir: str,
    **common: Unpack[CommonOptions],
) -> None:
    """List the scans within the scans dir."""
    # Process common options
    process_common_options(common)

    # initialize logging with the resolved log level
    project = read_project()
    top_level_async_init(resolve_common_log_level(ctx, common) or project.log_level)

    # if there is no scans dir then get it from the project
    if len(scans_dir) == 0:
        scans_dir = project.scans or "./scans"

    # list the scans
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
            shlex.quote(terminal_path(scan.location)),
            "complete" if scan.complete else "pending",
            str(len(scan.errors)),
        )

    # print
    display().print(table)
