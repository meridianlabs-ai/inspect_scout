"""Input/output extraction for Phoenix span data.

Phoenix uses OpenInference semantic conventions with two data paths:
1. Raw payloads: `input.value` / `output.value` contain native provider JSON
2. Flattened attributes: `llm.input_messages.<i>.message.*` OpenInference format

The raw payload path is preferred as it preserves the full provider format.
The flattened attribute path serves as a fallback.
"""

import json
import os
from datetime import datetime
from logging import getLogger
from typing import Any

from inspect_ai.model import ModelOutput
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
)
from inspect_ai.model._model_output import ModelUsage
from inspect_ai.tool import ToolCall, ToolInfo, ToolParams

from .detection import Provider

logger = getLogger(__name__)


async def extract_input_messages(
    span: dict[str, Any], provider: Provider
) -> list[ChatMessage]:
    """Extract input messages from Phoenix span.

    Tries two extraction paths:
    1. Parse raw `input.value` JSON payload using provider-specific converters
    2. Parse OpenInference flattened attributes (`llm.input_messages.<i>.message.*`)

    Args:
        span: Phoenix span dictionary
        provider: Detected LLM provider

    Returns:
        List of ChatMessage objects
    """
    attributes = span.get("attributes") or {}

    # Path 1: Try raw input.value payload (most complete)
    messages = _parse_raw_input(attributes, provider)
    if messages:
        return messages

    # Path 2: Try OpenInference flattened attributes
    oi_messages = _extract_openinference_messages(
        attributes, prefix="llm.input_messages"
    )
    if oi_messages:
        return await _convert_messages(oi_messages, provider)

    return []


def _parse_raw_input(
    attributes: dict[str, Any], provider: Provider
) -> list[ChatMessage] | None:
    """Parse raw input.value JSON payload into ChatMessages.

    Args:
        attributes: Span attributes
        provider: Detected provider

    Returns:
        List of ChatMessages or None if parsing fails
    """
    input_value = attributes.get("input.value")
    if not input_value:
        return None

    if isinstance(input_value, str):
        try:
            input_data = json.loads(input_value)
        except json.JSONDecodeError:
            return None
    elif isinstance(input_data := input_value, dict):
        pass
    else:
        return None

    if not isinstance(input_data, dict):
        return None

    # Extract messages from the payload
    messages = input_data.get("messages") or input_data.get("contents")
    if messages and isinstance(messages, list):
        # Use provider-specific converters via _convert_messages_sync
        return _convert_messages_sync(messages, provider)

    # OpenAI Responses API: input can be string or list of typed items
    input_items = input_data.get("input")
    if isinstance(input_items, str):
        return [ChatMessageUser(content=input_items)]
    if isinstance(input_items, list):
        return _convert_responses_input(input_items)

    return None


def _convert_messages_sync(
    messages: list[dict[str, Any]], provider: Provider
) -> list[ChatMessage] | None:
    """Synchronously convert raw messages to ChatMessages.

    For raw payloads we use simple conversion since we can't await
    the async converter functions in a sync context.

    Args:
        messages: Raw message dicts from provider payload
        provider: Provider type

    Returns:
        List of ChatMessages or None
    """
    result: list[ChatMessage] = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Handle Anthropic content blocks
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        # Tool result in user messages (Anthropic format)
                        pass
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts) if text_parts else ""

        if role == "system":
            from inspect_ai.model._chat_message import ChatMessageSystem

            result.append(ChatMessageSystem(content=str(content)))
        elif role == "user":
            result.append(ChatMessageUser(content=str(content)))
        elif role == "assistant":
            tool_calls = _extract_tool_calls_from_message(msg)
            result.append(
                ChatMessageAssistant(
                    content=str(content) if content else "",
                    tool_calls=tool_calls if tool_calls else None,
                )
            )
        elif role == "tool":
            from inspect_ai.model._chat_message import ChatMessageTool

            result.append(
                ChatMessageTool(
                    content=str(content),
                    tool_call_id=str(msg.get("tool_call_id", "")),
                )
            )

    return result if result else None


