import click
from inspect_ai._cli.trace import (
    anomalies_command_impl,
    dump_command_impl,
    http_command_impl,
    list_command_impl,
)

from inspect_scout._util.trace import scout_trace_dir


@click.group("trace")
def trace_command() -> None:
    """List and read execution traces.

    Inspect Scout includes a TRACE log-level which is right below the HTTP and INFO log levels (so not written to the console by default). However, TRACE logs are always recorded to a separate file, and the last 10 TRACE logs are preserved. The 'trace' command provides ways to list and read these traces.
    """
    return None


@trace_command.command("list")
@click.option(
    "--json",
    type=bool,
    is_flag=True,
    default=False,
    help="Output listing as JSON",
)
def list_command(json: bool) -> None:
    """List all trace files."""
    list_command_impl(json, scout_trace_dir())


@trace_command.command("dump")
@click.argument("trace-file", type=str, required=False)
@click.option(
    "--filter",
    type=str,
    help="Filter (applied to trace message field).",
)
def dump_command(trace_file: str | None, filter: str | None) -> None:
    """Dump a trace file to stdout (as a JSON array of log records)."""
    dump_command_impl(trace_file, filter, scout_trace_dir())


@trace_command.command("http")
@click.argument("trace-file", type=str, required=False)
@click.option(
    "--filter",
    type=str,
    help="Filter (applied to trace message field).",
)
@click.option(
    "--failed",
    type=bool,
    is_flag=True,
    default=False,
    help="Show only failed HTTP requests (non-200 status)",
)
@click.option(
    "--json",
    type=bool,
    is_flag=True,
    default=False,
    help="Output as JSON (a `{trace_file, as_of, requests}` envelope).",
)
def http_command(
    trace_file: str | None, filter: str | None, failed: bool, json: bool
) -> None:
    """View all HTTP requests in the trace log."""
    http_command_impl(trace_file, filter, failed, json, trace_dir=scout_trace_dir())


@trace_command.command("anomalies")
@click.argument("trace-file", type=str, required=False)
@click.option(
    "--filter",
    type=str,
    help="Filter (applied to trace message field).",
)
@click.option(
    "--all",
    is_flag=True,
    default=False,
    help="Show all anomalies including errors and timeouts (by default only still running and cancelled actions are shown; JSON output always includes all buckets).",
)
@click.option(
    "--json",
    type=bool,
    is_flag=True,
    default=False,
    help="Output as JSON (a `{trace_file, as_of, running, cancelled, errors, timeouts}` envelope).",
)
def anomalies_command(
    trace_file: str | None, filter: str | None, all: bool, json: bool
) -> None:
    """Look for anomalies in a trace file (never completed or cancelled actions)."""
    anomalies_command_impl(trace_file, filter, all, json, trace_dir=scout_trace_dir())
