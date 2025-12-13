import functools
from typing import Any, Callable, Literal, cast

import click
from inspect_ai._util.constants import ALL_LOG_LEVELS, DEFAULT_LOG_LEVEL
from typing_extensions import TypedDict

from inspect_scout._display._display import DisplayType, display, init_display_type
from inspect_scout._util.constants import DEFAULT_DISPLAY


class CommonOptions(TypedDict):
    display: Literal["rich", "plain", "log", "none"]
    log_level: str
    debug: bool
    debug_port: int
    fail_on_error: bool


def common_options(func: Callable[..., Any]) -> Callable[..., click.Context]:
    @click.option(
        "--display",
        type=click.Choice(
            ["rich", "plain", "log", "none"],
            case_sensitive=False,
        ),
        default=DEFAULT_DISPLAY,
        envvar="SCOUT_DISPLAY",
        help=f"Set the display type (defaults to '{DEFAULT_DISPLAY}')",
    )
    @click.option(
        "--log-level",
        type=click.Choice(
            [level.lower() for level in ALL_LOG_LEVELS],
            case_sensitive=False,
        ),
        default=DEFAULT_LOG_LEVEL,
        envvar="SCOUT_LOG_LEVEL",
        help=f"Set the log level (defaults to '{DEFAULT_LOG_LEVEL}')",
    )
    @click.option(
        "--debug", is_flag=True, envvar="SCOUT_DEBUG", help="Wait to attach debugger"
    )
    @click.option(
        "--debug-port",
        default=5678,
        envvar="SCOUT_DEBUG_PORT",
        help="Port number for debugger",
    )
    @click.option(
        "--fail-on-error",
        type=bool,
        is_flag=True,
        default=False,
        help="Re-raise exceptions instead of capturing them in results",
        envvar="SCOUT_SCAN_FAIL_ON_ERROR",
    )
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> click.Context:
        return cast(click.Context, func(*args, **kwargs))

    return wrapper


def process_common_options(options: CommonOptions) -> None:
    # propagate display
    display_type = cast(DisplayType, options["display"].lower().strip())
    init_display_type(display_type)

    # attach debugger if requested
    if options["debug"]:
        import debugpy

        debugpy.listen(options["debug_port"])
        display().print("Waiting for debugger attach")
        debugpy.wait_for_client()
        display().print("Debugger attached")
