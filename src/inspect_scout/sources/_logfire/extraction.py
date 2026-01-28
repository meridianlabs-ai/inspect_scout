"""Input/output extraction for Logfire span data.

Uses inspect_ai conversion functions to convert provider-specific
message formats to ChatMessage objects.

OpenTelemetry GenAI semantic conventions store data in span attributes:
- gen_ai.prompt.{n}.role / gen_ai.prompt.{n}.content - Input messages
- gen_ai.completion.{n}.role / gen_ai.completion.{n}.content - Output
- gen_ai.tool.name, gen_ai.tool.call.id, gen_ai.tool.call.arguments - Tools
- gen_ai.usage.input_tokens, gen_ai.usage.output_tokens - Token usage

Messages may also be stored in logged events (span events).
"""

import json
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

from .detection import Instrumentor

logger = getLogger(__name__)

# Content handling constants
CONTENT_TRUNCATION_LIMIT = 1000  # Max characters for fallback content truncation


async def extract_input_messages(
    span: dict[str, Any], instrumentor: Instrumentor
) -> list[ChatMessage]:
    """Extract input messages from Logfire span.

    Messages can be stored in:
    1. Logfire request_data.messages (OpenAI, Anthropic instrumentation)
    2. Span events (gen_ai.user.message, gen_ai.system.message, etc.)
    3. Attributes (gen_ai.prompt.{n}.role, gen_ai.prompt.{n}.content)
    4. Attributes as JSON strings (gen_ai.input.messages)

    Args:
        span: Logfire span dictionary
        instrumentor: Detected instrumentor type

    Returns:
        List of ChatMessage objects
    """
    attributes = span.get("attributes") or {}
    events = span.get("otel_events") or []

    # Try Logfire request_data first (most common for direct SDK instrumentation)
    request_data = attributes.get("request_data")
    if request_data:
        if isinstance(request_data, str):
            try:
                request_data = json.loads(request_data)
            except json.JSONDecodeError:
                request_data = None

        if isinstance(request_data, dict):
            messages = request_data.get("messages") or request_data.get("contents")
            if messages and isinstance(messages, list):
                return await _convert_messages(messages, instrumentor)

    # Try events attribute (Google GenAI instrumentation)
    events_attr = attributes.get("events")
    if events_attr:
        messages = _extract_messages_from_google_events(events_attr)
        if messages:
            return await _convert_messages(messages, instrumentor)

    # Try to extract from events (newer OpenTelemetry GenAI convention)
    messages = _extract_messages_from_events(events, is_input=True)
    if messages:
        return await _convert_messages(messages, instrumentor)

    # Try to extract from indexed attributes (gen_ai.prompt.{n}.*)
    messages = _extract_indexed_messages(attributes, prefix="gen_ai.prompt")
    if messages:
        return await _convert_messages(messages, instrumentor)

    # Try JSON attribute (gen_ai.input.messages - Pydantic AI format)
    input_messages = attributes.get("gen_ai.input.messages")
    if input_messages:
        if isinstance(input_messages, str):
            try:
                input_messages = json.loads(input_messages)
            except json.JSONDecodeError:
                input_messages = None

        if isinstance(input_messages, list):
            # Normalize Pydantic AI format with 'parts' to standard format
            normalized = _normalize_pydantic_ai_messages(input_messages)
            return await _convert_messages(normalized, instrumentor)

    return []


