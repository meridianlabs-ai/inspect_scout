"""KV store for in-progress scan metrics.

Provides cross-process visibility into metrics for all running scans.
Each scan writes metrics keyed by its main process PID.
"""

import json
import os
import time
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Protocol

from inspect_ai._util.kvstore import inspect_kvstore

from inspect_scout._display.util import scan_config_str, scan_title
from inspect_scout._recorder.summary import Summary

from .._concurrency.common import ScanMetrics

if TYPE_CHECKING:
    from .._scanner.result import ResultReport
    from .._scanspec import ScanSpec

_STORE_NAME = "scout_active_scans"


@dataclass
class ActiveScanInfo:
    """Info for an active scan stored in the KV store."""

    scan_id: str
    metrics: ScanMetrics
    summary: Summary
    last_updated: float
    title: str
    config: str
    total_scans: int
    start_time: float
    scanner_names: list[str]
    location: str
    running: bool
    error_message: str | None = None


class ActiveScansStore(Protocol):
    """Interface for scan metrics store operations."""

    def put_spec(
        self, scan_id: str, spec: "ScanSpec", total_scans: int, location: str
    ) -> None:
        """Store spec-derived info at scan start."""
        ...

    def put_metrics(self, scan_id: str, metrics: ScanMetrics) -> None:
        """Store metrics for the current process's scan."""
        ...

    def put_scanner_results(
        self, scan_id: str, scanner: str, results: Sequence["ResultReport"]
    ) -> None:
        """Store scanner results, aggregating into Summary."""
        ...

    def mark_completed(self) -> None:
        """Mark the current process's scan as completed."""
        ...

    def mark_interrupted(self, scan_id: str, message: str) -> None:
        """Mark the current process's scan as interrupted with error message.

        Creates a minimal entry if none exists (e.g., for PrerequisiteError before put_spec).
        """
        ...

    def read_all(self) -> dict[str, ActiveScanInfo]:
        """Read all active scan info, keyed by scan_id."""
        ...

    def read_by_pid(self, pid: int) -> ActiveScanInfo | None:
        """Read active scan info for a specific PID."""
        ...


def clear_active_scans() -> None:
    """Clear all entries from the active scans store. Call on server startup."""
    with inspect_kvstore(_STORE_NAME) as kvstore:
        kvstore.conn.execute("DELETE FROM kv_store")
        kvstore.conn.commit()


@contextmanager
def active_scans_store() -> Generator[ActiveScansStore, None, None]:
    """Context manager yielding a ActiveScansStore interface.

    Metrics are keyed by main process PID.

    Yields:
        ActiveScansStore interface with put and read methods.
    """
    pid_key = str(os.getpid())
    with inspect_kvstore(_STORE_NAME) as kvstore:

        class _Store:
            def put_spec(
                self, scan_id: str, spec: "ScanSpec", total_scans: int, location: str
            ) -> None:
                scanner_names = list(spec.scanners.keys())
                existing = json.loads(kvstore.get(pid_key) or "{}")
                existing.update(
                    {
                        "scan_id": scan_id,
                        "title": scan_title(spec),
                        "config": scan_config_str(spec),
                        "total_scans": total_scans,
                        "start_time": time.time(),
                        "last_updated": time.time(),
                        "scanner_names": scanner_names,
                        "summary": Summary(scanners=scanner_names).model_dump(),
                        "metrics": asdict(ScanMetrics()),
                        "location": location,
                        "running": True,
                        "error_message": None,
                    }
                )
                kvstore.put(pid_key, json.dumps(existing))

            def put_metrics(self, scan_id: str, metrics: ScanMetrics) -> None:
                existing = json.loads(kvstore.get(pid_key) or "{}")
                existing.update(
                    {
                        "scan_id": scan_id,
                        "metrics": asdict(metrics),
                        "last_updated": time.time(),
                    }
                )
                kvstore.put(pid_key, json.dumps(existing))

            def put_scanner_results(
                self, scan_id: str, scanner: str, results: Sequence["ResultReport"]
            ) -> None:
                existing = json.loads(kvstore.get(pid_key) or "{}")
                summary = Summary.model_validate(
                    existing.get("summary", {"complete": False})
                )
                # _report takes transcript but doesn't use it - pass dummy cast
                summary._report(None, scanner, results, None)  # type: ignore[arg-type]
                existing.update(
                    {
                        "scan_id": scan_id,
                        "summary": summary.model_dump(),
                        "last_updated": time.time(),
                    }
                )
                kvstore.put(pid_key, json.dumps(existing))

            def mark_completed(self) -> None:
                existing = json.loads(kvstore.get(pid_key) or "{}")
                existing.update({"running": False, "last_updated": time.time()})
                kvstore.put(pid_key, json.dumps(existing))

            def mark_interrupted(self, scan_id: str, message: str) -> None:
                existing = kvstore.get(pid_key)
                if existing:
                    data = json.loads(existing)
                    data.update(
                        {
                            "running": False,
                            "error_message": message,
                            "last_updated": time.time(),
                        }
                    )
                else:
                    # Create minimal entry for errors before put_spec (e.g., PrerequisiteError)
                    data = {
                        "scan_id": scan_id,
                        "title": "",
                        "config": "",
                        "total_scans": 0,
                        "start_time": time.time(),
                        "last_updated": time.time(),
                        "scanner_names": [],
                        "summary": Summary(scanners=[]).model_dump(),
                        "metrics": asdict(ScanMetrics()),
                        "location": "",
                        "running": False,
                        "error_message": message,
                    }
                kvstore.put(pid_key, json.dumps(data))

            def read_all(self) -> dict[str, ActiveScanInfo]:
                result: dict[str, ActiveScanInfo] = {}
                cursor = kvstore.conn.execute("SELECT key, value FROM kv_store")
                for _, value in cursor.fetchall():
                    data = json.loads(value)
                    info = _parse_active_scan_info(data)
                    result[info.scan_id] = info
                return result

            def read_by_pid(self, pid: int) -> ActiveScanInfo | None:
                value = kvstore.get(str(pid))
                if value is None:
                    return None
                data = json.loads(value)
                return _parse_active_scan_info(data)

        yield _Store()


def _parse_active_scan_info(data: dict[str, object]) -> ActiveScanInfo:
    return ActiveScanInfo(
        scan_id=str(data["scan_id"]),
        summary=Summary.model_validate(data["summary"]),
        metrics=ScanMetrics(**data["metrics"]),  # type: ignore[arg-type]
        last_updated=float(str(data["last_updated"])),
        title=str(data["title"]),
        config=str(data["config"]),
        total_scans=int(str(data["total_scans"])),
        start_time=float(str(data["start_time"])),
        scanner_names=list(data["scanner_names"]),  # type: ignore[call-overload]
        location=str(data["location"]),
        running=bool(data.get("running", True)),
        error_message=str(data["error_message"]) if data.get("error_message") else None,
    )
