import os
from logging import getLogger
from typing import Literal

from inspect_ai._display.core.rich import rich_initialise
from inspect_ai._util.thread import is_main_thread

from .constants import DEFAULT_DISPLAY

logger = getLogger(__name__)

DisplayType = Literal["rich", "plain", "none"]
"""Console display type."""


_display_type: DisplayType | None = None


def init_display_type(display: DisplayType | None = None) -> DisplayType:
    global _display_type
    if _display_type is None:
        # determine display
        display = (
            display or os.environ.get("SCOUT_DISPLAY", DEFAULT_DISPLAY).lower().strip()
        )

        # if we are on a background thread then throttle down to "plain"
        # ("full" requires textual which cannot run in a background thread
        # b/c it calls the Python signal function; "rich" assumes exclusive
        # display access which may not be the case for threads)
        if display in ["rich"] and not is_main_thread():
            display = "plain"

        match display:
            case "rich" | "plain" | "none":
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


PLAIN_DISPLAY_TYPES = ["plain"]
