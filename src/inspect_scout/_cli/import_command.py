"""Scout import CLI command.

Imports transcripts from registered sources into a local transcript database.
"""

import asyncio
import importlib
import inspect
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import click
import yaml
from typing_extensions import Unpack

from inspect_scout._cli.common import (
    CommonOptions,
    common_options,
    process_common_options,
)
from inspect_scout._display._display import display
from inspect_scout._util.constants import DEFAULT_TRANSCRIPTS_DIR


def _discover_sources() -> dict[str, Callable[..., Any]]:
    """Discover available source functions from inspect_scout.sources.

    Returns:
        Dict mapping source name to source function.
    """
    sources_module = importlib.import_module("inspect_scout.sources")
    source_names: list[str] = getattr(sources_module, "__all__", [])
    sources: dict[str, Callable[..., Any]] = {}
    for name in sorted(source_names):
        fn = getattr(sources_module, name, None)
        if fn is not None and callable(fn):
            sources[name] = fn
    return sources


def _get_type_name(annotation: Any) -> str:
    """Extract a readable type name from a type annotation."""
    if annotation is inspect.Parameter.empty:
        return ""
    # Handle union types (e.g., str | None, list[str] | None)
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    # Handle UnionType (X | Y)
    if origin is not None and str(origin) == "typing.Union":
        # Filter out NoneType
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _get_type_name(non_none[0])
        return " | ".join(_get_type_name(a) for a in non_none)

    # Python 3.10+ union syntax (types.UnionType)
    import types

    if isinstance(annotation, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _get_type_name(non_none[0])
        return " | ".join(_get_type_name(a) for a in non_none)

    # Handle generic types like list[str], dict[str, str]
    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin))
        if args:
            arg_names = ", ".join(_get_type_name(a) for a in args)
            return f"{origin_name}[{arg_names}]"
        return origin_name

    # Handle PathLike
    if hasattr(annotation, "__name__"):
        return str(annotation.__name__)
    return str(annotation)


def _print_sources(sources: dict[str, Callable[..., Any]]) -> None:
    """Print available sources and their parameters."""
    d = display()
    d.print("\nAvailable sources:\n")
    for name, fn in sources.items():
        d.print(f"  [bold]{name}[/bold]", markup=True)
        sig = inspect.signature(fn)
        for param_name, param in sig.parameters.items():
            type_name = _get_type_name(param.annotation)
            d.print(f"    {param_name:<20s}{type_name}")
        d.print("")


def _has_datetime_annotation(annotation: Any) -> bool:
    """Check if a parameter annotation includes datetime."""
    # Handle string annotations (from `from __future__ import annotations`)
    if isinstance(annotation, str):
        parts = [p.strip() for p in annotation.split("|")]
        return "datetime" in parts
    if annotation is datetime:
        return True
    args = getattr(annotation, "__args__", ())
    return any(a is datetime for a in args)


def _has_int_annotation(annotation: Any) -> bool:
    """Check if a parameter annotation includes int."""
    # Handle string annotations (from `from __future__ import annotations`)
    if isinstance(annotation, str):
        parts = [p.strip() for p in annotation.split("|")]
        return "int" in parts
    if annotation is int:
        return True
    args = getattr(annotation, "__args__", ())
    return any(a is int for a in args)


def _has_str_annotation(annotation: Any) -> bool:
    """Check if a parameter annotation includes str."""
    if isinstance(annotation, str):
        parts = [p.strip() for p in annotation.split("|")]
        return "str" in parts
    if annotation is str:
        return True
    args = getattr(annotation, "__args__", ())
    return any(a is str for a in args)


