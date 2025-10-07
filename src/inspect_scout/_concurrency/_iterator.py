from multiprocessing.queues import Queue as MPQueue
from typing import AsyncIterator, Generic, TypeVar

import anyio

from ._mp_common import run_sync_on_thread

T = TypeVar("T")


class SerializedAsyncIterator(Generic[T]):
    """Serialize access to an AsyncIterator using a lock.

    This ensures that concurrent calls to anext() are serialized. The runtime enforces
    that only one task can be within an iterator's __anext__ at a time. When the
    rule is broken, the runtime raises "anext(): asynchronous generator is already
    running".

    NOTE: Because the rule of no concurrent anext exists, generators are not expected
    to protect themselves with concurrent access. That's why this function will be
    used by consumers of AsyncIterators and not the generator itself.
    """

    def __init__(self, ait: AsyncIterator[T]) -> None:
        self._ait = ait
        self._lock = anyio.Lock()

    async def __anext__(self) -> T:
        async with self._lock:
            return await self._ait.__anext__()

    def __aiter__(self) -> "SerializedAsyncIterator[T]":
        return self


async def iterator_from_mp_queue(queue: MPQueue[T | None]) -> AsyncIterator[T]:
    """Adapts a multi-process queue to an AsyncIterator."""
    while True:
        if (item := await run_sync_on_thread(queue.get)) is None:
            break
        yield item
