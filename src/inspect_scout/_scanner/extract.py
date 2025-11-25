import re
from dataclasses import dataclass
from functools import reduce
from typing import Awaitable, Callable, Generic, Literal, TypeVar, overload

from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    Content,
)

from inspect_scout._scanner.result import Reference
from inspect_scout._transcript.types import Transcript

from .util import _message_id

T = TypeVar("T", Transcript, list[ChatMessage])


@dataclass(frozen=True)
class MessageFormatOptions:
    """Message formatting options for controlling message content display.

    These options control which parts of messages are included when
    formatting messages to strings.
    """

    exclude_system: bool = True
    """Exclude system messages (defaults to `True`)"""

    exclude_reasoning: bool = False
    """Exclude reasoning content (defaults to `False`)."""

    exclude_tool_usage: bool = False
    """Exclude tool usage (defaults to `False`)"""


@dataclass(frozen=True)
class MessagesPreprocessor(MessageFormatOptions, Generic[T]):
    """ChatMessage preprocessing transformations.

    Provide a `transform` function for fully custom transformations.
    Use the higher-level options (e.g. `exclude_system`) to
    perform various common content removal transformations.

    The default `MessagesPreprocessor` will exclude system
    messages and do no other transformations.
    """

    transform: Callable[[T], Awaitable[list[ChatMessage]]] | None = None
    """Transform the list of messages."""


@overload
async def messages_as_str(
    input: T,
    *,
    preprocessor: MessagesPreprocessor[T] | None = None,
) -> str: ...


@overload
async def messages_as_str(
    input: T,
    *,
    preprocessor: MessagesPreprocessor[T] | None = None,
    include_ids: Literal[True],
) -> tuple[str, Callable[[str], list[Reference]]]: ...


async def messages_as_str(
    input: T,
    *,
    preprocessor: MessagesPreprocessor[T] | None = None,
    include_ids: Literal[True] | None = None,
) -> str | tuple[str, Callable[[str], list[Reference]]]:
    """Concatenate list of chat messages into a string.

    Args:
       input: The Transcript with the messages or a list of messages.
       preprocessor: Content filter for messages.
       include_ids: If True, prepend ordinal references (e.g., [M1], [M2])
          to each message and return a function to extract references from text.
          If None (default), return plain formatted string.

    Returns:
       If include_ids is False: Messages concatenated as a formatted string.
       If include_ids is True: Tuple of (formatted string with [M1], [M2], etc.
          prefixes, function that takes text and returns list of Reference objects
          for any [M1], [M2], etc. references found in the text).
    """
    messages = (
        await preprocessor.transform(input)
        if preprocessor is not None and preprocessor.transform is not None
        else input.messages
        if isinstance(input, Transcript)
        else input
    )

    if not include_ids:
        return "\n".join([message_as_str(m, preprocessor) or "" for m in messages])

    def reduce_message(
        acc: tuple[list[str], dict[str, str]], message: ChatMessage
    ) -> tuple[list[str], dict[str, str]]:
        formatted_messages, message_id_map = acc
        if (msg_str := message_as_str(message, preprocessor)) is not None:
            ordinal = f"M{len(message_id_map) + 1}"
            message_id_map[ordinal] = _message_id(message)
            formatted_messages.append(f"[{ordinal}] {msg_str}")
        return formatted_messages, message_id_map

    formatted_messages, message_id_map = reduce(
        reduce_message, messages, (list[str](), dict[str, str]())
    )

    def extract_references(text: str) -> list[Reference]:
        return _extract_references(text, message_id_map)

    return "\n".join(formatted_messages), extract_references


def message_as_str(
    message: ChatMessage,
    preprocessor: MessageFormatOptions | None = None,
) -> str | None:
    """Convert a ChatMessage to a formatted string representation.

    Args:
        message: The `ChatMessage` to convert.
        preprocessor: Content filter for messages. Defaults to removing system messages.

    Returns:
        A formatted string with the message role and content, or None if the message
        should be excluded based on the provided flags.
    """
    preprocessor = preprocessor or MessageFormatOptions()

    if preprocessor.exclude_system and message.role == "system":
        return None

    content = _better_content_text(
        message.content, preprocessor.exclude_tool_usage, preprocessor.exclude_reasoning
    )

    if (
        not preprocessor.exclude_tool_usage
        and isinstance(message, ChatMessageAssistant)
        and message.tool_calls
    ):
        entry = f"{message.role.upper()}:\n{content}\n"

        for tool in message.tool_calls:
            func_name = tool.function
            args = tool.arguments

            if isinstance(args, dict):
                args_text = "\n".join(f"{k}: {v}" for k, v in args.items())
                entry += f"\nTool Call: {func_name}\nArguments:\n{args_text}\n"
            else:
                entry += f"\nTool Call: {func_name}\nArguments: {args}\n"

        return entry

    elif isinstance(message, ChatMessageTool):
        if preprocessor.exclude_tool_usage:
            return None
        func_name = message.function or "unknown"
        error_part = (
            f"\n\nError in tool call '{func_name}':\n{message.error.message}\n"
            if message.error
            else ""
        )
        return f"{message.role.upper()}:\n{content}{error_part}\n"

    else:
        return f"{message.role.upper()}:\n{content}\n"


def _text_from_content(
    content: Content, exclude_tool_usage: bool, exclude_reasoning: bool
) -> str | None:
    match content.type:
        case "text":
            return content.text
        case "reasoning":
            return (
                None
                if (
                    exclude_reasoning
                    or not (
                        reasoning := content.summary
                        if content.redacted
                        else content.reasoning
                    )
                )
                # We need to bracket it with a start/finish since it could be multiple
                # lines long, and we need to distinguish it from content text's
                else f"\n<think>{reasoning}</think>"
            )

        case "tool_use":
            return (
                None
                if exclude_tool_usage
                else f"\nTool Use: {content.name}({content.arguments}) -> {content.result} {content.error if content.error else ''}"
            )
        case "image" | "audio" | "video" | "data" | "document":
            return f"<{content.type} />"


def _better_content_text(
    content: str | list[Content],
    exclude_tool_usage: bool,
    exclude_reasoning: bool,
) -> str:
    if isinstance(content, str):
        return content
    else:
        all_text = [
            text
            for c in content
            if (text := _text_from_content(c, exclude_tool_usage, exclude_reasoning))
            is not None
        ]
        return "\n".join(all_text)


def _extract_references(text: str, id_map: dict[str, str]) -> list[Reference]:
    """Extract message and event references from text.

    Args:
        text: Text containing [M{n}] or [E{n}] style references
        id_map: Dict mapping ordinal IDs (e.g., "M1", "M2", "E1", "E2") to actual IDs

    Returns:
        List of Reference objects with type="message" or type="event"
    """
    # Find all [M{number}] or [E{number}] patterns in the text
    pattern = r"\[(M|E)\d+\]"
    matches = re.finditer(pattern, text)

    references = []
    seen_ids = set()

    for match in matches:
        cite = match.group(0)
        # Extract ordinal key (e.g., "M1" from "[M1]" or "E1" from "[E1]")
        ordinal_key = cite[1:-1]

        # Look up actual ID
        if ordinal_key in id_map:
            actual_id = id_map[ordinal_key]
            # Avoid duplicate references
            if actual_id not in seen_ids:
                ref_type: Literal["message", "event"] = (
                    "message" if ordinal_key.startswith("M") else "event"
                )
                references.append(Reference(type=ref_type, cite=cite, id=actual_id))
                seen_ids.add(actual_id)

    return references
