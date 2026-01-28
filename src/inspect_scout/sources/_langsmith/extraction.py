"""Input/output extraction for LangSmith data.

Uses inspect_ai conversion functions to convert provider-specific
message formats to ChatMessage objects.

Observed input patterns:
- Raw OpenAI/Anthropic: inputs.messages with standard {role, content} dicts
- LangChain (all providers): inputs.messages with serialized {id, kwargs, lc, type} format

Observed output patterns:
- Raw OpenAI: outputs.choices (native format)
- Raw Anthropic: outputs.message (native format)
- LangChain (all providers): outputs.generations (LLMResult format)
"""

import json
from logging import getLogger
from typing import Any, cast

from inspect_ai.model import ModelOutput
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
)
from inspect_ai.model._model_output import ModelUsage
from inspect_ai.tool import ToolCall, ToolInfo, ToolParams
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

            # Convert LangChain serialized format if detected
            if _is_langchain_serialized(messages):
                messages = _convert_langchain_messages(messages, for_anthropic=True)

            # Handle system message in first position (common pattern)
            if isinstance(messages, list) and messages:
                first_msg = messages[0]
                if isinstance(first_msg, dict) and first_msg.get("role") == "system":
                    system = first_msg.get("content", "")
                    messages = messages[1:]

            return await messages_from_anthropic(messages, system)

        case "google":
            from inspect_ai.model import messages_from_google

            # Native Google format uses "contents" - currently not observed in traces
            # since google.genai has no LangSmith wrapper. All Google traces come
            # through LangChain which uses "messages" in serialized format.
            contents = inputs.get("contents", [])
            system = None

            # Handle LangChain format (the only format we currently observe)
            if not contents:
                messages = inputs.get("messages", [])
                if _is_langchain_serialized(messages):
                    # Convert LangChain format to standard messages
                    converted = _convert_langchain_messages(messages)
                    # Extract system message
                    if converted and converted[0].get("role") == "system":
                        system = converted[0].get("content", "")
                        converted = converted[1:]
                    # Convert to Google "contents" format
                    contents = []
                    for msg in converted:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        tool_calls = msg.get("tool_calls", [])

                        # Handle content that might be a list (e.g., tool_use blocks)
                        if isinstance(content, list):
                            # Extract text from content blocks or use empty string
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict) and "text" in block:
                                    text_parts.append(str(block["text"]))
                                elif isinstance(block, str):
                                    text_parts.append(block)
                            content = "\n".join(text_parts) if text_parts else ""

                        # Map roles to Google format
                        if role == "assistant":
                            google_role = "model"
                            parts: list[dict[str, Any]] = []
                            if content:
                                parts.append({"text": content})
                            # Add function_call parts for tool_calls
                            for tc in tool_calls:
                                if isinstance(tc, dict):
                                    args = tc.get("args", {})
                                    if isinstance(args, str):
                                        try:
                                            args = json.loads(args)
                                        except json.JSONDecodeError:
                                            args = {}
                                    parts.append(
                                        {
                                            "function_call": {
                                                "name": tc.get("name", ""),
                                                "args": args,
                                            }
                                        }
                                    )
                            if not parts:
                                parts.append({"text": ""})
                            contents.append({"role": google_role, "parts": parts})
                        elif role == "tool":
                            # Google uses "user" role with function_response for tool results
                            tool_name = msg.get("name", "")
                            # Try to parse content as JSON for structured response
                            response_data: dict[str, Any]
                            if isinstance(content, str):
                                try:
                                    response_data = json.loads(content)
                                except json.JSONDecodeError:
                                    response_data = {"result": content}
                            elif isinstance(content, dict):
                                response_data = content
                            else:
                                response_data = {"result": str(content)}
                            contents.append(
                                {
                                    "role": "user",
                                    "parts": [
                                        {
                                            "function_response": {
                                                "name": tool_name,
                                                "response": response_data,
                                            }
                                        }
                                    ],
                                }
                            )
                        else:
                            # user or system (system already extracted above)
                            contents.append(
                                {"role": "user", "parts": [{"text": content}]}
                            )

            # Extract system instruction (native Google format - not currently observed)
            if not system:
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


def _is_langchain_serialized(messages: Any) -> bool:
    """Check if messages are in LangChain serialization format.

    LangChain serializes messages with structure like:
    [[{'id': ['langchain', ...], 'kwargs': {...}, 'lc': 1, 'type': 'constructor'}]]

    Args:
        messages: Raw messages from inputs

    Returns:
        True if messages appear to be LangChain serialized
    """
    if not isinstance(messages, list) or not messages:
        return False

    # Check for nested list structure [[...]]
    first = messages[0]
    if isinstance(first, list) and first:
        first = first[0]

    # Check for LangChain serialization markers
    if isinstance(first, dict):
        return "lc" in first and "kwargs" in first and "type" in first

    return False