def _extract_tool_calls_from_message(msg: dict[str, Any]) -> list[ToolCall]:
    """Extract tool calls from an assistant message.

    Args:
        msg: Message dictionary

    Returns:
        List of ToolCall objects
    """
    tool_calls: list[ToolCall] = []

    # OpenAI format: tool_calls array
    tc_list = msg.get("tool_calls")
    if isinstance(tc_list, list):
        for tc in tc_list:
            if not isinstance(tc, dict):
                continue
            func = tc.get("function", {})
            if not isinstance(func, dict):
                continue
            args_str = func.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}

            tool_calls.append(
                ToolCall(
                    id=str(tc.get("id", "")),
                    function=str(func.get("name", "")),
                    arguments=args if isinstance(args, dict) else {},
                    type="function",
                )
            )

    # Anthropic format: content blocks with type=tool_use
    content = msg.get("content")
    if isinstance(content, list) and not tool_calls:
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=str(block.get("id", "")),
                        function=str(block.get("name", "")),
                        arguments=block.get("input", {}),
                        type="function",
                    )
                )

    return tool_calls


def _convert_responses_input(items: list[Any]) -> list[ChatMessage] | None:
    """Convert OpenAI Responses API input items to ChatMessages.

    Handles input item types:
    - ``message`` → ChatMessageUser/ChatMessageAssistant/ChatMessageSystem
    - ``function_call`` → ChatMessageAssistant with ToolCall
    - ``function_call_output`` → ChatMessageTool

    Args:
        items: List of Responses API input items

    Returns:
        List of ChatMessages or None if no items parsed
    """
    from inspect_ai.model._chat_message import ChatMessageSystem, ChatMessageTool

    result: list[ChatMessage] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type", "")

        if item_type == "message":
            role = item.get("role", "user")
            # Content can be string or list of content items
            content = item.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") in ("input_text", "output_text", "text"):
                            text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = " ".join(text_parts) if text_parts else ""

            if role == "system":
                result.append(ChatMessageSystem(content=str(content)))
            elif role == "assistant":
                result.append(ChatMessageAssistant(content=str(content)))
            else:
                result.append(ChatMessageUser(content=str(content)))

        elif item_type == "function_call":
            args_str = item.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                args = {}
            result.append(
                ChatMessageAssistant(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id=str(item.get("call_id", "")),
                            function=str(item.get("name", "")),
                            arguments=args if isinstance(args, dict) else {},
                            type="function",
                        )
                    ],
                )
            )

        elif item_type == "function_call_output":
            result.append(
                ChatMessageTool(
                    content=str(item.get("output", "")),
                    tool_call_id=str(item.get("call_id", "")),
                )
            )

    return result if result else None


def _extract_openinference_messages(
    attributes: dict[str, Any], prefix: str
) -> list[dict[str, Any]]:
    """Extract messages from OpenInference flattened attributes.

    OpenInference stores messages as:
    - llm.input_messages.0.message.role = "user"
    - llm.input_messages.0.message.content = "Hello"
    - llm.input_messages.1.message.role = "assistant"
    - etc.

    Args:
        attributes: Span attributes dictionary
        prefix: Attribute prefix (e.g., "llm.input_messages" or "llm.output_messages")

    Returns:
        List of message dictionaries in OpenAI format
    """
    messages: list[dict[str, Any]] = []
    index = 0

    while True:
        role_key = f"{prefix}.{index}.message.role"
        content_key = f"{prefix}.{index}.message.content"

        role = attributes.get(role_key)
        content = attributes.get(content_key)

        if role is None and content is None:
            break

        msg: dict[str, Any] = {
            "role": role or "user",
            "content": content or "",
        }

        # Check for tool calls in this message
        tc_index = 0
        tool_calls: list[dict[str, Any]] = []
        while True:
            tc_name_key = f"{prefix}.{index}.message.tool_calls.{tc_index}.tool_call.function.name"
            tc_name = attributes.get(tc_name_key)
            if tc_name is None:
                break

            tc_id = attributes.get(
                f"{prefix}.{index}.message.tool_calls.{tc_index}.tool_call.id", ""
            )
            tc_args = attributes.get(
                f"{prefix}.{index}.message.tool_calls."
                f"{tc_index}.tool_call.function.arguments",
                "{}",
            )

            tool_calls.append(
                {
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": tc_name,
                        "arguments": tc_args
                        if isinstance(tc_args, str)
                        else json.dumps(tc_args),
                    },
                }
            )
            tc_index += 1

        if tool_calls:
            msg["tool_calls"] = tool_calls

        # Check for tool_call_id (tool response messages)
        tool_call_id_key = f"{prefix}.{index}.message.tool_call_id"
        tool_call_id = attributes.get(tool_call_id_key)
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
            msg["role"] = "tool"

        messages.append(msg)
        index += 1

    return messages


