"""Shared click option decorators for the ``scout scan`` command.

Each option is exported as a module-level decorator so callers (e.g. tools
that re-expose ``scout scan``'s CLI surface) can import and apply them
selectively. ``SCAN_OPTIONS`` is the full ordered list, and ``scan_options``
is a helper decorator that applies all of them.
"""

from typing import Any, Callable, TypeVar, cast

import click
from inspect_ai._cli.util import (
    int_bool_or_str_flag_callback,
    int_or_bool_flag_callback,
)
from inspect_ai._util.constants import DEFAULT_CACHE_DAYS

from .._util.constants import DEFAULT_BATCH_SIZE, DEFAULT_MAX_TRANSCRIPTS

F = TypeVar("F", bound=Callable[..., Any])


scanjob_args_option = click.option(
    "-S",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_ARGS",
    help="One or more scanjob or scanner arguments (e.g. -S arg=value)",
)

transcripts_option = click.option(
    "-T",
    "--transcripts",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_TRANSCRIPTS",
    help="One or more transcript sources (e.g. -T ./logs)",
)

filter_option = click.option(
    "-F",
    "--filter",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_FILTER",
    help="One or more transcript filters (e.g. -F \"task_set = 'cybench'\")",
)

scans_option = click.option(
    "--scans",
    type=str,
    default=None,
    help="Location to write scan results to.",
    envvar="SCOUT_SCAN_SCANS",
)

results_option = click.option(
    "--results",
    type=str,
    default=None,
    hidden=True,
    envvar="SCOUT_SCAN_RESULTS",
)

worklist_option = click.option(
    "--worklist",
    type=click.Path(exists=True),
    help="Transcript ids to process for each scanner (JSON or YAML file).",
    envvar="SCOUT_SCAN_WORKLIST",
)

validation_option = click.option(
    "-V",
    "--validation",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_VALIDATION",
    help="One or more validation sets to apply for scanners (e.g. -V myscanner:deception.csv)",
)

model_option = click.option(
    "--model",
    type=str,
    help="Model used by default for llm scanners.",
    envvar="SCOUT_SCAN_MODEL",
)

model_base_url_option = click.option(
    "--model-base-url",
    type=str,
    envvar="SCOUT_SCAN_MODEL_BASE_URL",
    help="Base URL for for model API",
)

model_args_option = click.option(
    "-M",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_MODEL_ARGS",
    help="One or more native model arguments (e.g. -M arg=value)",
)

model_config_option = click.option(
    "--model-config",
    type=str,
    envvar="SCOUT_SCAN_MODEL_CONFIG",
    help="YAML or JSON config file with model arguments.",
)

model_role_option = click.option(
    "--model-role",
    multiple=True,
    type=str,
    envvar="SCOUT_SCAN_MODEL_ROLE",
    help='Named model role with model name or YAML/JSON config, e.g. --model-role critic=openai/gpt-4o or --model-role grader="{model: mockllm/model, temperature: 0.5}"',
)

max_transcripts_option = click.option(
    "--max-transcripts",
    type=int,
    help=f"Maximum number of transcripts to scan concurrently (defaults to {DEFAULT_MAX_TRANSCRIPTS})",
    envvar="SCOUT_SCAN_MAX_TRANSCRIPTS",
)

max_processes_option = click.option(
    "--max-processes",
    type=int,
    help="Number of worker processes. Defaults to 4.",
    envvar="SCOUT_SCAN_MAX_PROCESSES",
)

limit_option = click.option(
    "--limit",
    type=int,
    help="Limit number of transcripts to scan.",
    envvar="SCOUT_SCAN_LIMIT",
)

shuffle_option = click.option(
    "--shuffle",
    is_flag=False,
    flag_value="true",
    default=None,
    callback=int_or_bool_flag_callback(-1),
    help="Shuffle order of transcripts (pass a seed to make the order deterministic)",
    envvar=["SCOUT_SCAN_SHUFFLE"],
)

tags_option = click.option(
    "--tags",
    type=str,
    help="Tags to associate with this scan job (comma separated)",
    envvar="SCOUT_SCAN_TAGS",
)

metadata_option = click.option(
    "--metadata",
    multiple=True,
    type=str,
    help="Metadata to associate with this scan job (more than one --metadata argument can be specified).",
    envvar="SCOUT_SCAN_METADATA",
)

cache_option = click.option(
    "--cache",
    is_flag=False,
    flag_value="true",
    default=None,
    callback=int_bool_or_str_flag_callback(DEFAULT_CACHE_DAYS, None),
    help="Policy for caching of model generations. Specify --cache to cache with 7 day expiration (7D). Specify an explicit duration (e.g. (e.g. 1h, 3d, 6M) to set the expiration explicitly (durations can be expressed as s, m, h, D, W, M, or Y). Alternatively, pass the file path to a YAML or JSON config file with a full `CachePolicy` configuration.",
    envvar="SCOUT_SCAN_CACHE",
)

