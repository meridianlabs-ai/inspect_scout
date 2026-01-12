"""OpenAI and OTEL-specific parsing and extraction for LangFuse data."""

import json
from typing import Any

from inspect_ai.model import (
    ChatMessageAssistant,
    ModelOutput,
)
from inspect_ai.model._model_output import ChatCompletionChoice, ModelUsage, StopReason
from inspect_ai.tool import ToolCall

from .anthropic import has_anthropic_tool_blocks, parse_json_content


def extract_text_from_otel_contents(contents: Any) -> str:
    """Extract text content from OTEL contents array.

    OTEL instrumentations may store content as a list of typed objects:
    - [{message_content: {type: "text", text: "..."}}]
    - [{type: "text", text: "..."}]
    - [{type: "input_text", text: "..."}]

    Args:
        contents: List of content objects or string

    Returns:
        Extracted text as a string
    """
    if isinstance(contents, str):
        return contents

    if not isinstance(contents, list):
        return str(contents) if contents else ""

    texts: list[str] = []
    for c in contents:
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, dict):
            # Handle nested message_content wrapper
            mc = c.get("message_content", c)
            if isinstance(mc, dict):
                content_type = mc.get("type", "")
                if content_type in ["text", "input_text", "output_text"]:
                    texts.append(mc.get("text", ""))
            elif isinstance(mc, str):
                texts.append(mc)

    return "\n".join(texts) if texts else ""


def normalize_otel_messages_to_openai(messages: Any) -> Any:
    """Normalize OTEL-instrumented messages to proper OpenAI format.

    OTEL instrumentations may produce messages with:
    - Nested 'message' wrapper (OpenAI OTEL): {"message": {"role": "...", ...}}
    - tool_calls that lack 'type' field (OpenAI requires type='function')
    - tool_calls using 'name' instead of nested 'function.name'
    - Missing 'tool_call_id' in tool response messages
    - 'contents' (plural) instead of 'content'

    Args:
        messages: List of message dicts from OTEL instrumentation

    Returns:
        Messages normalized to OpenAI format
    """
    if not isinstance(messages, list):
        return messages

    normalized = []
    for msg in messages:
        # Skip None messages (OpenAI OTEL instrumentation sometimes captures None)
        if msg is None:
            continue

        if not isinstance(msg, dict):
            normalized.append(msg)
            continue

        # Unwrap nested 'message' structure (OpenAI OTEL format)
        if "message" in msg and isinstance(msg["message"], dict):
            msg = msg["message"]

        # Copy the message to avoid mutating the original
        new_msg = dict(msg)

        # Add role if missing but can be inferred
        if "role" not in new_msg:
            # Tool response: has tool_call_id but no role
            if "tool_call_id" in new_msg:
                new_msg["role"] = "tool"
            # Otherwise skip this message as it's malformed
            else:
                continue

        # Convert 'contents' (plural) to 'content' for OpenAI compatibility
        if "contents" in new_msg and "content" not in new_msg:
            contents = new_msg.pop("contents")
            # Try parsing as JSON first (may contain Anthropic tool blocks)
            parsed = parse_json_content(contents)
            if has_anthropic_tool_blocks(parsed):
                # Keep structured Anthropic content with tool blocks
                new_msg["content"] = parsed
            else:
                new_msg["content"] = extract_text_from_otel_contents(contents)

        # Handle 'content' field - may be JSON string or list
        if "content" in new_msg:
            # Try parsing JSON string content
            new_msg["content"] = parse_json_content(new_msg["content"])
            # Only flatten to text if it's a list without tool blocks
            if isinstance(new_msg["content"], list):
                if not has_anthropic_tool_blocks(new_msg["content"]):
                    new_msg["content"] = extract_text_from_otel_contents(
                        new_msg["content"]
                    )

        # Normalize tool_calls in assistant messages
        if new_msg.get("role") == "assistant" and "tool_calls" in new_msg:
            tool_calls = new_msg.get("tool_calls", [])
            if isinstance(tool_calls, list):
                normalized_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        # Unwrap nested 'tool_call' wrapper (OpenAI OTEL format)
                        if "tool_call" in tc and isinstance(tc["tool_call"], dict):
                            tc = tc["tool_call"]
                        new_tc = dict(tc)
                        # Add type='function' if missing
                        if "type" not in new_tc:
                            new_tc["type"] = "function"
                        # Convert flat 'name'/'arguments' to nested 'function' structure
                        if "function" not in new_tc and "name" in new_tc:
                            new_tc["function"] = {
                                "name": new_tc.pop("name"),
                                "arguments": new_tc.pop("arguments", "{}"),
                            }
                        normalized_calls.append(new_tc)
                    else:
                        normalized_calls.append(tc)
                new_msg["tool_calls"] = normalized_calls

        # Normalize tool response messages
        if new_msg.get("role") == "tool":
            # Ensure tool_call_id exists
            if "tool_call_id" not in new_msg:
                new_msg["tool_call_id"] = new_msg.get("id", "unknown")

        normalized.append(new_msg)

    return normalized


