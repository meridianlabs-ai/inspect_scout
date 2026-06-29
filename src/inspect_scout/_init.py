"""Process bootstrap helpers shared across entry points.

These initialize the runtime environment (platform, dotenv, display, logging)
used by the CLI commands, the view server, scan execution, and the multi-process
subprocess entry point. They live here — rather than in ``_scan`` — so callers
that only need to bootstrap (e.g. ``scout import``) don't pull in the full
scanning machinery.
"""

from dotenv import find_dotenv, load_dotenv
from inspect_ai._util.constants import DEFAULT_LOG_LEVEL
from inspect_ai._util.platform import platform_init as init_platform

from ._concurrency._mp_common import set_log_level
from ._display._display import (
    DisplayType,
    display_type_initialized,
    init_display_type,
)
from ._util.log import init_log

_initialized_environment: bool = False


def init_environment() -> None:
    global _initialized_environment
    if not _initialized_environment:
        dotenv_file = find_dotenv(usecwd=True)
        load_dotenv(dotenv_file)
        _initialized_environment = True


def top_level_sync_init(display: DisplayType | None) -> None:
    init_environment()
    init_display_type(display)


def top_level_async_init(
    log_level: str | None,
    *,
    main_process: bool = True,
) -> None:
    init_platform(hooks=False)
    init_environment()

    log_level = log_level or DEFAULT_LOG_LEVEL

    if not display_type_initialized():
        init_display_type("plain")
    init_log(log_level)
    if main_process:
        set_log_level(log_level)
