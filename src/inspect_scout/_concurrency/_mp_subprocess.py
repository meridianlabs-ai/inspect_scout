"""Worker subprocess entry point for multiprocessing scanner execution.

This module contains the code that runs in forked worker processes. The main
process spawns these workers via ProcessPoolExecutor, and they inherit shared
state from _mp_context through fork.
"""

from __future__ import annotations

import time

import anyio

from inspect_scout._concurrency.common import ScanMetrics
from inspect_scout._display._display import display

from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from . import _mp_common
from ._iterator import iterator_from_mp_queue
from .single_process import single_process_strategy


def subprocess_main(
    worker_id: int,
) -> None:
    """Worker subprocess main function.

    Runs in a forked subprocess with access to parent's memory.
    Uses single_process_strategy internally to coordinate async tasks.

    Args:
        worker_id: Unique identifier for this worker process
    """
    # Access IPC context inherited from parent process via fork
    ctx = _mp_common.ipc_context

    async def _worker_main() -> None:
        """Main async function for worker process."""

        def print_diagnostics(actor_name: str, *message_parts: object) -> None:
            if ctx.diagnostics:
                running_time = f"+{time.time() - ctx.overall_start_time:.3f}s"
                display().print(
                    running_time, f"P{worker_id} ", f"{actor_name}:", *message_parts
                )

        print_diagnostics(
            "worker main",
            f"Starting with {ctx.tasks_per_process} max concurrent scans",
        )

        # Use single_process_strategy to coordinate the async tasks
        strategy = single_process_strategy(
            task_count=ctx.tasks_per_process,
            prefetch_multiple=ctx.prefetch_multiple,
            diagnostics=ctx.diagnostics,
            diag_prefix=f"P{worker_id}",
            overall_start_time=ctx.overall_start_time,
        )

        # Define callback to send results back to main process via queue
        async def _record_to_queue(
            transcript: TranscriptInfo, scanner: str, results: list[ResultReport]
        ) -> None:
            ctx.result_queue.put((transcript, scanner, results))

        def _update_worker_metrics(metrics: ScanMetrics) -> None:
            ctx.metrics_queue.put((worker_id, metrics))

        try:
            await strategy(
                record_results=_record_to_queue,
                parse_jobs=iterator_from_mp_queue(ctx.parse_job_queue),
                parse_function=ctx.parse_function,
                scan_function=ctx.scan_function,
                update_metrics=_update_worker_metrics,
            )
        except Exception as ex:
            # Send exception back to main process
            ctx.result_queue.put(ex)
            raise

        print_diagnostics("All tasks completed")

        # Send completion sentinels to both collectors
        ctx.result_queue.put(None)
        ctx.metrics_queue.put(None)

    # Run the async event loop in this worker process
    anyio.run(_worker_main)
