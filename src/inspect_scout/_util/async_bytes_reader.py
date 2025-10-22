from typing import IO, AsyncIterator, Protocol, TypeGuard, cast

import anyio


class AsyncBytesReader(Protocol):
    """Protocol defining the minimal async file-like interface for ijson.

    ijson.parse_async() requires an async file-like object with a read() method that:
    - Can be awaited (is an async method)
    - Returns bytes (binary mode)
    - Accepts a size parameter for the number of bytes to read

    This protocol captures that minimal requirement without requiring the full BinaryIO
    interface that includes methods like seek(), tell(), close(), etc.
    """

    async def read(self, size: int) -> bytes: ...


def _is_async_iterator(
    io_or_iter: IO[bytes] | AsyncIterator[bytes],
) -> TypeGuard[AsyncIterator[bytes]]:
    return hasattr(io_or_iter, "__anext__")


def adapt_to_reader(io_or_iter: IO[bytes] | AsyncIterator[bytes]) -> AsyncBytesReader:
    return (
        _BytesIteratorReader(io_or_iter)
        if _is_async_iterator(io_or_iter)
        # Oh Python!?
        else _BytesIOReader(cast(IO[bytes], io_or_iter))
    )


class _BytesIOReader(AsyncBytesReader):
    """Wrapper to make synchronous I/O operations async-compatible.

    This class is needed because zipfile.ZipFile and other standard library I/O
    operations are strictly synchronous. To achieve concurrency and avoid blocking
    the main thread, this wrapper uses anyio.to_thread to run blocking I/O operations
    in a thread pool while maintaining async/await compatibility.

    The internal lock ensures thread-safe access to the underlying synchronous I/O object.
    """

    def __init__(self, sync_io: IO[bytes]):
        self._sync_io = sync_io
        self._lock = anyio.Lock()

    async def read(self, size: int) -> bytes:
        async with self._lock:
            return await anyio.to_thread.run_sync(self._sync_io.read, size)


class _BytesIteratorReader(AsyncBytesReader):
    """AsyncBytesReader implementation that reads from an AsyncIterator[bytes]."""

    def __init__(self, async_iter: AsyncIterator[bytes]):
        self._async_iter = async_iter
        self._current_chunk: bytes = b""
        self._offset = 0

    async def read(self, size: int) -> bytes:
        if size < 0:
            raise ValueError("size must be non-negative")
        if size == 0:
            return b""

        chunks_to_return: list[bytes] = []
        total = 0

        while total < size:
            # Get more data from current chunk if available
            available = len(self._current_chunk) - self._offset
            if available > 0:
                bytes_to_take = min(size - total, available)
                chunks_to_return.append(
                    self._current_chunk[self._offset : self._offset + bytes_to_take]
                )
                self._offset += bytes_to_take
                total += bytes_to_take
            else:
                # Current chunk exhausted, fetch next
                try:
                    self._current_chunk = await anext(self._async_iter)
                    self._offset = 0
                except StopAsyncIteration:
                    break  # No more data

        return b"".join(chunks_to_return)
