import time
from collections import deque
from typing import AsyncIterator, Awaitable, Callable, Literal

import anyio
from anyio import create_task_group
from anyio.abc import TaskGroup
from inspect_ai.util._anyio import inner_exception

from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .common import ConcurrencyStrategy, ParseJob, ScannerJob, WorkerMetrics

# Module-level counter for assigning unique worker IDs
worker_id_counter: int = 0


def single_process_strategy(
    *,
    max_concurrent_scans: int,
    buffer_multiple: float | None = 1.0,
    diagnostics: bool = False,
    diag_prefix: str | None = None,
    overall_start_time: float | None = None,
) -> ConcurrencyStrategy:
    """Single-process execution strategy with adaptive application-layer scheduling.

    Overview
    --------
    Implements a homogeneous worker pool where all workers dynamically choose between
    parsing (producing scanner jobs) and scanning (consuming scanner jobs) based
    on runtime conditions using an adaptive scheduler that automatically balances
    work based on actual task characteristics and queue state.

    Design Goals
    ------------
    - **Fast Completion**: Minimize total execution time by maximizing worker utilization
    - **Adaptive Scheduling**: Automatically adjust parse:scan ratios based on workload
    - **I/O Optimization**: Maximize parallelism for I/O-bound tasks (e.g., LLM API calls)
    - **Variable Task Handling**: Efficiently handle tasks with widely varying durations
    - **Memory Efficiency**: Buffer only what's needed to keep workers saturated

    Architecture
    ------------
    Workers are identical and execute in a loop where each iteration:
    1. Consult the scheduler to determine next action (parse, scan, or wait)
    2. Execute the chosen action
    3. Update metrics
    4. Potentially spawn additional workers if under max_concurrent_scans
    5. Yield control to allow other workers to execute

    The scheduler decision function evaluates:
    - Whether parse jobs remain to be processed
    - Scanner job queue fullness (backpressure indicator)
    - Number of workers currently parsing vs scanning

    Scheduling Algorithm
    --------------------
    Priority order for action selection (note: "parse jobs remain" means the parse_jobs
    iterator has not yet been exhausted):

    1. If scan queue full → SCAN
    2. If scan queue empty AND parse jobs remain → PARSE (refill pipeline)
    3. If scan queue low (<20% capacity) AND few parsers (<2) AND parse jobs remain
       → PARSE (prevent starvation from slow parsers)
    4. If someone parsing AND queue not empty → SCAN (prefer consumption)
    5. If NO ONE parsing AND parse jobs remain AND queue not near full (<80% capacity)
       → PARSE (fill production gap, anti-stampede protection)
    6. If scanner jobs available → SCAN (consume remaining work)
    7. Otherwise → WAIT (check for exit condition)

    Edge Cases Handled
    ------------------
    - **Simultaneous Parser Completion**: Rule 5's 80% threshold prevents all workers
      from bursting into PARSE when multiple parsers finish at once and workers_parsing
      momentarily drops to 0. Workers only parse if queue genuinely needs filling.

    - **Slow Parser Starvation**: Rule 3 detects when a single slow parser can't keep
      up with fast scanners (queue <20%, only 1 parser active). Spawns a second parser
      to prevent queue from draining to empty and stalling workers.

    - **Fast Parser → Scanner Transition**: When the lone parser finishes and switches
      to scanning, Rule 5 ensures another worker quickly picks up parsing (queue <80%),
      maintaining continuous production without oscillation.

    - **Ramp-up Burst Parsing**: During startup when queue is empty, Rule 2 correctly
      allows multiple workers to parse simultaneously to quickly fill the pipeline.

    Args:
        max_concurrent_scans: Maximum number of workers. Controls both scan parallelism
            and worker pool size. Recommend setting to balance I/O parallelism with
            system resources (typically 50-200 for LLM-based scanners).
        buffer_multiple: Multiplier for scanner job queue size (base=max_concurrent_scans).
            Default 1.0 provides one buffered job per worker. Higher values increase
            memory usage without improving throughput if parsing is fast. Lower values
            risk parser stalls if scans complete in bursts.
        diagnostics: Enable detailed logging of worker actions, queue state, and timing.
            Useful for performance analysis and debugging scheduler behavior.
        diag_prefix: Optional prefix for diagnostic messages (internal use).
        overall_start_time: Optional start time for relative timestamps (internal use).
    """
    diag_prefix = f"{diag_prefix} " if diag_prefix else ""

    async def the_func(
        *,
        record_results: Callable[
            [TranscriptInfo, str, list[ResultReport]], Awaitable[None]
        ],
        parse_jobs: AsyncIterator[ParseJob],
        parse_function: Callable[[ParseJob], Awaitable[list[ScannerJob]]],
        scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]],
        bump_progress: Callable[[], None],
        update_metrics: Callable[[WorkerMetrics], None] | None = None,
    ) -> None:
        metrics = WorkerMetrics()
        nonlocal overall_start_time
        if not overall_start_time:
            overall_start_time = time.time()
        max_scanner_job_queue_size = int(
            max_concurrent_scans
            * (buffer_multiple if buffer_multiple is not None else 1.0)
        )

        scanner_job_deque: deque[ScannerJob] = deque()
        parse_jobs_exhausted = False

        def print_diagnostics(actor_name: str, *message_parts: object) -> None:
            if diagnostics:
                running_time = f"+{time.time() - overall_start_time:.3f}s"
                print(running_time, diag_prefix, f"{actor_name}:", *message_parts)

        def _metrics_info() -> str:
            return (
                f"workers: {metrics.worker_count} "
                f"(parsing: {metrics.workers_parsing}, "
                f"scanning: {metrics.workers_scanning}, "
                f"waiting: {metrics.workers_waiting}) "
                f"queue size: {len(scanner_job_deque)} "
            )

        def _scanner_job_info(item: ScannerJob) -> str:
            return f"{item.union_transcript.id, item.scanner_name}"

        def _update_metrics() -> None:
            if update_metrics:
                metrics.buffered_jobs = len(scanner_job_deque)
                update_metrics(metrics)

        def _choose_next_action() -> Literal["parse", "scan", "wait"]:
            """Decide what action this worker should take: 'parse', 'scan', or 'wait'."""
            scanner_job_queue_len = len(scanner_job_deque)

            # Rule 1: If scanner queue is full, we must scan to relieve backpressure
            if scanner_job_queue_len >= max_scanner_job_queue_size:
                return "scan"

            # Rule 2: If scanner queue is empty and we have parse jobs, we must parse
            if scanner_job_queue_len == 0 and not parse_jobs_exhausted:
                return "parse"

            # Rule 3: If queue is low and we have few parsers, help parse to prevent starvation
            # This handles the case where a single slow parser can't keep up with fast scanners
            if (
                scanner_job_queue_len < max_scanner_job_queue_size * 0.2
                and metrics.workers_parsing < 2
                and not parse_jobs_exhausted
            ):
                return "parse"

            # Rule 4: If someone is already parsing and we have scanner jobs, prefer to scan
            if metrics.workers_parsing > 0 and scanner_job_queue_len > 0:
                return "scan"

            # Rule 5: If no one is parsing and queue isn't near full, someone should parse
            # This prevents gaps in production when the last parser finishes and switches to scanning
            # The <80% check prevents parse stampedes when all parsers finish simultaneously
            if (
                metrics.workers_parsing == 0
                and not parse_jobs_exhausted
                and scanner_job_queue_len < max_scanner_job_queue_size * 0.8
            ):
                return "parse"

            # Rule 6: If we have scanner jobs, scan them
            if scanner_job_queue_len > 0:
                return "scan"

            # Rule 7: Both queues empty/exhausted
            return "wait"

        async def _unified_worker_task(
            worker_id: int, tg: TaskGroup, parse_jobs_iter: AsyncIterator[ParseJob]
        ) -> None:
            """Unified worker that dynamically chooses between parsing and scanning."""
            nonlocal parse_jobs_exhausted
            scans_completed = 0
            parses_completed = 0

            try:
                while True:
                    action = _choose_next_action()

                    if action == "wait":
                        # Both queues empty - wait briefly and check again
                        metrics.workers_waiting += 1
                        _update_metrics()
                        await anyio.sleep(0.1)
                        metrics.workers_waiting -= 1
                        _update_metrics()

                        # If still nothing to do, exit
                        if _choose_next_action() == "wait":
                            break
                        continue

                    elif action == "parse":
                        # Parse action: pull from parse_jobs iterator and create scanner jobs
                        try:
                            parse_job = await anext(parse_jobs_iter)
                        except StopAsyncIteration:
                            parse_jobs_exhausted = True
                            print_diagnostics(
                                f"Worker #{worker_id}", "Parse iterator exhausted"
                            )
                            continue

                        exec_start_time = time.time()
                        metrics.workers_parsing += 1
                        _update_metrics()

                        try:
                            scanner_jobs = await parse_function(parse_job)
                            print_diagnostics(
                                f"Worker #{worker_id}",
                                f"Parsed {parse_job.transcript_info.id} -> {len(scanner_jobs)} scanner jobs in {(time.time() - exec_start_time):.3f}s\n\t{_metrics_info()}",
                            )

                            for scanner_job in scanner_jobs:
                                scanner_job_deque.append(scanner_job)
                            _update_metrics()
                            parses_completed += 1
                        finally:
                            metrics.workers_parsing -= 1
                            _update_metrics()

                    elif action == "scan":
                        # Scan action: pop from scanner_job_deque and execute
                        if len(scanner_job_deque) == 0:
                            # Race condition: queue became empty
                            await anyio.sleep(0)
                            continue

                        scanner_job = scanner_job_deque.popleft()
                        _update_metrics()

                        print_diagnostics(
                            f"Worker #{worker_id}",
                            f"Starting scan on {_scanner_job_info(scanner_job)}\n\t{_metrics_info()}",
                        )

                        exec_start_time = time.time()
                        metrics.workers_scanning += 1
                        _update_metrics()

                        try:
                            await record_results(
                                scanner_job.union_transcript,
                                scanner_job.scanner_name,
                                await scan_function(scanner_job),
                            )
                            bump_progress()
                            print_diagnostics(
                                f"Worker #{worker_id}",
                                f"Completed {_scanner_job_info(scanner_job)} in {(time.time() - exec_start_time):.3f}s",
                            )
                            scans_completed += 1
                        finally:
                            metrics.workers_scanning -= 1
                            _update_metrics()

                    # After completing work, check if we should spawn more workers
                    if (
                        len(scanner_job_deque) > 0 or not parse_jobs_exhausted
                    ) and metrics.worker_count < max_concurrent_scans:
                        metrics.worker_count += 1
                        _update_metrics()
                        global worker_id_counter
                        worker_id_counter += 1
                        tg.start_soon(
                            _unified_worker_task, worker_id_counter, tg, parse_jobs_iter
                        )
                        print_diagnostics(
                            f"Worker #{worker_id}",
                            f"Spawned worker #{worker_id_counter}\n\t{_metrics_info()}",
                        )

                    await anyio.sleep(0)

                print_diagnostics(
                    f"Worker #{worker_id}",
                    f"Finished after {parses_completed} parses and {scans_completed} scans.\n\t{_metrics_info()}",
                )
            finally:
                metrics.worker_count -= 1
                _update_metrics()

        try:
            async with create_task_group() as outer_tg:
                progress_cancel_scope = None

                async def progress_task() -> None:
                    nonlocal progress_cancel_scope
                    with anyio.CancelScope() as cancel_scope:
                        progress_cancel_scope = cancel_scope
                        while True:
                            print_diagnostics(
                                "HelloTask",
                                f"hello at {time.time()} queue={len(scanner_job_deque)}",
                            )
                            await anyio.sleep(2)

                outer_tg.start_soon(progress_task)

                async with create_task_group() as tg:
                    # Spawn 2 initial workers
                    global worker_id_counter
                    for _ in range(2):
                        worker_id_counter += 1
                        metrics.worker_count += 1
                        tg.start_soon(
                            _unified_worker_task, worker_id_counter, tg, parse_jobs
                        )
                        print_diagnostics(
                            "Initialization",
                            f"Spawned initial worker #{worker_id_counter}",
                        )
                    _update_metrics()

                if progress_cancel_scope:
                    progress_cancel_scope.cancel()
        except Exception as ex:
            raise inner_exception(ex) from ex

    return the_func