async def _convert_messages(
    messages: list[dict[str, Any]], provider: Provider
) -> list[ChatMessage]:
    """Convert message dictionaries to ChatMessage objects.

    Uses inspect_ai converters based on detected provider.

    Args:
        messages: List of message dictionaries (OpenAI format)
        provider: Detected provider type

    Returns:
        List of ChatMessage objects
    """
    if not messages:
        return []

    # OpenInference normalizes to OpenAI-like format, so use OpenAI converter
    try:
        from inspect_ai.model import messages_from_openai

        normalized = _normalize_openai_messages(messages)
        return await messages_from_openai(normalized)  # type: ignore[arg-type]
    except Exception:
        if os.environ.get("PHOENIX_STRICT_IMPORT"):
            raise
        logger.warning("messages_from_openai failed, falling back to simple conversion")
        return _simple_message_conversion(messages)


def _normalize_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize messages for OpenAI converter.

    Args:
        messages: Raw message list

    Returns:
        Normalized message list
    """
    normalized = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        new_msg = dict(msg)

        # Normalize Google GenAI role names
        role = new_msg.get("role", "")
        if role == "model":
            new_msg["role"] = "assistant"

        # Normalize tool_calls if present
        if "tool_calls" in new_msg:
            tool_calls = new_msg["tool_calls"]
            if isinstance(tool_calls, list):
                normalized_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        new_tc = dict(tc)
                        if "type" not in new_tc:
                            new_tc["type"] = "function"
                        if "function" not in new_tc and "name" in new_tc:
                            args = new_tc.pop("args", None) or new_tc.pop(
                                "arguments", None
                            )
                            if isinstance(args, dict):
                                args = json.dumps(args)
                            elif args is None:
                                args = "{}"
                            new_tc["function"] = {
                                "name": new_tc.pop("name"),
                                "arguments": args,
                            }
                        normalized_calls.append(new_tc)
                new_msg["tool_calls"] = normalized_calls

        normalized.append(new_msg)

    return normalized


def _simple_message_conversion(messages: list[dict[str, Any]]) -> list[ChatMessage]:
    """Simple fallback message conversion.

    Args:
        messages: List of message dictionaries

    Returns:
        List of ChatMessage objects
    """
    result: list[ChatMessage] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = str(msg.get("content", ""))

        if role == "user":
            result.append(ChatMessageUser(content=content))
        elif role == "assistant":
            result.append(ChatMessageAssistant(content=content))

    return result


async def extract_output(span: dict[str, Any], provider: Provider) -> ModelOutput:
    """Extract output from Phoenix span.

    Args:
        span: Phoenix span dictionary
        provider: Detected provider type

    Returns:
        ModelOutput object
    """
    attributes = span.get("attributes") or {}
    model_name = get_model_name_from_attrs(attributes) or "unknown"

    # Path 1: Try raw output.value payload
    output = _parse_raw_output(attributes, model_name, provider)
    if output:
        usage = extract_usage(span)
        if usage:
            output.usage = usage
        return output

    # Path 2: Try OpenInference flattened output messages
    oi_messages = _extract_openinference_messages(
        attributes, prefix="llm.output_messages"
    )
    if oi_messages:
        last_msg = oi_messages[-1]
        content = last_msg.get("content", "") or ""
        tool_calls_data = last_msg.get("tool_calls")

        if tool_calls_data:
            from inspect_ai.model._model_output import ChatCompletionChoice

            tool_calls = []
            for tc in tool_calls_data:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = (
                        json.loads(args_str) if isinstance(args_str, str) else args_str
                    )
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(
                    ToolCall(
                        id=str(tc.get("id", "")),
                        function=str(func.get("name", "")),
                        arguments=args if isinstance(args, dict) else {},
                        type="function",
                    )
                )

            output = ModelOutput(
                model=model_name,
                choices=[
                    ChatCompletionChoice(
                        message=ChatMessageAssistant(
                            content=str(content),
                            tool_calls=tool_calls,
                        ),
                        stop_reason="tool_calls",
                    )
                ],
            )
        else:
            output = ModelOutput.from_content(model=model_name, content=str(content))

        usage = extract_usage(span)
        if usage:
            output.usage = usage
        return output

    # Fallback: empty output
    output = ModelOutput.from_content(model=model_name, content="")
    usage = extract_usage(span)
    if usage:
        output.usage = usage
    return output


def _parse_raw_output(
    attributes: dict[str, Any], model_name: str, provider: Provider
) -> ModelOutput | None:
    """Parse raw output.value JSON payload into ModelOutput.

    Args:
        attributes: Span attributes
        model_name: Model name for output
        provider: Detected provider

    Returns:
        ModelOutput or None if parsing fails
    """
    from inspect_ai.model._model_output import ChatCompletionChoice

    output_value = attributes.get("output.value")
    if not output_value:
        return None

    if isinstance(output_value, str):
        try:
            output_data = json.loads(output_value)
        except json.JSONDecodeError:
            return None
    elif isinstance(output_data := output_value, dict):
        pass
    else:
        return None

    if not isinstance(output_data, dict):
        return None

    # OpenAI format: choices array
    choices = output_data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            msg = choice.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", "") or ""
                tool_calls_data = msg.get("tool_calls")
                tool_calls = None

                if tool_calls_data and isinstance(tool_calls_data, list):
                    tool_calls = []
                    for tc in tool_calls_data:
                        if isinstance(tc, dict):
                            func = tc.get("function", {})
                            args_str = (
                                func.get("arguments", "{}")
                                if isinstance(func, dict)
                                else "{}"
                            )
                            try:
                                args = (
                                    json.loads(args_str)
                                    if isinstance(args_str, str)
                                    else args_str
                                )
                            except json.JSONDecodeError:
                                args = {}

                            tool_calls.append(
                                ToolCall(
                                    id=str(tc.get("id", "")),
                                    function=str(
                                        func.get("name", "")
                                        if isinstance(func, dict)
                                        else ""
                                    ),
                                    arguments=args if isinstance(args, dict) else {},
                                    type="function",
                                )
                            )

                return ModelOutput(
                    model=model_name,
                    choices=[
                        ChatCompletionChoice(
                            message=ChatMessageAssistant(
                                content=str(content),
                                tool_calls=tool_calls,
                            ),
                            stop_reason="tool_calls" if tool_calls else "stop",
                        )
                    ],
                )

    # Anthropic format: content array at top level
    content_blocks = output_data.get("content")
    if isinstance(content_blocks, list):
        text_parts = []
        tool_calls = []

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=str(block.get("id", "")),
                        function=str(block.get("name", "")),
                        arguments=block.get("input", {}),
                        type="function",
                    )
                )

        content = "".join(text_parts)

        return ModelOutput(
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessageAssistant(
                        content=content,
                        tool_calls=tool_calls if tool_calls else None,
                    ),
                    stop_reason="tool_calls" if tool_calls else "stop",
                )
            ],
        )

    # OpenAI Responses API format: output array with typed items
    output_items = output_data.get("output")
    if isinstance(output_items, list) and output_items:
        text_parts = []
        tool_calls = []

        for item in output_items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")

            if item_type == "message":
                for content_item in item.get("content", []):
                    if isinstance(content_item, dict):
                        if content_item.get("type") == "output_text":
                            text_parts.append(content_item.get("text", ""))

            elif item_type == "function_call":
                args_str = item.get("arguments", "{}")
                try:
                    args = (
                        json.loads(args_str) if isinstance(args_str, str) else args_str
                    )
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(
                    ToolCall(
                        id=str(item.get("call_id", "")),
                        function=str(item.get("name", "")),
                        arguments=args if isinstance(args, dict) else {},
                        type="function",
                    )
                )

        content = "".join(text_parts)

        return ModelOutput(
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessageAssistant(
                        content=content,
                        tool_calls=tool_calls if tool_calls else None,
                    ),
                    stop_reason="tool_calls" if tool_calls else "stop",
                )
            ],
        )

    return None


def get_model_name_from_attrs(attributes: dict[str, Any]) -> str | None:
    """Get model name from attributes dict.

    Args:
        attributes: Span attributes

    Returns:
        Model name or None
    """
    model = attributes.get("llm.model_name")
    if model:
        return str(model)

    model = attributes.get("gen_ai.response.model")
    if model:
        return str(model)

    model = attributes.get("gen_ai.request.model")
    if model:
        return str(model)

    return None


def extract_usage(span: dict[str, Any]) -> ModelUsage | None:
    """Extract model usage from span attributes.

    Args:
        span: Phoenix span dictionary

    Returns:
        ModelUsage object or None
    """
    attributes = span.get("attributes") or {}

    # OpenInference token count attributes
    input_tokens = attributes.get("llm.token_count.prompt")
    output_tokens = attributes.get("llm.token_count.completion")

    # Fallback to gen_ai attributes
    if input_tokens is None:
        input_tokens = attributes.get("gen_ai.usage.input_tokens")
    if output_tokens is None:
        output_tokens = attributes.get("gen_ai.usage.output_tokens")

    if input_tokens is not None or output_tokens is not None:
        input_t = int(input_tokens) if input_tokens is not None else 0
        output_t = int(output_tokens) if output_tokens is not None else 0
        return ModelUsage(
            input_tokens=input_t,
            output_tokens=output_t,
            total_tokens=input_t + output_t,
        )

    return None


def extract_tools(span: dict[str, Any]) -> list[ToolInfo]:
    """Extract tool definitions from span attributes.

    OpenInference stores tools as:
    - llm.tools.0.tool.json_schema = '{"type": "function", "function": {...}}'

    Args:
        span: Phoenix span dictionary

    Returns:
        List of ToolInfo objects
    """
    tools: list[ToolInfo] = []
    attributes = span.get("attributes") or {}

    index = 0
    while True:
        schema_key = f"llm.tools.{index}.tool.json_schema"
        schema_str = attributes.get(schema_key)

        if schema_str is None:
            break

        tool_info = _parse_tool_schema(schema_str)
        if tool_info:
            tools.append(tool_info)

        index += 1

    return tools


def _parse_tool_schema(schema: Any) -> ToolInfo | None:
    """Parse a tool JSON schema into ToolInfo.

    Args:
        schema: Tool schema (string or dict)

    Returns:
        ToolInfo or None
    """
    if isinstance(schema, str):
        try:
            schema = json.loads(schema)
        except json.JSONDecodeError:
            return None

    if not isinstance(schema, dict):
        return None

    # Handle OpenAI format (nested under "function")
    func = schema.get("function", schema)
    if not isinstance(func, dict):
        return None

    name = func.get("name", "")
    if not name:
        return None

    params = func.get("parameters", {})
    properties = params.get("properties", {}) if isinstance(params, dict) else {}
    required = params.get("required", []) if isinstance(params, dict) else []

    # Normalize uppercase type strings (e.g. Google GenAI uses "STRING", "OBJECT")
    normalized_properties = {}
    for prop_name, prop_value in properties.items():
        if isinstance(prop_value, dict) and isinstance(prop_value.get("type"), str):
            prop_value = {**prop_value, "type": prop_value["type"].lower()}
        normalized_properties[prop_name] = prop_value

    return ToolInfo(
        name=str(name),
        description=str(func.get("description", "")),
        parameters=ToolParams(
            type="object",
            properties=normalized_properties,
            required=required,
        ),
    )


def sum_tokens(spans: list[dict[str, Any]]) -> int:
    """Sum tokens across all spans.

    Args:
        spans: List of Phoenix spans

    Returns:
        Total token count
    """
    total = 0
    for span in spans:
        attributes = span.get("attributes") or {}
        input_t = (
            attributes.get("llm.token_count.prompt")
            or attributes.get("gen_ai.usage.input_tokens")
            or 0
        )
        output_t = (
            attributes.get("llm.token_count.completion")
            or attributes.get("gen_ai.usage.output_tokens")
            or 0
        )
        total += int(input_t) + int(output_t)
    return total


def sum_latency(spans: list[dict[str, Any]]) -> float:
    """Sum latency across all spans.

    Calculates duration from start_time and end_time ISO strings.

    Args:
        spans: List of Phoenix spans

    Returns:
        Total latency in seconds
    """
    total = 0.0
    for span in spans:
        start_str = span.get("start_time")
        end_str = span.get("end_time")
        if start_str and end_str:
            try:
                start = datetime.fromisoformat(str(start_str).replace("Z", "+00:00"))
                end = datetime.fromisoformat(str(end_str).replace("Z", "+00:00"))
                total += (end - start).total_seconds()
            except (ValueError, TypeError):
                pass
    return total
