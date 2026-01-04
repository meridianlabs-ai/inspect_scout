import click
from inspect_ai._util.error import set_exception_hook
from typing_extensions import Unpack

from .. import __version__
from .._scan import init_environment
from .._view.scout import scout_workbench
from .common import (
    CommonOptions,
    common_options,
    process_common_options,
    view_options,
)
from .db import db_command
from .info import info_command
from .scan import scan_command
from .scan_complete import scan_complete_command
from .scan_list import scan_list_command
from .scan_resume import scan_resume_command
from .scan_status import scan_status_command
from .scout_group import ScoutGroup
from .trace import trace_command
from .view import view_command


@click.group(
    cls=ScoutGroup,
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option(
    "--version",
    type=bool,
    is_flag=True,
    default=False,
    help="Print the scout version.",
)
@view_options
@common_options
@click.pass_context
def scout(
    ctx: click.Context,
    version: bool,
    host: str,
    port: int,
    browser: bool | None,
    **common: Unpack[CommonOptions],
) -> None:
    """Scout CLI - scan and view transcripts.

    Run 'scout [directory]' to view scan results (defaults to current directory).
    Run 'scout scan ...' to run scans.
    """
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    if version:
        print(__version__)
        ctx.exit()

    # Process common options
    process_common_options(common)

    # Get directory from extra args, default to current directory
    directory = ctx.args[0] if ctx.args else None

    # Launch workbench
    scout_workbench(
        project_dir=directory,
        host=host,
        port=port,
        browser=browser,
        log_level=common["log_level"],
    )


scout.add_command(scan_command)
scan_command.add_command(scan_resume_command)
scan_command.add_command(scan_complete_command)
scan_command.add_command(scan_list_command)
scan_command.add_command(scan_status_command)
scout.add_command(view_command)
scout.add_command(trace_command)
scout.add_command(info_command)
scout.add_command(db_command)


def main() -> None:
    init_environment()
    set_exception_hook()
    scout(auto_envvar_prefix="SCOUT")  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
