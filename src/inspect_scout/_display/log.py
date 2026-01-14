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
        per_scanner_total: dict[str, int] | None = None,
        per_scanner_skipped: dict[str, int] | None = None,
    ) -> Iterator[ScanDisplay]:
        logging.info(
            "Starting scan",
            extra={
                "total_scans": total,
                "skipped_scans": skipped,
                "scan_location": scan_location,
                "per_scanner_total": per_scanner_total,
            },
        )
        yield ScanDisplayLog(total, skipped, per_scanner_total, per_scanner_skipped)

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


class ScanDisplayLog(ScanDisplay):
    def __init__(
        self,
        total: int,
        skipped: int,
        per_scanner_total: dict[str, int] | None = None,
        per_scanner_skipped: dict[str, int] | None = None,
    ) -> None:
        self._total_scans: int = total
        self._skipped_scans: int = skipped
        self._completed_scans: int = skipped
        self._per_scanner_total: dict[str, int] = per_scanner_total or {}
        self._per_scanner_skipped: dict[str, int] = per_scanner_skipped or {}
        self._per_scanner_completed: dict[str, int] = dict(self._per_scanner_skipped)
        self._scanners_completed: set[str] = set()

        for scanner, expected in self._per_scanner_total.items():
            if self._per_scanner_completed.get(scanner, 0) >= expected > 0:
                self._scanners_completed.add(scanner)
                self._log_scanner_complete(scanner)

    @override
    def results(
        self,
        transcript: TranscriptInfo,
        scanner: str,
        results: Sequence[ResultReport],
        metrics: dict[str, dict[str, float]] | None,
    ) -> None:
        self._per_scanner_completed[scanner] = (
            self._per_scanner_completed.get(scanner, 0) + 1
        )

        expected = self._per_scanner_total.get(scanner, 0)
        if (
            scanner not in self._scanners_completed
            and self._per_scanner_completed[scanner] >= expected
            and expected > 0
        ):
            self._scanners_completed.add(scanner)
            self._log_scanner_complete(scanner)

    def _log_scanner_complete(self, scanner: str) -> None:
        logging.info(
            "Scanner %s complete (%d/%d scanners)",
            scanner,
            len(self._scanners_completed),
            len(self._per_scanner_total),
            extra={
                "event": "scanner_complete",
                "scanner": scanner,
                "scanners_complete": len(self._scanners_completed),
                "scanners_total": len(self._per_scanner_total),
                "transcripts_completed": self._per_scanner_completed.get(scanner, 0),
            },
        )

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

        logging.info(
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
        self._caption: str = caption
        self._count: bool | int = count
        self._total: int = 0

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

        logging.info("%s: %s", self._caption, text, extra=extra)
