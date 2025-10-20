from inspect_ai.analysis._dataframe.extract import (
    messages_as_str as messages_as_str_impl,
)
from inspect_ai.model import ChatMessage


def messages_as_str(messages: list[ChatMessage]) -> str:
    """Concatenate list of chat messages into a string.

    Args:
       messages: List of chat messages

    Returns:
       str: Messages as a string.
    """
    return messages_as_str_impl(messages)
