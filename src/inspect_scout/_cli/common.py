import functools
import os
from typing import Any, Callable, Literal, TypeVar, cast

import click
from click.core import ParameterSource
from inspect_ai._util.constants import ALL_LOG_LEVELS, DEFAULT_LOG_LEVEL
from typing_extensions import TypedDict

from inspect_scout._concurrency._mp_common import set_log_level
from inspect_scout._display._display import DisplayType, display, init_display_type
from inspect_scout._project._project import read_project
from inspect_scout._util.constants import DEFAULT_DISPLAY, DEFAULT_SERVER_HOST
from inspect_scout._util.log import init_log

F = TypeVar("F", bound=Callable[..., Any])


class CommonOptions(TypedDict):
    display: Literal["rich", "plain", "log", "none"]
    log_level: str
    debug: bool
    debug_port: int
    fail_on_error: bool


display_option = click.option(
    "--display",
    type=click.Choice(
        ["rich", "plain", "log", "none"],
        case_sensitive=False,
    ),
    default=DEFAULT_DISPLAY,
    envvar="SCOUT_DISPLAY",
    help=f"Set the display type (defaults to '{DEFAULT_DISPLAY}')",
)

log_level_option = click.option(
    "--log-level",
    type=click.Choice(
        [level.lower() for level in ALL_LOG_LEVELS],
        case_sensitive=False,
    ),
    default=DEFAULT_LOG_LEVEL,
    envvar="SCOUT_LOG_LEVEL",
    help=f"Set the log level (defaults to '{DEFAULT_LOG_LEVEL}')",
)

debug_option = click.option(
    "--debug", is_flag=True, envvar="SCOUT_DEBUG", help="Wait to attach debugger"
)

debug_port_option = click.option(
    "--debug-port",
    default=5678,
    envvar="SCOUT_DEBUG_PORT",
    help="Port number for debugger",
)

fail_on_error_option = click.option(
    "--fail-on-error",
    type=bool,
    is_flag=True,
    default=False,
    help="Re-raise exceptions instead of capturing them in results",
    envvar="SCOUT_SCAN_FAIL_ON_ERROR",
)


COMMON_OPTIONS: list[Callable[..., Any]] = [
    display_option,
    log_level_option,
    debug_option,
    debug_port_option,
    fail_on_error_option,
]


def common_options(func: Callable[..., Any]) -> Callable[..., click.Context]:
    for option in reversed(COMMON_OPTIONS):
        func = option(func)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> click.Context:
        return cast(click.Context, func(*args, **kwargs))

    return wrapper


def resolve_log_level(ctx: click.Context, options: CommonOptions) -> str:
    """Resolve the effective log level for a CLI command.

    Precedence (highest to lowest):

    1. The ``--log-level`` argument when supplied explicitly on the command line.
    2. The ``log_level`` field of the project configuration (``scout.yaml``).
    3. The ``SCOUT_LOG_LEVEL`` environment variable.
    4. The built-in default (``DEFAULT_LOG_LEVEL``).

    Environment variable and default both surface as ``options["log_level"]``
    (click resolves them into the option value), so they are handled by the
    final fallback.

    Args:
        ctx: The click context for the command (used to determine whether
            ``--log-level`` was supplied on the command line).
        options: The resolved common options for the command.

    Returns:
        The effective log level.
    """
    # an explicit command-line argument always wins
    if ctx.get_parameter_source("log_level") == ParameterSource.COMMANDLINE:
        return options["log_level"]

    # otherwise prefer a project-configured value
    project_log_level = read_project().log_level
    if project_log_level is not None:
        return project_log_level

    # fall back to the click-resolved value (environment variable or default)
    return options["log_level"]


def process_common_options(ctx: click.Context, options: CommonOptions) -> None:
    # propagate display
    display_type = cast(DisplayType, options["display"].lower().strip())
    init_display_type(display_type)

    # write the resolved log_level back so commands that forward it into the
    # scan/view runtime pass an already-resolved value (the runtime's
    # `log_level or project.log_level` keeps a truthy log_level as-is).
    log_level = resolve_log_level(ctx, options)
    options["log_level"] = log_level
    init_log(log_level)
    set_log_level(log_level)

    # attach debugger if requested
    if options["debug"]:
        import debugpy

        debugpy.listen(options["debug_port"])
        display().print("Waiting for debugger attach")
        debugpy.wait_for_client()
        display().print("Debugger attached")


def view_options(func: Callable[..., Any]) -> Callable[..., click.Context]:
    @click.option(
        "--host",
        default=DEFAULT_SERVER_HOST,
        help="Tcp/Ip host for view server.",
    )
    @click.option(
        "--port",
        type=int,
        default=7576,
        help="Port to use for the view server.",
        envvar="SCOUT_VIEW_PORT",
    )
    @click.option(
        "--browser/--no-browser",
        default=None,
        help="Open in web browser.",
    )
    @click.option(
        "--root-path",
        type=str,
        default="",
        envvar="UVICORN_ROOT_PATH",
        help="ASGI root_path for serving behind a reverse proxy.",
    )
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> click.Context:
        return cast(click.Context, func(*args, **kwargs))

    return wrapper


def resolve_view_authorization() -> str | None:
    """Resolve and consume the view authorization token from environment."""
    INSPECT_VIEW_AUTHORIZATION_TOKEN = "INSPECT_VIEW_AUTHORIZATION_TOKEN"
    authorization = os.environ.get(INSPECT_VIEW_AUTHORIZATION_TOKEN, None)
    if authorization:
        del os.environ[INSPECT_VIEW_AUTHORIZATION_TOKEN]
        os.unsetenv(INSPECT_VIEW_AUTHORIZATION_TOKEN)
    return authorization
