import inspect
import types
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Union,
    get_args,
    get_origin,
)

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from typing_extensions import Literal

from .._transcript.types import Transcript, TranscriptContent
from .._transcript.util import filter_list, filter_transcript
from .loader import Loader, loader
from .types import ScannerInput


def _IdentityLoader(
    content: TranscriptContent,
) -> Loader[Transcript]:
    @loader(name="IdentityLoader", content=content)
    def the_factory() -> Loader[Transcript]:
        async def the_loader(
            transcript: Transcript,
        ) -> AsyncIterator[Transcript]:
            yield filter_transcript(transcript, content)

        return the_loader

    return the_factory()


def _ListLoader(
    message_or_event: Literal["message", "event"],
    content: TranscriptContent,
) -> Loader[ScannerInput]:
    @loader(name="ListLoader", content=content)
    def the_factory() -> Loader[ScannerInput]:
        async def the_loader(
            transcript: Transcript,
        ) -> AsyncIterator[list[ChatMessage] | list[Event]]:
            yield _get_filtered_list(transcript, content, message_or_event)

        return the_loader

    return the_factory()


def _ListItemLoader(
    message_or_event: Literal["message", "event"],
    content: TranscriptContent,
) -> Loader[ScannerInput]:
    @loader(name="ListItemLoader", content=content)
    def the_factory() -> Loader[ScannerInput]:
        async def the_loader(
            transcript: Transcript,
        ) -> AsyncIterator[ChatMessage | Event]:
            filtered_list = _get_filtered_list(transcript, content, message_or_event)
            for item in filtered_list:
                yield item

        return the_loader

    return the_factory()


def create_implicit_loader(
    scanner_fn: Callable[..., Any], content: TranscriptContent
) -> Loader[ScannerInput]:
    """Create appropriate loader based on scanner function's input type annotation.

    Args:
        scanner_fn: The scanner function to analyze.
        content: The scanner's content filter to be adopted by the loader.

    Returns:
        Appropriate loader for the scanner's input type.
    """
    # Get the first parameter's annotation
    input_annotation = next(
        iter(inspect.signature(scanner_fn).parameters.values())
    ).annotation
    if input_annotation is inspect.Parameter.empty or input_annotation == Transcript:
        return _IdentityLoader(content)

    # Check if it's a list type
    origin = get_origin(input_annotation)
    if origin is list:
        # Get the element type
        args = get_args(input_annotation)
        assert args, "Scanner input list type annotation must not be bare"
        element_type = args[0]
        # Return list loader (yields entire list)
        return _ListLoader(_message_or_event(element_type), content)

    # Otherwise it's a single item type (ChatMessage or Event)
    # Return item loader (yields individual items)
    return _ListItemLoader(_message_or_event(input_annotation), content)


def _matches_union_type(type_annotation: Any, union_type: Any) -> bool:
    """Check if a type annotation matches a union type (by membership or subclass).

    Args:
        type_annotation: The type to check.
        union_type: The union type to check against (e.g., ChatMessage or Event).

    Returns:
        True if the type matches the union type.
    """
    # Get the constituent types of the union
    union_members = get_args(union_type)
    if not union_members:
        return False

    # Check if it's one of the union's constituent types
    if type_annotation in union_members:
        return True

    # Check if it's a class that derives from one of the union's types
    if isinstance(type_annotation, type):
        try:
            return any(issubclass(type_annotation, member) for member in union_members)
        except TypeError:
            pass

    return False


def _matches_message_or_event_type(type_annotation: Any, union_type: Any) -> bool:
    """Check if a type annotation matches a ChatMessage or Event union type.

    Args:
        type_annotation: The type to check (could be the union itself, a union member,
                        or a union of members).
        union_type: The union type to check against (ChatMessage or Event).

    Returns:
        True if the type matches the union type.
    """
    # Direct equality check for the union type itself
    if type_annotation == union_type:
        return True

    # Check if it's a Union type (e.g., ChatMessageUser | ChatMessageAssistant)
    origin = get_origin(type_annotation)
    # Handle both typing.Union and types.UnionType (from | syntax in Python 3.10+)
    if (
        origin is Union
        or isinstance(origin, type)
        and issubclass(origin, types.UnionType)
    ):
        args = get_args(type_annotation)
        if args:
            # The type system should prevent mixing ChatMessage and Event types
            # in a union, but we validate all members just to be safe.
            return all(_matches_message_or_event_type(arg, union_type) for arg in args)

    # Check if it's a union member or subclass
    return _matches_union_type(type_annotation, union_type)


def _message_or_event(type_annotation: Any) -> Literal["message", "event"]:
    assert type_annotation is not None, "Must have type annotation"

    # Check if it matches ChatMessage
    if _matches_message_or_event_type(type_annotation, ChatMessage):
        return "message"

    # Check if it matches Event
    if _matches_message_or_event_type(type_annotation, Event):
        return "event"

    # Programming error if neither ChatMessage nor Event
    raise RuntimeError(
        f"Type annotation must conform to ChatMessage or Event, got {type_annotation}"
    )


def _get_filtered_list(
    transcript: Transcript,
    content: TranscriptContent,
    message_or_event: Literal["message", "event"],
) -> list[ChatMessage] | list[Event]:
    # TODO: The generic typing used by apply_filter_to_list is confounding the inference
    # engine - preventing this from being more concise.
    if message_or_event == "message":
        return filter_list(transcript.messages, content.messages)
    else:
        return filter_list(transcript.events, content.events)
