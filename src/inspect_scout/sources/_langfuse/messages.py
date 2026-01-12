"""Message building and conversion for LangFuse transcripts."""

from typing import Any

from inspect_ai._util.content import ContentText
from inspect_ai.model._chat_message import ChatMessage

# Content handling constants
MESSAGE_KEY_PREFIX_LENGTH = 200  # Characters used for message deduplication key


def message_key(msg: ChatMessage) -> tuple[str, str]:
    """Create a key for message deduplication.

    Args:
        msg: ChatMessage to create key for

    Returns:
        Tuple of (role, content_prefix) for deduplication
    """
    content = ""
    if isinstance(msg.content, str):
        content = msg.content[:MESSAGE_KEY_PREFIX_LENGTH]
    elif isinstance(msg.content, list):
        # Extract text from content blocks
        texts = []
        for c in msg.content:
            if hasattr(c, "text"):
                texts.append(c.text)
        content = " ".join(texts)[:MESSAGE_KEY_PREFIX_LENGTH]
    return (msg.role, content)


def merge_transcript_messages(
    base_messages: list[ChatMessage],
    additional_messages: list[ChatMessage],
) -> list[ChatMessage]:
    """Merge message lists, avoiding duplicates while preserving order.

    Strategy:
    - Start with base_messages (has system/user context from Responses API)
    - Append additional_messages that aren't already present
    - Use message role + content prefix for deduplication

    Args:
        base_messages: Base messages (typically from Responses API format)
        additional_messages: Additional messages to merge (typically from final OTEL)

    Returns:
        Merged list of messages
    """
    if not additional_messages:
        return base_messages

    if not base_messages:
        return additional_messages

    # Create set of keys from base messages for O(1) lookup
    base_keys = {message_key(msg) for msg in base_messages}

    # Start with base and add unique additional messages
    merged = list(base_messages)

    for msg in additional_messages:
        key = message_key(msg)
        if key not in base_keys:
            merged.append(msg)
            base_keys.add(key)

    return merged


def build_messages_from_events(events: list[Any]) -> list[ChatMessage]:
    """Build message list from model events.

    This reconstructs the full conversation using the LAST model event's input
    (which contains the complete conversation history) plus its output.

    For OTEL-instrumented providers (Anthropic, Google, OpenAI):
    - Each model event's input contains the full conversation up to that point
    - The last model event's input has all messages including system, user, and tool
    - OpenAI Responses API is handled separately before this function is called

    Args:
        events: List of events (ModelEvent, ToolEvent, etc.)

    Returns:
        List of ChatMessage objects representing the full conversation
    """
    messages: list[ChatMessage] = []

    # Find model events
    model_events = [e for e in events if getattr(e, "event", "") == "model"]

    if not model_events:
        return messages

    last_model = model_events[-1]

    # Use the last model event's input - it has the complete conversation
    if last_model.input:
        for msg in last_model.input:
            messages.append(msg)

    # Add the output message (the final assistant response)
    if last_model.output and last_model.output.message:
        messages.append(last_model.output.message)

    return messages


def build_google_messages_from_events(events: list[Any]) -> list[ChatMessage]:
    """Build Google message list using ModelEvent outputs for assistant messages.

    Google's scaffold doesn't replay reasoning text to the model, so reasoning
    ONLY exists in ModelEvent.output. This function builds messages by:

    1. Taking non-assistant messages (system, user, tool) from the final
       ModelEvent's input (which has the complete conversation structure)
    2. For each assistant message in the input, finding the matching ModelEvent
       output by content (tool calls or text) and using that instead

    This ensures we capture all reasoning blocks that would otherwise be lost.

    Args:
        events: All events including ModelEvents

    Returns:
        List of ChatMessage objects with reasoning preserved
    """
    model_events = [e for e in events if getattr(e, "event", "") == "model"]

    if not model_events:
        return []

    # Get the final model event for conversation structure
    final_model = model_events[-1]

    # Build a list of assistant messages from ALL ModelEvent outputs
    # These contain the actual reasoning
    assistant_outputs: list[ChatMessage] = []
    for model_event in model_events:
        if model_event.output and model_event.output.message:
            assistant_outputs.append(model_event.output.message)

    # Build final message list, matching assistant messages by content
    messages: list[ChatMessage] = []
    used_outputs: set[int] = set()

    if final_model.input:
        for msg in final_model.input:
            if msg.role == "assistant":
                # Find matching output by content
                match = _find_matching_output(msg, assistant_outputs, used_outputs)
                if match is not None:
                    messages.append(assistant_outputs[match])
                    used_outputs.add(match)
                else:
                    # No match found, use input version
                    messages.append(msg)
            else:
                # Keep non-assistant messages as-is
                messages.append(msg)

    # Add any remaining unmatched outputs (e.g., the final response)
    for i, output in enumerate(assistant_outputs):
        if i not in used_outputs:
            messages.append(output)

    return messages


def _find_matching_output(
    input_msg: ChatMessage,
    outputs: list[ChatMessage],
    used: set[int],
) -> int | None:
    """Find the ModelEvent output that matches an input assistant message.

    Matches by comparing:
    1. Tool calls (by function name and arguments)
    2. Text content

    Args:
        input_msg: Assistant message from final ModelEvent input
        outputs: List of assistant messages from ModelEvent outputs
        used: Set of output indices already matched

    Returns:
        Index of matching output, or None if no match found
    """
    # Extract tool calls from input
    input_tool_calls = getattr(input_msg, "tool_calls", None) or []

    # Extract text from input
    input_text = _extract_text_content(input_msg)

    for i, output in enumerate(outputs):
        if i in used:
            continue

        # Try matching by tool calls first (more reliable)
        output_tool_calls = getattr(output, "tool_calls", None) or []

        if input_tool_calls and output_tool_calls:
            if _tool_calls_match(input_tool_calls, output_tool_calls):
                return i

        # Try matching by text content
        output_text = _extract_text_content(output)
        if input_text and output_text and input_text == output_text:
            return i

    return None


def _extract_text_content(msg: ChatMessage) -> str:
    """Extract plain text content from a message."""
    if isinstance(msg.content, str):
        return msg.content

    if isinstance(msg.content, list):
        text_parts = []
        for item in msg.content:
            if isinstance(item, ContentText) and item.text:
                text_parts.append(item.text)
            elif isinstance(item, str):
                text_parts.append(item)
        return " ".join(text_parts)

    return ""


def _tool_calls_match(
    calls1: list[Any],
    calls2: list[Any],
) -> bool:
    """Check if two tool call lists match by function name and arguments."""
    if len(calls1) != len(calls2):
        return False

    for tc1, tc2 in zip(calls1, calls2, strict=False):
        # Compare function name (ToolCall has .function attribute)
        name1 = getattr(tc1, "function", None)
        name2 = getattr(tc2, "function", None)

        if name1 != name2:
            return False

        # Compare arguments (ToolCall has .arguments attribute)
        args1 = getattr(tc1, "arguments", None) or {}
        args2 = getattr(tc2, "arguments", None) or {}

        if args1 != args2:
            return False

    return True
