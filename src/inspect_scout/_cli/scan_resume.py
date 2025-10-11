import click

from inspect_scout._scan import scan_resume


@click.command("scan-resume")
@click.argument("scan_dir", nargs=1)
def scan_resume_command(scan_dir: str) -> None:
    """Resume an interrupted scan or scan with errors."""
    scan_resume(scan_dir)
