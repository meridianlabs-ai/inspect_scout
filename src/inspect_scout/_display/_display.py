import os
from logging import getLogger
from typing import Literal, cast

from inspect_ai._display.core.rich import rich_initialise
from inspect_ai._util.thread import is_main_thread

from .._util.constants import DEFAULT_DISPLAY
from .log import DisplayLog
from .none import DisplayNone
from .plain import DisplayPlain
from .protocol import Display
from .rich import DisplayRich

logger = getLogger(__name__)

DisplayType = Literal["rich", "plain", "log", "none"]
"""Console display type."""


def display() -> Display:
    global _display
    if _display is None:
        match display_type():
            case "none":
                _display = DisplayNone()
            case "log":
                _display = DisplayLog()
            case "plain":
                _display = DisplayPlain()
            case "rich":
                _display = DisplayRich()

    return _display


def init_display_type(display: DisplayType | None = None) -> DisplayType:
    global _display_type
    if _display_type is None:
        # determine display (force 'plain' if in diagnostics mode)
        if os.getenv("SCOUT_DIAGNOSTICS", "false").lower() in (
            "1",
            "true",
            "yes",
        ):
            display = "plain"

        display = cast(
            DisplayType,
            display or os.environ.get("SCOUT_DISPLAY", DEFAULT_DISPLAY).lower().strip(),
        )

        # if we are on a background thread then throttle down to "plain"
        # ("full" requires textual which cannot run in a background thread
        # b/c it calls the Python signal function; "rich" assumes exclusive
        # display access which may not be the case for threads)
        if display in ["rich"] and not is_main_thread():
            display = "plain"

        match display:
            case "rich" | "plain" | "log" | "none":
                _display_type = display
            case _:
                logger.warning(
                    f"Unknown display type '{display}' (setting display to '{DEFAULT_DISPLAY}')"
                )
                _display_type = DEFAULT_DISPLAY

        # initialize rich
        rich_initialise(_display_type, _display_type in PLAIN_DISPLAY_TYPES)

    return _display_type


def display_type() -> DisplayType:
    """Get the current console display type.

    Returns:
       DisplayType: Display type.
    """
    global _display_type
    if _display_type:
        return _display_type
    else:
        return init_display_type()


def display_type_plain() -> bool:
    """Does the current display type prefer plain text?

    Returns:
       bool: True if the display type is "plain".
    """
    return display_type() in PLAIN_DISPLAY_TYPES


def display_type_initialized() -> bool:
    global _display_type
    return _display_type is not None


_display: Display | None = None

_display_type: DisplayType | None = None

PLAIN_DISPLAY_TYPES = ["log", "plain"]
