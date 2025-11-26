from __future__ import annotations

import time
from collections.abc import Sequence
from multiprocessing.context import SpawnProcess
from multiprocessing.queues import Queue
from queue import Empty
from typing import Any, Callable

import anyio

from . import _mp_common


async def shutdown_subprocesses(
    processes: Sequence[SpawnProcess],
    ctx: _mp_common.IPCContext,
    print_diagnostics: Callable[[str, object], None],
    shutdown_sentinel: _mp_common.ShutdownSentinel,
) -> None:
    """Unified shutdown sequence for both clean exit and Ctrl-C.

    This function is idempotent and can be called multiple times safely. Performs
    phased shutdown: signal → drain-while-waiting → terminate → kill → inject sentinel → drain remaining → close.

    During Ctrl-C, the collector stops reading from queues, causing worker feeder threads
    to block on full pipes. Phase 2 actively drains queues while waiting for workers to
    exit, unblocking feeder threads and enabling clean worker shutdown.

    Args:
        processes: List of worker processes
        ctx: IPC context with queues and shutdown condition
        print_diagnostics: Function to print diagnostic messages
        shutdown_sentinel: Sentinel value to inject into upstream queue to wake collector
    """
    # PHASE 1: Signal workers to stop (non-blocking)
    print_diagnostics("SubprocessShutdown", "Phase 1: Signaling workers")
    with ctx.shutdown_condition:
        ctx.shutdown_condition.notify_all()  # Wake all shutdown monitors

    # PHASE 2: Wait for graceful shutdown while draining queues
    # Actively drain queues to unblock worker feeder threads, allowing clean exit.
    # When Ctrl-C cancels the collector, it stops reading from queues. Workers trying
    # to exit get stuck because their feeder threads are blocked writing to full pipes.
    # By draining here, we unblock those feeder threads so workers can exit cleanly.
    print_diagnostics(
        "SubprocessShutdown", "Phase 2: Joining workers while draining queues"
    )
    deadline = time.time() + 2.0  # 2 second grace period
    drained_parse = 0
    drained_upstream = 0

    while time.time() < deadline:
        # Drain both queues to unblock worker feeder threads
        try:
            ctx.parse_job_queue.get_nowait()
            drained_parse += 1
        except Empty:
            pass

        try:
            ctx.upstream_queue.get_nowait()
            drained_upstream += 1
        except Empty:
            pass

        # Check if all workers have exited
        if all(not p.is_alive() for p in processes):
            print_diagnostics(
                "SubprocessShutdown",
                f"All workers exited cleanly (drained parse={drained_parse}, upstream={drained_upstream})",
            )
            break

        # Brief sleep to avoid tight CPU loop
        await anyio.sleep(0.01)
    else:
        # Timeout reached with some workers still alive
        print_diagnostics(
            "SubprocessShutdown",
            f"Timeout waiting for workers (drained parse={drained_parse}, upstream={drained_upstream})",
        )

    # PHASE 3: Terminate any still-running workers
    still_alive = [p for p in processes if p.is_alive()]
    if still_alive:
        print_diagnostics(
            "SubprocessShutdown", f"Phase 3: Terminating {len(still_alive)} workers"
        )
        for p in still_alive:
            print_diagnostics("SubprocessShutdown", f"Terminating {p.pid}")
            p.terminate()

        # Wait briefly for termination
        deadline = time.time() + 1.0
        for p in still_alive:
            remaining = deadline - time.time()
            if remaining > 0:
                p.join(timeout=remaining)
    else:
        print_diagnostics(
            "SubprocessShutdown",
            "Phase 3: Terminating workers. Skipping - no living workers",
        )

    # PHASE 4: Force kill any survivors
    survivors = [p for p in processes if p.is_alive()]
    if survivors:
        print_diagnostics(
            "SubprocessShutdown", f"Phase 4: Force killing {len(survivors)} workers"
        )
        for p in survivors:
            print_diagnostics("SubprocessShutdown", f"Killing {p.pid}")
            p.kill()

        # Final join (should be instant)
        for p in survivors:
            p.join(timeout=0.1)
    else:
        print_diagnostics(
            "SubprocessShutdown",
            "Phase 4: Force Killing workers. Skipping - no living workers",
        )

    # PHASE 5: Inject shutdown sentinel to wake collector
    print_diagnostics("SubprocessShutdown", "Phase 5: Injecting shutdown sentinel")
    try:
        ctx.upstream_queue.put(shutdown_sentinel)
        print_diagnostics("SubprocessShutdown", "Injected upstream queue sentinel")
    except (ValueError, OSError) as e:
        # Queue already closed - collector likely already exited via cancellation
        print_diagnostics("SubprocessShutdown", f"Upstream queue closed: {e}")

    # PHASE 6: Drain queues (collector should have exited by now)
    print_diagnostics("SubprocessShutdown", "Phase 6: Draining queues")

    def drain_queue(queue: Queue[Any], name: str) -> int:
        """Drain a queue and return count of items removed."""
        count = 0
        while True:
            try:
                queue.get_nowait()
                count += 1
                if count > 1000:  # Safety limit
                    print_diagnostics(
                        "SubprocessShutdown", f"WARNING: {name} had >1000 items"
                    )
                    break
            except (Empty, ValueError):
                # Empty: queue is empty (expected termination condition)
                # ValueError: queue is closed (Python 3.8+, can happen in shutdown race)
                break
        return count

    parse_count = drain_queue(ctx.parse_job_queue, "parse_job_queue")
    upstream_count = drain_queue(ctx.upstream_queue, "upstream_queue")

    print_diagnostics(
        "SubprocessShutdown",
        f"Drained: parse={parse_count}, upstream={upstream_count}",
    )

    # PHASE 7: Close queues (sends sentinel to feeder threads)
    print_diagnostics("SubprocessShutdown", "Phase 7: Closing queues")

    queues_to_close: list[tuple[Queue[Any], str]] = [
        (ctx.parse_job_queue, "parse_job_queue"),
        (ctx.upstream_queue, "upstream_queue"),
    ]
    for queue, name in queues_to_close:
        try:
            queue.close()  # Sends sentinel to feeder thread
            print_diagnostics("SubprocessShutdown", f"Closed {name}")
        except (ValueError, OSError):
            # ValueError: queue already closed (Python 3.8+)
            # OSError: queue already closed (pre-3.8, defensive)
            pass

    # PHASE 8: Wait briefly for feeder threads to exit
    print_diagnostics("SubprocessShutdown", "Phase 8: Sleeping")
    await anyio.sleep(0.1)  # Give feeder threads time to see sentinel

    # PHASE 9: Cancel join threads (orphan any stuck feeder threads)
    print_diagnostics("SubprocessShutdown", "Phase 9: Cancelling join threads")

    queues_to_cancel: list[tuple[Queue[Any], str]] = [
        (ctx.parse_job_queue, "parse_job_queue"),
        (ctx.upstream_queue, "upstream_queue"),
    ]
    for queue, name in queues_to_cancel:
        try:
            queue.cancel_join_thread()
            print_diagnostics("SubprocessShutdown", f"Cancelled {name}")
        except (ValueError, OSError):
            # ValueError: queue operation on closed queue (Python 3.8+)
            # OSError: queue operation on closed queue (pre-3.8, defensive)
            pass

    print_diagnostics(
        "SubprocessShutdown", "Complete - subprocesses should be completely gone"
    )
