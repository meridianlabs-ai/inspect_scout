from logging import getLogger
from typing import Any, Literal, TypeVar, cast

import click
from click.core import ParameterSource
from inspect_ai._cli.util import (
    int_bool_or_str_flag_callback,
    int_or_bool_flag_callback,
    parse_cli_args,
    parse_cli_config,
    parse_model_role_cli_args,
)
from inspect_ai._util.config import resolve_args
from inspect_ai._util.constants import DEFAULT_CACHE_DAYS
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.logger import warn_once
from inspect_ai.model import BatchConfig, CachePolicy, GenerateConfig, Model
from typing_extensions import Unpack

from inspect_scout._project._project import init_project, project
from inspect_scout._validation import validation_set
from inspect_scout._validation.predicates import PREDICATES, ValidationPredicate
from inspect_scout._validation.types import ValidationSet

from .._scan import scan
from .._scanjob import (
    ScanJob,
    merge_project_into_scanjob,
    scanjob_from_cli_spec,
    scanjob_from_file,
)
from .._scanner.scanner import scanners_from_file
from .._transcript.factory import transcripts_from
from .._util.constants import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_TRANSCRIPTS,
    DEFAULT_SCANS_DIR,
)
from .common import CommonOptions, common_options, process_common_options

logger = getLogger(__name__)


