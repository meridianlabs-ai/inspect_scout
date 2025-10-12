import click

from inspect_scout._scan import scan_complete


@click.command("complete")
@click.argument("scan_dir", nargs=1)
def scan_complete_command(scan_dir: str) -> None:
    """Complete a scan which is incomplete due to errors (errors are not retried)."""
    scan_complete(scan_dir)
