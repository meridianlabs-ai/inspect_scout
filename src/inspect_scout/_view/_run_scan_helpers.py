import asyncio
import io
import os
import subprocess
import sys
import tempfile
import threading
import time

from .._recorder.active_scans_store import ActiveScanInfo, active_scans_store
from .._scanjob_config import ScanJobConfig


def _tee_pipe(
    pipe: io.BufferedReader, dest: io.TextIOWrapper, accumulator: list[bytes]
) -> None:
    """Read from pipe, write to dest, and accumulate."""
    for line in pipe:
        dest.buffer.write(line)
        dest.buffer.flush()
        accumulator.append(line)
    pipe.close()


def spawn_scan_subprocess(
    config: ScanJobConfig,
) -> tuple[subprocess.Popen[bytes], str, list[bytes], list[bytes]]:
    """Spawn a subprocess to run the scan.

    Args:
        config: The scan job configuration

    Returns:
        Tuple of (Popen object, temp config file path, stdout_lines, stderr_lines)
        stdout_lines and stderr_lines accumulate as subprocess runs.
    """
    fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="scout_scan_config_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(config.model_dump_json(exclude_none=True))
    except Exception:
        os.close(fd)
        os.unlink(temp_path)
        raise

    proc = subprocess.Popen(
        ["scout", "scan", temp_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    stdout_lines: list[bytes] = []
    stderr_lines: list[bytes] = []

    assert proc.stdout is not None
    assert proc.stderr is not None

    threading.Thread(
        target=_tee_pipe, args=(proc.stdout, sys.stdout, stdout_lines), daemon=True
    ).start()
    threading.Thread(
        target=_tee_pipe, args=(proc.stderr, sys.stderr, stderr_lines), daemon=True
    ).start()

    return proc, temp_path, stdout_lines, stderr_lines


async def wait_for_active_scan(
    pid: int,
    timeout_seconds: float = 10.0,
    poll_interval: float = 0.5,
) -> ActiveScanInfo | None:
    """Wait for an active scan to appear for the given PID.

    Args:
        pid: The subprocess PID to monitor
        timeout_seconds: Max time to wait
        poll_interval: Time between polls

    Returns:
        ActiveScanInfo if found, None on timeout
    """
    start = time.time()

    while time.time() - start < timeout_seconds:
        with active_scans_store() as store:
            info = store.read_by_pid(pid)
            if info is not None:
                return info
        await asyncio.sleep(poll_interval)

    return None


async def _run_scan_background(config: ScanJobConfig, location: str) -> None:
    # import inspect_scout._display._display as display_module
    from inspect_scout._scan import scan_async

    # original_display = display_module._display

    await scan_async(scanners=config)
    # try:
    #     display_module._display = None
    # finally:
    #     display_module._display = original_display