class ScanGroup(click.Group):
    """Custom group that allows FILE argument when no subcommand is given."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Override parse_args to reorder arguments before parsing."""
        # Check if we have a subcommand
        if args and args[0] in self.commands:
            # Let the parent handle subcommand parsing
            return super().parse_args(ctx, args)

        # Normalize optional-value flags (--shuffle, --cache, --batch) by inserting
        # "true" after them if they don't have a value. This prevents the reordering
        # logic from incorrectly consuming positional args as their values.
        optional_value_flags = {"--shuffle", "--cache", "--batch"}

        def _looks_like_optional_flag_value(value: str) -> bool:
            """Check if value looks like a valid value for optional-value flags."""
            if value.startswith("-"):
                return False
            lower = value.lower()
            if lower in ("true", "false"):
                return True
            try:
                int(value)
                return True
            except ValueError:
                pass
            # Config files for --cache and --batch
            if lower.endswith((".yaml", ".yml", ".json")):
                return True
            return False

        # First pass: normalize optional-value flags by inserting "true" if needed
        normalized_args: list[str] = []
        i = 0
        while i < len(args):
            arg = args[i]
            normalized_args.append(arg)
            i += 1
            # Check if this is an optional-value flag without an explicit value
            if arg in optional_value_flags:
                # If no next arg, or next arg doesn't look like a valid value, insert "true"
                if i >= len(args) or not _looks_like_optional_flag_value(args[i]):
                    normalized_args.append("true")

        # Second pass: reorder args to put options before positional arguments
        # This allows: scout scan file.py -T ./logs to work correctly
        file_args = []
        option_args = []
        i = 0
        while i < len(normalized_args):
            arg = normalized_args[i]
            # Check if this is an option (starts with -)
            if arg.startswith("-"):
                option_args.append(arg)
                i += 1
                # For options that take values, check if next arg exists and is not a flag
                if i < len(normalized_args) and not normalized_args[i].startswith("-"):
                    option_args.append(normalized_args[i])
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
    "-F",
    "--filter",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_FILTER",
    help="One or more transcript filters (e.g. -F \"task_set = 'cybench'\")",
)
@click.option(
    "--scans",
    type=str,
    default=None,
    help="Location to write scan results to.",
    envvar="SCOUT_SCAN_SCANS",
)
@click.option(
    "--results",
    type=str,
    default=None,
    hidden=True,
    envvar="SCOUT_SCAN_RESULTS",
)
@click.option(
    "--worklist",
    type=click.Path(exists=True),
    help="Transcript ids to process for each scanner (JSON or YAML file).",
    envvar="SCOUT_SCAN_WORKLIST",
)
@click.option(
    "-V",
    "--validation",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_VALIDATION",
    help="One or more validation sets to apply for scanners (e.g. -V myscanner:deception.csv)",
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
    help="Number of worker processes. Defaults to 4.",
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
    "--cache",
    is_flag=False,
    flag_value="true",
    default=None,
    callback=int_bool_or_str_flag_callback(DEFAULT_CACHE_DAYS, None),
    help="Policy for caching of model generations. Specify --cache to cache with 7 day expiration (7D). Specify an explicit duration (e.g. (e.g. 1h, 3d, 6M) to set the expiration explicitly (durations can be expressed as s, m, h, D, W, M, or Y). Alternatively, pass the file path to a YAML or JSON config file with a full `CachePolicy` configuration.",
    envvar="SCOUT_SCAN_CACHE",
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
@click.option(
    "--max-tokens",
    type=int,
    help="The maximum number of tokens that can be generated in the completion (default is model specific)",
    envvar="SCOUT_SCAN_MAX_TOKENS",
)
@click.option(
    "--temperature",
    type=float,
    help="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.",
    envvar="SCOUT_SCAN_TEMPERATURE",
)
@click.option(
    "--top-p",
    type=float,
    help="An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass.",
    envvar="SCOUT_SCAN_TOP_P",
)
@click.option(
    "--top-k",
    type=int,
    help="Randomly sample the next word from the top_k most likely next words. Anthropic, Google, HuggingFace, and vLLM only.",
    envvar="SCOUT_SCAN_TOP_K",
)
@click.option(
    "--reasoning-effort",
    type=click.Choice(["minimal", "low", "medium", "high"]),
    help="Constrains effort on reasoning for reasoning models (defaults to `medium`). Open AI o-series and gpt-5 models only.",
    envvar="SCOUT_SCAN_REASONING_EFFORT",
)
@click.option(
    "--reasoning-tokens",
    type=int,
    help="Maximum number of tokens to use for reasoning. Anthropic Claude models only.",
    envvar="SCOUT_SCAN_REASONING_TOKENS",
)
@click.option(
    "--reasoning-summary",
    type=click.Choice(["concise", "detailed", "auto"]),
    help="Provide summary of reasoning steps (defaults to no summary). Use 'auto' to access the most detailed summarizer available for the current model. OpenAI reasoning models only.",
    envvar="SCOUT_SCAN_REASONING_SUMMARY",
)
@click.option(
    "--reasoning-history",
    type=click.Choice(["none", "all", "last", "auto"]),
    help='Include reasoning in chat message history sent to generate (defaults to "auto", which uses the recommended default for each provider)',
    envvar="SCOUT_SCAN_REASONING_HISTORY",
)
@click.option(
    "--response-schema",
    type=str,
    help="JSON schema for desired response format (output should still be validated). OpenAI, Google, and Mistral only.",
    envvar="SCOUT_SCAN_RESPONSE_SCHEMA",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print resolved scanners and transcript counts without scanning.",
    envvar="SCOUT_SCAN_DRY_RUN",
)
@common_options
@click.pass_context
def scan_command(
    ctx: click.Context,
    s: tuple[str, ...],
    transcripts: tuple[str, ...],
    filter: tuple[str, ...],
    scans: str | None,
    results: str | None,
    worklist: str | None,
    validation: tuple[str, ...] | None,
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
    cache: int | str | None,
    batch: int | str | None,
    max_retries: int | None,
    timeout: int | None,
    max_connections: int | None,
    max_tokens: int | None,
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None,
    reasoning_tokens: int | None,
    reasoning_summary: Literal["concise", "detailed", "auto"] | None,
    reasoning_history: Literal["none", "all", "last", "auto"] | None,
    dry_run: bool,
    **common: Unpack[CommonOptions],
) -> None:
    """Scan transcripts and read results.

    Pass a FILE which is either a Python script that contains @scanner or @scanjob decorated functions or a config file (YAML or JSON) that adheres to the `ScanJobConfig` schema.
    """
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    # Process common options
    process_common_options(common)

    # Handle deprecated --results option
    if results is not None:
        warn_once(
            logger, "CLI option '--results' is deprecated, please use '--scans' instead"
        )
        if scans is not None:
            raise click.UsageError("Cannot specify both --scans and --results")
        scans = results

    # Apply default for scans
    if scans is None:
        scans = DEFAULT_SCANS_DIR

    # Get the file argument from extra args
    if not ctx.args or len(ctx.args) == 0:
        raise click.UsageError("Missing argument 'FILE'.")
    file = ctx.args[0]

    # resolve scanjobs
    scanjob_args = parse_cli_args(s)

    # see if it is a package reference
    scanjob = scanjob_from_cli_spec(file, scanjob_args)
    if scanjob is None:
        # now check for a scanjob file (.py or .yaml)
        scanjob = scanjob_from_file(file, scanjob_args)
        if scanjob is None:
            # now check for a .py file with scanners
            scanners = scanners_from_file(file, scanjob_args)
            if len(scanners) == 0:
                raise PrerequisiteError(
                    f"No @scanjob or @scanner decorated functions found in '{file}'"
                )
            else:
                scanjob = ScanJob(transcripts=None, scanners=scanners)

    # need to resolve project against scanjob here so it can override env vars
    init_project()
    merge_project_into_scanjob(project(), scanjob)

    # resolve transcripts from cli/env (apply filter)
    tx = transcripts_from(transcripts) if len(transcripts) > 0 else None
    if tx is not None:
        for f in filter:
            tx = tx.where(f)

    # tx might have been from env so enable it to be overridden by project/scanjob
    tx = resolve_scan_option(ctx, "transcripts", tx, scanjob.transcripts)

    # resolve some options
    scans = resolve_scan_option(ctx, "scans", scans, scanjob.scans)
    scan_worklist = cast(
        str | None,
        resolve_scan_option(ctx, "worklist", worklist, scanjob.worklist),
    )

    # parse validation
    parsed_validation = _parse_validation(validation)
    scan_validation = cast(
        ValidationSet | dict[str, ValidationSet] | None,
        resolve_scan_option(ctx, "validation", parsed_validation, scanjob.validation),
    )

    # model
    scan_model = cast(
        str | None,
        resolve_scan_option(ctx, "model", model, scanjob.model),
    )
    scan_model_base_url = resolve_scan_option(
        ctx, "model_base_url", model_base_url, scanjob.model_base_url
    )
    scan_model_args = resolve_scan_option_multi(
        ctx,
        ["m", "model_config"],
        parse_cli_config(m, model_config),
        scanjob.model_args,
    )
    scan_model_roles = cast(
        dict[str, str | Model] | None,
        resolve_scan_option(
            ctx,
            "model_role",
            parse_model_role_cli_args(model_role),
            scanjob.model_roles,
        ),
    )

    # resolve cache
    cache_config: bool | CachePolicy | None = None
    match cache:
        case str():
            policy = CachePolicy.from_string(cache)
            if policy is not None:
                cache_config = policy
            else:
                cache_config = CachePolicy.model_validate(resolve_args(cache))
        case int():
            cache_config = CachePolicy(expiry=f"{cache}D")
        case _:
            cache_config = cache
    if scanjob.generate_config is not None:
        cache_config = cast(
            bool | CachePolicy | None,
            resolve_scan_option(
                ctx, "cache", cache_config, scanjob.generate_config.cache
            ),
        )

    # resolve batch
    if isinstance(batch, str):
        batch_config: bool | int | BatchConfig | None = BatchConfig.model_validate(
            resolve_args(batch)
        )
    else:
        batch_config = batch
    if scanjob.generate_config is not None:
        batch_config = cast(
            bool | int | BatchConfig | None,
            resolve_scan_option(
                ctx, "batch", batch_config, scanjob.generate_config.batch
            ),
        )

    # resolve model config
    scanjob_model_config = scanjob.generate_config or GenerateConfig()
    scan_model_config = GenerateConfig(
        max_retries=resolve_scan_option(
            ctx, "max_retries", max_retries, scanjob_model_config.max_retries
        ),
        timeout=resolve_scan_option(
            ctx, "timeout", timeout, scanjob_model_config.timeout
        ),
        max_connections=resolve_scan_option(
            ctx,
            "max_connections",
            max_connections,
            scanjob_model_config.max_connections,
        ),
        cache=cache_config,
        batch=batch_config,
        max_tokens=resolve_scan_option(
            ctx, "max_tokens", max_tokens, scanjob_model_config.max_tokens
        ),
        temperature=resolve_scan_option(
            ctx, "temperature", temperature, scanjob_model_config.temperature
        ),
        top_p=resolve_scan_option(ctx, "top_p", top_p, scanjob_model_config.top_p),
        top_k=resolve_scan_option(ctx, "top_k", top_k, scanjob_model_config.top_k),
        reasoning_effort=resolve_scan_option(
            ctx,
            "reasoning_effort",
            reasoning_effort,
            scanjob_model_config.reasoning_effort,
        ),
        reasoning_tokens=resolve_scan_option(
            ctx,
            "reasoning_tokens",
            reasoning_tokens,
            scanjob_model_config.reasoning_tokens,
        ),
        reasoning_summary=resolve_scan_option(
            ctx,
            "reasoning_summary",
            reasoning_summary,
            scanjob_model_config.reasoning_summary,
        ),
        reasoning_history=resolve_scan_option(
            ctx,
            "reasoning_history",
            reasoning_history,
            scanjob_model_config.reasoning_history,
        ),
    )

    scan_max_transcripts = resolve_scan_option(
        ctx, "max_transcripts", max_transcripts, scanjob.max_transcripts
    )
    scan_max_processes = resolve_scan_option(
        ctx, "max_processes", max_processes, scanjob.max_processes
    )
    scan_limit = resolve_scan_option(ctx, "limit", limit, scanjob.limit)

    # shuffle
    if shuffle == -1:
        scan_shuffle: Literal[True] | int | None = True
    elif shuffle == 0:
        scan_shuffle = None
    else:
        scan_shuffle = shuffle
    scan_shuffle = resolve_scan_option(ctx, "shuffle", scan_shuffle, scanjob.shuffle)

    # tags and metadata
    scan_tags = resolve_scan_option(
        ctx, "tags", _parse_comma_separated(tags), scanjob.tags
    )
    scan_metadata = resolve_scan_option(
        ctx, "metadata", parse_cli_args(metadata), scanjob.metadata
    )

    # log level
    scan_log_level = resolve_scan_option(
        ctx, "log_level", common.get("log_level", None), scanjob.log_level
    )

    # run scan
    scan(
        scanners=scanjob,
        transcripts=tx,
        scans=scans,
        worklist=scan_worklist,
        validation=scan_validation,
        model=scan_model,
        model_config=scan_model_config,
        model_base_url=scan_model_base_url,
        model_args=scan_model_args,
        model_roles=scan_model_roles,
        max_transcripts=scan_max_transcripts,
        max_processes=scan_max_processes,
        limit=scan_limit,
        shuffle=scan_shuffle,
        tags=scan_tags,
        metadata=scan_metadata,
        fail_on_error=common["fail_on_error"],
        log_level=scan_log_level,
        dry_run=dry_run,
    )


def _parse_comma_separated(value: str | None) -> list[str] | None:
    if value is not None:
        return value.split(",")
    else:
        return None


def _parse_validation(
    v: tuple[str, ...] | None,
) -> ValidationSet | dict[str, ValidationSet] | None:
    """Parse command line validation arguments into validation set(s).

    The following formats are valid for the CLI:

    -V deception.csv  this applies the deception.csv validation dataset to a single scanner (in this case the return value is ValidationSet)

    -V myscanner:deception.csv  this applies the deception.csv validation dataset to the scanner named 'myscanner' (in this case dict[str, ValidationSet] is returned)

    -V deception.csv:gt or myscanner:deception.csv:gt (in this case a predicate 'gt' is appended to the specification which will result in this predicate ending up in the validation set)

    Note that multiple -V CLI args can be passed (that's why the 'v' is a tuple), so the following is valid:

    -V myscanner:deception.csv -V yourscanner:thrift.csv

    Args:
        v: Tuple of validation specification strings from CLI.

    Returns:
        ValidationSet if single validation without scanner name,
        dict[str, ValidationSet] if multiple validations or with scanner names,
        None if no validations provided.

    Raises:
        click.UsageError: If the validation format is invalid.
    """
    if not v or len(v) == 0:
        return None

    # Parse each validation spec
    validation_dict: dict[str, ValidationSet] = {}
    single_validation: ValidationSet | None = None

    for spec in v:
        parts = spec.split(":")

        scanner_name: str | None = None
        file_path: str
        predicate: ValidationPredicate = "eq"

        if len(parts) == 1:
            # Format: file.csv
            file_path = parts[0]
        elif len(parts) == 2:
            # Format: scanner:file.csv OR file.csv:predicate
            # Check if the last part is a known predicate
            if parts[1] in PREDICATES:
                # file.csv:predicate
                file_path = parts[0]
                predicate = parts[1]  # type: ignore[assignment]
            else:
                # scanner:file.csv
                scanner_name = parts[0]
                file_path = parts[1]
        elif len(parts) == 3:
            # Format: scanner:file.csv:predicate
            scanner_name = parts[0]
            file_path = parts[1]
            if parts[2] not in PREDICATES:
                raise click.UsageError(
                    f"Unknown validation predicate '{parts[2]}'. Valid predicates: {', '.join(PREDICATES.keys())}"
                )
            predicate = parts[2]  # type: ignore[assignment]
        else:
            raise click.UsageError(
                f"Invalid validation format: '{spec}'. Expected format: [scanner:]file[:predicate]"
            )

        # Load the validation set
        try:
            vset = validation_set(file_path, predicate=predicate)
        except Exception as e:
            raise click.UsageError(
                f"Error loading validation file '{file_path}': {e}"
            ) from e

        # Store in appropriate structure
        if scanner_name:
            if scanner_name in validation_dict:
                raise click.UsageError(
                    f"Multiple validation sets specified for scanner '{scanner_name}'"
                )
            validation_dict[scanner_name] = vset
        else:
            if single_validation is not None:
                raise click.UsageError(
                    "Multiple validation sets without scanner names. Use format 'scanner:file.csv' to specify which scanner each validation applies to."
                )
            single_validation = vset

    # Decide what to return based on what we collected
    if validation_dict and single_validation:
        raise click.UsageError(
            "Cannot mix validation sets with and without scanner names. Either specify scanner names for all validations or for none."
        )
    elif validation_dict:
        return validation_dict
    elif single_validation:
        return single_validation
    else:
        return None


T = TypeVar("T")


def resolve_scan_option(
    ctx: click.Context,
    option: str,
    option_value: T | None,
    scan_job_value: T | None,
) -> T | None:
    if scan_job_value is not None:
        if ctx.get_parameter_source(option) != ParameterSource.COMMANDLINE:
            return scan_job_value

    return option_value


def resolve_scan_option_multi(
    ctx: click.Context,
    options: list[str],
    option_value: T | None,
    scan_job_value: T | None,
) -> T | None:
    """Resolve option when value is derived from multiple CLI options."""
    if scan_job_value is not None:
        if not any(
            ctx.get_parameter_source(opt) == ParameterSource.COMMANDLINE
            for opt in options
        ):
            return scan_job_value
    return option_value
