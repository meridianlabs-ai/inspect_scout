import click

from inspect_scout._scan import scan_resume


@click.command("resume")
@click.argument("scan_dir", nargs=1)
def scan_resume_command(scan_dir: str) -> None:
    """Resume a scan which is incomplete due to interruption or errors (errors are retried)."""
    scan_resume(scan_dir)
