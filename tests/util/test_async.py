import sys
from collections.abc import AsyncGenerator, AsyncIterator

import pytest
from inspect_scout._util._async import aclosing_iter


@pytest.mark.asyncio
async def test_aclosing_iter_exits_cleanly_after_its_iterator_is_finalized() -> None:
    """An abandoned stream closes cleanly whatever order its generators close in.

    Garbage collection and loop shutdown finalize abandoned async generators
    in arbitrary order, so the inner ones may already be closed when the outer
    one's `aclosing_iter` exits.
    """
    started: list[AsyncGenerator[object, None]] = []
    hooks = sys.get_asyncgen_hooks()

    def firstiter(agen: AsyncGenerator[object, None]) -> None:
        started.append(agen)
        if hooks.firstiter is not None:
            hooks.firstiter(agen)

    async def numbers() -> AsyncIterator[int]:
        yield 1
        yield 2

    async def stream() -> AsyncIterator[int]:
        async with aclosing_iter(numbers()) as items:
            async for item in items:
                yield item

    sys.set_asyncgen_hooks(firstiter=firstiter, finalizer=hooks.finalizer)
    try:
        await anext(stream())
    finally:
        sys.set_asyncgen_hooks(*hooks)

    for agen in reversed(started):  # innermost first
        await agen.aclose()
