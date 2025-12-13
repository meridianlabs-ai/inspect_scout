import inspect
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Literal,
    Mapping,
    ParamSpec,
    Protocol,
    Sequence,
    TypeVar,
    cast,
)

from inspect_ai._util._async import is_callable_coroutine
from inspect_ai._util.decorator import parse_decorators
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.module import load_module
from inspect_ai._util.package import get_installed_package_name
from inspect_ai._util.path import add_to_syspath, pretty_path
from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_info,
    registry_kwargs,
    registry_lookup,
    registry_name,
    registry_tag,
)
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from inspect_ai.scorer import Metric
from typing_extensions import overload

from inspect_scout._util.decorator import split_spec

from .._concurrency._mp_common import register_plugin_directory
from .._transcript.types import (
    EventType,
    MessageType,
    Transcript,
    TranscriptContent,
)
from ._loaders import create_implicit_loader
from .filter import (
    normalize_events_filter,
    normalize_messages_filter,
)
from .loader import Loader
from .result import Result
from .types import ScannerInput
from .validate import infer_filters_from_type, validate_scanner_signature

SCANNER_CONFIG = "scanner_config"
SCANNER_METRICS = "scanner_metrics"
SCANNER_VERSION = "scanner_version"

SCANNER_FILE_ATTR = "___scanner_file___"
SCANNER_NAME_ATTR = "___scanner_name___"

# core types
# Use bounded TypeVar (contravariant for scanner input)
T = TypeVar("T", bound=ScannerInput, contravariant=True)
TM = TypeVar(
    "TM", bound=Transcript | ChatMessage | list[ChatMessage], contravariant=True
)
TE = TypeVar("TE", bound=Transcript | Event | list[Event], contravariant=True)
P = ParamSpec("P")
# Invariant TypeVar for decorator overloads where type inference is needed
TScan = TypeVar("TScan", bound=ScannerInput)


class Scanner(Protocol[T]):
    """Scanner protocol."""

    def __call__(self, input: T, /) -> Awaitable[Result | list[Result]]:
        """Scan transcript content.

        Args:
           input: Input to scan.

        Returns:
           ScanResult: Result of scan (value and related metadata).
        """
        ...


@dataclass
class ScannerConfig:
    content: TranscriptContent = field(default_factory=TranscriptContent)
    # TODO: I want to make loader non-optional, but this obviously isn't right
    loader: Loader[ScannerInput] = field(default=cast(Loader[ScannerInput], None))


ScannerFactory = Callable[P, Scanner[T]]


# overloads for both messages and events present: scanner takes Transcript
# mypy: disable-error-code="overload-overlap"
@overload
def scanner(
    *,
    messages: Literal["all"],
    events: list[EventType],
    loader: Loader[Transcript] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, Transcript]], ScannerFactory[P, Transcript]]: ...
@overload
def scanner(
    *,
    messages: list[MessageType],
    events: Literal["all"],
    loader: Loader[Transcript] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, Transcript]], ScannerFactory[P, Transcript]]: ...
@overload
def scanner(
    *,
    messages: list[MessageType],
    events: list[EventType],
    loader: Loader[Transcript] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, Transcript]], ScannerFactory[P, Transcript]]: ...
@overload
def scanner(
    *,
    messages: Literal["all"],
    events: Literal["all"],
    loader: Loader[Transcript] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, Transcript]], ScannerFactory[P, Transcript]]: ...


# overloads for type lists: scanner can take T or list[T] or Transcript
@overload
def scanner(
    *,
    messages: list[MessageType],
    events: None = ...,
    loader: Loader[list[ChatMessage]] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, TM]], ScannerFactory[P, ScannerInput]]: ...
@overload
def scanner(
    *,
    events: list[EventType],
    messages: None = ...,
    loader: Loader[list[Event]] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, TE]], ScannerFactory[P, ScannerInput]]: ...


# overloads for "all": scanner can take T or list[T] or Transcript
@overload
def scanner(
    *,
    messages: Literal["all"],
    events: None = ...,
    loader: Loader[ChatMessage] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, TM]], ScannerFactory[P, ScannerInput]]: ...
