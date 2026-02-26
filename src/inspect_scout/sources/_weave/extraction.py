"""Input/output extraction for W&B Weave data.

Uses inspect_ai conversion functions to convert provider-specific
message formats to ChatMessage objects.
"""

import json
from logging import getLogger
from typing import Any, cast

from inspect_ai.model import ModelOutput
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageUser,
)
from inspect_ai.model._model_output import ModelUsage
from inspect_ai.tool import ToolInfo, ToolParams
from pydantic import JsonValue

logger = getLogger(__name__)

# Content handling constants
CONTENT_TRUNCATION_LIMIT = 1000  # Max characters for fallback content truncation


async def extract_input_messages(inputs: Any, format_type: str) -> list[ChatMessage]:
    """Extract input messages using format-appropriate converter.

    Args:
        inputs: Raw inputs from Weave call
        format_type: Detected provider format

    Returns:
        List of ChatMessage objects
    """
    # Handle string input regardless of detected format
    if isinstance(inputs, str):
        return [ChatMessageUser(content=inputs)]

    if not isinstance(inputs, dict):
        return [ChatMessageUser(content=str(inputs)[:CONTENT_TRUNCATION_LIMIT])]

    match format_type:
        case "openai":
            from inspect_ai.model import messages_from_openai

            messages = inputs.get("messages", [])
            if not messages:
                return []

            return await messages_from_openai(messages)

        case "anthropic":
            from inspect_ai.model import messages_from_anthropic

            messages = inputs.get("messages", [])
            system = inputs.get("system")

            # Handle system message in first position (common pattern)
            if isinstance(messages, list) and messages:
                first_msg = messages[0]
                if isinstance(first_msg, dict) and first_msg.get("role") == "system":
                    system = first_msg.get("content", "")
                    messages = messages[1:]

            return await messages_from_anthropic(messages, system)

        case "google":
            from inspect_ai.model import messages_from_google

            contents = inputs.get("contents", [])
            system = None

            # Extract system instruction
            system_instruction = inputs.get("system_instruction")
            if system_instruction:
                if isinstance(system_instruction, list):
                    system = "\n".join(str(s) for s in system_instruction)
                elif isinstance(system_instruction, str):
                    system = system_instruction

            return await messages_from_google(contents, system)

        case _:
            # Unknown format - try OpenAI as default (most common)
            messages = inputs.get("messages", [])
            if messages:
                try:
                    from inspect_ai.model import messages_from_openai

                    return await messages_from_openai(messages)
                except Exception as e:
                    logger.warning(f"Failed to parse messages as OpenAI: {e}")

            # Fallback to simple string extraction
            return [
                ChatMessageUser(
                    content=str(inputs)[:CONTENT_TRUNCATION_LIMIT] if inputs else ""
                )
            ]


async def extract_output(output: Any, call: Any, format_type: str) -> ModelOutput:
    """Extract output using format-appropriate converter.

    Args:
        output: Raw output from Weave call
        call: Weave call object (for usage data)
        format_type: Detected provider format

    Returns:
        ModelOutput object
    """
    from .detection import get_model_name

    model_name = get_model_name(call)

    if not output:
        return ModelOutput.from_content(model=model_name, content="")

    try:
        match format_type:
            case "openai":
                from inspect_ai.model import model_output_from_openai

                # OpenAI outputs have "choices" structure
                if isinstance(output, dict) and "choices" in output:
                    return await model_output_from_openai(output)

                # Fallback
                return ModelOutput.from_content(
                    model=model_name, content=_extract_text_content(output)
                )

            case "anthropic":
                from inspect_ai.model import model_output_from_anthropic

                return await model_output_from_anthropic(output)

            case "google":
                from inspect_ai.model import model_output_from_google

                return await model_output_from_google(output)

            case _:
                # Unknown format - extract text content
                content = _extract_text_content(output)
                result = ModelOutput.from_content(model=model_name, content=content)
                usage = extract_usage(call)
                if usage:
                    result.usage = usage
                return result

    except Exception as e:
        logger.warning(f"Failed to parse output: {e}, falling back to string")
        result = ModelOutput.from_content(
            model=model_name, content=_extract_text_content(output)
        )
        usage = extract_usage(call)
        if usage:
            result.usage = usage
        return result


