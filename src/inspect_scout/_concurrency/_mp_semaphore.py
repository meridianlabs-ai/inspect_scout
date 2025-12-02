from contextlib import AbstractAsyncContextManager
from multiprocessing.managers import SyncManager
from types import TracebackType
from typing import Any

import anyio
from inspect_ai.util._concurrency import ConcurrencySemaphore


class PicklableMPSemaphore:
    """Cross-process semaphore using Manager primitives.

    Unlike `multiprocessing.Semaphore`, this can be stored in a `DictProxy` because
    it's built from `SyncManager` proxy objects that can be pickled. This enables
    lazy/dynamic semaphore creation across spawn boundaries.

    Uses a Condition variable to efficiently block and avoid polling.
    """

    def __init__(self, manager: SyncManager, value: int) -> None:
        """Initialize semaphore with given capacity.

        Args:
            manager: SyncManager instance to create proxy objects
            value: Initial semaphore value (max concurrent holders)
        """
        self._value_proxy = manager.Value("i", value)
        self._condition = manager.Condition()

    def acquire(self) -> None:
        """Acquire the semaphore, blocking until available."""
        with self._condition:
            while self._value_proxy.value <= 0:
                self._condition.wait()
            self._value_proxy.value -= 1

    def release(self) -> None:
        """Release the semaphore, waking one waiting acquirer."""
        with self._condition:
            self._value_proxy.value += 1
            self._condition.notify()

    def get_value(self) -> int:
        """Get current semaphore value (available slots)."""
        return self._value_proxy.value


class MPConcurrencySemaphore(ConcurrencySemaphore, AbstractAsyncContextManager[None]):
    """ConcurrencySemaphore implementation wrapping MPSemaphoreLike.

    Since MPSemaphoreLike is synchronous, this class runs acquire/release operations
    in threads to avoid blocking the async event loop. The class itself serves as the
    async context manager (semaphore attribute points to self).
    """

    def __init__(
        self, name: str, concurrency: int, visible: bool, sem: PicklableMPSemaphore
    ) -> None:
        self.name = name
        self.concurrency = concurrency
        self.visible = visible
        self._sem = sem
        self.semaphore: AbstractAsyncContextManager[Any] = self

    async def __aenter__(self) -> None:
        await anyio.to_thread.run_sync(self._sem.acquire)

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        self._sem.release()

    @property
    def value(self) -> int:
        return self._sem.get_value()
