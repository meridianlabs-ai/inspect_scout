import shlex

from inspect_ai._display.core.rich import rich_theme
from inspect_ai._util.constants import DEFAULT_MAX_CONNECTIONS_BATCH
from inspect_ai._util.path import pretty_path
from inspect_ai._util.registry import is_model_dict, is_registry_dict
from inspect_ai._util.rich import rich_traceback
from inspect_ai._util.text import truncate_text
from rich.console import RenderableType
from rich.text import Text

from inspect_scout._recorder.recorder import Status
from inspect_scout._scanspec import ScanSpec


def scan_interrupted_message(status: Status) -> str:
    theme = rich_theme()
    return (
        f"\n[bold][{theme.error}]scan interrupted, resume scan with:[/{theme.error}]\n\n"
        + f"[bold][{theme.light}]scout scan resume {shlex.quote(pretty_path(status.location))}[/{theme.light}][/bold]\n"
    )


def scan_complete_message(status: Status) -> str:
    return (
        f"\n[bold]scan complete:[/bold] {shlex.quote(pretty_path(status.location))}\n"
    )


def scan_errors_message(status: Status) -> str:
    theme = rich_theme()
    return "\n".join(
        [
            f"\n[bold]{len(status.errors)} scan errors occurred![/bold]\n",
            f"Resume (retrying errors):   [bold][{theme.light}]scout scan resume {shlex.quote(pretty_path(status.location))}[/{theme.light}][/bold]\n",
            f"Complete (ignoring errors): [bold][{theme.light}]scout scan complete {shlex.quote(pretty_path(status.location))}[/{theme.light}][/bold]\n",
        ]
    )


def scan_title(spec: ScanSpec) -> str:
    SCAN = "scan"
    if spec.scan_file is not None:
        title = f"{SCAN}: {pretty_path(spec.scan_file)}"
    elif spec.scan_name not in ["scan", "job"]:
        title = f"{SCAN}: {spec.scan_name}"
    else:
        title = SCAN
    if spec.options.limit:
        title = f"{title} ({spec.options.limit:,} transcripts)"
    elif spec.transcripts is not None:
        title = f"{title} ({len(spec.transcripts.transcript_ids):,} transcripts)"
    return title


def scan_config(spec: ScanSpec) -> RenderableType:
    config = scan_config_str(spec)
    if config:
        config_text = Text(config)
        config_text.truncate(500, overflow="ellipsis")
        return config_text
    else:
        return ""


def scan_config_str(spec: ScanSpec) -> str:
    scan_args = dict(spec.scan_args or {})
    for key in scan_args.keys():
        value = scan_args[key]
        if is_registry_dict(value):
            scan_args[key] = value["name"]
        if is_model_dict(value):
            scan_args[key] = value["model"]

    batch_in_use = spec.model.config.batch is not None if spec.model else False

    scan_options = spec.options.model_dump(
        exclude_none=True,
        exclude={
            "max_transcripts": batch_in_use
            and spec.options.max_transcripts == DEFAULT_MAX_CONNECTIONS_BATCH
        },
    )

    config = scan_args | scan_options

    if spec.model:
        config = config | dict(
            spec.model.config.model_dump(
                exclude_none=True, exclude={"max_connections": batch_in_use}
            )
        )
        config["model"] = spec.model.model

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

    return ", ".join(config_str)


def exception_to_rich_traceback(ex: Exception) -> RenderableType:
    rich_tb = rich_traceback(type(ex), ex, ex.__traceback__)

    return rich_tb
