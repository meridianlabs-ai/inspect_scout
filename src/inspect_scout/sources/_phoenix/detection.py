"""Provider detection for Phoenix spans.

Phoenix uses OpenInference semantic conventions with uniform span attributes.
The `span_kind` field directly indicates type ("LLM", "TOOL", "CHAIN"),
and `llm.system` identifies the provider.
"""

from enum import Enum
from typing import Any


class Provider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    UNKNOWN = "unknown"


# Mapping from llm.system values to providers
SYSTEM_TO_PROVIDER = {
    "openai": Provider.OPENAI,
    "anthropic": Provider.ANTHROPIC,
    "google": Provider.GOOGLE,
    "google_genai": Provider.GOOGLE,
    "gcp.vertex_ai": Provider.GOOGLE,
}


def detect_provider(span: dict[str, Any]) -> Provider:
    """Detect the LLM provider from Phoenix span attributes.

    Detection priority:
    1. Check attributes["llm.system"]
    2. Infer from model name patterns

    Args:
        span: Phoenix span dictionary with 'attributes'

    Returns:
        Detected Provider enum value
    """
    attributes = span.get("attributes") or {}

    # 1. Check llm.system (most reliable for Phoenix)
    llm_system = attributes.get("llm.system")
    if llm_system:
        system_lower = str(llm_system).lower()
        if system_lower in SYSTEM_TO_PROVIDER:
            return SYSTEM_TO_PROVIDER[system_lower]

    # 2. Infer from model name
    model_name = get_model_name(span)
    if model_name:
        model_lower = model_name.lower()
        if any(p in model_lower for p in ["gpt-", "o1-", "o3-", "text-davinci"]):
            return Provider.OPENAI
        if "claude" in model_lower:
            return Provider.ANTHROPIC
        if "gemini" in model_lower or "palm" in model_lower:
            return Provider.GOOGLE

    return Provider.UNKNOWN


def get_model_name(span: dict[str, Any]) -> str | None:
    """Get the model name from span attributes.

    Args:
        span: Phoenix span dictionary

    Returns:
        Model name or None if not found
    """
    attributes = span.get("attributes") or {}

    model = attributes.get("llm.model_name")
    if model:
        return str(model)

    # Fallback to gen_ai attributes (some instrumentors use these)
    model = attributes.get("gen_ai.response.model")
    if model:
        return str(model)

    model = attributes.get("gen_ai.request.model")
    if model:
        return str(model)

    return None


def is_llm_span(span: dict[str, Any]) -> bool:
    """Check if a span represents an LLM operation.

    Args:
        span: Phoenix span dictionary

    Returns:
        True if this is an LLM span
    """
    span_kind = str(span.get("span_kind", "")).upper()
    return span_kind == "LLM"


def is_tool_span(span: dict[str, Any]) -> bool:
    """Check if a span represents a tool execution.

    Args:
        span: Phoenix span dictionary

    Returns:
        True if this is a tool execution span
    """
    span_kind = str(span.get("span_kind", "")).upper()
    if span_kind == "TOOL":
        return True

    # Fallback: check for tool-related attributes
    attributes = span.get("attributes") or {}
    if attributes.get("tool.name"):
        return True

    return False


def is_chain_span(span: dict[str, Any]) -> bool:
    """Check if a span represents a chain/agent operation.

    Args:
        span: Phoenix span dictionary

    Returns:
        True if this is a chain or agent span
    """
    span_kind = str(span.get("span_kind", "")).upper()
    return span_kind in ("CHAIN", "AGENT")
