from logging import getLogger
from typing import Literal

import click
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_view_authorization,
    view_options,
)

from .._view.view import view

logger = getLogger(__name__)


class ViewGroup(click.Group):
    """Custom group letting an optional PROJECT_DIR coexist with subcommands.

    Without this:
      - ``scout view bundle`` would consume ``bundle`` as PROJECT_DIR and
        then fail to find a subcommand.
      - ``scout view PATH --port 8080`` would stop parsing options at
        PATH (click.Group sets ``allow_interspersed_args=False``).
    """

    # Let options appear anywhere on the command line — `scout view PATH
    # --port 8080` is the documented form.
    allow_interspersed_args = True

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        for i, a in enumerate(args):
            if a in self.commands:
                rest = super().parse_args(ctx, args[:i])
                ctx._protected_args = args[i:]
                return rest
        return super().parse_args(ctx, args)


@click.group(
    name="view",
    cls=ViewGroup,
    invoke_without_command=True,
)
@click.argument("project_dir", required=False, default=None)
@click.option(
    "-T",
    "--transcripts",
    type=str,
    default=None,
    help="Location of transcripts to view.",
)
@click.option(
    "--scans",
    type=str,
    default=None,
    help="Location of scan results to view.",
)
@click.option(
    "--mode",
    type=click.Choice(("default", "scans")),
    default="default",
    help="View display mode.",
)
@view_options
@common_options
@click.pass_context
def view_command(
    ctx: click.Context,
    project_dir: str | None,
    transcripts: str | None,
    scans: str | None,
    mode: Literal["default", "scans"],
    host: str,
    port: int,
    browser: bool | None,
    root_path: str,
    **common: Unpack[CommonOptions],
) -> None:
    """View scan results."""
    if ctx.invoked_subcommand is not None:
        # A subcommand (e.g. `scout view bundle`) will handle its own
        # option parsing.
        return

    process_common_options(common)

    view(
        project_dir=project_dir,
        transcripts=transcripts,
        scans=scans,
        host=host,
        port=port,
        browser=browser is True,
        mode=mode,
        authorization=resolve_view_authorization(),
        log_level=common["log_level"],
        root_path=root_path,
    )
