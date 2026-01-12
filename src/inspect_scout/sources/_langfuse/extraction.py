"""Input/output extraction for LangFuse data."""

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

from .providers.anthropic import parse_json_content
from .providers.google import (
    parse_google_content_repr,
    parse_google_system_instruction,
    parse_google_tools_from_config,
)
from .providers.openai import (
    extract_otel_output,
    normalize_otel_messages_to_openai,
)

logger = getLogger(__name__)

# Content handling constants
CONTENT_TRUNCATION_LIMIT = 1000  # Max characters for fallback content truncation


async def extract_input_messages(
    input_data: Any, format_type: str
) -> list[ChatMessage]:
    """Extract input messages using format-appropriate converter.

    Args:
        input_data: Raw input data from LangFuse
        format_type: Detected provider format

    Returns:
        List of ChatMessage objects
    """
    # Handle string input regardless of detected format
    if isinstance(input_data, str):
        return [ChatMessageUser(content=input_data)]

    match format_type:
        case "openai_responses":
            from inspect_ai.model import messages_from_openai_responses

            # Responses API: input is a dict with "input" array containing the conversation
            if isinstance(input_data, dict) and "input" in input_data:
                input_items = input_data["input"]
            elif isinstance(input_data, list):
                input_items = input_data
            else:
                return []

            if not input_items:
                return []

            return await messages_from_openai_responses(input_items)
        case "openai":
            from inspect_ai.model import messages_from_openai

            messages = (
                input_data.get("messages", input_data)
                if isinstance(input_data, dict)
                else input_data
            )

            # Transform OTEL-normalized messages to proper OpenAI format
            # OTEL tool_calls lack 'type' field and use 'name' instead of 'function'
            # Also filters out None messages from some OTEL instrumentations
            messages = normalize_otel_messages_to_openai(messages)

            # Handle empty messages (e.g., OpenAI OTEL may not capture input)
            if not messages:
                return []

            return await messages_from_openai(messages)
        case "anthropic":
            from inspect_ai.model import messages_from_anthropic

            messages = (
                input_data.get("messages", input_data)
                if isinstance(input_data, dict)
                else input_data
            )
            system = input_data.get("system") if isinstance(input_data, dict) else None

            # Handle inline system message in list format (OpenTelemetry instrumentation)
            if isinstance(messages, list) and len(messages) > 0:
                first_msg = messages[0]
                if isinstance(first_msg, dict) and first_msg.get("role") == "system":
                    # Extract system from messages and remove it from the list
                    system = first_msg.get("content", "")
                    messages = messages[1:]

            # Parse JSON string content that contains tool_use/tool_result blocks
            # OTEL instrumentation may serialize Anthropic content blocks as JSON strings
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict) and "content" in msg:
                        msg["content"] = parse_json_content(msg["content"])

            return await messages_from_anthropic(messages, system)
        case "google":
            from inspect_ai.model import messages_from_google

            contents = (
                input_data.get("contents", input_data)
                if isinstance(input_data, dict)
                else input_data
            )

            # Handle string-serialized contents from Google OTEL instrumentation
            # The instrumentation uses repr() which produces strings like:
            # "parts=[Part(text='...')] role='user'"
            if isinstance(contents, list) and contents:
                if isinstance(contents[0], str) and "parts=" in contents[0]:
                    # Parse repr strings to ContentDict format
                    parsed_contents = []
                    for c in contents:
                        if isinstance(c, str):
                            parsed = parse_google_content_repr(c)
                            if parsed.get("parts"):
                                parsed_contents.append(parsed)
                    contents = parsed_contents

            # Extract system instruction
            system = None
            if isinstance(input_data, dict):
                # Try direct system_instruction field first
                si = input_data.get("system_instruction")
                if si:
                    if isinstance(si, list):
                        system = "\n".join(str(s) for s in si)
                    elif isinstance(si, str):
                        system = si

                # If not found, try parsing from config repr string
                if not system:
                    config = input_data.get("config")
                    if isinstance(config, str) and "system_instruction=" in config:
                        system = parse_google_system_instruction(config)

            return await messages_from_google(contents, system)
        case "string":
            return [ChatMessageUser(content=str(input_data))]
        case _:
            logger.warning(
                f"Unknown input format, creating simple message: {type(input_data)}"
            )
            return [
                ChatMessageUser(
                    content=str(input_data)[:CONTENT_TRUNCATION_LIMIT]
                    if input_data
                    else ""
                )
            ]


def extract_usage(gen: Any) -> ModelUsage | None:
    """Extract model usage from generation observation.

    Args:
        gen: LangFuse generation observation

    Returns:
        ModelUsage object or None
    """
    usage_details = getattr(gen, "usage_details", None)
    if not usage_details:
        return None

    return ModelUsage(
        input_tokens=usage_details.get("input", 0),
        output_tokens=usage_details.get("output", 0),
        total_tokens=usage_details.get("total", 0),
    )


