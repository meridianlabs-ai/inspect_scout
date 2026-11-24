import contextlib
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Awaitable, Callable, Literal

import anyio
import psutil
from anyio import create_task_group
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from inspect_ai.model._providers.util.batch_log import (
    BatchStatus,
    set_batch_log_callback,
    set_batch_status_callback,
)
from inspect_ai.util import throttle
from inspect_ai.util._anyio import inner_exception

from .._display import display
from .._scanner.result import ResultReport
from .._transcript.transcripts import TranscriptsReader
from .._transcript.types import TranscriptInfo
from ._iterator import SerializedAsyncIterator
from .common import (
    ConcurrencyStrategy,
    LoaderItemJob,
    ParseFunctionResult,
    ParseJob,
    ReaderCMFactory,
    ScanFunction,
    ScanMetrics,
    ScannerJob,
)

# Module-level counter for assigning unique worker IDs
worker_id_counter: int = 0

ItemResult = MemoryObjectReceiveStream[ResultReport | None]
"""Result stream of one started item scan."""


@dataclass(eq=False)
class _JobRecord:
    """Scheduler state of one admitted `ScannerJob`."""

    job: ScannerJob
    followers: tuple["_JobRecord", ...]
    grants: MemoryObjectSendStream[None] | None = None
    """Grants one pull to the job's owner task. None until the first pull."""
    replies: MemoryObjectReceiveStream[ItemResult | None] | None = None
    """The owner's reply to a grant: an item's result stream, or None at end of loader."""
    in_flight: int = 0
    loader_done: bool = False
    reports: list[ResultReport] = field(default_factory=list)


def _job_record(job: ScannerJob) -> _JobRecord:
    return _JobRecord(job, tuple(_job_record(follower) for follower in job.followers))


