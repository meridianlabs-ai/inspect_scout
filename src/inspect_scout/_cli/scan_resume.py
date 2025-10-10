import click
from inspect_ai._util._async import run_coroutine

from inspect_scout._scan import scan_resume_async


@click.command("scan-resume")
@click.argument("scan_dir", nargs=1)
def scan_resume_command(scan_dir: str) -> None:
    """Resume an interrupted transcipt scan."""
    run_coroutine(scan_resume_async(scan_dir))
