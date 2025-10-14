from inspect_ai._display.core.rich import rich_theme
from inspect_ai._util.path import pretty_path
from rich.console import RenderableType

from inspect_scout._recorder.recorder import ScanStatus
from inspect_scout._scanner.result import Error


def scan_interrupted_messages(
    message: RenderableType, scan_dir: str
) -> list[RenderableType]:
    theme = rich_theme()

    return [
        message,
        f"\n[bold][{theme.error}]Scan interrupted. Resume scan with:[/{theme.error}]\n\n"
        + f'[bold][{theme.light}]scout scan-resume "{pretty_path(scan_dir)}"[/{theme.light}][/bold]\n',
    ]


def scan_complete_message(status: ScanStatus) -> str:
    return f'\n[bold]Scan complete:[/bold] "{pretty_path(status.location)}"\n'


def scan_errors_message(status: ScanStatus) -> str:
    theme = rich_theme()
    return "\n".join(
        [
            f"\n[bold]{len(status.errors)} scan errors occurred![/bold]\n",
            f'Resume (retrying errors):   [bold][{theme.light}]scout scan resume "{pretty_path(status.location)}"[/{theme.light}][/bold]\n',
            f'Complete (ignoring errors): [bold][{theme.light}]scout scan complete "{pretty_path(status.location)}"[/{theme.light}][/bold]\n',
        ]
    )
