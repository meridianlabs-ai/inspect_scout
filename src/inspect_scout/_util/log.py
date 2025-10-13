from inspect_ai._util.logger import LogHandlerVar, init_logger

from inspect_scout._util.constants import PKG_NAME
from inspect_scout._util.trace import scout_trace_dir


def init_log(log_level: str | None) -> None:
    init_logger(
        log_level=log_level,
        log_level_transcript="INFO",
        env_prefix="SCOUT",
        pkg_name=PKG_NAME,
        trace_dir=scout_trace_dir(),
        log_handler_var=_scout_log_handler,
    )


_scout_log_handler: LogHandlerVar = LogHandlerVar(handler=None)
