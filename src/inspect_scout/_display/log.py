import contextlib
import dataclasses
import logging
import time
from typing import Any, Iterator, Sequence

from inspect_ai._util.format import format_progress_time
from inspect_ai.util import throttle
from typing_extensions import override

from .._concurrency.common import ScanMetrics
from .._recorder.recorder import Status
from .._recorder.summary import Summary
from .._scancontext import ScanContext
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .plain import DisplayPlain
from .protocol import ScanDisplay, TextProgress

logger = logging.getLogger(__name__)


def _status_for_log(status: Status) -> Status:
    """Return a copy of *status* with tracebacks stripped from errors.

    Tracebacks are recorded in the scan database and shown in the UI.
    They're noisy in structured logs, so we blank them out here.
    """
    if not status.errors:
        return status
    return dataclasses.replace(
        status,
        errors=[error.model_copy(update={"traceback": ""}) for error in status.errors],
    )


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
    @contextlib.contextmanager
    def text_progress(self, caption: str, count: bool | int) -> Iterator[TextProgress]:
        yield TextProgressLog(caption, count)

    @override
    @contextlib.contextmanager
    def scan_display(
        self,
        scan: ScanContext,
        scan_location: str,
        summary: Summary,
        total: int,
        skipped: int,
    ) -> Iterator[ScanDisplay]:
        logger.info(
            "Starting scan",
            extra={
                "total_scans": total,
                "skipped_scans": skipped,
                "scan_location": scan_location,
            },
        )
        yield ScanDisplayLog(total, skipped)

    @override
    def scan_interrupted(self, message_or_exc: str | Exception, status: Status) -> None:
        log_status = _status_for_log(status)
        if isinstance(message_or_exc, Exception):
            logger.warning(
                "Scan interrupted",
                extra={"status": log_status},
                exc_info=message_or_exc,
            )
        else:
            logger.warning(message_or_exc, extra={"status": log_status})

    @override
    def scan_complete(self, status: Status) -> None:
        log_status = _status_for_log(status)
        if status.complete:
            logger.info(
                "Scan complete: %s", status.summary, extra={"status": log_status}
            )
        else:
            logger.info(
                "%d scan errors occurred!",
                len(status.errors),
                extra={"status": log_status},
            )

    @override
    def scan_status(self, status: Status) -> None:
        log_status = _status_for_log(status)
        if status.complete:
            logger.info(
                "Scan complete: %s", status.summary, extra={"status": log_status}
            )
        elif len(status.errors) > 0:
            logger.info(
                "%d scan errors occurred!",
                len(status.errors),
                extra={"status": log_status},
            )
        else:
            logger.info("Scan interrupted", extra={"status": log_status})


class ScanDisplayLog(ScanDisplay):
    def __init__(self, total: int, skipped: int) -> None:
        self._total_scans = total
        self._skipped_scans = skipped
        self._completed_scans = skipped

    @override
    def results(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        pass

    @override
    def metrics(self, metrics: ScanMetrics) -> None:
        self._completed_scans = self._skipped_scans + metrics.completed_scans
        self._log_metrics_throttled(metrics)

    @throttle(5)
    def _log_metrics_throttled(self, metrics: ScanMetrics) -> None:
        self._log_metrics(metrics)

    def _log_metrics(self, metrics: ScanMetrics) -> None:
        percent = (
            100.0 * self._completed_scans / self._total_scans
            if self._total_scans > 0
            else 0.0
        )

        batch_age: int | None = None
        if metrics.batch_oldest_created is not None:
            batch_age = int(time.time() - metrics.batch_oldest_created)

        msg = f"Scan progress: {percent:.0f}% ({self._completed_scans:,}/{self._total_scans:,})"
        if batch_age is not None:
            msg += f" batch: {metrics.batch_pending}/{format_progress_time(batch_age, pad_hours=False)}"

        logger.info(
            msg,
            extra={
                "scan_progress": {
                    "completed": self._completed_scans,
                    "total": self._total_scans,
                    "percent": percent,
                },
                "scan_metrics": dataclasses.asdict(metrics),
            },
        )


class TextProgressLog(TextProgress):
    def __init__(self, caption: str, count: bool | int) -> None:
        self._caption = caption
        self._count = count
        self._total = 0

    @override
    def update(self, text: str) -> None:
        self._total += 1
        if self._total == 1:
            self._log_update(text)
        else:
            self._log_update_throttled(text)

    @throttle(5)
    def _log_update_throttled(self, text: str) -> None:
        self._log_update(text)

    def _log_update(self, text: str) -> None:
        extra: dict[str, Any] = {"caption": self._caption, "text": text}
        if self._count:
            extra["progress"] = self._total
            if not isinstance(self._count, bool):
                extra["total"] = self._count

        logger.info("%s: %s", self._caption, text, extra=extra)