def _normalize_pydantic_ai_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize Pydantic AI message format to standard OpenAI format.

    Pydantic AI stores messages as:
        {'role': 'system', 'parts': [{'type': 'text', 'content': '...'}]}

    Convert to standard format:
        {'role': 'system', 'content': '...'}

    Args:
        messages: Messages in Pydantic AI format

    Returns:
        Normalized messages in OpenAI format
    """
    normalized = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role", "user")
        parts = msg.get("parts")
        content = msg.get("content")

        # If content already exists at top level, use it
        if content is not None and not parts:
            normalized.append(msg)
            continue

        # Extract content from parts array
        if isinstance(parts, list):
            text_parts = []
            tool_calls = []

            for part in parts:
                if not isinstance(part, dict):
                    continue

                part_type = part.get("type", "text")

                if part_type == "text":
                    text_content = part.get("content", "")
                    if text_content:
                        text_parts.append(text_content)
                elif part_type == "tool_call":
                    tool_calls.append(
                        {
                            "id": part.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": part.get("name", ""),
                                "arguments": json.dumps(part.get("arguments", {})),
                            },
                        }
                    )
                elif part_type == "tool_result":
                    # Tool result message
                    normalized.append(
                        {
                            "role": "tool",
                            "tool_call_id": part.get("tool_call_id", ""),
                            "content": str(part.get("content", "")),
                        }
                    )
                    continue
                elif part_type == "tool_call_response":
                    # Pydantic AI tool response format (different keys)
                    # Has: id, name, result instead of tool_call_id, content
                    normalized.append(
                        {
                            "role": "tool",
                            "tool_call_id": part.get("id", ""),
                            "content": str(part.get("result", "")),
                        }
                    )
                    continue

            # Build the normalized message
            new_msg: dict[str, Any] = {"role": role}
            if text_parts:
                new_msg["content"] = " ".join(text_parts)
            elif role == "assistant":
                new_msg["content"] = ""  # Assistant can have empty content with tools

            if tool_calls:
                new_msg["tool_calls"] = tool_calls

            if new_msg.get("content") is not None or new_msg.get("tool_calls"):
                normalized.append(new_msg)
        else:
            # No parts, try to pass through
            normalized.append(msg)

    return normalized


def _extract_messages_from_events(
    events: list[dict[str, Any]], is_input: bool
) -> list[dict[str, Any]]:
    """Extract messages from OpenTelemetry span events.

    GenAI events follow naming pattern:
    - gen_ai.user.message, gen_ai.system.message (input)
    - gen_ai.assistant.message, gen_ai.choice (output)

    Args:
        events: List of span events
        is_input: True to extract input messages, False for output

    Returns:
        List of message dictionaries
    """
    messages: list[dict[str, Any]] = []

    input_event_names = {"gen_ai.user.message", "gen_ai.system.message"}
    output_event_names = {"gen_ai.assistant.message", "gen_ai.choice"}

    target_names = input_event_names if is_input else output_event_names

    for event in events:
        event_name = event.get("name", "")
        if event_name not in target_names:
            continue

        event_attrs = event.get("attributes", {})

        # Extract role and content
        role = event_attrs.get("role")
        if not role:
            # Infer role from event name
            if "user" in event_name:
                role = "user"
            elif "system" in event_name:
                role = "system"
            elif "assistant" in event_name or "choice" in event_name:
                role = "assistant"

        content = event_attrs.get("content", "")

        if role:
            messages.append({"role": role, "content": content})

    return messages


def _extract_messages_from_google_events(
    events_attr: str | list[Any],
) -> list[dict[str, Any]]:
    """Extract input messages from Google GenAI events attribute.

    Google GenAI instrumentation stores messages in an 'events' attribute as:
    [
        {"content": "...", "role": "user"},  # Input
        {"message": {"role": "assistant", "content": [...]}, ...}  # Output
    ]

    Args:
        events_attr: Events attribute (may be JSON string or list)

    Returns:
        List of input message dictionaries with 'role' and 'content'
    """
    if isinstance(events_attr, str):
        try:
            events_attr = json.loads(events_attr)
        except json.JSONDecodeError:
            return []

    if not isinstance(events_attr, list):
        return []

    messages: list[dict[str, Any]] = []

    for event in events_attr:
        if not isinstance(event, dict):
            continue

        # Check if this is an input message (has content and role at top level)
        role = event.get("role")
        content = event.get("content")

        if role and content and isinstance(content, str):
            # Direct input message format
            messages.append({"role": role, "content": content})

    return messages


def _extract_output_from_google_events(
    events_attr: str | list[Any],
) -> str:
    """Extract output content from Google GenAI events attribute.

    Google GenAI stores output in events like:
    {"message": {"role": "assistant", "content": [{"text": "..."}]}}

    Args:
        events_attr: Events attribute (may be JSON string or list)

    Returns:
        Extracted output text content
    """
    if isinstance(events_attr, str):
        try:
            events_attr = json.loads(events_attr)
        except json.JSONDecodeError:
            return ""

    if not isinstance(events_attr, list):
        return ""

    for event in events_attr:
        if not isinstance(event, dict):
            continue

        # Check if this is an output message (has 'message' nested structure)
        message = event.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                # Extract text from content parts
                texts = []
                for part in content:
                    if isinstance(part, dict):
                        text = part.get("text", "")
                        if text:
                            texts.append(text)
                if texts:
                    return " ".join(texts)
            elif isinstance(content, str):
                return content

    return ""


def _extract_indexed_messages(
    attributes: dict[str, Any], prefix: str
) -> list[dict[str, Any]]:
    """Extract messages from indexed attributes.

    OpenTelemetry GenAI stores messages as:
    - gen_ai.prompt.0.role, gen_ai.prompt.0.content
    - gen_ai.prompt.1.role, gen_ai.prompt.1.content
    - etc.

    Args:
        attributes: Span attributes dictionary
        prefix: Attribute prefix (e.g., "gen_ai.prompt" or "gen_ai.completion")

    Returns:
        List of message dictionaries
    """
    messages: list[dict[str, Any]] = []
    index = 0

    while True:
        role_key = f"{prefix}.{index}.role"
        content_key = f"{prefix}.{index}.content"

        role = attributes.get(role_key)
        content = attributes.get(content_key)

        if role is None and content is None:
            break

        messages.append(
            {
                "role": role or "user",
                "content": content or "",
            }
        )
        index += 1

    return messages


async def _convert_messages(
    messages: list[dict[str, Any]], instrumentor: Instrumentor
) -> list[ChatMessage]:
    """Convert message dictionaries to ChatMessage objects.

    Uses inspect_ai converters based on detected instrumentor.

    Args:
        messages: List of message dictionaries
        instrumentor: Detected instrumentor type

    Returns:
        List of ChatMessage objects
    """
    if not messages:
        return []

    # Determine format based on instrumentor
    match instrumentor:
        case Instrumentor.OPENAI | Instrumentor.LITELLM:
            from inspect_ai.model import messages_from_openai

            normalized = _normalize_openai_messages(messages)
            return await messages_from_openai(normalized)  # type: ignore[arg-type]

        case Instrumentor.ANTHROPIC:
            from inspect_ai.model import messages_from_anthropic

            system = None
            # Extract system message if first message
            if messages and messages[0].get("role") == "system":
                system = messages[0].get("content", "")
                messages = messages[1:]

            return await messages_from_anthropic(messages, system)  # type: ignore[arg-type]

        case Instrumentor.GOOGLE_GENAI:
            from inspect_ai.model import messages_from_google

            # Convert to Google format
            contents = _convert_to_google_contents(messages)
            system = None

            # Extract system message
            if messages and messages[0].get("role") == "system":
                system = messages[0].get("content", "")
                messages = messages[1:]
                contents = _convert_to_google_contents(messages)

            return await messages_from_google(contents, system)  # type: ignore[arg-type]

        case _:
            # Default: try OpenAI format
            try:
                from inspect_ai.model import messages_from_openai

                return await messages_from_openai(messages)  # type: ignore[arg-type]
            except Exception:
                # Fallback to simple conversion
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

        # Normalize tool_calls if present
        if "tool_calls" in new_msg:
            tool_calls = new_msg["tool_calls"]
            if isinstance(tool_calls, list):
                normalized_calls = []
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        new_tc = dict(tc)
                        # Add missing 'type' field
                        if "type" not in new_tc:
                            new_tc["type"] = "function"
                        # Normalize function structure
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


def _convert_to_google_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert messages to Google API format.

    Args:
        messages: List of message dictionaries

    Returns:
        List in Google contents format
    """
    contents = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Skip system messages (handled separately)
        if role == "system":
            continue

        # Map roles
        google_role = "model" if role == "assistant" else "user"

        parts: list[dict[str, Any]] = []
        if content:
            parts.append({"text": str(content)})
        else:
            parts.append({"text": ""})

        contents.append({"role": google_role, "parts": parts})

    return contents


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
        # Skip system messages in fallback

    return result


