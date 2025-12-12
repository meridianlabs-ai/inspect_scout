"""Shared context for multiprocessing communication.

This module contains types and globals shared between the main process and worker
subprocesses. State is serialized and passed to spawned workers via IPCContext.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import LogRecord, getLogger
from multiprocessing.managers import DictProxy
from multiprocessing.queues import Queue
from threading import Condition, Event
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    TypeAlias,
    TypeVar,
)

import anyio
import cloudpickle  # type:ignore
from inspect_ai._util.logger import warn_once
from inspect_ai.model import GenerateConfig, Model, ModelConfig
from typing_extensions import TypeVarTuple, Unpack

if TYPE_CHECKING:
    from .._scanner.result import ResultReport
    from .._transcript.types import TranscriptInfo
    from ._mp_semaphore import PicklableMPSemaphore

    # TODO: This import from .common needs to be within a TYPE_CHECKING check since
    # it creates a circular dependency. We should fix this.
    from .common import ParseFunctionResult, ParseJob, ScanMetrics, ScannerJob


class DillCallable:
    """Wrapper for callables that uses dill for pickling.

    This allows closures and other complex callables to be serialized
    for use with spawn multiprocessing context.
    """

    def __init__(self, func: Callable[..., Any]) -> None:
        """Initialize with a callable.

        Args:
            func: The callable to wrap (can be closure, lambda, etc)
        """
        self._pickled_func: bytes = cloudpickle.dumps(func)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the wrapped function.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from calling the wrapped function
        """
        func = cloudpickle.loads(self._pickled_func)
        return func(*args, **kwargs)

    def __getstate__(self) -> bytes:
        """Get state for pickling.

        Returns:
            Pickled function bytes
        """
        return self._pickled_func

    def __setstate__(self, state: bytes) -> None:
        """Set state from unpickling.

        Args:
            state: Pickled function bytes
        """
        self._pickled_func = state


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
    Shared state for IPC between main process and spawned workers.

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

    completed: Callable[[], Awaitable[None]]
    """Function to indicate the stragegy is complete."""

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

    plugin_dir: str | None
    """Plugin directory to add to sys.path in subprocesses."""

    log_level: str | None
    """Log level for subprocess initialization."""

    model_config: ModelConfig
    """Configuration specifying which model provider and settings to use."""

    model_roles: dict[str, Model] | None
    """Optional mapping of role names to specific Model instances."""

    generate_config: GenerateConfig
    """Generation parameters (temperature, max_tokens, etc.) for model calls."""


T_Retval = TypeVar("T_Retval")
PosArgsT = TypeVarTuple("PosArgsT")


async def run_sync_on_thread(
    func: Callable[[Unpack[PosArgsT]], T_Retval],
    *args: Unpack[PosArgsT],
) -> T_Retval:
    """Run a blocking callable in a thread, preserving its return type.

    This is a type-safe wrapper around `anyio.to_thread.run_sync` that preserves
    the return type of the callable, enabling proper downstream type checking.

    Note: `anyio.to_thread.run_sync` is correctly annotated, but some type
    checkers/configurations may widen its return type to ``Any``. This wrapper
    keeps the return type precise (via the TypeVar/Unpack typing) so callers
    and downstream type checkers retain the specific return type of ``func``.

    Args:
        func: A blocking callable
        *args: Arguments to pass to the callable

    Returns:
        The return value of ``func``, with type information preserved for
        static checkers.
    """
    return await anyio.to_thread.run_sync(func, *args, abandon_on_cancel=True)


# Deferred config for spawn-based subprocess initialization.
# Set early during scan setup, retrieved later if multi-process.
_plugin_directory: str | None = None
_log_level: str | None = None


def register_plugin_directory(directory: str) -> None:
    global _plugin_directory
    if _plugin_directory is not None:
        warn_once(
            getLogger(__name__),
            "WARNING: Plugin directory has already been registered",
        )
    else:
        _plugin_directory = directory


def get_plugin_directory() -> str | None:
    return _plugin_directory


def set_log_level(level: str | None) -> None:
    global _log_level
    _log_level = level


def get_log_level() -> str | None:
    return _log_level
