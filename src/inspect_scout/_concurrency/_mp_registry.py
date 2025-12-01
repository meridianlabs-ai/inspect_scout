"""Cross-process semaphore registry implementations.

This module provides `ConcurrencySemaphoreRegistry` implementations for parent and
child processes that coordinate cross-process semaphore creation and access via shared
Manager primitives.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from multiprocessing.managers import DictProxy, SyncManager
from multiprocessing.queues import Queue
from threading import Condition

import anyio
from inspect_ai.util._concurrency import (
    ConcurrencySemaphore,
    ConcurrencySemaphoreRegistry,
)

from ._mp_common import SemaphoreRequest, UpstreamQueueItem, run_sync_on_thread
from ._mp_semaphore import MPConcurrencySemaphore, PicklableMPSemaphore

# Python 3.12 doesn't support generic Queue at runtime, but with
# `from __future__ import annotations`, the subscript becomes a string
# and won't be evaluated at runtime
if sys.version_info < (3, 13):
    DictProxy = DictProxy


class ParentSemaphoreRegistry(ConcurrencySemaphoreRegistry):
    """Registry for parent process - creates PicklableMPSemaphore in shared DictProxy.

    The parent process uses this registry to create semaphores in the shared
    registry (DictProxy) when requested by children via IPC.
    """

    def __init__(self, sync_manager: SyncManager) -> None:
        self.sync_manager = sync_manager
        self.sync_manager_dict: DictProxy[str, PicklableMPSemaphore] = (
            sync_manager.dict()
        )
        self.sync_manager_condition: Condition = sync_manager.Condition()
        self._lock = anyio.Lock()
        self._semaphores: dict[str, ConcurrencySemaphore] = {}

    def _create_semaphore_sync(self, name: str, concurrency: int) -> None:
        """Create a semaphore and notify waiters (synchronous).

        This is the synchronous implementation that runs in a thread.

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
        """
        with self.sync_manager_condition:
            if name not in self.sync_manager_dict:
                sem = PicklableMPSemaphore(self.sync_manager, concurrency)
                self.sync_manager_dict[name] = sem
            self.sync_manager_condition.notify_all()

    async def _create_semaphore(self, name: str, concurrency: int) -> None:
        """Create a semaphore and notify waiters (async).

        Runs the synchronous creation logic in a thread to avoid blocking the
        event loop.

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
        """
        await run_sync_on_thread(self._create_semaphore_sync, name, concurrency)

    async def get_or_create(
        self, name: str, concurrency: int, key: str | None, visible: bool
    ) -> ConcurrencySemaphore:
        """Get or create a cross-process semaphore.

        Creates the underlying ManagerSemaphore in the shared registry if it doesn't
        exist, then wraps it in a ConcurrencySemaphore.

        Args:
            name: Semaphore display name
            concurrency: Maximum concurrent holders
            key: Unique storage key (defaults to name if None)
            visible: Whether visible in status display

        Returns:
            Wrapped semaphore instance
        """
        k = key if key else name
        async with self._lock:
            if k in self._semaphores:
                return self._semaphores[k]

            # Create ManagerSemaphore in shared registry
            await self._create_semaphore(name, concurrency)
            sem = self.sync_manager_dict[name]

            # Wrap and cache it
            wrapper = MPConcurrencySemaphore(name, concurrency, visible, sem)
            self._semaphores[k] = wrapper
            return wrapper

    def values(self) -> Iterable[ConcurrencySemaphore]:
        """Return all registered semaphores for status display."""
        return self._semaphores.values()


class ChildSemaphoreRegistry(ConcurrencySemaphoreRegistry):
    """Registry for child process - requests ManagerSemaphores via IPC.

    Child processes use this registry to request semaphores from the parent.
    On first access, sends a SemaphoreRequest via the upstream queue and waits
    for the parent to create the semaphore in the shared registry.
    """

    def __init__(
        self,
        registry: DictProxy[str, PicklableMPSemaphore],
        condition: Condition,
        upstream_queue: Queue[UpstreamQueueItem],
    ) -> None:
        self.registry = registry
        self.condition = condition
        self.upstream_queue = upstream_queue
        self._lock = anyio.Lock()
        self._wrappers: dict[str, ConcurrencySemaphore] = {}

    async def _request_semaphore(
        self, name: str, concurrency: int, visible: bool
    ) -> PicklableMPSemaphore:
        """Request semaphore from parent, wait for creation.

        Sends a SemaphoreRequest via the upstream queue and blocks on the
        condition variable until the parent creates the semaphore.

        Args:
            name: Semaphore name
            concurrency: Maximum concurrent holders
            visible: Whether visible in status display

        Returns:
            The ManagerSemaphore instance from the shared registry
        """

        def wait_for_semaphore() -> PicklableMPSemaphore:
            """Synchronous function to run in thread."""
            with self.condition:
                if name not in self.registry:
                    # Send IPC request to parent
                    self.upstream_queue.put(
                        SemaphoreRequest(name, concurrency, visible)
                    )

                # Wait for parent to create it
                while name not in self.registry:
                    self.condition.wait(timeout=1.0)

                return self.registry[name]

        return await run_sync_on_thread(wait_for_semaphore)

    async def get_or_create(
        self, name: str, concurrency: int, key: str | None, visible: bool
    ) -> ConcurrencySemaphore:
        """Get or create a cross-process semaphore via IPC.

        Checks local cache first. If not found, requests creation from parent
        via IPC (sends SemaphoreRequest, blocks on condition variable until
        parent creates it).

        Args:
            name: Semaphore display name
            concurrency: Maximum concurrent holders
            key: Unique storage key (defaults to name if None)
            visible: Whether visible in status display

        Returns:
            Wrapped semaphore instance
        """
        k = key if key else name
        async with self._lock:
            if k in self._wrappers:
                return self._wrappers[k]

            # Request via IPC
            sem = await self._request_semaphore(name, concurrency, visible)

            # Wrap and cache it
            wrapper = MPConcurrencySemaphore(name, concurrency, visible, sem)
            self._wrappers[k] = wrapper
            return wrapper

    def values(self) -> Iterable[ConcurrencySemaphore]:
        """Return all registered semaphores for status display."""
        return self._wrappers.values()
