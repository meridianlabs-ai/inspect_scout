from typing import NamedTuple

from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    Content,
)


class ContentFilter(NamedTuple):
    """Message content options for LLM scanner."""

    exclude_system: bool = True
    """Exclude system messages (defaults to `True`)"""

    exclude_reasoning: bool = False
    """Exclude reasoning content (defaults to `False`)."""

    exclude_tool_usage: bool = False
    """Exclude tool usage (defaults to `False`)"""


def messages_as_str(
    messages: list[ChatMessage], filter: ContentFilter | None = None
) -> str:
    """Concatenate list of chat messages into a string.

    Args:
       messages: List of chat messages
       filter: Content filter for messages.

    Returns:
       str: Messages as a string.
    """
    return "\n".join([message_as_str(m, filter) or "" for m in messages])


def message_as_str(
    message: ChatMessage, filter: ContentFilter | None = None
) -> str | None:
    """Convert a ChatMessage to a formatted string representation.

    Args:
        message: The `ChatMessage` to convert.
        filter: Content filter for messages.

    Returns:
        A formatted string with the message role and content, or None if the message
        should be excluded based on the provided flags.
    """
    filter = filter or ContentFilter()
    exclude_system, exclude_reasoning, exclude_tool_usage = filter

    if exclude_system and message.role == "system":
        return None

    content = _better_content_text(
        message.content, exclude_tool_usage, exclude_reasoning
    )

    if (
        not exclude_tool_usage
        and isinstance(message, ChatMessageAssistant)
        and message.tool_calls
    ):
        entry = f"{message.role}:\n{content}\n"

        for tool in message.tool_calls:
            func_name = tool.function
            args = tool.arguments

            if isinstance(args, dict):
                args_text = "\n".join(f"{k}: {v}" for k, v in args.items())
                entry += f"\nTool Call: {func_name}\nArguments:\n{args_text}"
            else:
                entry += f"\nTool Call: {func_name}\nArguments: {args}"

        return entry

    elif isinstance(message, ChatMessageTool):
        if exclude_tool_usage:
            return None
        func_name = message.function or "unknown"
        error_part = (
            f"\n\nError in tool call '{func_name}':\n{message.error.message}\n"
            if message.error
            else ""
        )
        return f"{message.role}:\n{content}{error_part}"

    else:
        return f"{message.role}:\n{content}\n"


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
