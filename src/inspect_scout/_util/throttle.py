import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def throttle(seconds: float) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Throttle a function to ensure it is called no more than every n seconds.

    Note: The wrapped function must not return None. This decorator caches
    and returns the last result between throttle intervals, and uses None
    internally to detect the uninitialized state.

    Args:
       seconds (float): Throttle time.

    Returns:
       Callable: Throttled function.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        last_called: float = 0
        last_result: T | None = None

        @wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal last_called
            nonlocal last_result
            current_time = time.time()
            if current_time - last_called >= seconds:
                last_result = func(*args, **kwargs)
                last_called = current_time
            assert last_result is not None
            return last_result

        return wrapped

    return decorator
