import time
from collections import deque
from typing import AsyncIterator, Awaitable, Callable, Literal

import anyio
import psutil
from anyio import create_task_group
from inspect_ai.model._providers.util.batch_log import (
    BatchStatus,
    set_batch_log_callback,
    set_batch_status_callback,
)
from inspect_ai.util import throttle
from inspect_ai.util._anyio import inner_exception

from .._display import display
from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from ._iterator import SerializedAsyncIterator
from .common import (
    ConcurrencyStrategy,
    ParseFunctionResult,
    ParseJob,
    ScanMetrics,
    ScannerJob,
)

# Module-level counter for assigning unique worker IDs
worker_id_counter: int = 0


def single_process_strategy(
    *,
    task_count: int,
    prefetch_multiple: float | None = 1.0,
    diagnostics: bool = False,
    diag_prefix: str | None = None,
    overall_start_time: float | None = None,
) -> ConcurrencyStrategy:
    """Single-process execution strategy with adaptive application-layer scheduling.

    Overview
    --------
    Implements a worker pool where workers dynamically choose between parsing and
    scanning based on runtime conditions using an adaptive scheduler.

    Design Goals
    ------------
    - **Fast Completion**: Minimize total execution time by maximizing worker utilization
    - **Adaptive Scheduling**: Automatically adjust parse:scan ratios based on workload
    - **I/O Optimization**: Maximize parallelism for I/O-bound tasks (e.g., LLM API calls)
    - **Variable Task Handling**: Efficiently handle tasks with widely varying durations
    - **Memory Efficiency**: Buffer only what's needed to keep workers saturated

    Architecture
    ------------
    Spawns initial_workers at startup (default: min(10, task_count)), then workers
    spawn additional workers dynamically up to task_count as they complete tasks.
    Workers execute in a loop where in each iteration they:
    1. Consult the scheduler to determine next action (parse, scan, or wait)
    2. Execute the chosen action
    3. Update metrics
    4. Potentially spawn additional workers if under task_count
    5. Yield control to allow other workers to execute

    The scheduler decision function evaluates:
    - Whether parse jobs remain to be processed
    - Scanner job queue fullness (backpressure indicator)
    - Number of workers currently parsing vs scanning

    Args:
        task_count: Number of worker tasks.
        prefetch_multiple: Multiplier for scanner job queue size (base=task_count).
        diagnostics: Enable detailed logging of worker actions, queue state, and
            timing. Useful for performance analysis and debugging scheduler behavior.
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
        parse_function: Callable[[ParseJob], Awaitable[ParseFunctionResult]],
        scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]],
        update_metrics: Callable[[ScanMetrics], None] | None = None,
        completed: Callable[[], Awaitable[None]],
    ) -> None:
        metrics = ScanMetrics(1)
        nonlocal overall_start_time
        if not overall_start_time:
            overall_start_time = time.time()
        max_scanner_job_queue_size = int(
            task_count * (prefetch_multiple if prefetch_multiple is not None else 1.0)
        )

        scanner_job_deque: deque[ScannerJob] = deque()
        process = psutil.Process()

        def _on_batch_status(status: BatchStatus) -> None:
            metrics.batch_pending = status.pending_requests
            metrics.batch_failures = status.failed_requests
            metrics.batch_oldest_created = status.oldest_created_at
            _update_metrics()

        def _on_batch_log(msg: str) -> None:
            # suppress the detailed logging
            pass

        set_batch_status_callback(_on_batch_status)
        set_batch_log_callback(_on_batch_log)

        # CRITICAL: Serialize access to the parse_jobs iterator.
        #
        # This strategy spawns multiple concurrent worker tasks. When multiple workers
        # choose to parse simultaneously, because anext is by definition async, they
        # could both end up within anext(parse_jobs). This is not supported, and
        # the runtime will raise "anext(): asynchronous generator is already running".
        parse_jobs = SerializedAsyncIterator(parse_jobs)
        parse_jobs_exhausted = False

        def print_diagnostics(actor_name: str, *message_parts: object) -> None:
            if diagnostics:
                running_time = f"+{time.time() - overall_start_time:.3f}s"
                display().print(
                    running_time, diag_prefix, f"{actor_name}:", *message_parts
                )

        def _scanner_job_info(item: ScannerJob) -> str:
            return f"{item.union_transcript.transcript_id, item.scanner_name}"

        @throttle(2)
        def _update_metrics() -> None:
            if update_metrics:
                # USS - Unique Set Size
                metrics.memory_usage = process.memory_full_info().uss
                # print(f"{diag_prefix} CPU {metrics.cpu_use}")
                metrics.buffered_scanner_jobs = len(scanner_job_deque)
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
                and metrics.tasks_parsing < 2
                and not parse_jobs_exhausted
            ):
                return "parse"

            # Rule 4: If someone is already parsing and we have scanner jobs, prefer to scan
            if metrics.tasks_parsing > 0 and scanner_job_queue_len > 0:
                return "scan"

            # Rule 5: If no one is parsing and queue isn't near full, someone should parse
            # This prevents gaps in production when the last parser finishes and switches to scanning
            # The <80% check prevents parse stampedes when all parsers finish simultaneously
            if (
                metrics.tasks_parsing == 0
                and not parse_jobs_exhausted
                and scanner_job_queue_len < max_scanner_job_queue_size * 0.8
            ):
                return "parse"

            # Rule 6: If we have scanner jobs, scan them
            if scanner_job_queue_len > 0:
                return "scan"

            # Rule 7: Both queues empty/exhausted
            return "wait"

        async def _perform_wait(current_wait_duration: float) -> float:
            """Perform the wait action: yield control and update metrics.

            Returns the next wait duration to use. First wait is 0s, subsequent waits are 1s.
            """
            metrics.tasks_idle += 1
            _update_metrics()
            await anyio.sleep(current_wait_duration)
            metrics.tasks_idle -= 1
            return 1.0 if current_wait_duration == 0 else 1.0

        async def _perform_parse(worker_id: int) -> bool:
            """Perform the parse action. Returns True if parse job was pulled from the queue, False if there was no parse job to perform."""
            # Pull from parse_jobs iterator and create scanner jobs
            try:
                parse_job = await anext(parse_jobs)
            except StopAsyncIteration:
                return False

            exec_start_time = time.time()
            metrics.tasks_parsing += 1
            _update_metrics()

            try:
                result = await parse_function(parse_job)
                print_diagnostics(
                    f"Worker #{worker_id:02d}",
                    f"Parsed  ({(time.time() - exec_start_time):.3f}s) - ('{parse_job.transcript_info.transcript_id}')",
                )

                # Check success/failure tag
                if result[0]:
                    # Success: enqueue scanner jobs
                    for scanner_job in result[1]:
                        scanner_job_deque.append(scanner_job)
                else:
                    # Error: record error results
                    for result_report in result[1]:
                        assert result_report.error is not None
                        await record_results(
                            parse_job.transcript_info,
                            result_report.error.scanner,
                            [result_report],
                        )

                _update_metrics()
                return True
            finally:
                metrics.tasks_parsing -= 1

        async def _perform_scan(worker_id: int) -> bool:
            """Perform the scan action. Returns True if scan completed, False otherwise."""
            if len(scanner_job_deque) == 0:
                # Race condition: queue became empty
                await anyio.sleep(0)
                return False

            scanner_job = scanner_job_deque.popleft()
            exec_start_time = time.time()
            metrics.tasks_scanning += 1
            _update_metrics()

            try:
                await record_results(
                    scanner_job.union_transcript,
                    scanner_job.scanner_name,
                    await scan_function(scanner_job),
                )
                metrics.completed_scans += 1
                print_diagnostics(
                    f"Worker #{worker_id:02d}",
                    f"Scanned ({(time.time() - exec_start_time):.3f}s) - {_scanner_job_info(scanner_job)}",
                )
                return True
            finally:
                metrics.tasks_scanning -= 1

        async def _worker_task(
            worker_id: int,
        ) -> None:
            """Worker that dynamically chooses between parsing and scanning."""
            nonlocal parse_jobs_exhausted
            scans_completed = 0
            parses_completed = 0
            wait_duration = 0.0

            try:
                while True:
                    action = _choose_next_action()

                    if action == "wait":
                        wait_duration = await _perform_wait(wait_duration)
                    elif action == "parse":
                        wait_duration = 0.0
                        if await _perform_parse(worker_id):
                            parses_completed += 1
                        else:
                            print_diagnostics(
                                f"Worker #{worker_id:02d}", "No more parse jobs"
                            )
                            parse_jobs_exhausted = True
                    elif action == "scan":
                        wait_duration = 0.0
                        if await _perform_scan(worker_id):
                            scans_completed += 1

                    # Check if we're done: parse queue exhausted, scanner queue empty, all tasks waiting
                    if (
                        parse_jobs_exhausted
                        and len(scanner_job_deque) == 0
                        and metrics.tasks_idle == metrics.task_count - 1
                    ):
                        break

                print_diagnostics(
                    f"Worker #{worker_id:02d}",
                    f"Finished after {parses_completed} parses and {scans_completed} scans.",
                )
            finally:
                metrics.task_count -= 1
                _update_metrics()

        try:
            async with create_task_group() as tg:
                # Spawn initial workers for faster ramp-up
                global worker_id_counter
                for _ in range(task_count):
                    worker_id_counter += 1
                    metrics.task_count += 1
                    tg.start_soon(_worker_task, worker_id_counter)

        except Exception as ex:
            raise inner_exception(ex) from None
        finally:
            set_batch_status_callback(None)
            metrics.process_count = 0
            metrics.tasks_parsing = 0
            metrics.tasks_scanning = 0
            metrics.tasks_idle = 0
            _update_metrics()
            await completed()

    return the_func