@overload
def scanner(
    *,
    events: Literal["all"],
    messages: None = ...,
    loader: Loader[Event] | None = ...,
    name: str | None = ...,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, TE]], ScannerFactory[P, ScannerInput]]: ...


# overload for direct decoration without parentheses (will infer from types)
# This needs to be last as it's the most general
@overload
def scanner(factory: ScannerFactory[P, T], /) -> ScannerFactory[P, T]: ...


@overload
def scanner(
    *,
    loader: Loader[TScan] | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    name: str | None = None,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = ...,
) -> Callable[[ScannerFactory[P, TScan]], ScannerFactory[P, TScan]]: ...


def scanner(
    factory: ScannerFactory[P, T] | None = None,
    *,
    loader: Loader[TScan] | None = None,
    messages: list[MessageType] | Literal["all"] | None = None,
    events: list[EventType] | Literal["all"] | None = None,
    name: str | None = None,
    version: int = 0,
    metrics: Sequence[Metric | Mapping[str, Sequence[Metric]]]
    | Mapping[str, Sequence[Metric]]
    | None = None,
) -> (
    ScannerFactory[P, T]
    | Callable[[ScannerFactory[P, T]], ScannerFactory[P, T]]
    | Callable[[ScannerFactory[P, TScan]], ScannerFactory[P, TScan]]
    | Callable[[ScannerFactory[P, TM]], ScannerFactory[P, ScannerInput]]
    | Callable[[ScannerFactory[P, TE]], ScannerFactory[P, ScannerInput]]
):
    """Decorator for registering scanners.

    Args:
       factory: Decorated scanner function.
       loader: Custom data loader for scanner.
       messages: Message types to scan.
       events: Event types to scan.
       name: Scanner name (defaults to function name).
       version: Scanner version (defaults to 0).
       metrics: One or more metrics to calculate over the values
           (only used if scanner is converted to a scorer via `as_scorer()`).

    Returns:
        Scanner with registry info.
    """
    # Handle direct decoration without parentheses
    if factory is not None:
        # Called as @scanner (without parentheses)
        return scanner()(factory)  # type: ignore[return-value]

    # Don't raise error here anymore - we'll check after attempting inference
    messages = normalize_messages_filter(messages) if messages is not None else None
    events = normalize_events_filter(events) if events is not None else None

    def decorate(factory_fn: ScannerFactory[P, T]) -> ScannerFactory[P, T]:
        @wraps(factory_fn)
        def factory_wrapper(*args: P.args, **kwargs: P.kwargs) -> Scanner[T]:
            scanner_fn = factory_fn(*args, **kwargs)

            # determine scanner name
            if name is not None:
                scanner_name = name
            elif hasattr(scanner_fn, SCANNER_NAME_ATTR):
                scanner_name = getattr(scanner_fn, SCANNER_NAME_ATTR)
            else:
                scanner_name = str(getattr(factory_fn, "__name__", "scanner"))

            scanner_name = registry_name(factory_fn, scanner_name)

            if not is_callable_coroutine(scanner_fn):
                raise TypeError(
                    f"'{scanner_name}' is not declared as an async callable."
                )

            # Infer filters from type annotations if not provided
            # Use explicit filters if provided, otherwise try to infer
            inferred_messages = messages
            inferred_events = events

            # Only infer if no loader and no explicit filters
            if loader is None and messages is None and events is None:
                temp_messages, temp_events = infer_filters_from_type(
                    scanner_fn, factory_fn.__globals__
                )
                # Cast to proper types (mypy can't infer the string literals)
                inferred_messages = (
                    cast(list[MessageType] | None, temp_messages)
                    if temp_messages
                    else None
                )
                inferred_events = (
                    cast(list[EventType] | None, temp_events) if temp_events else None
                )
                # If we couldn't infer anything, raise an error
                if inferred_messages is None and inferred_events is None:
                    raise ValueError(
                        f"scanner '{scanner_name}' requires at least one of: "
                        "messages=..., events=..., loader=..., or specific type annotations"
                    )

            # Validate scanner signature matches filters
            # Only validate if we have filters (not just a custom loader)
            if inferred_messages is not None or inferred_events is not None:
                validate_scanner_signature(
                    scanner_fn,
                    inferred_messages,
                    inferred_events,
                    factory_fn.__globals__,
                )

            # compute scanner config
            scanner_config = ScannerConfig()
            if inferred_messages is not None:
                scanner_config.content.messages = inferred_messages
            if inferred_events is not None:
                scanner_config.content.events = inferred_events
            if loader is not None:
                # TODO: how are we ensuring that the writer of a custom loader sets
                # the proper content filter? We could do it for them, but I'm not
                # sure how - syntactically
                scanner_config.loader = cast(Loader[ScannerInput], loader)
            else:
                scanner_config.loader = create_implicit_loader(
                    scanner_fn, scanner_config.content
                )

            registry_tag(
                factory_fn,
                scanner_fn,
                RegistryInfo(
                    type="scanner",
                    name=scanner_name,
                    metadata={
                        SCANNER_CONFIG: scanner_config,
                        SCANNER_METRICS: metrics,
                        SCANNER_VERSION: version,
                    },
                ),
                *args,
                **kwargs,
            )

            # if its not from an installed package then it is a "local"
            # module import, so set its scanner file
            if get_installed_package_name(factory_fn) is None:
                file = inspect.getfile(factory_fn)
                if file:
                    setattr(scanner_fn, SCANNER_FILE_ATTR, Path(file).as_posix())

            return scanner_fn

        scanner_name = registry_name(
            factory_fn, name or str(getattr(factory_fn, "__name__", "scanner"))
        )
        scanner_factory_wrapper = cast(ScannerFactory[P, T], factory_wrapper)
        registry_add(
            scanner_factory_wrapper,
            RegistryInfo(
                type="scanner",
                name=scanner_name,
                metadata={SCANNER_METRICS: metrics, SCANNER_VERSION: version},
            ),
        )
        return scanner_factory_wrapper

    return decorate


