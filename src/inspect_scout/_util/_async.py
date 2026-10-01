from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

import anyio

T = TypeVar("T")


async def as_value(fn: Callable[[], Awaitable[T]]) -> T | BaseException:
    """Run an async function, returning its failure as a value instead of raising.

    Concurrent helpers such as `tg_collect` run their tasks in a task group,
    which cancels the remaining tasks as soon as one raises — and drops a child
    cancellation without reporting it at all, so the collected results come back
    short with no error. Capturing each failure keeps every task accounted for
    and lets the caller decide which ones to skip and which to re-raise.

    Cancellation is captured too. A genuine cancellation still propagates: the
    caller re-raises the captured value, and anyio re-delivers the cancellation
    on scope exit either way. KeyboardInterrupt and SystemExit are left alone so
    they unwind immediately, as they would without this wrapper.
    """
    try:
        return await fn()
    except (Exception, anyio.get_cancelled_exc_class()) as ex:
        return ex


@asynccontextmanager
async def aclosing_iter(
    iterator: AsyncIterator[T],
) -> AsyncIterator[AsyncIterator[T]]:
    """`contextlib.aclosing` for an iterator typed as a plain `AsyncIterator`.

    `aclosing` needs `aclose()`, which `AsyncIterator` does not promise (e.g.
    `TranscriptHandle.messages()`). Closing an async generator on exit, rather
    than whenever it is garbage collected, ends its iteration (and releases
    what it holds open) as soon as the caller stops reading it.
    """
    try:
        yield iterator
    finally:
        if isinstance(iterator, AsyncGenerator):
            await iterator.aclose()
