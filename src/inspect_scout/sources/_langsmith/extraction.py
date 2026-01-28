"""Input/output extraction for LangSmith data.

Uses inspect_ai conversion functions to convert provider-specific
message formats to ChatMessage objects:
- OpenAI: messages_from_openai(), model_output_from_openai()
- Anthropic: messages_from_anthropic(), model_output_from_anthropic()
- Google: messages_from_google(), model_output_from_google()
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
        inputs: Raw inputs from LangSmith run
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

            # Normalize messages for OpenAI converter
            messages = _normalize_openai_messages(messages)

            return await messages_from_openai(messages)  # type: ignore[arg-type]

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

            # Extract system instruction if present
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


def _normalize_openai_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Normalize messages for OpenAI converter.

    Handles quirks from various sources:
    - LangChain IDs in messages (langchain namespace)
    - Missing 'type' field in tool_calls
    - Nested message structures

    Args:
        messages: Raw message list

    Returns:
        Normalized message list for OpenAI converter
    """
    normalized = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # Skip None messages (some instrumentations produce these)
        if msg is None:
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
                            new_tc["function"] = {
                                "name": new_tc.pop("name"),
                                "arguments": new_tc.pop("arguments", "{}"),
                            }
                        normalized_calls.append(new_tc)
                new_msg["tool_calls"] = normalized_calls

        # Handle 'contents' (plural) as 'content'
        if "contents" in new_msg and "content" not in new_msg:
            new_msg["content"] = new_msg.pop("contents")

        normalized.append(new_msg)

    return normalized


async def extract_output(outputs: Any, run: Any, format_type: str) -> ModelOutput:
    """Extract output using format-appropriate converter.

    Args:
        outputs: Raw outputs from LangSmith run
        run: LangSmith run object (for usage data)
        format_type: Detected provider format

    Returns:
        ModelOutput object
    """
    from .detection import get_model_name

    model_name = get_model_name(run)

    if not outputs:
        return ModelOutput.from_content(model=model_name, content="")

    try:
        match format_type:
            case "openai":
                from inspect_ai.model import model_output_from_openai

                # OpenAI outputs have "choices" structure
                if isinstance(outputs, dict) and "choices" in outputs:
                    return await model_output_from_openai(outputs)

                # Handle LangChain-style outputs
                if isinstance(outputs, dict):
                    # Try to build OpenAI-compatible structure
                    generations = outputs.get("generations", [])
                    if generations and isinstance(generations[0], list):
                        # Flatten nested generations
                        first_gen = generations[0][0] if generations[0] else {}
                        text = first_gen.get("text", "")
                        return ModelOutput.from_content(model=model_name, content=text)

                # Fallback
                return ModelOutput.from_content(
                    model=model_name, content=_extract_text_content(outputs)
                )

            case "anthropic":
                from inspect_ai.model import model_output_from_anthropic

                return await model_output_from_anthropic(outputs)

            case "google":
                from inspect_ai.model import model_output_from_google

                return await model_output_from_google(outputs)

            case _:
                # Unknown format - extract text content
                content = _extract_text_content(outputs)
                output = ModelOutput.from_content(model=model_name, content=content)
                usage = extract_usage(run)
                if usage:
                    output.usage = usage
                return output

    except Exception as e:
        logger.warning(f"Failed to parse output: {e}, falling back to string")
        output = ModelOutput.from_content(
            model=model_name, content=_extract_text_content(outputs)
        )
        usage = extract_usage(run)
        if usage:
            output.usage = usage
        return output


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
        for key in ("content", "text", "output", "message"):
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

    return str(data)[:CONTENT_TRUNCATION_LIMIT]


