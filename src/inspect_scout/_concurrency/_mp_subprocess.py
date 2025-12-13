"""Worker subprocess entry point for multiprocessing scanner execution.

This module contains the code that runs in spawned worker processes. The main
process spawns these workers, passing serialized IPCContext. Workers send both
results and metrics back to the main process via a single multiplexed upstream queue.
"""

from __future__ import annotations

import logging
import sys
import time
from threading import Condition
from typing import Callable

import anyio
from inspect_ai._eval.context import init_model_context
from inspect_ai.model._model_config import model_config_to_model
from inspect_ai.util._concurrency import init_concurrency

from inspect_scout._display._display import display

from .._scan import top_level_async_init
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from . import _mp_common
from ._iterator import iterator_from_queue
from ._mp_common import IPCContext, LoggingItem, run_sync_on_thread
from ._mp_logging import patch_inspect_log_handler
from ._mp_registry import ChildSemaphoreRegistry
from .common import ScanMetrics
from .single_process import single_process_strategy


async def _shutdown_monitor_task(
    condition: Condition,
    cancel_scope: anyio.CancelScope,
    print_diagnostics: Callable[[str, object], None],
) -> None:
    """Monitor shutdown condition and cancel worker when signaled.

    This task burns one thread waiting on the Condition. When the parent process
    signals shutdown, this cancels the entire worker via the cancel_scope, enabling
    immediate shutdown response.

    Args:
        condition: Shutdown condition shared with parent process
        cancel_scope: Cancel scope of the worker's task group
        print_diagnostics: Function to print diagnostic messages
    """
    try:

        def _wait_for_shutdown() -> None:
            with condition:
                condition.wait()

        await run_sync_on_thread(_wait_for_shutdown)

        print_diagnostics(
            "Shutdown Monitor", "Shutdown signal received - cancelling worker"
        )
        cancel_scope.cancel()

    except anyio.get_cancelled_exc_class():
        cancel_scope.cancel()

    except BaseException as ex:  # pylint: disable=W0718
        print_diagnostics("Shutdown Monitor", f"Monitor BaseException: {ex}")
        # On error, still cancel to be safe
        cancel_scope.cancel()


