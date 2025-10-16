import time
from multiprocessing.context import ForkProcess
from multiprocessing.queues import Queue as MPQueue
from queue import Empty
from typing import Any, Callable, cast

import anyio

from . import _mp_common


async def shutdown_subprocesses(
    processes: list[ForkProcess],
    ctx: _mp_common.IPCContext,
    print_diagnostics: Callable[[str, object], None],
    shutdown_sentinel: object,
) -> None:
    """Unified shutdown sequence for both clean exit and Ctrl-C.

    This function is idempotent and can be called multiple times safely. Performs
    phased shutdown: signal → wait → terminate → kill → inject sentinels → drain → close.

    Args:
        processes: List of worker processes
        ctx: IPC context with queues and shutdown condition
        print_diagnostics: Function to print diagnostic messages
        shutdown_sentinel: Sentinel value to inject into queues to wake collectors
    """
    # PHASE 1: Signal workers to stop (non-blocking)
    print_diagnostics("SubprocessShutdown", "Phase 1: Signaling workers")
    with ctx.shutdown_condition:
        ctx.shutdown_condition.notify_all()  # Wake all shutdown monitors

    # PHASE 2: Wait briefly for graceful shutdown
    print_diagnostics("SubprocessShutdown", "Phase 2: Joining workers (with timeout)")
    deadline = time.time() + 2.0  # 2 second grace period

    for p in processes:
        remaining = deadline - time.time()
        if remaining > 0 and p.is_alive():
            p.join(timeout=remaining)

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

    # PHASE 5: Inject shutdown sentinels to wake collectors
    print_diagnostics("SubprocessShutdown", "Phase 5: Injecting shutdown sentinels")
    try:
        # Cast sentinel to queue's type - at runtime it's just an object identity check
        ctx.result_queue.put(cast(_mp_common.ResultQueueItem, shutdown_sentinel))
        print_diagnostics("SubprocessShutdown", "Injected result queue sentinel")
    except (ValueError, OSError) as e:
        # Queue already closed - collectors likely already exited via cancellation
        print_diagnostics("SubprocessShutdown", f"Result queue closed: {e}")

    try:
        # Cast sentinel to queue's type - at runtime it's just an object identity check
        ctx.metrics_queue.put(cast(_mp_common.MetricsQueueItem, shutdown_sentinel))
        print_diagnostics("SubprocessShutdown", "Injected metrics queue sentinel")
    except (ValueError, OSError) as e:
        # Queue already closed - collectors likely already exited via cancellation
        print_diagnostics("SubprocessShutdown", f"Metrics queue closed: {e}")

    # PHASE 6: Drain queues (collectors should have exited by now)
    print_diagnostics("SubprocessShutdown", "Phase 6: Draining queues")

    def drain_queue(queue: MPQueue[Any], name: str) -> int:
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
    result_count = drain_queue(ctx.result_queue, "result_queue")
    metrics_count = drain_queue(ctx.metrics_queue, "metrics_queue")

    print_diagnostics(
        "SubprocessShutdown",
        f"Drained: parse={parse_count}, result={result_count}, metrics={metrics_count}",
    )

    # PHASE 7: Close queues (sends sentinel to feeder threads)
    print_diagnostics("SubprocessShutdown", "Phase 7: Closing queues")

    queues_to_close: list[tuple[MPQueue[Any], str]] = [
        (ctx.parse_job_queue, "parse_job_queue"),
        (ctx.result_queue, "result_queue"),
        (ctx.metrics_queue, "metrics_queue"),
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

    queues_to_cancel: list[tuple[MPQueue[Any], str]] = [
        (ctx.parse_job_queue, "parse_job_queue"),
        (ctx.result_queue, "result_queue"),
        (ctx.metrics_queue, "metrics_queue"),
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
