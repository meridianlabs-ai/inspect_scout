from inspect_ai._display.core.rich import rich_theme
from inspect_ai._util.path import pretty_path
from inspect_ai._util.registry import is_model_dict, is_registry_dict
from inspect_ai._util.text import truncate_text
from rich.console import RenderableType

from inspect_scout._recorder.recorder import ScanStatus
from inspect_scout._scanspec import ScanOptions, ScanSpec


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


def scan_title(spec: ScanSpec) -> str:
    SCAN = "scan"
    if spec.scan_file is not None:
        return f"{SCAN}: {pretty_path(spec.scan_file)}"
    elif spec.scan_name not in ["scan", "job"]:
        return f"{SCAN}: {spec.scan_name}"
    else:
        return SCAN


def scan_config_str(spec: ScanSpec, options: ScanOptions) -> str:
    scan_args = dict(spec.scan_args)
    for key in scan_args.keys():
        value = scan_args[key]
        if is_registry_dict(value):
            scan_args[key] = value["name"]
        if is_model_dict(value):
            scan_args[key] = value["model"]

    scan_options = options.model_dump(exclude_none=True)

    config = scan_args | scan_options

    if spec.model:
        config["model"] = spec.model.model
        config = config | dict(spec.model.config.model_dump(exclude_none=True))

    if spec.tags:
        config["tags"] = ",".join(spec.tags)

    # format config str
    config_str: list[str] = []
    for name, value in config.items():
        if isinstance(value, list):
            value = ",".join([str(v) for v in value])
        elif isinstance(value, dict):
            value = "{...}"
        if isinstance(value, str):
            value = truncate_text(value, 50)
            value = value.replace("[", "\\[")
        config_str.append(f"{name}: {value}")

    return config_str
