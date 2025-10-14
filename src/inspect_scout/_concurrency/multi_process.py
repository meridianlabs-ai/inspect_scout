"""Multi-process work pool implementation for scanner operations.

This module provides a process-based concurrency strategy using fork-based
multiprocessing. Each worker process runs its own async event loop with
multiple concurrent tasks, allowing efficient parallel execution of scanner work.

Workers communicate with the main process via a single multiplexed upstream queue
that carries both results and metrics, simplifying the collection architecture.

Note: multiprocessing.Queue.get() is blocking with no async support, so we use
anyio.to_thread.run_sync to wrap .get() calls to prevent blocking the event loop.
Queue.put() on unbounded queues (our case) only blocks briefly for lock contention,
so threading is unnecessary.
See: https://stackoverflow.com/questions/75270606
"""

from __future__ import annotations

import multiprocessing
import signal
import time
from multiprocessing.context import ForkProcess
from typing import AsyncIterator, Awaitable, Callable, cast

import anyio
from anyio import create_task_group
from inspect_ai.util._anyio import inner_exception
from inspect_ai.util._concurrency import init_concurrency

from inspect_scout._display._display import display

from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from . import _mp_common
from ._mp_common import (
    IPCContext,
    MetricsItem,
    ResultItem,
    SemaphoreRequest,
    ShutdownSentinel,
    WorkerComplete,
    run_sync_on_thread,
)
from ._mp_registry import ParentSemaphoreRegistry
from ._mp_shutdown import shutdown_subprocesses
from ._mp_subprocess import subprocess_main
from .common import ConcurrencyStrategy, ParseJob, ScanMetrics, ScannerJob, sum_metrics

# Sentinel value to signal collectors to shut down during Ctrl-C.
#
# MUST be a sentinel: During Ctrl-C shutdown, workers are terminated before they can
# send their normal completion sentinels (WorkerComplete). The collectors are blocked
# waiting on queue.get() in a thread (via run_sync_on_thread). To wake them up and
# allow them to exit, we inject this shutdown sentinel into their queues from the main
# process.
#
# Uses a dedicated ShutdownSentinel dataclass to maintain type safety while still
# providing a distinct sentinel value for emergency shutdown.
_SHUTDOWN_SENTINEL = ShutdownSentinel()