def _coerce_value(value: str, annotation: Any) -> Any:
    """Coerce a string value based on the parameter's type annotation."""
    if _has_datetime_annotation(annotation):
        return datetime.fromisoformat(value)
    if _has_int_annotation(annotation):
        return int(value)
    # String-annotated params should stay as strings (YAML parsing would
    # coerce values like "123" or "true" into int/bool).
    if _has_str_annotation(annotation):
        return value
    # Use YAML parsing for everything else (handles lists, dicts, bools)
    try:
        parsed = yaml.safe_load(value)
        if parsed is not None:
            return parsed
        return value
    except yaml.YAMLError:
        return value


def _parse_params(
    source_fn: Callable[..., Any],
    params: tuple[str, ...],
    limit: int | None,
    from_time: str | None,
    to_time: str | None,
) -> dict[str, Any]:
    """Parse -P key=value pairs and promoted params into kwargs for a source function.

    Args:
        source_fn: The source function to call.
        params: Tuple of "key=value" strings from -P options.
        limit: Promoted --limit value.
        from_time: Promoted --from value.
        to_time: Promoted --to value.

    Returns:
        Dict of kwargs to pass to the source function.

    Raises:
        click.UsageError: If a parameter is unknown or value parsing fails.
    """
    sig = inspect.signature(source_fn)
    valid_params = set(sig.parameters.keys())

    # Parse -P key=value pairs
    kwargs: dict[str, Any] = {}
    for param_str in params:
        if "=" not in param_str:
            raise click.UsageError(
                f"Invalid parameter format: '{param_str}'. Expected 'name=value'."
            )
        key, value = param_str.split("=", 1)
        if key not in valid_params:
            valid_list = ", ".join(sorted(valid_params))
            raise click.UsageError(
                f"Unknown parameter '{key}' for source. Valid parameters: {valid_list}"
            )
        annotation = sig.parameters[key].annotation
        try:
            kwargs[key] = _coerce_value(value, annotation)
        except (ValueError, TypeError) as e:
            raise click.UsageError(f"Invalid value for '{key}': {e}") from e

    # Merge promoted params (take precedence over -P)
    if limit is not None:
        if "limit" in valid_params:
            kwargs["limit"] = limit
        else:
            raise click.UsageError("This source does not accept a 'limit' parameter.")

    if from_time is not None:
        if "from_time" in valid_params:
            try:
                kwargs["from_time"] = datetime.fromisoformat(from_time)
            except ValueError as e:
                raise click.UsageError(f"Invalid --from value: {e}") from e
        else:
            raise click.UsageError(
                "This source does not accept a 'from_time' parameter."
            )

    if to_time is not None:
        if "to_time" in valid_params:
            try:
                kwargs["to_time"] = datetime.fromisoformat(to_time)
            except ValueError as e:
                raise click.UsageError(f"Invalid --to value: {e}") from e
        else:
            raise click.UsageError("This source does not accept a 'to_time' parameter.")

    return kwargs


async def _run_import(
    source_fn: Callable[..., Any],
    source_name: str,
    kwargs: dict[str, Any],
    transcripts_dir: str,
) -> None:
    """Execute the import: call source function and write to database."""
    from inspect_scout._transcript.database.factory import transcripts_db

    d = display()
    d.print(f"\nImporting from [bold]{source_name}[/bold]...\n", markup=True)

    async with transcripts_db(transcripts_dir) as db:
        await db.insert(source_fn(**kwargs))

    d.print("\nImport complete. To view transcripts:\n")
    d.print(f"  scout view -T {transcripts_dir}\n")


