"""Provider format detection for W&B Weave data.

Weave traces can come from multiple sources:
- OpenAI API calls
- Anthropic API calls
- Google/Gemini API calls
- LangChain integrations
- Custom instrumented code

This module detects the provider format from call data to enable
correct message extraction using inspect_ai converters.
"""

from typing import Any


def detect_provider_format(call: Any) -> str:
    """Detect the provider format from Weave call data.

    Detection priority:
    1. Check call attributes for explicit provider info
    2. Check op_name for provider hints (e.g., "openai.chat.completions")
    3. Check input/output structure for provider signals
    4. Model name hints as fallback

    Args:
        call: Weave call object with inputs, outputs, attributes

    Returns:
        Format string: "openai", "anthropic", "google", or "unknown"
    """
    # Get call attributes
    op_name = _get_op_name(call)
    inputs = _get_inputs(call)
    output = _get_output(call)
    model_name = _extract_model_name(call)

    # 1. Check op_name for explicit provider hints
    op_lower = op_name.lower() if op_name else ""

    if "openai" in op_lower:
        return "openai"
    if "anthropic" in op_lower:
        return "anthropic"
    if "google" in op_lower or "gemini" in op_lower or "genai" in op_lower:
        return "google"

    # 2. Check attributes for provider metadata
    attributes = _get_attributes(call)
    if attributes:
        provider = attributes.get("provider", "").lower()
        if provider in ("openai", "azure"):
            return "openai"
        if provider == "anthropic":
            return "anthropic"
        if provider in ("google", "gemini"):
            return "google"

    # 3. Check output structure for provider signals
    if isinstance(output, dict):
        # OpenAI: has "choices" key
        if "choices" in output:
            return "openai"
        # Google: has "candidates" key
        if "candidates" in output:
            return "google"
        # Anthropic: has "content" as list with content blocks
        if "content" in output and isinstance(output.get("content"), list):
            content_list = output["content"]
            if content_list and isinstance(content_list[0], dict):
                block_type = content_list[0].get("type", "")
                if block_type in ("text", "tool_use"):
                    return "anthropic"

    # 4. Check input structure for provider signals
    if isinstance(inputs, dict):
        # Google: has "contents" key
        if "contents" in inputs:
            return "google"
        # Anthropic: messages have content as list with blocks
        messages = inputs.get("messages", [])
        if isinstance(messages, list) and messages:
            first_msg = messages[0]
            if isinstance(first_msg, dict):
                content = first_msg.get("content")
                if isinstance(content, list) and content:
                    block = content[0]
                    if isinstance(block, dict) and block.get("type") in (
                        "text",
                        "tool_use",
                        "tool_result",
                    ):
                        return "anthropic"

    # 5. Model name hints as fallback
    model_lower = model_name.lower() if model_name else ""

    if any(p in model_lower for p in ["gpt-", "o1-", "o3-", "text-davinci", "chatgpt"]):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower or "palm" in model_lower:
        return "google"

    # 6. Default: assume OpenAI format (most common)
    if isinstance(inputs, dict) and "messages" in inputs:
        return "openai"

    return "unknown"


def _get_op_name(call: Any) -> str:
    """Extract operation name from call.

    Args:
        call: Weave call object

    Returns:
        Operation name or empty string
    """
    # Try different attribute names
    for attr in ("op_name", "name", "display_name"):
        value = getattr(call, attr, None)
        if value:
            return str(value)

    return ""


def _get_inputs(call: Any) -> dict[str, Any]:
    """Extract inputs from call.

    Args:
        call: Weave call object

    Returns:
        Inputs dictionary
    """
    inputs = getattr(call, "inputs", None)
    if isinstance(inputs, dict):
        return inputs
    return {}


def _get_output(call: Any) -> Any:
    """Extract output from call.

    Args:
        call: Weave call object

    Returns:
        Output data
    """
    return getattr(call, "output", None)


def _get_attributes(call: Any) -> dict[str, Any]:
    """Extract attributes from call.

    Args:
        call: Weave call object

    Returns:
        Attributes dictionary
    """
    attrs = getattr(call, "attributes", None)
    if isinstance(attrs, dict):
        return attrs
    return {}


def _extract_model_name(call: Any) -> str:
    """Extract model name from call data.

    Model name can be stored in multiple locations:
    - call.attributes["model"]
    - call.inputs["model"]
    - call.summary["model"]

    Args:
        call: Weave call object

    Returns:
        Model name string or empty string if not found
    """
    # Try attributes first
    attrs = _get_attributes(call)
    if attrs:
        model = attrs.get("model") or attrs.get("model_name")
        if model:
            return str(model)

    # Try inputs
    inputs = _get_inputs(call)
    if inputs:
        model = inputs.get("model") or inputs.get("model_name")
        if model:
            return str(model)

    # Try summary
    summary = getattr(call, "summary", None)
    if isinstance(summary, dict):
        model = summary.get("model") or summary.get("model_name")
        if model:
            return str(model)

    return ""


def get_model_name(call: Any) -> str:
    """Get the model name from a Weave call.

    Public interface for extracting model name.

    Args:
        call: Weave call object

    Returns:
        Model name string or "unknown" if not found
    """
    name = _extract_model_name(call)
    return name if name else "unknown"