async def extract_output(
    span: dict[str, Any], instrumentor: Instrumentor
) -> ModelOutput:
    """Extract output from Logfire span.

    Args:
        span: Logfire span dictionary
        instrumentor: Detected instrumentor type

    Returns:
        ModelOutput object
    """
    from .detection import get_model_name

    attributes = span.get("attributes") or {}
    events = span.get("otel_events") or []
    model_name = get_model_name(span) or "unknown"

    # Try Logfire response_data first (most common for direct SDK instrumentation)
    response_data = attributes.get("response_data")
    if response_data:
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except json.JSONDecodeError:
                response_data = None

        if isinstance(response_data, dict):
            output = _extract_output_from_response_data(
                response_data, model_name, instrumentor
            )
            if output:
                usage = extract_usage(span)
                if usage:
                    output.usage = usage
                return output

    # Try Google GenAI events attribute
    events_attr = attributes.get("events")
    if events_attr:
        content = _extract_output_from_google_events(events_attr)
        if content:
            output = ModelOutput.from_content(model=model_name, content=content)
            usage = extract_usage(span)
            if usage:
                output.usage = usage
            return output

    # Try to extract from events
    messages = _extract_messages_from_events(events, is_input=False)
    if messages:
        content = messages[-1].get("content", "") if messages else ""
        tool_calls = _extract_tool_calls_from_attributes(attributes)

        if tool_calls:
            from inspect_ai.model._model_output import ChatCompletionChoice

            output = ModelOutput(
                model=model_name,
                choices=[
                    ChatCompletionChoice(
                        message=ChatMessageAssistant(
                            content=content,
                            tool_calls=tool_calls,
                        ),
                        stop_reason="tool_calls",
                    )
                ],
            )
        else:
            output = ModelOutput.from_content(model=model_name, content=content)

        usage = extract_usage(span)
        if usage:
            output.usage = usage
        return output

    # Try indexed attributes
    messages = _extract_indexed_messages(attributes, prefix="gen_ai.completion")
    if messages:
        content = messages[-1].get("content", "") if messages else ""
        output = ModelOutput.from_content(model=model_name, content=content)
        usage = extract_usage(span)
        if usage:
            output.usage = usage
        return output

    # Try gen_ai.output.messages (Pydantic AI format)
    output_messages = attributes.get("gen_ai.output.messages")
    if output_messages:
        if isinstance(output_messages, str):
            try:
                output_messages = json.loads(output_messages)
            except json.JSONDecodeError:
                output_messages = None

        if isinstance(output_messages, list) and output_messages:
            # Normalize Pydantic AI format with 'parts'
            normalized = _normalize_pydantic_ai_messages(output_messages)
            if normalized:
                last_msg = normalized[-1]
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
                                json.loads(args_str)
                                if isinstance(args_str, str)
                                else args_str
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
                    output = ModelOutput.from_content(
                        model=model_name, content=str(content)
                    )

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


