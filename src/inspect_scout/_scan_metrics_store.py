"""KV store for in-progress scan metrics.

Provides cross-process visibility into metrics for all running scans.
Each scan writes metrics keyed by its main process PID.
"""

import json
import os
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import asdict

from inspect_ai._util.kvstore import inspect_kvstore

from ._concurrency.common import ScanMetrics

_STORE_NAME = "scout_active_scans"
_STORE_VERSION = 1
_VERSION_KEY = "__version__"


def _pid_exists(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@contextmanager
def scan_metrics_store(
    scan_id: str,
) -> Generator[tuple[Callable[[ScanMetrics], None], Callable[[], None]], None, None]:
    """Context manager yielding (put, delete) functions for scan metrics.

    Metrics are keyed by main process PID. The delete function should be
    called when the scan completes to clean up the entry.

    Args:
        scan_id: Unique identifier for the scan.

    Yields:
        Tuple of (put_metrics, delete_metrics) functions.
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

        def put(metrics: ScanMetrics) -> None:
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

        def delete() -> None:
            kvstore.delete(pid_key)

        yield put, delete
