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
def view_command(results: str) -> None:
    """View scan results."""
    view(results)