def _convert_langchain_messages(
    messages: list[Any], for_anthropic: bool = False
) -> list[dict[str, Any]]:
    """Convert LangChain serialized messages to standard format.

    Converts from LangChain format:
    [[{'id': [...], 'kwargs': {'content': '...', 'type': 'system'}, 'lc': 1, 'type': 'constructor'}]]

    To standard format:
    [{'role': 'system', 'content': '...'}]

    Args:
        messages: LangChain serialized messages
        for_anthropic: If True, convert tool messages to Anthropic's tool_result format

    Returns:
        List of messages in standard format
    """
    # Unwrap nested list if present
    if messages and isinstance(messages[0], list):
        messages = messages[0]

    result = []
    pending_tool_results: list[dict[str, Any]] = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # Check if this is LangChain serialized format
        if "kwargs" in msg and "lc" in msg:
            kwargs = msg.get("kwargs", {})
            msg_type = kwargs.get("type", "")

            # Map LangChain types to roles
            role_map = {
                "system": "system",
                "human": "user",
                "ai": "assistant",
                "tool": "tool",
            }
            role = role_map.get(msg_type, "user")

            # Handle tool messages for Anthropic format
            if role == "tool" and for_anthropic:
                # Collect tool results to bundle into a user message
                tool_result: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": kwargs.get("tool_call_id", ""),
                    "content": kwargs.get("content", ""),
                }
                pending_tool_results.append(tool_result)
                continue

            # Flush any pending tool results before non-tool message
            if pending_tool_results and role != "tool":
                result.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []

            converted: dict[str, Any] = {"role": role}

            # Extract content
            content = kwargs.get("content")
            if content is not None:
                converted["content"] = content

            # Extract tool_calls for assistant messages
            if role == "assistant" and "tool_calls" in kwargs:
                converted["tool_calls"] = kwargs["tool_calls"]

            # Extract tool_call_id for tool messages (non-Anthropic)
            if role == "tool" and not for_anthropic:
                if "tool_call_id" in kwargs:
                    converted["tool_call_id"] = kwargs["tool_call_id"]
                if "name" in kwargs:
                    converted["name"] = kwargs["name"]

            result.append(converted)
        else:
            # Flush any pending tool results
            if pending_tool_results:
                result.append({"role": "user", "content": pending_tool_results})
                pending_tool_results = []
            # Not LangChain format, pass through
            result.append(msg)

    # Flush any remaining tool results
    if pending_tool_results:
        result.append({"role": "user", "content": pending_tool_results})

    return result


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
    # First convert LangChain format if detected
    if _is_langchain_serialized(messages):
        messages = _convert_langchain_messages(messages)

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
                        # Add missing 'type' field (OpenAI uses 'function', not 'tool_call')
                        if new_tc.get("type") == "tool_call":
                            new_tc["type"] = "function"
                        elif "type" not in new_tc:
                            new_tc["type"] = "function"
                        # Normalize function structure
                        if "function" not in new_tc and "name" in new_tc:
                            # Handle LangChain 'args' (dict) vs OpenAI 'arguments' (JSON string)
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


