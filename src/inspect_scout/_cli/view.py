from logging import getLogger
from typing import Literal

import click
from inspect_ai._util.path import chdir
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
    resolve_view_authorization,
    view_options,
)

from .._view.view import view
from .bundle import bundle_command

logger = getLogger(__name__)


def _set_protected_args(ctx: click.Context, args: list[str]) -> None:
    """Set the args click reserves for subcommand dispatch.

    click 8.2+ stores them in the private ``_protected_args`` attribute
    (``protected_args`` became a read-only deprecated property), while on
    8.1.x ``protected_args`` is a plain settable attribute.
    """
    if hasattr(ctx, "_protected_args"):
        ctx._protected_args = args
    else:
        ctx.protected_args = args  # type: ignore[misc]


class ViewGroup(click.Group):
    """Custom group letting an optional PROJECT_DIR coexist with subcommands.

    Without this:
      - ``scout view bundle`` would consume ``bundle`` as PROJECT_DIR and
        then fail to find a subcommand.
      - ``scout view PATH --port 8080`` would stop parsing options at
        PATH (click.Group sets ``allow_interspersed_args=False``).

    Subcommand names are reserved: a PROJECT_DIR that collides with one must
    be spelled unambiguously (e.g. ``scout view ./bundle``).
    """

    # Let options appear anywhere on the command line — `scout view PATH
    # --port 8080` is the documented form.
    allow_interspersed_args = True

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        # Tokens consumed as option values (e.g. `-T bundle`) must not be
        # mistaken for subcommand names.
        value_opt_nargs = {
            opt: param.nargs
            for param in self.params
            if isinstance(param, click.Option) and not param.is_flag and not param.count
            for opt in (*param.opts, *param.secondary_opts)
        }
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in value_opt_nargs:
                i += 1 + value_opt_nargs[arg]
                continue
            if arg in self.commands:
                rest = super().parse_args(ctx, args[:i])
                _set_protected_args(ctx, args[i:])
                return rest
            i += 1
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
        # A subcommand (e.g. `scout view bundle`) handles its own options.
        return

    # chdir to correctly resolve log level based on the relevant project_dir
    with chdir(project_dir or "."):
        process_common_options(ctx, common, init_logging=False)

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


view_command.add_command(bundle_command)
