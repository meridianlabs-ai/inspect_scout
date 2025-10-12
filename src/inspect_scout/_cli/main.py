import click

from inspect_scout._cli.trace import trace_command
from inspect_scout._scan import init_environment

from .. import __version__
from .scan import scan_command
from .scan_complete import scan_complete_command
from .scan_resume import scan_resume_command


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    type=bool,
    is_flag=True,
    default=False,
    help="Print the scout version.",
)
@click.pass_context
def scout(ctx: click.Context, version: bool) -> None:
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    if version:
        print(__version__)
        ctx.exit()
    else:
        click.echo(ctx.get_help())
        ctx.exit()


scout.add_command(scan_command)
scan_command.add_command(scan_resume_command)
scan_command.add_command(scan_complete_command)

scout.add_command(trace_command)


def main() -> None:
    init_environment()
    scout(auto_envvar_prefix="SCOUT")  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
