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
_STORE_VERSION = 4
_VERSION_KEY = "__version__"


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

    def delete_current(self) -> None:
        """Delete the current process's entry."""
        ...

    def read_all(self) -> dict[str, ActiveScanInfo]:
        """Read all active scan info, keyed by scan_id."""
        ...

    def read_by_pid(self, pid: int) -> ActiveScanInfo | None:
        """Read active scan info for a specific PID."""
        ...


def _pid_exists(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@contextmanager
def active_scans_store() -> Generator[ActiveScansStore, None, None]:
    """Context manager yielding a ActiveScansStore interface.

    Metrics are keyed by main process PID. Call delete_current() when
    the scan completes to clean up the entry.

    Yields:
        ActiveScansStore interface with put, delete_current, and read_all methods.
    """
    pid_key = str(os.getpid())
    with inspect_kvstore(_STORE_NAME) as kvstore:
        # Version management - clear store if version mismatch
        stored_version = kvstore.get(_VERSION_KEY)
        if stored_version != str(_STORE_VERSION):
            kvstore.conn.execute("DELETE FROM kv_store")
            kvstore.conn.commit()
            kvstore.put(_VERSION_KEY, str(_STORE_VERSION))

        # Cleanup stale entries from dead processes
        cursor = kvstore.conn.execute(
            "SELECT key FROM kv_store WHERE key != ?", (_VERSION_KEY,)
        )
        for (key,) in cursor.fetchall():
            if not _pid_exists(int(key)):
                kvstore.delete(key)

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

            def delete_current(self) -> None:
                kvstore.delete(pid_key)

            def read_all(self) -> dict[str, ActiveScanInfo]:
                result: dict[str, ActiveScanInfo] = {}
                cursor = kvstore.conn.execute(
                    "SELECT key, value FROM kv_store WHERE key != ?", (_VERSION_KEY,)
                )
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
    )