def scanner_version(scanner: Scanner[Any]) -> int:
    return int(registry_info(scanner).metadata.get(SCANNER_VERSION, 0))


def config_for_scanner(scanner: Scanner[Any]) -> ScannerConfig:
    return cast(ScannerConfig, registry_info(scanner).metadata[SCANNER_CONFIG])


def scanners_from_file(file: str, scanner_args: dict[str, Any]) -> list[Scanner[Any]]:
    file, job = split_spec(file)

    # compute path
    scanner_path = Path(file).resolve()

    # check for existence
    if not scanner_path.exists():
        raise PrerequisiteError(f"The file '{pretty_path(file)}' does not exist.")

    # add file directory to sys.path for imports
    scanner_dir = scanner_path.parent.as_posix()

    with add_to_syspath(scanner_dir):
        # create scanners
        load_module(scanner_path)
        scanners: list[Scanner[Any]] = []
        for decorator, _ in parse_decorators(scanner_path, "scanner"):
            # filter by job
            if job is not None and decorator != job:
                continue

            scanner_fn = registry_lookup("scanner", decorator)
            if scanner_fn is None:
                raise PrerequisiteError(f"{scanner_fn} was not found in the registry")
            assert callable(scanner_fn)
            scanner_param_names = list(inspect.signature(scanner_fn).parameters.keys())
            scanner_params = {
                k: v for k, v in scanner_args.items() if k in scanner_param_names
            }
            scanner = scanner_create(decorator, scanner_params)
            scanners.append(scanner)

        if scanners:
            register_plugin_directory(scanner_dir)
        return scanners


def scanner_create(name: str, params: dict[str, Any]) -> Scanner[Any]:
    obj = registry_lookup("scanner", name)
    assert callable(obj)
    kwargs = registry_kwargs(**params)
    return cast(Scanner[Any], obj(**kwargs))
