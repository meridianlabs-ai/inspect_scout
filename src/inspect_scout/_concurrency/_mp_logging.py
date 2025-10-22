import logging
from logging import Logger, getLogger
from typing import Callable

from inspect_ai._util.logger import LogHandler as InspectLogHandler


def patch_inspect_log_handler(patch_fn: Callable[[logging.LogRecord], None]) -> None:
    """Replace the emit method of the Inspect log handler with a custom function.

    This function allows worker processes to intercept log records and redirect them
    to the parent process via the upstream queue instead of handling them locally.

    Note: Uses object.__setattr__ to bypass the frozen dataclass restriction on
    InspectLogHandler, allowing runtime patching of the emit method.

    Args:
        patch_fn: A callable that receives a LogRecord and handles it (typically by
            queuing it for transmission to the parent process).
    """
    object.__setattr__(find_inspect_log_handler(), "emit", patch_fn)


def find_inspect_log_handler() -> InspectLogHandler:
    """Locate the Inspect AI log handler in the Python logging hierarchy.

    Traverses the logger tree starting from the root logger, searching through each
    logger's handlers to find the InspectLogHandler instance. This handler is used
    by Inspect AI to manage structured logging output.

    The function walks up the logger parent chain to ensure it checks all loggers
    in the hierarchy, as the handler could be attached at any level.

    Returns:
        The InspectLogHandler instance found in the logging hierarchy.

    Raises:
        RuntimeError: If no InspectLogHandler is found in the entire logging hierarchy,
            which indicates that Inspect AI's logging system has not been properly
            initialized.
    """
    c: Logger | None = getLogger()
    while c is not None:
        for handler in c.handlers:
            if isinstance(handler, InspectLogHandler):
                return handler
        c = c.parent
    raise RuntimeError("Unable to find inspect log handler")
