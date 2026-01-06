from logging import getLogger
from typing import NoReturn

from inspect_ai._util.logger import warn_once

logger = getLogger(__name__)


def show_results_warning() -> None:
    warn_once(logger, "Scan job 'results' is deprecated, please use 'scans' instead")


def raise_results_error() -> NoReturn:
    raise TypeError(
        "Unexpected value 'results' present when 'scans' has already been specified."
    )
