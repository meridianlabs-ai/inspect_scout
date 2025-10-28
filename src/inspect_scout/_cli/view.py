import click

from .._view.view import view


@click.command("view")
@click.option(
    "--results",
    type=str,
    default="./scans",
    help="Location to read scan results from.",
    envvar="SCOUT_SCAN_RESULTS",
)
@click.option(
    "--port",
    type=int,
    default=7576,
    help="Port to use for the view server.",
    envvar="SCOUT_VIEW_PORT",
)
def view_command(results: str, port: int) -> None:
    """View scan results."""
    view(results, port=port)