def _extract_langchain_output(
    outputs: dict[str, Any], model_name: str, run: Any
) -> ModelOutput:
    """Extract output from LangChain LLMResult format.

    LangChain outputs look like:
    {
        'generations': [[{'text': '...', 'message': {...}, 'type': 'ChatGeneration'}]],
        'llm_output': {},
        'type': 'LLMResult'
    }

    The message.kwargs may contain tool_calls for function calling.

    Args:
        outputs: LangChain LLMResult dict
        model_name: Model name for output
        run: LangSmith run object (for usage data)

    Returns:
        ModelOutput object
    """
    from inspect_ai.model._model_output import ChatCompletionChoice, StopReason

    generations = outputs.get("generations", [])
    content = ""
    tool_calls: list[ToolCall] = []
    stop_reason: StopReason = "stop"

    if generations and isinstance(generations[0], list) and generations[0]:
        first_gen = generations[0][0]
        if isinstance(first_gen, dict):
            # Try to get text directly
            content = first_gen.get("text", "")

            # Extract from message for more details
            message = first_gen.get("message", {})
            if isinstance(message, dict):
                kwargs = message.get("kwargs", {})
                if isinstance(kwargs, dict):
                    # If no text content, try message content
                    if not content:
                        msg_content = kwargs.get("content", "")
                        if isinstance(msg_content, str):
                            content = msg_content
                        elif isinstance(msg_content, list):
                            # Handle content blocks (may be tool_use blocks)
                            text_parts = []
                            for block in msg_content:
                                if isinstance(block, dict):
                                    if block.get("type") == "text" or "text" in block:
                                        text_parts.append(str(block.get("text", "")))
                                elif isinstance(block, str):
                                    text_parts.append(block)
                            content = "\n".join(text_parts)

                    # Extract tool calls
                    lc_tool_calls = kwargs.get("tool_calls", [])
                    if isinstance(lc_tool_calls, list):
                        for tc in lc_tool_calls:
                            if isinstance(tc, dict):
                                tool_calls.append(
                                    ToolCall(
                                        id=tc.get("id", ""),
                                        function=tc.get("name", ""),
                                        arguments=tc.get("args", {}),
                                        type="function",
                                    )
                                )

                    # Google/Gemini uses function_call in additional_kwargs
                    if not tool_calls:
                        additional_kwargs = kwargs.get("additional_kwargs", {})
                        if isinstance(additional_kwargs, dict):
                            func_call = additional_kwargs.get("function_call")
                            if isinstance(func_call, dict):
                                # Parse arguments - may be JSON string
                                args = func_call.get("arguments", "{}")
                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except json.JSONDecodeError:
                                        args = {}
                                tc_id = kwargs.get("id", "") or ""
                                tool_calls.append(
                                    ToolCall(
                                        id=tc_id,
                                        function=func_call.get("name", ""),
                                        arguments=args,
                                        type="function",
                                    )
                                )

                    # Extract stop reason
                    response_metadata = kwargs.get("response_metadata", {})
                    if isinstance(response_metadata, dict):
                        raw_stop = response_metadata.get(
                            "stop_reason"
                        ) or response_metadata.get("finish_reason", "")
                        if raw_stop in ("tool_use", "tool_calls", "function_call"):
                            stop_reason = "tool_calls"
                        elif raw_stop in ("end_turn", "stop", "STOP"):
                            stop_reason = "stop"

    # Build output with tool calls if present
    if tool_calls:
        output = ModelOutput(
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessageAssistant(
                        content=content,
                        tool_calls=tool_calls,
                    ),
                    stop_reason=stop_reason,
                )
            ],
        )
    else:
        output = ModelOutput.from_content(model=model_name, content=content)

    usage = extract_usage(run)
    if usage:
        output.usage = usage
    return output


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

                # Handle LangChain-style outputs (LLMResult format)
                if isinstance(outputs, dict) and "generations" in outputs:
                    return _extract_langchain_output(outputs, model_name, run)

                # Fallback
                return ModelOutput.from_content(
                    model=model_name, content=_extract_text_content(outputs)
                )

            case "anthropic":
                from inspect_ai.model import model_output_from_anthropic

                # Handle LangChain-style outputs (LLMResult format)
                if isinstance(outputs, dict) and "generations" in outputs:
                    return _extract_langchain_output(outputs, model_name, run)

                return await model_output_from_anthropic(outputs)

            case "google":
                from inspect_ai.model import model_output_from_google

                # Handle LangChain-style outputs (LLMResult format)
                if isinstance(outputs, dict) and "generations" in outputs:
                    return _extract_langchain_output(outputs, model_name, run)

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

    Observed patterns:
    - Raw traces: inputs["tools"] (OpenAI format)
    - Legacy traces: inputs["functions"] (legacy OpenAI format)
    - LangChain traces: extra["invocation_params"]["tools"]

    Args:
        run: LangSmith run object

    Returns:
        List of ToolInfo objects
    """
    tools: list[ToolInfo] = []
    inputs = getattr(run, "inputs", None) or {}
    extra = getattr(run, "extra", None) or {}

    # Try inputs["tools"] (modern OpenAI format)
    if isinstance(inputs, dict):
        input_tools = inputs.get("tools", [])
        if isinstance(input_tools, list):
            for tool in input_tools:
                tool_info = _parse_openai_tool(tool)
                if tool_info:
                    tools.append(tool_info)

    # Try inputs["functions"] (legacy OpenAI format)
    if not tools and isinstance(inputs, dict):
        input_functions = inputs.get("functions", [])
        if isinstance(input_functions, list):
            for func in input_functions:
                tool_info = _parse_legacy_function(func)
                if tool_info:
                    tools.append(tool_info)

    # Try extra["invocation_params"]["tools"] (LangChain traces)
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


def _parse_legacy_function(func: Any) -> ToolInfo | None:
    """Parse legacy OpenAI function format.

    Legacy format has name/description/parameters directly on the object,
    not nested under a "function" key.

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