def _extract_text_content(data: Any) -> str:
    """Extract text content from various output formats.

    Args:
        data: Output data in various formats

    Returns:
        Extracted text content
    """
    if isinstance(data, str):
        return data[:CONTENT_TRUNCATION_LIMIT]

    if isinstance(data, dict):
        # Try common content keys
        for key in ("content", "text", "output", "message", "result"):
            if key in data:
                value = data[key]
                if isinstance(value, str):
                    return value[:CONTENT_TRUNCATION_LIMIT]
                if isinstance(value, list) and value:
                    # Handle content blocks
                    texts = []
                    for block in value:
                        if isinstance(block, dict) and "text" in block:
                            texts.append(str(block["text"]))
                        elif isinstance(block, str):
                            texts.append(block)
                    if texts:
                        return "\n".join(texts)[:CONTENT_TRUNCATION_LIMIT]

        # Try nested message structure
        if "message" in data:
            msg = data["message"]
            if isinstance(msg, dict) and "content" in msg:
                return str(msg["content"])[:CONTENT_TRUNCATION_LIMIT]

        # Try choices (OpenAI format)
        if "choices" in data:
            choices = data["choices"]
            if isinstance(choices, list) and choices:
                first_choice = choices[0]
                if isinstance(first_choice, dict):
                    msg = first_choice.get("message", {})
                    if isinstance(msg, dict):
                        return str(msg.get("content", ""))[:CONTENT_TRUNCATION_LIMIT]

    return str(data)[:CONTENT_TRUNCATION_LIMIT]


def extract_usage(call: Any) -> ModelUsage | None:
    """Extract model usage from call object.

    Token counts can be in:
    - call.summary["usage"]
    - call.output["usage"]
    - call.attributes["usage"]

    Args:
        call: Weave call object

    Returns:
        ModelUsage object or None
    """
    # Try summary first
    summary = getattr(call, "summary", None)
    if isinstance(summary, dict):
        usage = summary.get("usage", {})
        if isinstance(usage, dict) and usage:
            return _parse_usage_dict(usage)

    # Try output
    output = getattr(call, "output", None)
    if isinstance(output, dict):
        usage = output.get("usage", {})
        if isinstance(usage, dict) and usage:
            return _parse_usage_dict(usage)

    # Try attributes
    attrs = getattr(call, "attributes", None)
    if isinstance(attrs, dict):
        usage = attrs.get("usage", {})
        if isinstance(usage, dict) and usage:
            return _parse_usage_dict(usage)

    return None


def _parse_usage_dict(usage: dict[str, Any]) -> ModelUsage:
    """Parse a usage dictionary into ModelUsage.

    Args:
        usage: Dictionary with token counts

    Returns:
        ModelUsage object
    """
    return ModelUsage(
        input_tokens=usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0)
        or usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
    )


def extract_tools(call: Any) -> list[ToolInfo]:
    """Extract tool definitions from call data.

    Args:
        call: Weave call object

    Returns:
        List of ToolInfo objects
    """
    tools: list[ToolInfo] = []
    inputs = getattr(call, "inputs", None) or {}

    if not isinstance(inputs, dict):
        return tools

    # Try inputs["tools"] (OpenAI format)
    input_tools = inputs.get("tools", [])
    if isinstance(input_tools, list):
        for tool in input_tools:
            tool_info = _parse_openai_tool(tool)
            if tool_info:
                tools.append(tool_info)

    # Try inputs["functions"] (legacy OpenAI format)
    if not tools:
        input_functions = inputs.get("functions", [])
        if isinstance(input_functions, list):
            for func in input_functions:
                tool_info = _parse_legacy_function(func)
                if tool_info:
                    tools.append(tool_info)

    return tools


