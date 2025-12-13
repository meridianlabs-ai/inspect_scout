import logging
from typing import Any

from typing_extensions import override

from .._recorder.recorder import Status
from .plain import DisplayPlain


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
        logging.info(sep.join([str(obj) for obj in objects]))

    @override
    def scan_interrupted(self, message_or_exc: str | Exception, status: Status) -> None:
        if isinstance(message_or_exc, Exception):
            logging.warning(
                "Scan interrupted", extra={"status": status}, exc_info=message_or_exc
            )
        else:
            logging.warning(message_or_exc, extra={"status": status})

    @override
    def scan_complete(self, status: Status) -> None:
        if status.complete:
            logging.info("Scan complete: %s", status.summary, extra={"status": status})
        else:
            logging.info(
                "%d scan errors occurred!", len(status.errors), extra={"status": status}
            )

    @override
    def scan_status(self, status: Status) -> None:
        if status.complete:
            logging.info("Scan complete: %s", status.summary, extra={"status": status})
        elif len(status.errors) > 0:
            logging.info(
                "%d scan errors occurred!", len(status.errors), extra={"status": status}
            )
        else:
            logging.info("Scan interrupted", extra={"status": status})