def multi_process_strategy(
    *,
    process_count: int,
    task_count: int,
    prefetch_multiple: float | None = None,
    diagnostics: bool = False,
) -> ConcurrencyStrategy:
    """Multi-process execution strategy with nested async concurrency.

    Distributes ParseJob work items across multiple worker processes. Each worker
    uses single-process strategy internally to control scan concurrency and buffering.
    The ParseJob queue is unbounded since ParseJobs are lightweight metadata objects.

    Args:
        process_count: Number of worker processes.
        task_count: Target total task concurrency across all processes
        prefetch_multiple: Buffer size multiple passed to each worker's
            single-process strategy
        diagnostics: Whether to print diagnostic information
    """
    if process_count <= 1:
        raise ValueError(
            f"processes must be >= 1 when specified as int, got {process_count}"
        )

    async def the_func(
        *,
        record_results: Callable[
            [TranscriptInfo, str, list[ResultReport]], Awaitable[None]
        ],
        parse_jobs: AsyncIterator[ParseJob],
        parse_function: Callable[[ParseJob], Awaitable[list[ScannerJob]]],
        scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]],
        update_metrics: Callable[[ScanMetrics], None] | None = None,
    ) -> None:
        all_metrics: dict[int, ScanMetrics] = {}

        # Enforce single active instance - check if ipc_context is already set
        # (ipc_context is cast(IPCContext, None) initially, so we check truthiness)
        if _mp_common.ipc_context is not None:
            raise RuntimeError(
                "Another multi_process_strategy is already running. Only one instance can be active at a time."
            )
        # Create Manager and parent registry for cross-process semaphore coordination
        manager = multiprocessing.Manager()
        parent_registry = ParentSemaphoreRegistry(manager)

        # Initialize parent's concurrency system with cross-process registry
        # This ensures parent creates ManagerSemaphore instances in shared registry
        # when it receives SemaphoreRequest from children
        init_concurrency(parent_registry)

        # Block SIGINT before creating processes - workers will inherit SIG_IGN
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            # TODO: Obviously, hack_factor is just for exploration for now
            hack_factor = 1
            tasks_per_process = hack_factor * max(1, task_count // process_count)
            # Initialize shared IPC context that will be inherited by forked workers
            _mp_common.ipc_context = IPCContext(
                parse_function=parse_function,
                scan_function=scan_function,
                tasks_per_process=tasks_per_process,
                prefetch_multiple=prefetch_multiple,
                diagnostics=diagnostics,
                overall_start_time=time.time(),
                parse_job_queue=multiprocessing.Queue(),
                upstream_queue=multiprocessing.Queue(),
                shutdown_condition=manager.Condition(),
                semaphore_registry=parent_registry.sync_manager_dict,
                semaphore_condition=parent_registry.sync_manager_condition,
            )

            def print_diagnostics(actor_name: str, *message_parts: object) -> None:
                if diagnostics:
                    running_time = f"+{time.time() - _mp_common.ipc_context.overall_start_time:.3f}s"
                    display().print(running_time, f"{actor_name}:", *message_parts)

            print_diagnostics(
                "Setup",
                f"Multi-process strategy: {process_count} processes × "
                f"{tasks_per_process} scans = {process_count * tasks_per_process} total concurrency",
            )

            # Queues are part of IPC context and inherited by forked processes.
            # ParseJob queue is unbounded - ParseJobs are tiny metadata objects with
            # no backpressure needed. Real backpressure happens inside each worker via
            # single-process strategy's ScannerJob buffer.
            # Upstream queue is also unbounded and multiplexes both results and metrics.
            parse_job_queue = _mp_common.ipc_context.parse_job_queue
            upstream_queue = _mp_common.ipc_context.upstream_queue

            async def _producer() -> None:
                """Producer task that feeds work items into the queue."""
                try:
                    async for item in parse_jobs:
                        parse_job_queue.put(item)
                        print_diagnostics(
                            "MP Producer",
                            f"Added ParseJob {item.transcript_info.id, item.scanner_indices}",
                        )
                finally:
                    # Send sentinel values to signal worker tasks to stop (one per task)
                    # This runs even if cancelled, allowing graceful shutdown
                    for _ in range(process_count * tasks_per_process):
                        parse_job_queue.put(None)

                    print_diagnostics("MP Producer", "FINISHED PRODUCING ALL WORK")

            async def _upstream_collector() -> None:
                """Collector task that receives results and metrics."""
                items_processed = 0
                workers_finished = 0

                while workers_finished < process_count:
                    # Thread sleeps in kernel until data arrives or shutdown sentinel injected
                    item = await run_sync_on_thread(upstream_queue.get)

                    match item:
                        case ResultItem(transcript_info, scanner_name, results):
                            await record_results(transcript_info, scanner_name, results)
                            items_processed += 1
                            print_diagnostics(
                                "MP Collector",
                                f"Recorded results for {transcript_info.id} (total: {items_processed})",
                            )

                        case MetricsItem(worker_id, metrics):
                            all_metrics[worker_id] = metrics
                            if update_metrics:
                                update_metrics(sum_metrics(all_metrics.values()))

                        case SemaphoreRequest(name, concurrency, visible):
                            # Use parent registry to create and register semaphore
                            # This creates the ManagerSemaphore in the shared DictProxy
                            await parent_registry.get_or_create(
                                name, concurrency, None, visible
                            )

                            print_diagnostics(
                                "MP Collector",
                                f"Created semaphore '{name}' with concurrency={concurrency}",
                            )

                        # Shutdown signal from ourself - exit collector immediately
                        case ShutdownSentinel():
                            print_diagnostics(
                                "MP Collector",
                                f"Received shutdown sentinel (got {workers_finished}/{process_count} worker completions)",
                            )
                            break

                        case WorkerComplete():
                            workers_finished += 1
                            print_diagnostics(
                                "MP Collector",
                                f"Worker finished ({workers_finished}/{process_count})",
                            )

                        case Exception():
                            raise item

                        # Should never happen - defensive check
                        # case _:
                        #     print_diagnostics(
                        #         "MP Collector",
                        #         f"WARNING: Unexpected item: {item!r}",
                        #     )

                print_diagnostics("MP Collector", "Finished collecting all items")

            # Start worker processes directly
            ctx = multiprocessing.get_context("fork")
            processes: list[ForkProcess] = []
            for worker_id in range(process_count):
                try:
                    p = ctx.Process(target=subprocess_main, args=(worker_id,))
                    p.start()
                    processes.append(p)
                    print_diagnostics(
                        "Main", f"Spawned worker process #{worker_id} {p.pid}"
                    )
                except Exception as ex:
                    display().print(ex)
                    raise

            # Restore SIGINT handler in parent only (workers inherited SIG_IGN)
            signal.signal(signal.SIGINT, original_sigint_handler)

            try:
                # Run producer and collector concurrently - all in one cancel scope
                async with create_task_group() as tg:
                    tg.start_soon(_producer)
                    tg.start_soon(_upstream_collector)

                # If we get here, everything completed normally
                print_diagnostics("MP Main", "Task group exited normally")

            except KeyboardInterrupt:
                # ONLY parent gets here on Ctrl-C (workers are immune)
                print_diagnostics("MP Main", "KeyboardInterrupt - initiating shutdown")
                # Will proceed to finally block for cleanup

            except Exception as ex:
                print_diagnostics("MP Main", f"Exception: {ex}")
                raise inner_exception(ex) from ex

            except anyio.get_cancelled_exc_class():
                print_diagnostics("MP Main", "Caught cancelled exception")
                raise

            finally:
                print_diagnostics("MP Main", "In finally")
                # Unified shutdown sequence for both clean and Ctrl-C shutdown
                # Shield from cancellation so cleanup can complete even if we were cancelled
                with anyio.CancelScope(shield=True):
                    await shutdown_subprocesses(
                        processes,
                        _mp_common.ipc_context,
                        print_diagnostics,
                        _SHUTDOWN_SENTINEL,
                    )

        finally:
            # Always restore signal handler and reset IPC context
            signal.signal(signal.SIGINT, original_sigint_handler)
            _mp_common.ipc_context = cast(IPCContext, None)

    return the_func