def _flatten(record: _JobRecord) -> list[_JobRecord]:
    return [record, *(r for follower in record.followers for r in _flatten(follower))]


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
    Starts all task_count workers at once. Workers execute in a loop where in
    each iteration they:
    1. Consult the scheduler to determine next action (parse, scan, or wait)
    2. Execute the chosen action
    3. Update metrics

    The unit of scan work is a `LoaderItemJob`: one loader item of a
    `ScannerJob`. One owner task per job does every pull of the job's loader
    and closes it. A worker that scans grants one pull to the owner. The owner
    starts the item scan as a child task (so the scanner sees the loader's
    context), and the worker holds its slot until that scan ends. While the
    item scans, the job goes back to the front of the queue so that another
    worker can pull its next item. A job finishes after its loader ends and its
    last item scan ends: `on_complete`, then `record_results` with all its
    reports, then its followers go into the queue. Idle workers wait on an
    event and wake when a job goes into the queue.

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
        parse_function: Callable[
            [ParseJob, TranscriptsReader], Awaitable[ParseFunctionResult]
        ],
        scan_function: ScanFunction,
        update_metrics: Callable[[ScanMetrics], None] | None = None,
        reader_cm_factory: ReaderCMFactory,
    ) -> None:
        metrics = ScanMetrics(1)
        nonlocal overall_start_time
        if not overall_start_time:
            overall_start_time = time.time()
        max_scanner_job_queue_size = int(
            task_count * (prefetch_multiple if prefetch_multiple is not None else 1.0)
        )

        # jobs that wait for a pull
        scanner_job_deque: deque[_JobRecord] = deque()
        # every admitted job that has not finished (leads and followers)
        live: set[_JobRecord] = set()
        # one event per idle worker
        waiters: deque[anyio.Event] = deque()
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
            transcript_id = item.transcript_info.transcript_id
            return f"{transcript_id, item.scanner_name}"

        # the finally at the end of the_func delivers the final zeroed update
        # itself, and sets this so a trailing-edge fire still pending in the
        # throttle does not deliver a duplicate of it after teardown. the guard
        # lives in the throttled wrapper, so the suppression holds regardless of
        # the order of the delivery and the flag in that finally
        final_metrics_delivered = False

        def _update_metrics_now() -> None:
            if update_metrics:
                # USS - Unique Set Size
                metrics.memory_usage = process.memory_full_info().uss
                # print(f"{diag_prefix} CPU {metrics.cpu_use}")
                metrics.buffered_scanner_jobs = len(scanner_job_deque)
                update_metrics(metrics)

        @throttle(1)
        def _update_metrics() -> None:
            if not final_metrics_delivered:
                _update_metrics_now()

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

        def _enqueue(record: _JobRecord, *, front: bool = False) -> None:
            """Put a job into the queue and wake one idle worker."""
            if front:
                scanner_job_deque.appendleft(record)
            else:
                scanner_job_deque.append(record)
            if waiters:
                waiters.popleft().set()

        def _wake_all() -> None:
            while waiters:
                waiters.popleft().set()

        async def _perform_wait() -> None:
            """Perform the wait action: wait until a job goes into the queue or a worker exits."""
            event = anyio.Event()
            waiters.append(event)
            metrics.tasks_idle += 1
            _update_metrics()
            await event.wait()
            metrics.tasks_idle -= 1

        async def _perform_parse(worker_id: int, reader: TranscriptsReader) -> bool:
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
                result = await parse_function(parse_job, reader)
                print_diagnostics(
                    f"Worker #{worker_id:02d}",
                    f"Parsed  ({(time.time() - exec_start_time):.3f}s) - ('{parse_job.transcript_info.transcript_id}')",
                )

                # Check success/failure tag
                if result[0]:
                    # Success: enqueue the lead scanner job (followers are
                    # attached to it and released when it completes).
                    lead = _job_record(result[1])
                    live.update(_flatten(lead))
                    _enqueue(lead)
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

        async def _run_item(
            item: LoaderItemJob, result: MemoryObjectSendStream[ResultReport | None]
        ) -> None:
            report = await item.scan()
            with result:
                await result.send(report)

        async def _loader_owner(
            job: ScannerJob,
            grants: MemoryObjectReceiveStream[None],
            replies: MemoryObjectSendStream[ItemResult | None],
        ) -> None:
            """Do every pull of the job's loader, and close it, in this one task.

            Pulls one item per grant and starts its scan as a child task, so the
            scan sees the context that the loader set up.
            """
            with anyio.CancelScope() as cleanup:
                items = scan_function(job)
                try:
                    async for _ in grants:
                        try:
                            item = await anext(items)
                        except StopAsyncIteration:
                            await replies.send(None)
                            grants.close()
                            replies.close()
                            return
                        result_send, result_receive = anyio.create_memory_object_stream[
                            ResultReport | None
                        ]()
                        worker_tg.start_soon(_run_item, item, result_send)
                        await replies.send(result_receive)
                finally:
                    # a cancelled scan must still close the loader
                    cleanup.shield = True
                    await items.aclose()

        def _start_owner(
            job: ScannerJob,
        ) -> tuple[
            MemoryObjectSendStream[None], MemoryObjectReceiveStream[ItemResult | None]
        ]:
            grant_send, grant_receive = anyio.create_memory_object_stream[None]()
            reply_send, reply_receive = anyio.create_memory_object_stream[
                ItemResult | None
            ]()
            worker_tg.start_soon(_loader_owner, job, grant_receive, reply_send)
            return grant_send, reply_receive

        async def _finish(record: _JobRecord) -> None:
            """Finish a job once: `on_complete`, record its reports, release its followers."""
            # the claim: no await before this, so only one caller gets here
            live.remove(record)
            try:
                if record.job.on_complete is not None:
                    with anyio.CancelScope(shield=True):
                        await record.job.on_complete()
                await record_results(
                    record.job.transcript_info,
                    record.job.scanner_name,
                    record.reports,
                )
                metrics.completed_scans += 1
            finally:
                # Release any followers held back by this lead. No-op when the
                # job has no followers (single-scanner-per-transcript case).
                for follower in record.followers:
                    _enqueue(follower)

        async def _perform_scan(worker_id: int) -> bool:
            """Perform the scan action: pull one item of a job, and scan it.

            Returns True if it pulled from a job, False if the queue was empty.
            """
            if len(scanner_job_deque) == 0:
                # Race condition: queue became empty
                await anyio.sleep(0)
                return False

            record = scanner_job_deque.popleft()
            exec_start_time = time.time()
            metrics.tasks_scanning += 1
            _update_metrics()

            try:
                if record.grants is None or record.replies is None:
                    record.grants, record.replies = _start_owner(record.job)
                await record.grants.send(None)
                item_result = await record.replies.receive()
                if item_result is None:
                    record.loader_done = True
                    record.grants.close()
                    record.replies.close()
                else:
                    # let another worker pull the next item while this one scans
                    _enqueue(record, front=True)
                    record.in_flight += 1
                    with item_result:
                        report = await item_result.receive()
                    if report is not None:
                        record.reports.append(report)
                    record.in_flight -= 1
                    print_diagnostics(
                        f"Worker #{worker_id:02d}",
                        f"Scanned ({(time.time() - exec_start_time):.3f}s) - {_scanner_job_info(record.job)}",
                    )
                # If the item scan raises, this worker does not get here: the
                # task group failure path and the drain own the job.
                if record.loader_done and record.in_flight == 0:
                    await _finish(record)
                return True
            finally:
                metrics.tasks_scanning -= 1

        async def _worker_task(
            worker_id: int,
            reader: TranscriptsReader,
        ) -> None:
            """Worker that dynamically chooses between parsing and scanning."""
            nonlocal parse_jobs_exhausted
            scans_completed = 0
            parses_completed = 0

            try:
                while True:
                    action = _choose_next_action()

                    if action == "wait":
                        await _perform_wait()
                    elif action == "parse":
                        if await _perform_parse(worker_id, reader):
                            parses_completed += 1
                        else:
                            print_diagnostics(
                                f"Worker #{worker_id:02d}", "No more parse jobs"
                            )
                            parse_jobs_exhausted = True
                    elif action == "scan":
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
                # the woken workers see this worker gone and check for the end
                _wake_all()
                _update_metrics()

        async def _metrics_ticker(scope: anyio.CancelScope) -> None:
            """Periodically push metrics to the display during long-running operations."""
            with scope:
                while True:
                    await anyio.sleep(1)
                    _update_metrics()

        try:
            async with reader_cm_factory() as reader:
                async with create_task_group() as tg:
                    ticker_scope = anyio.CancelScope()
                    tg.start_soon(_metrics_ticker, ticker_scope)

                    # Start all workers at once
                    global worker_id_counter
                    async with create_task_group() as worker_tg:
                        for _ in range(task_count):
                            worker_id_counter += 1
                            metrics.task_count += 1
                            worker_tg.start_soon(
                                _worker_task, worker_id_counter, reader
                            )
                    ticker_scope.cancel()

            # The pool can also end with no exception when a scanner or loader
            # raises a bare CancelledError. Do not report that as a success.
            if not parse_jobs_exhausted or live:
                raise RuntimeError(
                    f"Scan interrupted: {len(live)} scanner jobs did not finish"
                    + (
                        ""
                        if parse_jobs_exhausted
                        else ", and transcripts remain to parse"
                    )
                )

        except Exception as ex:
            raise inner_exception(ex) from None
        finally:
            set_batch_status_callback(None)
            set_batch_log_callback(None)
            metrics.process_count = 0
            metrics.tasks_parsing = 0
            metrics.tasks_scanning = 0
            metrics.tasks_idle = 0
            # deliver synchronously, since a throttled call would defer to a
            # trailing-edge fire that may not survive teardown (#569). the flag
            # suppresses any such fire that is still pending
            _update_metrics_now()
            final_metrics_delivered = True

            # A worker pool torn down early (exception, cancellation) can
            # leave jobs that did not finish: in the queue, during a pull or
            # an item scan, or followers never released. Each carries a share
            # of a refcounted TranscriptHandle (see ScannerJob.on_complete);
            # unfinished, its on_complete never fires and the handle never
            # closes. A job leaves `live` exactly once (here or in its finish
            # step), so no share is released twice. Shielded: the ambient
            # scope may already be cancelled here, and an unshielded await
            # would raise before closing anything. Runs after
            # reader_cm_factory's context manager has exited -- safe today
            # because on_complete only touches the handle, not the reader, but
            # an unstated coupling worth knowing about.
            with anyio.CancelScope(shield=True):
                while live:
                    on_complete = live.pop().job.on_complete
                    if on_complete is not None:
                        # One job's on_complete raising must not stop the
                        # rest from draining -- each still holds a real share
                        # of the refcount, and swallowing this exception (not
                        # letting it replace whatever's already propagating)
                        # is strictly better than leaking the handle.
                        with contextlib.suppress(Exception):
                            await on_complete()

    return the_func
