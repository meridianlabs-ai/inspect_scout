import multiprocessing
from contextlib import AbstractAsyncContextManager
from multiprocessing.managers import DictProxy, SyncManager
from multiprocessing.synchronize import Semaphore as MPSemaphore
from threading import Condition as ThreadingCondition
from types import TracebackType
from typing import Any, Callable

import anyio
from inspect_ai.util._concurrency import ConcurrencySemaphore

from . import _mp_common


class SemaphoreProvider:
    """Manages cross-process semaphore creation and distribution.

    Encapsulates both the parent-side provider task (which creates semaphores)
    and the child-side factory logic (which requests and retrieves them).
    Uses a Condition variable for efficient notification instead of polling.
    """

    def __init__(self, manager: SyncManager) -> None:
        self.registry: DictProxy[str, MPSemaphore] = manager.dict()
        self.request_queue: multiprocessing.Queue[
            tuple[str, int, bool] | None
        ] = multiprocessing.Queue()
        self.condition: ThreadingCondition = manager.Condition()

    async def run_provider_task(
        self,
        diagnostics: bool,
        print_diagnostics: Callable[[str, object], None],
    ) -> None:
        """Parent-side: Run the semaphore creation task.

        Should be started as an async task in the main process.
        Listens for requests and creates semaphores on demand.

        Args:
            diagnostics: Whether diagnostics are enabled
            print_diagnostics: Function to print diagnostic messages
        """
        while True:
            request = await _mp_common.run_sync_on_thread(self.request_queue.get)

            if request is None:  # Shutdown sentinel
                if diagnostics:
                    print_diagnostics("MP Semaphore Provider", "Shutting down")
                break

            name, concurrency, visible = request

            # Create semaphore under lock and notify waiters
            def create_fn(
                n: str = name, c: int = concurrency, v: bool = visible
            ) -> None:
                self._create_and_notify(n, c, v, diagnostics, print_diagnostics)

            await _mp_common.run_sync_on_thread(create_fn)

    def _create_and_notify(
        self,
        name: str,
        concurrency: int,
        visible: bool,
        diagnostics: bool,
        print_diagnostics: Callable[[str, object], None],
    ) -> None:
        """Internal: Create semaphore and notify waiters (synchronous)."""
        with self.condition:
            if name not in self.registry:
                sem = multiprocessing.Semaphore(concurrency)
                self.registry[name] = sem
                if diagnostics:
                    print_diagnostics(
                        "MP Semaphore Provider",
                        f"Created semaphore '{name}' with concurrency={concurrency}",
                    )
            else:
                if diagnostics:
                    print_diagnostics(
                        "MP Semaphore Provider",
                        f"Semaphore '{name}' already exists, reusing",
                    )
            self.condition.notify_all()

    def shutdown(self) -> None:
        """Signal provider task to shutdown."""
        self.request_queue.put(None)

    async def get_or_create_semaphore(
        self, name: str, concurrency: int, visible: bool
    ) -> MPSemaphore:
        """Child-side: Get semaphore from registry, requesting creation if needed.

        Called by worker processes. Blocks until semaphore is available.
        Uses Condition variable for efficient waiting (no polling).

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
            visible: Whether visible in status display

        Returns:
            The multiprocessing.Semaphore instance
        """

        def wait_for_semaphore() -> MPSemaphore:
            """Synchronous function to run in thread."""
            with self.condition:
                if name not in self.registry:
                    # Request creation (outside the condition wait)
                    self.request_queue.put((name, concurrency, visible))

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