def subprocess_main(
    worker_id: int,
    task_count: int,
    ipc_ctx: IPCContext,
) -> None:
    """Worker subprocess main function.

    Runs in a spawned subprocess with IPCContext passed as argument.
    Uses single_process_strategy internally to coordinate async tasks.

    Args:
        worker_id: Unique identifier for this worker process
        task_count: Number of concurrent tasks for this worker process
        ipc_ctx: Shared IPC context passed from parent process
    """

    async def _worker_main() -> None:
        _initialize_subprocess()

        # Use single_process_strategy to coordinate the async tasks
        strategy = single_process_strategy(
            task_count=task_count,
            prefetch_multiple=ipc_ctx.prefetch_multiple,
            diagnostics=ipc_ctx.diagnostics,
            diag_prefix=f"P{worker_id}",
            overall_start_time=ipc_ctx.overall_start_time,
        )

        print_diagnostics(
            "Worker main",
            f"Initialized with {task_count} max tasks. Waiting for start...",
        )
        ipc_ctx.upstream_queue.put(_mp_common.WorkerReady(worker_id))
        await run_sync_on_thread(ipc_ctx.workers_ready_event.wait)

        # Run everything in a task group with shutdown monitor
        shutdown_monitor_scope: anyio.CancelScope | None = None

        try:
            async with anyio.create_task_group() as tg:
                # Spawn shutdown monitor in a separate cancel scope
                # This allows us to cancel it independently when work completes
                async def _monitor_wrapper() -> None:
                    nonlocal shutdown_monitor_scope
                    with anyio.CancelScope() as scope:
                        shutdown_monitor_scope = scope
                        await _shutdown_monitor_task(
                            ipc_ctx.shutdown_condition,
                            tg.cancel_scope,
                            print_diagnostics,
                        )

                tg.start_soon(_monitor_wrapper)

                # Run actual work - sends results and metrics via upstream queue
                async def _work_task() -> None:
                    try:
                        await strategy(
                            record_results=_record_to_queue,
                            parse_jobs=iterator_from_queue(ipc_ctx.parse_job_queue),
                            parse_function=ipc_ctx.parse_function,
                            scan_function=ipc_ctx.scan_function,
                            update_metrics=_update_worker_metrics,
                            completed=ipc_ctx.completed,
                        )
                        print_diagnostics("Worker main", "All tasks completed normally")
                    except Exception as ex:
                        print_diagnostics("Worker main", f"Work task error: {ex}")
                        # Send exception back to main process via upstream queue
                        ipc_ctx.upstream_queue.put(ex)
                        raise
                    finally:
                        # CRITICAL: Cancel the shutdown monitor to prevent hang.
                        # The monitor blocks indefinitely on condition.wait(), so
                        # if we don't cancel it when work completes, the task group
                        # will never exit and the sentinel will never be sent, causing
                        # the collector to wait forever.
                        if shutdown_monitor_scope:
                            print_diagnostics(
                                "Worker main", "Cancelling shutdown monitor"
                            )
                            shutdown_monitor_scope.cancel()

                tg.start_soon(_work_task)

        except anyio.get_cancelled_exc_class():
            # Cancelled by shutdown monitor - this is NORMAL during shutdown
            print_diagnostics("Worker main", "Worker cancelled by shutdown signal")
            # Do NOT raise - this is expected, and don't send sentinels

        except Exception as ex:
            print_diagnostics("Worker main", f"Worker error: {ex}")
            # Unexpected exception - re-raise
            raise

        else:
            # Clean completion - send completion sentinel
            # The else clause runs only if NO exception was raised in the try block.
            # We use else: instead of putting this at the end of the try block because
            # an exception in _work_task would prevent this from running, but the
            # except blocks above would catch and handle it, making control flow unclear.
            # With else:, it's explicit: sentinel is sent ONLY on clean completion.
            print_diagnostics("Worker main", "Sending completion sentinel")
            ipc_ctx.upstream_queue.put(_mp_common.WorkerComplete())

        print_diagnostics("Worker main", "exiting")

    def print_diagnostics(actor_name: str, *message_parts: object) -> None:
        if ipc_ctx.diagnostics:
            running_time = f"+{time.time() - ipc_ctx.overall_start_time:.3f}s"
            display().print(
                running_time, f"P{worker_id} ", f"{actor_name}:", *message_parts
            )

    # Define callbacks to send results and metrics back to main process via upstream queue
    async def _record_to_queue(
        transcript: TranscriptInfo, scanner: str, results: list[ResultReport]
    ) -> None:
        ipc_ctx.upstream_queue.put(_mp_common.ResultItem(transcript, scanner, results))

    def _update_worker_metrics(metrics: ScanMetrics) -> None:
        ipc_ctx.upstream_queue.put(_mp_common.MetricsItem(worker_id, metrics))

    def _log_in_parent(record: logging.LogRecord) -> None:
        # Strip exc_info from record to avoid pickling traceback objects since it
        # cannot be serialized across process boundaries
        record.exc_info = None
        ipc_ctx.upstream_queue.put(LoggingItem(record))

    def _initialize_subprocess() -> None:
        # Set up sys.path with plugin directory before any user imports
        if ipc_ctx.plugin_dir is not None and ipc_ctx.plugin_dir not in sys.path:
            sys.path.insert(0, ipc_ctx.plugin_dir)

        top_level_async_init(ipc_ctx.log_level, main_process=False)

        init_model_context(
            model=model_config_to_model(ipc_ctx.model_config),
            model_roles=ipc_ctx.model_roles,
            config=ipc_ctx.generate_config,
        )

        patch_inspect_log_handler(_log_in_parent)

        # Initialize concurrency with cross-process semaphore registry
        # This allows workers to request semaphores from the parent via IPC
        init_concurrency(
            ChildSemaphoreRegistry(
                ipc_ctx.semaphore_registry,
                ipc_ctx.semaphore_condition,
                ipc_ctx.upstream_queue,
            )
        )

    # Run the async event loop in this worker process
    anyio.run(_worker_main)