def extract_usage(run: Any) -> ModelUsage | None:
    """Extract model usage from run object.

    Token counts can be in:
    - run.prompt_tokens, run.completion_tokens, run.total_tokens
    - run.outputs["usage"]

    Args:
        run: LangSmith run object

    Returns:
        ModelUsage object or None
    """
    prompt_tokens = getattr(run, "prompt_tokens", None)
    completion_tokens = getattr(run, "completion_tokens", None)
    total_tokens = getattr(run, "total_tokens", None)

    # Try run attributes first
    if prompt_tokens is not None or completion_tokens is not None:
        return ModelUsage(
            input_tokens=prompt_tokens or 0,
            output_tokens=completion_tokens or 0,
            total_tokens=total_tokens
            or ((prompt_tokens or 0) + (completion_tokens or 0)),
        )

    # Try outputs["usage"]
    outputs = getattr(run, "outputs", None) or {}
    if isinstance(outputs, dict):
        usage = outputs.get("usage", {})
        if isinstance(usage, dict):
            return ModelUsage(
                input_tokens=usage.get("prompt_tokens", 0)
                or usage.get("input_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0)
                or usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

    return None


def extract_tools(run: Any) -> list[ToolInfo]:
    """Extract tool definitions from run data.

    Tools can be in:
    - run.inputs["tools"] (OpenAI format)
    - run.inputs["functions"] (legacy OpenAI format)
    - run.extra["invocation_params"]["tools"] (LangChain)

    Args:
        run: LangSmith run object

    Returns:
        List of ToolInfo objects
    """
    tools: list[ToolInfo] = []
    inputs = getattr(run, "inputs", None) or {}
    extra = getattr(run, "extra", None) or {}

    # Try inputs["tools"] (OpenAI format)
    if isinstance(inputs, dict):
        input_tools = inputs.get("tools", [])
        if isinstance(input_tools, list):
            for tool in input_tools:
                tool_info = _parse_openai_tool(tool)
                if tool_info:
                    tools.append(tool_info)

        # Try inputs["functions"] (legacy format)
        if not tools:
            functions = inputs.get("functions", [])
            if isinstance(functions, list):
                for func in functions:
                    tool_info = _parse_function_def(func)
                    if tool_info:
                        tools.append(tool_info)

    # Try extra["invocation_params"]["tools"]
    if not tools and isinstance(extra, dict):
        invocation_params = extra.get("invocation_params", {})
        if isinstance(invocation_params, dict):
            inv_tools = invocation_params.get("tools", [])
            if isinstance(inv_tools, list):
                for tool in inv_tools:
                    tool_info = _parse_openai_tool(tool)
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


def _parse_function_def(func: Any) -> ToolInfo | None:
    """Parse legacy function definition format.

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


def sum_tokens(runs: list[Any]) -> int:
    """Sum tokens across all runs.

    Args:
        runs: List of LangSmith runs

    Returns:
        Total token count
    """
    total = 0
    for run in runs:
        prompt = getattr(run, "prompt_tokens", 0) or 0
        completion = getattr(run, "completion_tokens", 0) or 0
        total += prompt + completion
    return total


def sum_latency(runs: list[Any]) -> float:
    """Sum latency across all runs.

    Args:
        runs: List of LangSmith runs

    Returns:
        Total latency in seconds
    """
    total = 0.0
    for run in runs:
        start = getattr(run, "start_time", None)
        end = getattr(run, "end_time", None)
        if start and end:
            delta = (end - start).total_seconds()
            total += delta
    return total


def extract_metadata(run: Any) -> dict[str, Any]:
    """Extract metadata from root run for Scout transcript.

    Args:
        run: LangSmith run object

    Returns:
        Metadata dictionary
    """
    metadata: dict[str, Any] = {}

    # Basic run info
    if getattr(run, "name", None):
        metadata["name"] = run.name
    if getattr(run, "run_type", None):
        metadata["run_type"] = run.run_type
    if getattr(run, "tags", None):
        metadata["tags"] = run.tags

    # Extra metadata from run.extra
    extra = getattr(run, "extra", None) or {}
    if isinstance(extra, dict):
        run_metadata = extra.get("metadata", {})
        if isinstance(run_metadata, dict):
            metadata.update(run_metadata)

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
                # If parsing fails, return the original string
                return value
        else:
            return value
    else:
        return value