async def _run_dry_run(
    source_fn: Callable[..., Any],
    source_name: str,
    kwargs: dict[str, Any],
) -> None:
    """Execute a dry run: fetch transcripts and display summary without writing."""
    from inspect_scout._transcript.types import Transcript

    d = display()
    d.print(f"\nDry run — fetching from [bold]{source_name}[/bold]...\n", markup=True)

    transcripts: list[Transcript] = []
    async_iter = source_fn(**kwargs)
    async for transcript in async_iter:
        transcripts.append(transcript)

    if not transcripts:
        d.print("No transcripts found.")
        return

    # Print summary table
    d.print(f"{'ID':<40s} {'Date':<12s} {'Model':<25s} {'Messages':>8s} {'Tokens':>8s}")
    d.print("-" * 95)
    for t in transcripts:
        date_str = t.date[:10] if t.date else "-"
        model_str = (t.model or "-")[:25]
        msg_count = str(t.message_count) if t.message_count is not None else "-"
        token_count = str(t.total_tokens) if t.total_tokens is not None else "-"
        d.print(
            f"{t.transcript_id[:40]:<40s} {date_str:<12s} {model_str:<25s} "
            f"{msg_count:>8s} {token_count:>8s}"
        )

    d.print(f"\n{len(transcripts)} transcript(s) found.")


@click.command("import")
@click.argument("source", required=False, default=None)
@click.option(
    "-T",
    "--transcripts",
    type=str,
    default=DEFAULT_TRANSCRIPTS_DIR,
    help="Transcripts database directory.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of transcripts to import.",
)
@click.option(
    "--from",
    "from_time",
    type=str,
    default=None,
    help="Only import transcripts on or after this time (ISO 8601).",
)
@click.option(
    "--to",
    "to_time",
    type=str,
    default=None,
    help="Only import transcripts before this time (ISO 8601).",
)
@click.option(
    "-P",
    "params",
    type=str,
    multiple=True,
    help="Source parameter as name=value (repeatable).",
)
@click.option(
    "--sources",
    is_flag=True,
    default=False,
    help="List available sources and their parameters.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch and display summary without writing.",
)
def _remove_transcripts_dir(path: Path) -> None:
    """Remove a transcripts directory, validating it is a real directory."""
    import shutil

    if not path.is_dir():
        raise click.UsageError(f"'{path}' exists but is not a directory.")
    if path.is_symlink():
        path.unlink()
    else:
        shutil.rmtree(path)


@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing transcripts directory without prompting.",
)
@common_options
def import_command(
    source: str | None,
    transcripts: str,
    limit: int | None,
    from_time: str | None,
    to_time: str | None,
    params: tuple[str, ...],
    sources: bool,
    dry_run: bool,
    overwrite: bool,
    **common: Unpack[CommonOptions],
) -> None:
    """Import transcripts from a source."""
    process_common_options(common)

    available_sources = _discover_sources()

    # Handle --sources flag
    if sources:
        _print_sources(available_sources)
        return

    # Require source name if not listing
    if source is None:
        raise click.UsageError(
            "Missing source name. Use 'scout import --sources' to see available sources."
        )

    # Validate source name
    if source not in available_sources:
        source_list = ", ".join(sorted(available_sources.keys()))
        raise click.UsageError(
            f"Unknown source '{source}'. Available sources: {source_list}"
        )

    source_fn = available_sources[source]

    # Parse parameters
    kwargs = _parse_params(source_fn, params, limit, from_time, to_time)

    if dry_run:
        asyncio.run(_run_dry_run(source_fn, source, kwargs))
    else:
        # Check if transcripts directory exists
        transcripts_path = Path(transcripts)
        if transcripts_path.exists():
            if overwrite:
                _remove_transcripts_dir(transcripts_path)
            else:
                from rich.prompt import Prompt

                choice = Prompt.ask(
                    f"\nTranscripts directory '{transcripts}' already exists\n"
                    "  [bold]1[/bold]) Add transcripts (existing transcripts won't be re-imported)\n"
                    "  [bold]2[/bold]) Overwrite (delete existing transcripts first)\n"
                    "  [bold]3[/bold]) Cancel\n",
                    choices=["1", "2", "3"],
                    default="1",
                )
                if choice == "3":
                    raise SystemExit(0)
                if choice == "2":
                    _remove_transcripts_dir(transcripts_path)

        asyncio.run(_run_import(source_fn, source, kwargs, transcripts))