def _parse_openai_tool(tool: Any) -> ToolInfo | None:
    """Parse OpenAI tool format.

    Args:
        tool: Tool definition dict

    Returns:
        ToolInfo or None
    """
    if not isinstance(tool, dict):
        return None

    func = tool.get("function", {})
    if not isinstance(func, dict):
        return None

    name = func.get("name", "")
    if not name:
        return None

    params = func.get("parameters", {})
    properties = params.get("properties", {}) if isinstance(params, dict) else {}
    required = params.get("required", []) if isinstance(params, dict) else []

    return ToolInfo(
        name=name,
        description=func.get("description", ""),
        parameters=ToolParams(
            type="object",
            properties=properties,
            required=required,
        ),
    )


def _parse_legacy_function(func: Any) -> ToolInfo | None:
    """Parse legacy OpenAI function format.

    Args:
        func: Function definition dict

    Returns:
        ToolInfo or None
    """
    if not isinstance(func, dict):
        return None

    name = func.get("name", "")
    if not name:
        return None

    params = func.get("parameters", {})
    properties = params.get("properties", {}) if isinstance(params, dict) else {}
    required = params.get("required", []) if isinstance(params, dict) else []

    return ToolInfo(
        name=name,
        description=func.get("description", ""),
        parameters=ToolParams(
            type="object",
            properties=properties,
            required=required,
        ),
    )


def sum_tokens(calls: list[Any]) -> int:
    """Sum tokens across all calls.

    Args:
        calls: List of Weave calls

    Returns:
        Total token count
    """
    total = 0
    for call in calls:
        usage = extract_usage(call)
        if usage:
            total += usage.total_tokens
    return total


def sum_latency(calls: list[Any]) -> float:
    """Sum latency across all calls.

    Args:
        calls: List of Weave calls

    Returns:
        Total latency in seconds
    """
    total = 0.0
    for call in calls:
        started_at = getattr(call, "started_at", None)
        ended_at = getattr(call, "ended_at", None)
        if started_at and ended_at:
            delta = (ended_at - started_at).total_seconds()
            total += delta
    return total


def extract_metadata(call: Any) -> dict[str, Any]:
    """Extract metadata from call for Scout transcript.

    Args:
        call: Weave call object

    Returns:
        Metadata dictionary
    """
    metadata: dict[str, Any] = {}

    # Basic call info
    if getattr(call, "op_name", None):
        metadata["op_name"] = call.op_name
    if getattr(call, "display_name", None):
        metadata["display_name"] = call.display_name

    # Attributes
    attrs = getattr(call, "attributes", None) or {}
    if isinstance(attrs, dict):
        metadata.update(attrs)

    return metadata


def extract_str(field: str, metadata: dict[str, Any]) -> str | None:
    """Extract and remove a string field from metadata."""
    value = metadata.get(field, None)
    if value is not None:
        del metadata[field]
        return str(value)
    return None


def extract_int(field: str, metadata: dict[str, Any]) -> int | None:
    """Extract and remove an integer field from metadata."""
    value = metadata.get(field, None)
    if value is not None:
        del metadata[field]
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    return None


def extract_bool(field: str, metadata: dict[str, Any]) -> bool | None:
    """Extract and remove a boolean field from metadata."""
    value = metadata.get(field, None)
    if value is not None:
        del metadata[field]
        return bool(value)
    return None


def extract_dict(field: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Extract and remove a dict field from metadata."""
    value = metadata.get(field, None)
    if isinstance(value, dict):
        del metadata[field]
        return value
    return None


def extract_json(field: str, metadata: dict[str, Any]) -> JsonValue | None:
    """Extract and remove a JSON field from metadata."""
    value = metadata.get(field, None)
    if isinstance(value, str) and len(value) > 0:
        del metadata[field]
        value_stripped = value.strip()
        if value_stripped and value_stripped[0] in ("{", "["):
            try:
                return cast(JsonValue, json.loads(value))
            except json.JSONDecodeError:
                return value
        else:
            return value
    else:
        return value
