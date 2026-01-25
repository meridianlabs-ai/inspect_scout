"""Observe context types and context variable management."""

import inspect
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    ParamSpec,
    TypeVar,
)

from inspect_ai.log._transcript import Transcript as InspectTranscript

from inspect_scout._transcript.database.database import TranscriptsDB
from inspect_scout._transcript.types import TranscriptInfo

# Type variables for decorated functions
OP = ParamSpec("OP")
OR = TypeVar("OR")


@dataclass
class ObserveContext:
    """Context for an observe decorator/context manager invocation."""

    info: TranscriptInfo
    """Merged TranscriptInfo for this context."""

    inspect_transcript: InspectTranscript
    """Inspect AI's transcript for event capture."""

    db: TranscriptsDB
    """Database for writing transcripts (always present, resolved at root)."""

    had_children: bool = False
    """True if any child observe contexts ran inside this one."""

    parent: "ObserveContext | None" = None
    """Parent context if nested."""

    is_root: bool = False
    """True if this is the outermost observe context."""

    pending_captures: list[tuple[dict[str, Any], str]] = field(default_factory=list)
    """Pending SDK captures as (data, provider_key) tuples to process at exit."""


_current_context: ContextVar[ObserveContext | None] = ContextVar(
    "observe_context", default=None
)


def current_observe_context() -> ObserveContext | None:
    """Get the current observe context.

    Returns:
        The current ObserveContext if inside an observe context, None otherwise.
    """
    return _current_context.get()


class _ObserveContextManager(AsyncContextManager[ObserveContext]):
    """Wrapper that works as both async context manager and decorator.

    This enables all usage patterns:
    - `async with observe():` - context manager
    - `@observe()` - decorator with parens
    - `@observe(task_set="x")` - decorator with args
    """

    def __init__(
        self, context_factory: Callable[[], AsyncContextManager[ObserveContext]]
    ) -> None:
        self._factory = context_factory
        self._ctx: AsyncContextManager[ObserveContext] | None = None

    def __call__(
        self, func: Callable[OP, Awaitable[OR]]
    ) -> Callable[OP, Awaitable[OR]]:
        """Use as decorator."""
        if not inspect.iscoroutinefunction(func):
            raise TypeError("@observe can only decorate async functions")

        @wraps(func)
        async def wrapper(*args: OP.args, **kwargs: OP.kwargs) -> OR:
            async with self._factory():
                return await func(*args, **kwargs)

        return wrapper

    async def __aenter__(self) -> ObserveContext:
        """Enter async context."""
        self._ctx = self._factory()
        return await self._ctx.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool | None:
        """Exit async context."""
        assert self._ctx is not None
        return await self._ctx.__aexit__(exc_type, exc_val, exc_tb)