batch_option = click.option(
    "--batch",
    is_flag=False,
    flag_value="true",
    default=None,
    callback=int_bool_or_str_flag_callback(DEFAULT_BATCH_SIZE, None),
    help="Batch requests together to reduce API calls when using a model that supports batching (by default, no batching). Specify --batch to batch with default configuration, specify a batch size e.g. `--batch=1000` to configure batches of 1000 requests, or pass the file path to a YAML or JSON config file with batch configuration.",
    envvar="SCOUT_SCAN_BATCH",
)

max_connections_option = click.option(
    "--max-connections",
    type=int,
    help="Maximum number of concurrent connections to Model API (defaults to max_transcripts)",
    envvar="SCOUT_SCAN_MAX_CONNECTIONS",
)

max_retries_option = click.option(
    "--max-retries",
    type=int,
    help="Maximum number of times to retry model API requests (defaults to unlimited)",
    envvar="SCOUT_SCAN_MAX_RETRIES",
)

timeout_option = click.option(
    "--timeout",
    type=int,
    help="Model API request timeout in seconds (defaults to no timeout)",
    envvar="SCOUT_SCAN_TIMEOUT",
)

max_tokens_option = click.option(
    "--max-tokens",
    type=int,
    help="The maximum number of tokens that can be generated in the completion (default is model specific)",
    envvar="SCOUT_SCAN_MAX_TOKENS",
)

temperature_option = click.option(
    "--temperature",
    type=float,
    help="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.",
    envvar="SCOUT_SCAN_TEMPERATURE",
)

top_p_option = click.option(
    "--top-p",
    type=float,
    help="An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass.",
    envvar="SCOUT_SCAN_TOP_P",
)

top_k_option = click.option(
    "--top-k",
    type=int,
    help="Randomly sample the next word from the top_k most likely next words. Anthropic, Google, HuggingFace, and vLLM only.",
    envvar="SCOUT_SCAN_TOP_K",
)

reasoning_effort_option = click.option(
    "--reasoning-effort",
    type=click.Choice(["minimal", "low", "medium", "high"]),
    help="Constrains effort on reasoning for reasoning models (defaults to `medium`). Open AI o-series and gpt-5 models only.",
    envvar="SCOUT_SCAN_REASONING_EFFORT",
)

reasoning_tokens_option = click.option(
    "--reasoning-tokens",
    type=int,
    help="Maximum number of tokens to use for reasoning. Anthropic Claude models only.",
    envvar="SCOUT_SCAN_REASONING_TOKENS",
)

reasoning_summary_option = click.option(
    "--reasoning-summary",
    type=click.Choice(["concise", "detailed", "auto"]),
    help="Provide summary of reasoning steps (defaults to no summary). Use 'auto' to access the most detailed summarizer available for the current model. OpenAI reasoning models only.",
    envvar="SCOUT_SCAN_REASONING_SUMMARY",
)

reasoning_history_option = click.option(
    "--reasoning-history",
    type=click.Choice(["none", "all", "last", "auto"]),
    help='Include reasoning in chat message history sent to generate (defaults to "auto", which uses the recommended default for each provider)',
    envvar="SCOUT_SCAN_REASONING_HISTORY",
)

response_schema_option = click.option(
    "--response-schema",
    type=str,
    help="JSON schema for desired response format (output should still be validated). OpenAI, Google, and Mistral only.",
    envvar="SCOUT_SCAN_RESPONSE_SCHEMA",
)

dry_run_option = click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print resolved scanners and transcript counts without scanning.",
    envvar="SCOUT_SCAN_DRY_RUN",
)


SCAN_OPTIONS: list[Callable[..., Any]] = [
    scanjob_args_option,
    transcripts_option,
    filter_option,
    scans_option,
    results_option,
    worklist_option,
    validation_option,
    model_option,
    model_base_url_option,
    model_args_option,
    model_config_option,
    model_role_option,
    max_transcripts_option,
    max_processes_option,
    limit_option,
    shuffle_option,
    tags_option,
    metadata_option,
    cache_option,
    batch_option,
    max_connections_option,
    max_retries_option,
    timeout_option,
    max_tokens_option,
    temperature_option,
    top_p_option,
    top_k_option,
    reasoning_effort_option,
    reasoning_tokens_option,
    reasoning_summary_option,
    reasoning_history_option,
    response_schema_option,
    dry_run_option,
]


def scan_options(func: F) -> F:
    """Apply all scan command click options to ``func``."""
    for option in reversed(SCAN_OPTIONS):
        func = cast(F, option(func))
    return func