def _build_tool_info(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> ToolInfo:
    """Build a ToolInfo object with consistent structure.

    Args:
        name: Tool name
        description: Tool description
        properties: Parameter properties dict
        required: List of required parameter names

    Returns:
        ToolInfo object
    """
    return ToolInfo(
        name=name,
        description=description,
        parameters=ToolParams(
            type="object",
            properties=properties or {},
            required=required or [],
        ),
    )


def _extract_native_openai_tools(input_data: dict[str, Any]) -> list[ToolInfo]:
    """Extract tools from native OpenAI format: gen.input['tools']."""
    tools: list[ToolInfo] = []
    input_tools = input_data.get("tools", [])
    if not isinstance(input_tools, list):
        return tools

    for tool in input_tools:
        if not isinstance(tool, dict):
            continue
        func = tool.get("function", {})
        if not isinstance(func, dict):
            continue
        name = func.get("name", "")
        if not name:
            continue
        params = func.get("parameters", {})
        props = params.get("properties", {}) if isinstance(params, dict) else {}
        req = params.get("required", []) if isinstance(params, dict) else []
        tools.append(_build_tool_info(name, func.get("description", ""), props, req))

    return tools


def _extract_google_tools(input_data: dict[str, Any]) -> list[ToolInfo]:
    """Extract tools from Google config format (serialized as string).

    Note: Only extracts name/description, not parameters (Schema is hard to parse).
    """
    tools: list[ToolInfo] = []
    config = input_data.get("config")
    if not isinstance(config, str) or "FunctionDeclaration" not in config:
        return tools

    for gt in parse_google_tools_from_config(config):
        tools.append(
            _build_tool_info(
                gt["name"],
                gt["description"],
                gt.get("properties"),
                gt.get("required"),
            )
        )
    return tools


def _extract_anthropic_otel_tools(attributes: dict[str, Any]) -> list[ToolInfo]:
    """Extract tools from Anthropic OTEL format: llm.request.functions.{N}.*"""
    tools: list[ToolInfo] = []
    i = 0
    while True:
        name = attributes.get(f"llm.request.functions.{i}.name")
        if name is None:
            break
        description = attributes.get(f"llm.request.functions.{i}.description", "")
        schema = attributes.get(f"llm.request.functions.{i}.input_schema", {})
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        req = schema.get("required", []) if isinstance(schema, dict) else []
        tools.append(_build_tool_info(name, description, props, req))
        i += 1
    return tools


def _extract_openai_otel_tools(attributes: dict[str, Any]) -> list[ToolInfo]:
    """Extract tools from OpenAI OTEL format: llm.tools.{N}.tool.json_schema"""
    tools: list[ToolInfo] = []
    i = 0
    while True:
        schema_raw = attributes.get(f"llm.tools.{i}.tool.json_schema")
        if schema_raw is None:
            break

        # Parse JSON schema if it's a string
        if isinstance(schema_raw, str):
            try:
                schema = json.loads(schema_raw)
            except json.JSONDecodeError:
                i += 1
                continue
        elif isinstance(schema_raw, dict):
            schema = schema_raw
        else:
            i += 1
            continue

        name = schema.get("name", "")
        if name:
            params = schema.get("parameters", {})
            props = params.get("properties", {}) if isinstance(params, dict) else {}
            req = params.get("required", []) if isinstance(params, dict) else []
            tools.append(
                _build_tool_info(name, schema.get("description", ""), props, req)
            )
        i += 1

    return tools


def extract_tools(gen: Any) -> list[ToolInfo]:
    """Extract tool definitions from generation data.

    Tools can be stored in multiple locations depending on the format:
    - Native OpenAI: gen.input['tools'] (list of tool definitions)
    - Native Google: gen.input['config'] (string with FunctionDeclaration)
    - Anthropic OTEL: metadata.attributes['llm.request.functions.{N}.*']
    - OpenAI OTEL: metadata.attributes['llm.tools.{N}.tool.json_schema']

    Args:
        gen: LangFuse generation observation

    Returns:
        List of ToolInfo objects
    """
    input_data = getattr(gen, "input", None)

    # Try native OpenAI format first
    if isinstance(input_data, dict):
        tools = _extract_native_openai_tools(input_data)
        if tools:
            return tools

        # Try Google config format
        tools = _extract_google_tools(input_data)
        if tools:
            return tools

    # Fall back to OTEL metadata attributes
    metadata = getattr(gen, "metadata", None)
    if not metadata:
        return []

    attributes = metadata.get("attributes", {}) if isinstance(metadata, dict) else {}
    if not attributes:
        return []

    # Try Anthropic OTEL format
    tools = _extract_anthropic_otel_tools(attributes)
    if tools:
        return tools

    # Try OpenAI OTEL format
    return _extract_openai_otel_tools(attributes)


async def extract_output(output_data: Any, gen: Any, format_type: str) -> ModelOutput:
    """Extract output using format-appropriate converter.

    Args:
        output_data: Raw output data from LangFuse
        gen: LangFuse generation observation (for usage data)
        format_type: Detected provider format

    Returns:
        ModelOutput object
    """
    model_name = gen.model or "unknown"

    if not output_data:
        return ModelOutput.from_content(model=model_name, content="")

    try:
        match format_type:
            case "openai_responses":
                from inspect_ai.model import model_output_from_openai_responses

                # OpenAI Responses API: output_data is the full Response object
                return await model_output_from_openai_responses(output_data)
            case "openai":
                from inspect_ai.model import model_output_from_openai

                # Handle OTEL-normalized format: output is a list with message dicts
                # This format doesn't match OpenAI schema, so handle it specially
                if isinstance(output_data, list) and len(output_data) > 0:
                    first = output_data[0]
                    if isinstance(first, dict) and "finish_reason" in first:
                        usage = extract_usage(gen)
                        return extract_otel_output(output_data, model_name, usage)

                return await model_output_from_openai(output_data)
            case "anthropic":
                from inspect_ai.model import model_output_from_anthropic

                return await model_output_from_anthropic(output_data)
            case "google":
                from inspect_ai.model import model_output_from_google

                return await model_output_from_google(output_data)
            case _:
                # Fallback: extract text content
                content: str
                if isinstance(output_data, dict):
                    raw_content = output_data.get(
                        "content", output_data.get("text", str(output_data))
                    )
                    if isinstance(raw_content, list) and raw_content:
                        # Try to extract text from content blocks
                        texts = []
                        for block in raw_content:
                            if isinstance(block, dict) and "text" in block:
                                texts.append(str(block["text"]))
                            elif isinstance(block, str):
                                texts.append(block)
                        content = "\n".join(texts) if texts else str(output_data)
                    elif isinstance(raw_content, str):
                        content = raw_content
                    else:
                        content = str(raw_content)
                elif isinstance(output_data, str):
                    content = output_data
                else:
                    content = str(output_data)

                output = ModelOutput.from_content(model=model_name, content=content)
                # Add usage if available
                usage = extract_usage(gen)
                if usage:
                    output.usage = usage
                return output
    except Exception as e:
        logger.warning(f"Failed to parse output: {e}, falling back to string")
        output = ModelOutput.from_content(
            model=model_name, content=str(output_data)[:CONTENT_TRUNCATION_LIMIT]
        )
        usage = extract_usage(gen)
        if usage:
            output.usage = usage
        return output


def sum_tokens(generations: list[Any]) -> int:
    """Sum tokens across all generations.

    Args:
        generations: List of generation observations

    Returns:
        Total token count
    """
    total = 0
    for g in generations:
        usage = getattr(g, "usage_details", None)
        if usage:
            total += usage.get("input", 0) + usage.get("output", 0)
    return total


def sum_latency(observations: list[Any]) -> float:
    """Sum latency across all observations.

    Args:
        observations: List of observations

    Returns:
        Total latency in seconds
    """
    total = 0.0
    for obs in observations:
        latency = getattr(obs, "latency", None)
        if latency:
            total += latency
    return total


def extract_metadata(trace: Any) -> dict[str, Any]:
    """Extract metadata from trace for Scout transcript.

    Args:
        trace: LangFuse trace object

    Returns:
        Metadata dictionary
    """
    if not trace:
        return {}

    metadata: dict[str, Any] = {}

    if getattr(trace, "user_id", None):
        metadata["user_id"] = trace.user_id
    if getattr(trace, "session_id", None):
        metadata["session_id"] = trace.session_id
    if getattr(trace, "name", None):
        metadata["name"] = trace.name
    if getattr(trace, "tags", None):
        metadata["tags"] = trace.tags
    if getattr(trace, "version", None):
        metadata["version"] = trace.version
    if getattr(trace, "release", None):
        metadata["release"] = trace.release
    if getattr(trace, "environment", None):
        metadata["environment"] = trace.environment

    # Include any custom metadata from the trace
    trace_metadata = getattr(trace, "metadata", None)
    if trace_metadata:
        metadata.update(trace_metadata)

    return metadata


def extract_json(field: str, metadata: dict[str, Any]) -> JsonValue | None:
    value = metadata.get(field, None)
    if isinstance(value, str) and len(value) > 0:
        del metadata[field]
        value_stripped = value.strip()
        if value_stripped[0] in ["{", "["]:
            return cast(JsonValue, json.loads(value))
        else:
            return value
    else:
        return value


def extract_bool(field: str, metadata: dict[str, Any]) -> bool | None:
    value = metadata.get(field, None)
    if value is not None:
        del metadata[field]
        return bool(value)
    else:
        return None


def extract_int(field: str, metadata: dict[str, Any]) -> int | None:
    value = metadata.get(field, None)
    if value is not None:
        del metadata[field]
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    else:
        return None


def extract_str(field: str, metadata: dict[str, Any]) -> str | None:
    value = metadata.get(field, None)
    if value is not None:
        del metadata[field]
        return str(value)
    else:
        return None


def extract_dict(field: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
    value = metadata.get(field, None)
    if isinstance(value, dict):
        del metadata[field]
        return value
    else:
        return None
