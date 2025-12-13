"""Multi-process work pool implementation for scanner operations.

This module provides a process-based concurrency strategy using spawn-based
multiprocessing. Each worker process runs its own async event loop with
multiple concurrent tasks, allowing efficient parallel execution of scanner work.

Workers communicate with the main process via a single multiplexed upstream queue
that carries both results and metrics, simplifying the collection architecture.

Note: multiprocessing.Queue.get() is blocking with no async support, so we use
anyio.to_thread.run_sync to wrap .get() calls to prevent blocking the event loop.
Queue.put() on bounded queues blocks when full, so we also wrap .put() calls in
the producer to provide lazy consumption without blocking the event loop.
See: https://stackoverflow.com/questions/75270606
"""

from __future__ import annotations

import multiprocessing
import signal
import time
from multiprocessing.context import SpawnProcess
from typing import AsyncIterator, Awaitable, Callable

import anyio
from anyio import create_task_group
from inspect_ai.model._generate_config import active_generate_config
from inspect_ai.model._model import active_model, model_roles
from inspect_ai.model._model_config import model_to_model_config
from inspect_ai.util._anyio import inner_exception
from inspect_ai.util._concurrency import init_concurrency

from inspect_scout._display._display import display

from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from ._mp_common import (
    DillCallable,
    IPCContext,
    LoggingItem,
    MetricsItem,
    ResultItem,
    SemaphoreRequest,
    ShutdownSentinel,
    WorkerComplete,
    WorkerReady,
    get_log_level,
    get_plugin_directory,
    run_sync_on_thread,
)
from ._mp_logging import find_inspect_log_handler
from ._mp_registry import ParentSemaphoreRegistry
from ._mp_shutdown import shutdown_subprocesses
from .common import (
    ConcurrencyStrategy,
    ParseFunctionResult,
    ParseJob,
    ScanMetrics,
    ScannerJob,
    sum_metrics,
)

# If no explicit number of processes is presented, we'll limit process concurrency
# to this number regardless of the number of CPUs. We may raise this as we see real
# world data suggesting that even more concurrency actually reduces the wall clock
# time of a scan.
DEFAULT_MAX_PROCESS = 4

# Maximum number of ParseJobs to prefetch into the queue.
# Provides backpressure to prevent buffering hundreds of thousands of ParseJobs
# when parse_jobs iterator is very large. Producer will block when queue is full.
PARSE_JOB_PREFETCH_SIZE = 50

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

# Singleton guard - only one multi_process_strategy can be active at a time
_active: bool = False


