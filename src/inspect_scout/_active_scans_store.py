"""KV store for in-progress scan metrics.

Provides cross-process visibility into metrics for all running scans.
Each scan writes metrics keyed by its main process PID.
"""

import json
import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Protocol

from inspect_ai._util.kvstore import inspect_kvstore

from inspect_scout._recorder.summary import ScannerSummary

from ._concurrency.common import ScanMetrics

_STORE_NAME = "scout_active_scans"
_STORE_VERSION = 1
_VERSION_KEY = "__version__"


@dataclass
class ActiveScanInfo:
    """Info for an active scan stored in the KV store."""

    scan_id: str
    metrics: ScanMetrics
    summary: ScannerSummary
    last_updated: float


class ActiveScansStore(Protocol):
    """Interface for scan metrics store operations."""

    def put(self, scan_id: str, metrics: ScanMetrics) -> None:
        """Store metrics for the current process's scan."""
        ...

    def delete_current(self) -> None:
        """Delete the current process's entry."""
        ...

    def read_all(self) -> dict[str, ActiveScanInfo]:
        """Read all active scan info, keyed by scan_id."""
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
            def put(self, scan_id: str, metrics: ScanMetrics) -> None:
                kvstore.put(
                    pid_key,
                    json.dumps(
                        {
                            "scan_id": scan_id,
                            "metrics": asdict(metrics),
                            "last_updated": time.time(),
                        }
                    ),
                )

            def delete_current(self) -> None:
                kvstore.delete(pid_key)

            def read_all(self) -> dict[str, ActiveScanInfo]:
                result: dict[str, ActiveScanInfo] = {}
                cursor = kvstore.conn.execute(
                    "SELECT key, value FROM kv_store WHERE key != ?", (_VERSION_KEY,)
                )
                for _, value in cursor.fetchall():
                    data = json.loads(value)
                    info = ActiveScanInfo(
                        scan_id=data["scan_id"],
                        summary=ScannerSummary(),
                        metrics=ScanMetrics(**data["metrics"]),
                        last_updated=data["last_updated"],
                    )
                    result[info.scan_id] = info
                return result

        yield _Store()
