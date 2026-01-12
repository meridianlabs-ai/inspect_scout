"""Provider format detection for LangFuse data."""

from typing import Any

from .providers.anthropic import has_anthropic_tool_blocks, parse_json_content


def detect_provider_format(gen: Any) -> str:
    """Detect the provider format from generation data.

    Detection priority:
    1. OpenAI Responses API: input has "input" key with typed messages
    2. Native OpenAI Chat Completions: output has "choices"
    3. Native Google: output has "candidates" OR input has "contents"
    4. OTEL-normalized: output is list with finish_reason (returns "openai")
    5. Anthropic content blocks: messages contain tool_use/tool_result blocks
    6. Model name hints as fallback

    Note: Anthropic OTEL instrumentation may produce OpenAI-like structure but with
    Anthropic-style content blocks (tool_use, tool_result). We detect these and
    return "anthropic" to ensure proper message conversion.

    Args:
        gen: LangFuse generation observation

    Returns:
        Format string: "openai_responses", "openai", "google", "anthropic",
            "string", or "unknown"
    """
    input_data = gen.input
    output_data = gen.output
    model = gen.model or ""
    model_lower = model.lower()

    # 1. Check for OpenAI Responses API format (special case)
    # Input: {"input": [{"type": "message", ...}]}
    if isinstance(input_data, dict) and "input" in input_data:
        input_items = input_data.get("input", [])
        if isinstance(input_items, list) and input_items:
            first = input_items[0]
            if isinstance(first, dict) and first.get("type") == "message":
                return "openai_responses"

    # Also check output for Responses API format
    # Output: {"output": [{"type": "function_call"|"reasoning"|...}]}
    if isinstance(output_data, dict) and "output" in output_data:
        output_items = output_data.get("output", [])
        if isinstance(output_items, list) and output_items:
            first = output_items[0]
            if isinstance(first, dict) and first.get("type") in [
                "function_call",
                "reasoning",
                "message",
                "web_search_call",
                "file_search_call",
                "computer_call",
            ]:
                return "openai_responses"

    # 2. Check output structure for clear provider signals
    if isinstance(output_data, dict):
        if "choices" in output_data:
            return "openai"
        if "candidates" in output_data:
            return "google"

    # 3. Check for Anthropic content blocks in messages (OTEL may serialize as JSON)
    # This MUST run before the OTEL check since Anthropic OTEL data has finish_reason
    # but also has Anthropic-style content blocks that need special handling
    messages = None
    if isinstance(input_data, dict) and "messages" in input_data:
        messages = input_data["messages"]
    elif isinstance(input_data, list):
        messages = input_data

    if messages and isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content = msg["content"]
                # Try parsing JSON string content
                parsed = parse_json_content(content)
                if has_anthropic_tool_blocks(parsed):
                    return "anthropic"

    # 4. Check for OTEL-normalized list format (after Anthropic check)
    if isinstance(output_data, list) and output_data:
        first = output_data[0]
        if isinstance(first, dict):
            if "tool_calls" in first or "finish_reason" in first:
                return "openai"

    # 5. Check input structure
    if isinstance(input_data, dict):
        if "contents" in input_data:
            return "google"

    # 6. Fall back to model name hints
    if any(p in model_lower for p in ["gpt-", "o1-", "text-davinci", "text-embedding"]):
        return "openai"
    if "claude" in model_lower:
        return "openai"  # OTEL-normalized
    if "gemini" in model_lower or "palm" in model_lower:
        return "google"

    # 7. Final fallback: check input structure
    if isinstance(input_data, dict) and "messages" in input_data:
        return _detect_from_messages(input_data["messages"])
    if isinstance(input_data, list) and input_data:
        return _detect_from_messages(input_data)
    if isinstance(input_data, str):
        return "string"

    return "unknown"


def _detect_from_messages(messages: list[Any]) -> str:
    """Detect format from message list structure.

    Args:
        messages: List of message objects

    Returns:
        Provider format string
    """
    if not messages or not isinstance(messages[0], dict):
        return "unknown"

    first = messages[0]

    # Google: uses "parts" instead of "content", or role="model"
    if "parts" in first:
        return "google"
    if first.get("role") == "model":
        return "google"

    # Now distinguish OpenAI vs Anthropic
    # Both use role + content, but content structure differs
    content = first.get("content")

    if content is None:
        return "unknown"

    # String content -> OpenAI (Anthropic always uses list)
    if isinstance(content, str):
        return "openai"

    # List content -> need to check block types
    if isinstance(content, list) and len(content) > 0:
        block = content[0]
        if isinstance(block, dict):
            block_type = block.get("type")
            # Anthropic-specific types
            if block_type in ["tool_use", "tool_result"]:
                return "anthropic"
            # OpenAI-specific types
            if block_type == "image_url":
                return "openai"
            # Anthropic image format has "source" object
            if block_type == "image" and "source" in block:
                return "anthropic"
            # Both have "text" type - check other messages for distinguishing types
            if block_type == "text":
                for msg in messages:
                    msg_content = msg.get("content")
                    if isinstance(msg_content, list):
                        for b in msg_content:
                            if isinstance(b, dict):
                                if b.get("type") in [
                                    "tool_use",
                                    "tool_result",
                                    "image",
                                ]:
                                    return "anthropic"
                                if b.get("type") == "image_url":
                                    return "openai"
                # Default to Anthropic if content is list (more common case)
                return "anthropic"

    return "openai"  # Default fallback


def find_best_responses_api_generation(
    generations: list[Any],
) -> tuple[int, Any] | None:
    """Find the last generation with OpenAI Responses API format input.

    The Responses API format has complete message history including system/user
    messages that are often missing from OTEL-captured generations.

    Args:
        generations: List of LangFuse generation observations

    Returns:
        Tuple of (index, generation) or None if no Responses API format found
    """
    # Search backwards to find the last (most complete) one
    for i in range(len(generations) - 1, -1, -1):
        if detect_provider_format(generations[i]) == "openai_responses":
            return (i, generations[i])
    return None
