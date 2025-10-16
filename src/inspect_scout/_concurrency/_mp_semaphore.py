import multiprocessing
from contextlib import AbstractAsyncContextManager
from multiprocessing.managers import DictProxy, SyncManager
from multiprocessing.synchronize import Semaphore as MPSemaphore
from threading import Condition as ThreadingCondition
from types import TracebackType
from typing import Any

import anyio
from inspect_ai.util._concurrency import ConcurrencySemaphore

from . import _mp_common


class SemaphoreProvider:
    """Manages cross-process semaphore creation and distribution.

    The parent process calls create_semaphore() when it receives requests
    from the upstream queue. Child processes call get_or_create_semaphore()
    which sends requests via the upstream queue and waits on a Condition
    variable for efficient notification (no polling).
    """

    def __init__(self, manager: SyncManager) -> None:
        self.registry: DictProxy[str, MPSemaphore] = manager.dict()
        self.condition: ThreadingCondition = manager.Condition()

    def create_semaphore(self, name: str, concurrency: int) -> None:
        """Parent-side: Create a semaphore and notify waiters (synchronous).

        Called by the upstream collector when it receives a semaphore request.
        Must be called from a thread context (via run_sync_on_thread) since it
        acquires the condition lock.

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
        """
        with self.condition:
            if name not in self.registry:
                sem = multiprocessing.Semaphore(concurrency)
                self.registry[name] = sem
            self.condition.notify_all()

    async def get_or_create_semaphore(
        self, name: str, concurrency: int, visible: bool
    ) -> MPSemaphore:
        """Child-side: Get semaphore from registry, requesting creation if needed.

        Called by worker processes. Blocks until semaphore is available.
        Uses Condition variable for efficient waiting (no polling).

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
            visible: Whether visible in status display (not used currently)

        Returns:
            The multiprocessing.Semaphore instance
        """

        def wait_for_semaphore() -> MPSemaphore:
            """Synchronous function to run in thread."""
            with self.condition:
                if name not in self.registry:
                    # Request creation via upstream queue
                    ctx = _mp_common.ipc_context
                    ctx.upstream_queue.put(
                        ("semaphore_request", name, concurrency, visible)
                    )

                # Wait for parent to create it
                while name not in self.registry:
                    self.condition.wait(timeout=1.0)

                return self.registry[name]

        # Run the blocking wait in a thread to avoid blocking event loop
        return await _mp_common.run_sync_on_thread(wait_for_semaphore)


class _AsyncSemaphoreWrapper(AbstractAsyncContextManager[None]):
    """Async context manager wrapper for multiprocessing.Semaphore.

    Since multiprocessing.Semaphore is synchronous, we run its acquire/release
    operations in a thread to avoid blocking the async event loop.
    """

    def __init__(self, sem: MPSemaphore) -> None:
        self._sem = sem

    async def __aenter__(self) -> None:
        await anyio.to_thread.run_sync(self._sem.acquire)

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        self._sem.release()


async def mp_semaphore_factory(
    name: str, concurrency: int, visible: bool
) -> ConcurrencySemaphore:
    """Factory function for creating cross-process semaphores.

    Delegates to the SemaphoreProvider in the IPC context to get or create
    the semaphore. The provider ensures all processes share the same
    multiprocessing.Semaphore instance for a given name.

    Args:
        name: Semaphore name
        concurrency: Maximum concurrent holders
        visible: Whether visible in status display

    Returns:
        A ConcurrencySemaphore instance wrapping the shared semaphore
    """
    ctx = _mp_common.ipc_context
    provider = ctx.semaphore_provider

    # Get or create the semaphore through the provider
    sem = await provider.get_or_create_semaphore(name, concurrency, visible)

    class _ConcurrencySemaphore(ConcurrencySemaphore):
        def __init__(self, name: str, concurrency: int, visible: bool) -> None:
            self.name = name
            self.concurrency = concurrency
            self.visible = visible
            self._sem = sem
            self.semaphore: AbstractAsyncContextManager[Any] = _AsyncSemaphoreWrapper(
                sem
            )

        @property
        def value(self) -> int:
            return self._sem.get_value()

    return _ConcurrencySemaphore(name, concurrency, visible)
