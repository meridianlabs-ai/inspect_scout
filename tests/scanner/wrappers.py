"""Scanner wrappers used to test annotation resolution."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def wrap_async(
    function: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    """Wrap an async function in a module with separate globals."""

    @wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return await function(*args, **kwargs)

    return wrapped
