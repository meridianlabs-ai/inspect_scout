import logging
from typing import Any

from typing_extensions import override

from .plain import DisplayPlain
from .._recorder.recorder import Status

logger = logging.getLogger(__name__)


class DisplayLog(DisplayPlain):
    @override
    def print(
            self,
            *objects: Any,
            sep: str = " ",
            end: str = "\n",
            markup: bool | None = None,
            highlight: bool | None = None,
    ) -> None:
        logger.info(sep.join([str(obj) for obj in objects]))

    @override
    def scan_interrupted(self, message_or_exc: str | Exception, status: Status) -> None:
        if isinstance(message_or_exc, Exception):
            logger.warning("Scan interrupted", extra={"status": status}, exc_info=message_or_exc)
        else:
            logger.warning(message_or_exc, extra={"status": status})

    @override
    def scan_complete(self, status: Status) -> None:
        if status.complete:
            logger.info("Scan complete: %s", status.summary, extra={"status": status})
        else:
            logger.info("%d scan errors occurred!", len(status.errors), extra={"status": status})

    @override
    def scan_status(self, status: Status) -> None:
        if status.complete:
            logger.info("Scan complete: %s", status.summary, extra={"status": status})
        elif len(status.errors) > 0:
            logger.info("%d scan errors occurred!", len(status.errors), extra={"status": status})
        else:
            logger.info("Scan interrupted", extra={"status": status})