def extract_otel_output(
    output_data: list[Any], model_name: str, usage: ModelUsage | None
) -> ModelOutput:
    """Extract output from OTEL-normalized format.

    Note: This function handles similar OTEL patterns as normalize_otel_messages_to_openai()
    but constructs a ModelOutput directly. The patterns are kept separate because input
    normalization prepares data for messages_from_openai(), while this builds the final output.

    OTEL instrumentations normalize provider outputs in different formats:

    Anthropic OTEL format:
    - `[{content, role, finish_reason, tool_calls}]`
    - `tool_calls` is `[{id, name, arguments}]`

    OpenAI OTEL format:
    - `[{message: {role, contents, tool_calls}}]`
    - `contents` is `[{message_content: {type, text}}]`
    - `tool_calls` is `[{tool_call: {id, function: {name, arguments}}}]`

    Args:
        output_data: List of message dicts from OTEL instrumentation
        model_name: Model name for the output
        usage: Optional usage data

    Returns:
        ModelOutput object
    """
    if not output_data:
        return ModelOutput.from_content(model=model_name, content="")

    # Take the first message (typically there's only one)
    msg = output_data[0]
    if not isinstance(msg, dict):
        return ModelOutput.from_content(model=model_name, content=str(output_data))

    # Handle nested 'message' wrapper (OpenAI OTEL format)
    if "message" in msg and isinstance(msg["message"], dict):
        msg = msg["message"]

    # Extract content - handle both 'content' and 'contents' (plural, OpenAI OTEL)
    content = ""
    if "content" in msg:
        raw_content = msg["content"]
        if isinstance(raw_content, str):
            content = raw_content
        elif raw_content:
            content = str(raw_content)
    elif "contents" in msg:
        # OpenAI OTEL: contents is list of {message_content: {type, text}}
        contents = msg.get("contents", [])
        if isinstance(contents, list):
            texts = []
            for c in contents:
                if isinstance(c, dict):
                    mc = c.get("message_content", c)
                    if isinstance(mc, dict) and mc.get("type") == "text":
                        texts.append(mc.get("text", ""))
            content = "\n".join(texts)

    # Extract tool calls - handle both flat and nested formats
    tool_calls: list[ToolCall] = []
    raw_tool_calls = msg.get("tool_calls", [])
    if isinstance(raw_tool_calls, list):
        for tc in raw_tool_calls:
            if isinstance(tc, dict):
                # OpenAI OTEL: nested {tool_call: {id, function: {name, arguments}}}
                if "tool_call" in tc and isinstance(tc["tool_call"], dict):
                    tc = tc["tool_call"]

                tc_id = tc.get("id", "")
                tc_args: dict[str, Any] = {}

                # Get function name and arguments
                if "function" in tc and isinstance(tc["function"], dict):
                    tc_name = tc["function"].get("name", "")
                    tc_args_raw = tc["function"].get("arguments", "{}")
                else:
                    # Flat format (Anthropic OTEL)
                    tc_name = tc.get("name", "")
                    tc_args_raw = tc.get("arguments", "{}")

                # Parse arguments (may be JSON string)
                if isinstance(tc_args_raw, str):
                    try:
                        tc_args = json.loads(tc_args_raw)
                    except json.JSONDecodeError:
                        tc_args = {"raw": tc_args_raw}
                elif isinstance(tc_args_raw, dict):
                    tc_args = tc_args_raw

                if tc_name:
                    tool_calls.append(
                        ToolCall(
                            id=tc_id,
                            function=tc_name,
                            arguments=tc_args,
                            type="function",
                        )
                    )

    # Map finish_reason to StopReason
    finish_reason = msg.get("finish_reason", "stop")
    stop_reason: StopReason
    if finish_reason in ["tool_use", "tool_calls"]:
        stop_reason = "tool_calls"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
    elif finish_reason == "content_filter":
        stop_reason = "content_filter"
    else:
        stop_reason = "stop"

    # Build assistant message
    assistant_msg = ChatMessageAssistant(
        content=content,
        tool_calls=tool_calls if tool_calls else None,
    )

    # Wrap in ChatCompletionChoice
    choice = ChatCompletionChoice(
        message=assistant_msg,
        stop_reason=stop_reason,
    )

    # Build output
    output = ModelOutput(
        model=model_name,
        choices=[choice],
    )

    # Add usage if available
    if usage:
        output.usage = usage

    return output