def _extract_output_from_response_data(
    response_data: dict[str, Any], model_name: str, instrumentor: Instrumentor
) -> ModelOutput | None:
    """Extract ModelOutput from Logfire response_data attribute.

    Handles different formats:
    - OpenAI: response_data.message (single message dict)
    - OpenAI: response_data.choices (list of choices)
    - Anthropic: response_data.content (list of content blocks)

    Args:
        response_data: Parsed response_data dictionary
        model_name: Model name for output
        instrumentor: Detected instrumentor type

    Returns:
        ModelOutput or None
    """
    from inspect_ai.model._model_output import ChatCompletionChoice

    # OpenAI format: single message
    message = response_data.get("message")
    if isinstance(message, dict):
        content = message.get("content", "") or ""
        tool_calls_data = message.get("tool_calls")
        tool_calls = None

        if tool_calls_data and isinstance(tool_calls_data, list):
            tool_calls = []
            for tc in tool_calls_data:
                if isinstance(tc, dict):
                    tc_id = tc.get("id", "")
                    func = tc.get("function", {})
                    func_name = func.get("name", "") if isinstance(func, dict) else ""
                    args_str = (
                        func.get("arguments", "{}") if isinstance(func, dict) else "{}"
                    )
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else {}
                    except json.JSONDecodeError:
                        args = {}

                    tool_calls.append(
                        ToolCall(
                            id=str(tc_id),
                            function=str(func_name),
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
                        tool_calls=tool_calls if tool_calls else None,
                    ),
                    stop_reason="tool_calls" if tool_calls else "stop",
                )
            ],
        )

    # OpenAI format: choices array
    choices = response_data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            msg = choice.get("message", {})
            content = msg.get("content", "") or "" if isinstance(msg, dict) else ""
            return ModelOutput.from_content(model=model_name, content=str(content))

    # Anthropic format: content array
    content_blocks = response_data.get("content")
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

    return None


