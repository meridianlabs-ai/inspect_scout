import click

from inspect_scout._scan import scan_complete


@click.command("scan-complete")
@click.argument("scan_dir", nargs=1)
def scan_complete_command(scan_dir: str) -> None:
    """Resume an interrupted transcipt scan."""
    scan_complete(scan_dir)
