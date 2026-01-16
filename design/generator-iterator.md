# Async Generators vs Async Iterators: Streams vs Lifetimes


## Background Context

### Terminology

These concepts overlap:

- **AsyncIterable**: has `__aiter__()` returning an AsyncIterator
- **AsyncIterator**: has `__anext__()` returning awaitable values
- **AsyncGenerator**: a specific kind of AsyncIterator created by `async def` + `yield`

All async generators are async iterators, but not all async iterators are generators. A class with `__aiter__`/`__anext__` is an iterator but not a generator. A function using `yield` produces a generator (which is also an iterator). Type hints don't distinguish them—both may be annotated `AsyncIterator[T]`.

The key difference: generators have implicit cleanup via `finally` blocks (unreliable if abandoned), while class-based iterators can implement explicit `aclose()` methods (reliable when called).

### Example AsyncGenerator (function with `yield`)

```python
# This is an AsyncGenerator: uses `async def` + `yield`.
# Also an AsyncIterator (all generators are iterators).
# Also an AsyncIterable (has implicit __aiter__ returning self).
# Return type hint could be AsyncGenerator[int, None] or AsyncIterator[int].
async def count_up(n: int) -> AsyncIterator[int]:
    """Yields 0 to n-1, one at a time."""
    for i in range(n):
        await asyncio.sleep(0.1)
        yield i

async for num in count_up(5):
    print(num)
```

### Example AsyncIterator (class with `__anext__`)

```python
class ManagedStream:
    """AsyncIterator with explicit resource management.

    Also an AsyncIterable (has __aiter__ returning self).
    NOT an AsyncGenerator (no yield, just a class).
    """

    def __init__(self, resource):
        self._resource = resource

    async def __aenter__(self):
        await self._resource.open()
        return self

    async def __aexit__(self, *exc):
        await self.aclose()

    async def aclose(self):
        await self._resource.close()  # guaranteed cleanup

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        data = await self._resource.read()
        if data is None:
            raise StopAsyncIteration
        return data

# Consuming (context manager):
async with ManagedStream(resource) as stream:
    async for item in stream:
        print(item)
        if done_early:
            break  # __aexit__ calls aclose(), cleanup guaranteed

# Consuming (aclosing):
async with aclosing(ManagedStream(resource)) as stream:
    async for item in stream:
        print(item)
```

## Guidance

**Async generators are for streams, not lifetimes.**

Use async generators only when abandoning iteration is safe. If an async generator’s correctness or resource safety depends on cleanup that requires `await`, do **not** rely on its `finally` block: if iteration is abandoned, cleanup may run during garbage collection, where async finalization is unreliable—`await`'s in `finally` may not execute.

**When authoring APIs that manage lifetimes requiring deterministic async teardown**—especially when partial consumption is possible—model that lifetime explicitly. Prefer an explicit lifetime boundary such as an `async with`–managed iterator or an object with an explicit `aclose()` method, and require callers to use it.

**When implementing such APIs**, ensure that `__anext__` is cancellation-safe with respect to the resource’s invariants. If `__anext__` is awaiting when the caller cancels or exits the context manager, `__aexit__` may run while `__anext__` is half-completed. Either make `__anext__` atomic with respect to resource state, or use shielding to guarantee cleanup completes before the cancellation propagates (noting that shielding trades off responsiveness for safety).

**When consuming async iterables you don’t control and may abandon early**, the defensive approach depends on whether the object supports `aclose()`:

* If the object exposes an `aclose()` method, wrap iteration with `contextlib.aclosing()` to ensure deterministic cleanup on early exit.
* If it does not support `aclose()`, you are at the mercy of the implementation. Either it does not require cleanup, or there is no safe way to provide it. Consult the documentation or source, and consider opening an issue if the behavior is unclear.

Note that `inspect.isasyncgenfunction()` does not help at the call site. An API may return a C extension type or custom async iterable rather than a native async generator, even if the function signature suggests otherwise (for example, `ijson.items_async` when using the `yajl2_c` backend).

The `ijson` case is a useful cautionary example: a widely used library’s async API does not consistently follow the protocol you might expect, and its cleanup behavior varies by backend. This reinforces the need to reason about async iteration in terms of observable lifetime guarantees, not surface syntax.