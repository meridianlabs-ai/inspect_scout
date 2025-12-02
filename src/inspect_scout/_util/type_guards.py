from collections.abc import AsyncIterable
from typing import IO, TypeGuard


def is_async_iterable(
    io_or_iter: IO[bytes] | AsyncIterable[bytes],
) -> TypeGuard[AsyncIterable[bytes]]:
    return hasattr(io_or_iter, "__aiter__")
