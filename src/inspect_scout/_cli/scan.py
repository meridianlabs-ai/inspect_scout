import click
from inspect_ai._cli.util import (
    int_or_bool_flag_callback,
    parse_cli_args,
    parse_cli_config,
    parse_model_role_cli_args,
)
from typing_extensions import Literal

from inspect_scout._scan import scan


@click.command("scan")
@click.argument("scanners", nargs=-1)
@click.option(
    "-T",
    "--transcripts",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_TRANSCRIPTS",
    help="One or more transcript sources (e.g. -T ./logs)",
)
@click.option(
    "--results",
    type=str,
    default="./scans",
    help="Location to write scan results to.",
    envvar="SCOUT_SCAN_RESULTS",
)
@click.option(
    "--model",
    type=str,
    help="Model used by default for llm scanners.",
    envvar="SCOUT_SCAN_MODEL",
)
@click.option(
    "--model-base-url",
    type=str,
    envvar="SCOUT_SCAN_MODEL_BASE_URL",
    help="Base URL for for model API",
)
@click.option(
    "-M",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_MODEL_ARGS",
    help="One or more native model arguments (e.g. -M arg=value)",
)
@click.option(
    "--model-config",
    type=str,
    envvar="SCOUT_SCAN_MODEL_CONFIG",
    help="YAML or JSON config file with model arguments.",
)
@click.option(
    "--model-role",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_MODEL_ROLE",
    help='Named model role with model name or YAML/JSON config, e.g. --model-role critic=openai/gpt-4o or --model-role grader="{model: mockllm/model, temperature: 0.5}"',
)
@click.option(
    "--max-transcripts",
    type=int,
    help="Maximum number of transcripts to scan concurrently.",
    envvar="SCOUT_SCAN_MAX_TRANSCRIPTS",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of transcripts to scan.",
    envvar="SCOUT_SCAN_LIMIT",
)
@click.option(
    "--shuffle",
    is_flag=False,
    flag_value="true",
    default=None,
    callback=int_or_bool_flag_callback(-1),
    help="Shuffle order of transcripts (pass a seed to make the order deterministic)",
    envvar=["SCOUT_SCAN_SHUFFLE"],
)
@click.option(
    "--tags",
    type=str,
    help="Tags to associate with this scan job (comma separated)",
    envvar="SCOUT_SCAN_TAGS",
)
@click.option(
    "--metadata",
    multiple=True,
    type=str,
    help="Metadata to associate with this scan job (more than one --metadata argument can be specified).",
    envvar="SCOUT_METADATA",
)
def scan_command(
    scanners: tuple[str, ...] | None,
    transcripts: tuple[str, ...] | None,
    results: str,
    model: str | None,
    model_base_url: str | None,
    m: tuple[str, ...] | None,
    model_config: str | None,
    model_role: tuple[str, ...] | None,
    max_transcripts: int | None,
    limit: int | None,
    shuffle: int | None,
    tags: str | None,
    metadata: tuple[str, ...] | None,
) -> None:
    # model args and role
    scan_model_args = parse_cli_config(m, model_config)
    scan_model_roles = parse_model_role_cli_args(model_role)

    # tags and metadata
    scan_tags = parse_comma_separated(tags)
    scan_metadata = parse_cli_args(metadata)

    # shuffle
    # resolve sample_shuffle
    if shuffle == -1:
        scan_suffle: Literal[True] | int | None = True
    elif shuffle == 0:
        scan_suffle = None
    else:
        scan_suffle = shuffle

    # resolve scanners

    # resolve transcripts

    # TODO: model_config ?

    # run scan
    scan(
        scanners=[],
        transcripts=[],
        results=results,
        model=model,
        model_base_url=model_base_url,
        model_args=scan_model_args,
        model_roles=scan_model_roles,
        max_transcripts=max_transcripts,
        limit=limit,
        shuffle=scan_suffle,
        tags=scan_tags,
        metadata=scan_metadata,
    )


def parse_comma_separated(value: str | None) -> list[str] | None:
    if value is not None:
        return value.split(",")
    else:
        return None
