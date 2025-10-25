"""Shared context for multiprocessing communication.

This module contains theglobals that are shared between the main process and worker
subprocesses via fork. The main process initializes these values, and forked workers
inherit them through copy-on-write memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import LogRecord
from multiprocessing.managers import DictProxy
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Event
from threading import Condition
from typing import TYPE_CHECKING, Awaitable, Callable, TypeAlias, TypeVar, cast

import anyio

from .._scanner.result import ResultReport
from .._transcript.types import TranscriptInfo
from .common import ParseFunctionResult, ParseJob, ScanMetrics, ScannerJob

if TYPE_CHECKING:
    from ._mp_semaphore import PicklableMPSemaphore


@dataclass(frozen=True)
class ResultItem:
    """Scan results from a worker process."""

    transcript_info: TranscriptInfo
    scanner_name: str
    results: list[ResultReport]


@dataclass(frozen=True)
class MetricsItem:
    """Metrics update from a worker process."""

    worker_id: int
    metrics: ScanMetrics


@dataclass(frozen=True)
class LoggingItem:
    """Logging call from a worker process."""

    record: LogRecord


@dataclass(frozen=True)
class SemaphoreRequest:
    """Request to create a cross-process semaphore."""

    name: str
    concurrency: int
    visible: bool


@dataclass(frozen=True)
class WorkerReady:
    """Signal from worker that it's initialized and ready to consume parse jobs."""

    worker_id: int


@dataclass(frozen=True)
class WorkerComplete:
    """Sentinel indicating a worker has finished all work."""

    pass


@dataclass(frozen=True)
class ShutdownSentinel:
    """Emergency shutdown signal injected by parent during forced termination."""

    pass


UpstreamQueueItem: TypeAlias = (
    ResultItem
    | MetricsItem
    | LoggingItem
    | SemaphoreRequest
    | WorkerReady
    | WorkerComplete
    | ShutdownSentinel
    | Exception
)


@dataclass
class IPCContext:
    """
    Shared state for IPC between main process and forked workers.

    For consistency, it should contain ALL data used by subprocesses that is invariant
    across subprocesses. The `executor.submit` should only pass subprocess specific
    arguments.

    The upstream_queue is a multiplexed channel carrying both results and metrics
    from workers to the main process.
    """

    parse_function: Callable[[ParseJob], Awaitable[ParseFunctionResult]]
    """Function that executes a parse job yielding scanner jobs."""

    scan_function: Callable[[ScannerJob], Awaitable[list[ResultReport]]]
    """Function that executes a scanner job and returns results."""

    prefetch_multiple: float | None
    """Multiplier for scanner job queue size (base=task_count)."""

    diagnostics: bool
    """Whether to enable diagnostic output during execution."""

    overall_start_time: float
    """Timestamp when the overall scan started, for timing metrics."""

    parse_job_queue: Queue[ParseJob | None]
    """Queue of parse jobs sent from main process to workers; None signals completion."""

    upstream_queue: Queue[UpstreamQueueItem]
    """Multiplexed queue carrying results, metrics, and control messages from workers to main."""

    shutdown_condition: Condition
    """
    Cross-process condition variable for coordinating shutdown.

    Despite the threading.Condition type, this is actually a proxy object created
    via SyncManager.Condition() that enables cross-process coordination. The main
    process notifies this condition during shutdown to wake up all worker shutdown
    monitors, allowing them to cancel their work tasks and exit cleanly.

    Note: Don't be confused by the threading.Condition type - it works across processes
    because it's a manager proxy, not a raw threading primitive.
    """

    workers_ready_event: Event
    """
    Cross-process event for coordinating worker startup.

    Created via SyncManager.Event(). Workers signal ready via upstream queue, then
    block waiting on this event. Once the parent receives ready signals from all
    workers, it sets this event, releasing all workers simultaneously to ensure
    even distribution of parse jobs from the queue.
    """

    semaphore_registry: DictProxy[str, PicklableMPSemaphore]
    """
    Cross-process registry mapping semaphore names to their manager proxies.

    When a worker needs a concurrency-limited semaphore, it first checks this registry.
    If found, the worker uses it directly; if not found, the worker requests creation
    via the upstream queue. The main process populates this registry as semaphore
    requests arrive from workers.
    """

    semaphore_condition: Condition
    """
    Cross-process condition variable for synchronizing semaphore registry access.

    Despite the threading.Condition type, this is actually a proxy object created
    via SyncManager.Condition() that enables cross-process coordination. Workers
    wait on this condition when a requested semaphore hasn't been created yet. The
    main process notifies this condition after creating new semaphores in the registry,
    waking up any waiting workers.

    Note: Like shutdown_condition, this is created via SyncManager for consistency
    and works across processes despite the threading.Condition type.
    """


# Global IPC context shared between main process and forked subprocesses.
# Initialized by multi_process strategy, inherited by workers via fork.
# Type is non-None but runtime starts as None (cast) to avoid | None everywhere.
ipc_context = cast(IPCContext, None)


T = TypeVar("T")


async def run_sync_on_thread(func: Callable[[], T]) -> T:
    """Run a blocking callable in a thread, preserving its return type.

    This is a type-safe wrapper around anyio.to_thread.run_sync that preserves
    the return type of the callable, enabling proper downstream type checking.

    Args:
        func: A blocking callable with no arguments

    Returns:
        The return value of func, with proper type information preserved
    """
    return await anyio.to_thread.run_sync(func, cancellable=True)
