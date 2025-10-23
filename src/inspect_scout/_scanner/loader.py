from dataclasses import dataclass, field
from functools import wraps
from typing import (
    AsyncIterator,
    Callable,
    Literal,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
)

from inspect_ai._util._async import is_callable_coroutine
from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_info,
    registry_name,
    registry_tag,
)

from .._transcript.types import (
    EventType,
    MessageType,
    Transcript,
    TranscriptContent,
)
from .filter import (
    normalize_events_filter,
    normalize_messages_filter,
)
from .types import ScannerInput

LOADER_CONFIG = "loader_config"

# Use bounded TypeVar (covariant for loader output)
TLoaderResult = TypeVar("TLoaderResult", bound=ScannerInput, covariant=True)
P = ParamSpec("P")


class Loader(Protocol[TLoaderResult]):
    """Custom loader for transcript data."""

    def __call__(
        self,
        transcript: Transcript,
    ) -> AsyncIterator[TLoaderResult]:
        """Load transcript data.

        Args:
           transcript: Transcript to yield from.

        Returns:
           AsyncIterator: Iterator that returns transcript data.
        """
        ...


@dataclass
class LoaderConfig:
    content: TranscriptContent = field(default_factory=TranscriptContent)


LoaderFactory = Callable[P, Loader[TLoaderResult]]


def loader(
    *,
    name: str | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    content: TranscriptContent | None = None,
) -> Callable[[LoaderFactory[P, TLoaderResult]], LoaderFactory[P, TLoaderResult]]:
    """Decorator for registering loaders.

    Args:
       name: Loader name (defaults to function name).
       messages: Message types to load from.
       events: Event types to load from.
       content: Transcript content filter.

    Returns:
        Loader with registry info.
    """
    if content is None:
        if messages is None and events is None:
            raise RuntimeError("Must filter on messages or events")
        content = TranscriptContent(
            normalize_messages_filter(messages) if messages is not None else None,
            normalize_events_filter(events) if events is not None else None,
        )
    else:
        assert messages is None and events is None, (
            "Don't pass messages or events if you pass content"
        )

    def decorate(
        factory: LoaderFactory[P, TLoaderResult],
    ) -> LoaderFactory[P, TLoaderResult]:
        loader_name = registry_name(
            factory, name or str(getattr(factory, "__name__", "loader"))
        )

        @wraps(factory)
        def factory_wrapper(*args: P.args, **kwargs: P.kwargs) -> Loader[TLoaderResult]:
            loader_fn = factory(*args, **kwargs)

            if not is_callable_coroutine(loader_fn):
                raise TypeError(
                    f"'{loader_name}' is not declared as an async callable."
                )

            loader_config = LoaderConfig(content)

            registry_tag(
                factory,
                loader_fn,
                RegistryInfo(
                    type="loader",
                    name=loader_name,
                    metadata={LOADER_CONFIG: loader_config},
                ),
                *args,
                **kwargs,
            )
            return loader_fn

        registry_add(
            factory,
            RegistryInfo(type="loader", name=loader_name),
        )
        return cast(LoaderFactory[P, TLoaderResult], factory_wrapper)

    return decorate


def config_for_loader(loader: Loader[ScannerInput]) -> LoaderConfig:
    return cast(LoaderConfig, registry_info(loader).metadata[LOADER_CONFIG])