def _extract_tool_calls_from_attributes(
    attributes: dict[str, Any],
) -> list[ToolCall]:
    """Extract tool calls from span attributes.

    Args:
        attributes: Span attributes dictionary

    Returns:
        List of ToolCall objects
    """
    tool_calls: list[ToolCall] = []

    # Check for single tool call
    tool_name = attributes.get("gen_ai.tool.name")
    if tool_name:
        tool_id = attributes.get("gen_ai.tool.call.id", "")
        args = attributes.get("gen_ai.tool.call.arguments", {})

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        tool_calls.append(
            ToolCall(
                id=str(tool_id),
                function=str(tool_name),
                arguments=args if isinstance(args, dict) else {},
                type="function",
            )
        )

    # Check for indexed tool calls (gen_ai.tool.0.name, etc.)
    index = 0
    while True:
        name_key = f"gen_ai.tool.{index}.name"
        name = attributes.get(name_key)

        if name is None:
            break

        tool_id = attributes.get(f"gen_ai.tool.{index}.call.id", f"call_{index}")
        args = attributes.get(f"gen_ai.tool.{index}.call.arguments", {})

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        tool_calls.append(
            ToolCall(
                id=str(tool_id),
                function=str(name),
                arguments=args if isinstance(args, dict) else {},
                type="function",
            )
        )
        index += 1

    return tool_calls


def extract_usage(span: dict[str, Any]) -> ModelUsage | None:
    """Extract model usage from span attributes.

    Args:
        span: Logfire span dictionary

    Returns:
        ModelUsage object or None
    """
    attributes = span.get("attributes") or {}

    input_tokens = attributes.get("gen_ai.usage.input_tokens")
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

    Args:
        span: Logfire span dictionary

    Returns:
        List of ToolInfo objects
    """
    tools: list[ToolInfo] = []
    attributes = span.get("attributes") or {}

    # Check for tool definitions in gen_ai.tool.definitions
    tool_defs = attributes.get("gen_ai.tool.definitions")
    if tool_defs:
        if isinstance(tool_defs, str):
            try:
                tool_defs = json.loads(tool_defs)
            except json.JSONDecodeError:
                tool_defs = None

        if isinstance(tool_defs, list):
            for tool_def in tool_defs:
                tool_info = _parse_tool_definition(tool_def)
                if tool_info:
                    tools.append(tool_info)

    return tools


def _parse_tool_definition(tool_def: Any) -> ToolInfo | None:
    """Parse a tool definition.

    Args:
        tool_def: Tool definition dict (OpenAI format)

    Returns:
        ToolInfo or None
    """
    if not isinstance(tool_def, dict):
        return None

    # Handle OpenAI format (nested under "function")
    func = tool_def.get("function", tool_def)
    if not isinstance(func, dict):
        return None

    name = func.get("name", "")
    if not name:
        return None

    params = func.get("parameters", {})
    properties = params.get("properties", {}) if isinstance(params, dict) else {}
    required = params.get("required", []) if isinstance(params, dict) else []

    return ToolInfo(
        name=str(name),
        description=str(func.get("description", "")),
        parameters=ToolParams(
            type="object",
            properties=properties,
            required=required,
        ),
    )


def sum_tokens(spans: list[dict[str, Any]]) -> int:
    """Sum tokens across all spans.

    Args:
        spans: List of Logfire spans

    Returns:
        Total token count
    """
    total = 0
    for span in spans:
        attributes = span.get("attributes") or {}
        input_t = attributes.get("gen_ai.usage.input_tokens", 0) or 0
        output_t = attributes.get("gen_ai.usage.output_tokens", 0) or 0
        total += int(input_t) + int(output_t)
    return total


def sum_latency(spans: list[dict[str, Any]]) -> float:
    """Sum latency across all spans.

    Args:
        spans: List of Logfire spans

    Returns:
        Total latency in seconds
    """
    total = 0.0
    for span in spans:
        duration = span.get("duration")
        if duration is not None:
            total += float(duration)
    return total