def multi_process_strategy(
    *,
    total_scans: int,
    max_processes: int | None,
    task_count: int,
    prefetch_multiple: float | None = None,
    diagnostics: bool = False,
) -> ConcurrencyStrategy:
    """Multi-process execution strategy with nested async concurrency.

    Distributes ParseJob work items across multiple worker processes. Each worker
    uses single-process strategy internally to control scan concurrency and buffering.
    The ParseJob queue is bounded to provide lazy consumption and prevent memory
    explosion when parse_jobs iterators are very large.

    Args:
        total_scans: The total number of scan invocations for this job.
        max_processes: Max number of worker processes. If provided, it must be > 1
        task_count: Target total task concurrency across all processes
        prefetch_multiple: Buffer size multiple passed to each worker's
            single-process strategy
        diagnostics: Whether to print diagnostic information
    """
    if isinstance(max_processes, int) and max_processes <= 1:
        raise ValueError(
            f"processes must be >= 1 when specified as int, got {max_processes}"
        )

    if max_processes is None:
        max_processes = min(
            DEFAULT_MAX_PROCESS, multiprocessing.cpu_count(), total_scans
        )

    async def the_func(
        *,
        record_results: Callable[
            [TranscriptInfo, str, list[ResultReport]], Awaitable[None]
        ],
        parse_jobs: AsyncIterator[ParseJob],
        parse_function: Callable[[ParseJob], Awaitable[ParseFunctionResult]],
        scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]],
        update_metrics: Callable[[ScanMetrics], None] | None = None,
        completed: Callable[[], Awaitable[None]],
    ) -> None:
        all_metrics: dict[int, ScanMetrics] = {}

        # Enforce single active instance
        global _active
        if _active:
            raise RuntimeError(
                "Another multi_process_strategy is already running. Only one instance can be active at a time."
            )
        _active = True
        # Create Manager and parent registry for cross-process semaphore coordination
        spawn_ctx = multiprocessing.get_context("spawn")
        manager = spawn_ctx.Manager()
        parent_registry = ParentSemaphoreRegistry(manager)

        # Initialize parent's concurrency system with cross-process registry
        # This ensures parent creates ManagerSemaphore instances in shared registry
        # when it receives SemaphoreRequest from children
        init_concurrency(parent_registry)

        inspect_log_handler = find_inspect_log_handler()

        # Block SIGINT before creating processes - workers will inherit SIG_IGN
        original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

        try:
            # Distribute tasks evenly: some processes get base+1, others get base
            # This ensures we use exactly task_count total tasks
            base_tasks = task_count // max_processes
            remainder_tasks = task_count % max_processes
            # Create a shared IPC context that will be passed to spawned workers
            ipc_ctx = IPCContext(
                parse_function=DillCallable(parse_function),
                scan_function=DillCallable(scan_function),
                completed=DillCallable(completed),
                prefetch_multiple=prefetch_multiple,
                diagnostics=diagnostics,
                overall_start_time=time.time(),
                parse_job_queue=spawn_ctx.Queue(maxsize=PARSE_JOB_PREFETCH_SIZE),
                upstream_queue=spawn_ctx.Queue(),
                shutdown_condition=manager.Condition(),
                workers_ready_event=manager.Event(),
                semaphore_registry=parent_registry.sync_manager_dict,
                semaphore_condition=parent_registry.sync_manager_condition,
                plugin_dir=get_plugin_directory(),
                log_level=get_log_level(),
                model_config=model_to_model_config(active_model()),  # type: ignore[arg-type]
                model_roles=model_roles(),
                generate_config=active_generate_config(),
            )

            def print_diagnostics(actor_name: str, *message_parts: object) -> None:
                if diagnostics:
                    running_time = f"+{time.time() - ipc_ctx.overall_start_time:.3f}s"
                    display().print(running_time, f"{actor_name}:", *message_parts)

            print_diagnostics(
                "Setup",
                f"Multi-process strategy: {max_processes} processes with "
                f"{task_count} total concurrency",
            )

            # Queues are part of IPC context and passed to spawned processes.
            # ParseJob queue is bounded to prevent memory explosion when parse_jobs
            # iterator contains a huge number of items. Producer blocks when queue
            # is full, providing lazy consumption.
            # Upstream queue is unbounded and multiplexes both results and metrics.
            parse_job_queue = ipc_ctx.parse_job_queue
            upstream_queue = ipc_ctx.upstream_queue

            # Track worker ready signals for startup coordination
            workers_ready_count = 0

            async def _producer() -> None:
                """Producer task that feeds work items into the queue."""
                try:
                    async for item in parse_jobs:
                        await run_sync_on_thread(parse_job_queue.put, item)
                finally:
                    # Send sentinel values to signal worker processes to stop (one per process).
                    # Each process's iterator_from_queue consumes one sentinel, then the shared
                    # parse_jobs_exhausted flag propagates termination to all workers in that process.
                    # This runs even if cancelled, allowing graceful shutdown.
                    for _ in range(max_processes):
                        await run_sync_on_thread(parse_job_queue.put, None)

            async def _upstream_collector() -> None:
                """Collector task that receives results and metrics."""
                nonlocal workers_ready_count

                items_processed = 0
                workers_finished = 0

                while workers_finished < max_processes:
                    # Thread sleeps in kernel until data arrives or shutdown sentinel injected
                    item = await run_sync_on_thread(upstream_queue.get)

                    match item:
                        case WorkerReady(worker_id):
                            # Should only receive these during startup phase
                            assert workers_ready_count < max_processes, (
                                f"Received WorkerReady from worker {worker_id} but already got {workers_ready_count}/{max_processes}"
                            )

                            workers_ready_count += 1
                            print_diagnostics(
                                "MP Collector",
                                f"P{worker_id} ready. {workers_ready_count}/{max_processes}",
                            )

                            # When all workers are ready, release them to start consuming
                            if workers_ready_count == max_processes:
                                print_diagnostics(
                                    "MP Collector",
                                    "All workers ready - releasing workers to consume parse jobs",
                                )
                                ipc_ctx.workers_ready_event.set()

                        case ResultItem(transcript_info, scanner_name, results):
                            await record_results(transcript_info, scanner_name, results)
                            items_processed += 1
                            print_diagnostics(
                                "MP Collector",
                                f"Recorded results for {transcript_info.transcript_id} (total: {items_processed})",
                            )

                        case MetricsItem(worker_id, metrics):
                            all_metrics[worker_id] = metrics
                            if update_metrics:
                                update_metrics(sum_metrics(all_metrics.values()))

                        case LoggingItem(record):
                            inspect_log_handler.emit(record)

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
                                f"Received shutdown sentinel (got {workers_finished}/{max_processes} worker completions)",
                            )
                            break

                        case WorkerComplete():
                            workers_finished += 1
                            print_diagnostics(
                                "MP Collector",
                                f"Worker finished ({workers_finished}/{max_processes})",
                            )

                        case Exception():
                            raise item

                print_diagnostics("MP Collector", "Finished collecting all items")

            from ._mp_subprocess import subprocess_main

            # Start worker processes directly
            processes: list[SpawnProcess] = []
            for worker_id in range(max_processes):
                task_count_for_worker = base_tasks + (
                    1 if worker_id < remainder_tasks else 0
                )
                try:
                    p = spawn_ctx.Process(
                        target=subprocess_main,
                        args=(
                            worker_id,
                            task_count_for_worker,
                            ipc_ctx,
                        ),
                    )
                    p.start()
                    processes.append(p)
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
                        ipc_ctx,
                        print_diagnostics,
                        _SHUTDOWN_SENTINEL,
                    )

        finally:
            signal.signal(signal.SIGINT, original_sigint_handler)
            _active = False

    return the_func
