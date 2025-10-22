from typing import Any, Literal

import click
from inspect_ai._cli.util import (
    int_bool_or_str_flag_callback,
    int_or_bool_flag_callback,
    parse_cli_args,
    parse_cli_config,
    parse_model_role_cli_args,
)
from inspect_ai._util.config import resolve_args
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import BatchConfig, GenerateConfig
from typing_extensions import Unpack

from .._scan import scan
from .._scanjob import ScanJob, scanjob_from_file
from .._scanner.scanner import scanners_from_file
from .._transcript.database import transcripts_from_logs as transcripts_from
from .._util.constants import DEFAULT_BATCH_SIZE, DEFAULT_MAX_TRANSCRIPTS
from .common import CommonOptions, common_options, process_common_options


class ScanGroup(click.Group):
    """Custom group that allows FILE argument when no subcommand is given."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Override parse_args to reorder arguments before parsing."""
        # Check if we have a subcommand
        if args and args[0] in self.commands:
            # Let the parent handle subcommand parsing
            return super().parse_args(ctx, args)

        # Reorder args to put options before positional arguments
        # This allows: scout scan file.py -T ./logs to work correctly
        file_args = []
        option_args = []
        i = 0
        while i < len(args):
            arg = args[i]
            # Check if this is an option (starts with -)
            if arg.startswith("-"):
                option_args.append(arg)
                i += 1
                # For options that take values, check if next arg exists and is not a flag
                if i < len(args) and not args[i].startswith("-"):
                    option_args.append(args[i])
                    i += 1
            else:
                file_args.append(arg)
                i += 1

        # Reorder: options first, then file arguments
        reordered_args = option_args + file_args

        # Let parent parse the reordered args
        return super().parse_args(ctx, reordered_args)

    def invoke(self, ctx: click.Context) -> Any:
        # Get the unparsed args
        args = ctx.protected_args + ctx.args

        # Check if we have a subcommand
        if args and args[0] in self.commands:
            # Let the parent handle subcommand invocation
            return super().invoke(ctx)

        # No subcommand - invoke the group's callback with the args
        # The callback will get FILE from ctx.args
        with ctx:
            ctx.invoked_subcommand = None
            ctx.args = args
            return ctx.invoke(self.callback or (lambda: None), **ctx.params)


@click.group(
    name="scan",
    cls=ScanGroup,
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.option(
    "-S",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_ARGS",
    help="One or more scanjob or scanner arguments (e.g. -S arg=value)",
)
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
    help=f"Maximum number of transcripts to scan concurrently (defaults to {DEFAULT_MAX_TRANSCRIPTS})",
    envvar="SCOUT_SCAN_MAX_TRANSCRIPTS",
)
@click.option(
    "--max-processes",
    type=int,
    help="Number of worker processes. Defaults to `multiprocessing.cpu_count()`.",
    envvar="SCOUT_SCAN_MAX_PROCESSES",
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
    envvar="SCOUT_SCAN_METADATA",
)
@click.option(
    "--batch",
    is_flag=False,
    flag_value="true",
    default=None,
    callback=int_bool_or_str_flag_callback(DEFAULT_BATCH_SIZE, None),
    help="Batch requests together to reduce API calls when using a model that supports batching (by default, no batching). Specify --batch to batch with default configuration, specify a batch size e.g. `--batch=1000` to configure batches of 1000 requests, or pass the file path to a YAML or JSON config file with batch configuration.",
    envvar="SCOUT_SCAN_BATCH",
)
@click.option(
    "--max-connections",
    type=int,
    help="Maximum number of concurrent connections to Model API (defaults to max_transcripts)",
    envvar="SCOUT_SCAN_MAX_CONNECTIONS",
)
@click.option(
    "--max-retries",
    type=int,
    help="Maximum number of times to retry model API requests (defaults to unlimited)",
    envvar="SCOUT_SCAN_MAX_RETRIES",
)
@click.option(
    "--timeout",
    type=int,
    help="Model API request timeout in seconds (defaults to no timeout)",
    envvar="SCOUT_SCAN_TIMEOUT",
)
@common_options
@click.pass_context
def scan_command(
    ctx: click.Context,
    s: tuple[str, ...],
    transcripts: tuple[str, ...],
    results: str,
    model: str | None,
    model_base_url: str | None,
    m: tuple[str, ...] | None,
    model_config: str | None,
    model_role: tuple[str, ...] | None,
    max_transcripts: int | None,
    max_processes: int | None,
    limit: int | None,
    shuffle: int | None,
    tags: str | None,
    metadata: tuple[str, ...] | None,
    batch: int | str | None,
    max_retries: int | None,
    timeout: int | None,
    max_connections: int | None,
    **common: Unpack[CommonOptions],
) -> None:
    """Scan transcripts and read results."""
    # Process common options
    process_common_options(common)

    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    # Get the file argument from extra args
    if not ctx.args or len(ctx.args) == 0:
        raise click.UsageError("Missing argument 'FILE'.")

    file = ctx.args[0]
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

    # resolve scanjobs
    scanjob_args = parse_cli_args(s)
    scanjob = scanjob_from_file(file, scanjob_args)
    if scanjob is None:
        scanners = scanners_from_file(file, scanjob_args)
        if len(scanners) == 0:
            raise PrerequisiteError(
                f"No @scanjob or @scanner decorated functions found in '{file}'"
            )
        else:
            scanjob = ScanJob(transcripts=None, scanners=scanners)

    # resolve transcripts (could be from ScanJob)
    tx = transcripts_from(transcripts) if len(transcripts) > 0 else scanjob.transcripts
    if tx is None:
        raise PrerequisiteError(
            "No transcripts specified for scanning (pass as --transcripts or include in @scanjob)"
        )

    # resolve batch
    if isinstance(batch, str):
        batch_config: bool | int | BatchConfig | None = BatchConfig.model_validate(
            resolve_args(batch)
        )
    else:
        batch_config = batch

    # resolve model config
    scan_model_config = GenerateConfig(
        max_retries=max_retries,
        timeout=timeout,
        max_connections=max_connections,
        batch=batch_config,
    )

    # run scan
    scan(
        scanners=scanjob,
        transcripts=tx,
        results=results,
        model=model,
        model_config=scan_model_config,
        model_base_url=model_base_url,
        model_args=scan_model_args,
        model_roles=scan_model_roles,
        max_transcripts=max_transcripts,
        max_processes=max_processes,
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
