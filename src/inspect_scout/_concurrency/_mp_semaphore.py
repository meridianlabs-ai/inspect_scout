from contextlib import AbstractAsyncContextManager
from multiprocessing.managers import DictProxy, SyncManager, ValueProxy
from threading import Condition as ThreadingCondition
from types import TracebackType
from typing import Any

import anyio
from inspect_ai.util._concurrency import ConcurrencySemaphore

from . import _mp_common


class ManagerSemaphore:
    """Cross-process semaphore using Manager primitives.

    Unlike multiprocessing.Semaphore, this can be stored in a DictProxy
    because it's built from Manager proxy objects that can be pickled.
    This enables lazy/dynamic semaphore creation after process forking.

    Uses a Condition variable for efficient blocking (no polling).
    """

    def __init__(self, manager: SyncManager, value: int) -> None:
        """Initialize semaphore with given capacity.

        Args:
            manager: SyncManager instance to create proxy objects
            value: Initial semaphore value (max concurrent holders)
        """
        self._value: ValueProxy[int] = manager.Value("i", value)
        self._condition: ThreadingCondition = manager.Condition()

    def acquire(self) -> None:
        """Acquire the semaphore, blocking until available."""
        with self._condition:
            while self._value.value <= 0:
                self._condition.wait()
            self._value.value -= 1

    def release(self) -> None:
        """Release the semaphore, waking one waiting acquirer."""
        with self._condition:
            self._value.value += 1
            self._condition.notify()

    def get_value(self) -> int:
        """Get current semaphore value (available slots)."""
        return self._value.value


class SemaphoreProvider:
    """Manages cross-process semaphore creation and distribution.

    The parent process calls create_semaphore() when it receives requests
    from the upstream queue. Child processes call get_or_create_semaphore()
    which sends requests via the upstream queue and waits on a Condition
    variable for efficient notification (no polling).
    """

    def __init__(self, manager: SyncManager) -> None:
        self.manager = manager
        self.registry: DictProxy[str, ManagerSemaphore] = manager.dict()
        self.condition: ThreadingCondition = manager.Condition()

    def _create_semaphore_sync(self, name: str, concurrency: int) -> None:
        """Internal: Create a semaphore and notify waiters (synchronous).

        This is the synchronous implementation that runs in a thread.
        Callers should use the async create_semaphore() method instead.

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
        """
        with self.condition:
            if name not in self.registry:
                sem = ManagerSemaphore(self.manager, concurrency)
                self.registry[name] = sem
            self.condition.notify_all()

    async def create_semaphore(self, name: str, concurrency: int) -> None:
        """Parent-side: Create a semaphore and notify waiters (async).

        Called by the upstream collector when it receives a semaphore request.
        Runs the synchronous creation logic in a thread to avoid blocking the
        event loop.

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
        """
        await _mp_common.run_sync_on_thread(
            lambda: self._create_semaphore_sync(name, concurrency)
        )

    async def get_or_create_semaphore(
        self, name: str, concurrency: int, visible: bool
    ) -> ManagerSemaphore:
        """Child-side: Get semaphore from registry, requesting creation if needed.

        Called by worker processes. Blocks until semaphore is available.
        Uses Condition variable for efficient waiting (no polling).

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
            visible: Whether visible in status display (not used currently)

        Returns:
            The ManagerSemaphore instance
        """

        def wait_for_semaphore() -> ManagerSemaphore:
            """Synchronous function to run in thread."""
            with self.condition:
                if name not in self.registry:
                    # Request creation via upstream queue
                    ctx = _mp_common.ipc_context
                    ctx.upstream_queue.put(
                        _mp_common.SemaphoreRequest(name, concurrency, visible)
                    )

                # Wait for parent to create it
                while name not in self.registry:
                    self.condition.wait(timeout=1.0)

                return self.registry[name]

        # Run the blocking wait in a thread to avoid blocking event loop
        return await _mp_common.run_sync_on_thread(wait_for_semaphore)


class _AsyncSemaphoreWrapper(AbstractAsyncContextManager[None]):
    """Async context manager wrapper for ManagerSemaphore.

    Since ManagerSemaphore is synchronous, we run its acquire/release
    operations in a thread to avoid blocking the async event loop.
    """

    def __init__(self, sem: ManagerSemaphore) -> None:
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
    ManagerSemaphore instance for a given name.

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
