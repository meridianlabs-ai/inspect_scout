"""Provider format detection for LangSmith data.

LangSmith traces can come from multiple sources:
- LangChain agents/chains (OpenAI-style format)
- Raw OpenAI via wrap_openai (native OpenAI format)
- Raw Anthropic via wrap_anthropic (native Anthropic format)
- Raw Google via wrap_gemini (native Google format)

This module detects the provider format from run data to enable
correct message extraction using inspect_ai converters.
"""

from typing import Any


def detect_provider_format(run: Any) -> str:
    """Detect the provider format from LangSmith run data.

    Detection priority:
    1. Check run.extra["metadata"]["ls_provider"] (explicit, most reliable)
    2. Check output structure for provider signals
    3. Check input structure for provider signals
    4. Model name hints as fallback

    Args:
        run: LangSmith run object with inputs, outputs, extra metadata

    Returns:
        Format string: "openai", "anthropic", "google", or "unknown"
    """
    inputs = getattr(run, "inputs", None) or {}
    outputs = getattr(run, "outputs", None) or {}
    extra = getattr(run, "extra", None) or {}
    model_name = _extract_model_name(run)

    # 1. Check explicit provider metadata from LangSmith wrappers
    # wrap_openai, wrap_anthropic, wrap_gemini set ls_provider
    metadata = extra.get("metadata", {}) if isinstance(extra, dict) else {}
    ls_provider = metadata.get("ls_provider", "").lower() if metadata else ""

    if ls_provider == "openai" or ls_provider == "azure":
        return "openai"
    if ls_provider == "anthropic":
        return "anthropic"
    if ls_provider == "google":
        return "google"

    # 2. Check output structure for provider signals
    if isinstance(outputs, dict):
        # OpenAI: has "choices" key
        if "choices" in outputs:
            return "openai"
        # Google: has "candidates" key
        if "candidates" in outputs:
            return "google"
        # Anthropic: has "content" as list with content blocks
        if "content" in outputs and isinstance(outputs.get("content"), list):
            content_list = outputs["content"]
            if content_list and isinstance(content_list[0], dict):
                block_type = content_list[0].get("type", "")
                if block_type in ("text", "tool_use"):
                    return "anthropic"

    # 3. Check input structure for provider signals
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

    # 4. Model name hints as fallback
    model_lower = model_name.lower() if model_name else ""

    if any(p in model_lower for p in ["gpt-", "o1-", "o3-", "text-davinci", "chatgpt"]):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower or "palm" in model_lower:
        return "google"

    # 5. Default: assume OpenAI format (LangChain default)
    # LangChain agents typically use OpenAI-style message format
    if isinstance(inputs, dict) and "messages" in inputs:
        return "openai"

    return "unknown"


def _extract_model_name(run: Any) -> str:
    """Extract model name from run data.

    Model name can be stored in multiple locations:
    - run.extra["metadata"]["ls_model_name"] (LangSmith wrappers)
    - run.extra["invocation_params"]["model"] (LangChain)
    - run.name (sometimes)

    Args:
        run: LangSmith run object

    Returns:
        Model name string or empty string if not found
    """
    extra = getattr(run, "extra", None) or {}

    # Try ls_model_name first (from LangSmith wrappers)
    metadata = extra.get("metadata", {}) if isinstance(extra, dict) else {}
    if metadata:
        model = metadata.get("ls_model_name")
        if model:
            return str(model)

    # Try invocation_params (from LangChain)
    invocation_params = extra.get("invocation_params", {})
    if invocation_params:
        model = invocation_params.get("model") or invocation_params.get("model_name")
        if model:
            return str(model)

    # Try run name as fallback
    run_name = getattr(run, "name", None)
    if run_name and isinstance(run_name, str):
        # Check if name looks like a model name
        if any(p in run_name.lower() for p in ["gpt", "claude", "gemini"]):
            return str(run_name)

    return ""


def get_model_name(run: Any) -> str:
    """Get the model name from a LangSmith run.

    Public interface for extracting model name.

    Args:
        run: LangSmith run object

    Returns:
        Model name string or "unknown" if not found
    """
    name = _extract_model_name(run)
    return name if name else "unknown"
