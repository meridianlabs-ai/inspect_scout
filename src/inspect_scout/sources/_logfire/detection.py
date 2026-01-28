"""Instrumentor detection for Logfire spans.

Logfire traces can come from multiple instrumentors:
- Pydantic AI - logfire.instrument_pydantic_ai()
- OpenAI - logfire.instrument_openai()
- Anthropic - logfire.instrument_anthropic()
- Google GenAI - logfire.instrument_google_genai()
- LiteLLM - logfire.instrument_litellm()

This module detects the instrumentor from span attributes to enable
correct message extraction.
"""

from enum import Enum
from typing import Any


class Instrumentor(Enum):
    """Supported Logfire instrumentors."""

    PYDANTIC_AI = "pydantic_ai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_GENAI = "google_genai"
    LITELLM = "litellm"
    UNKNOWN = "unknown"


# Mapping from gen_ai.system values to instrumentors
SYSTEM_TO_INSTRUMENTOR = {
    "openai": Instrumentor.OPENAI,
    "anthropic": Instrumentor.ANTHROPIC,
    "google_genai": Instrumentor.GOOGLE_GENAI,
    "google": Instrumentor.GOOGLE_GENAI,
    "gcp.vertex_ai": Instrumentor.GOOGLE_GENAI,
    "litellm": Instrumentor.LITELLM,
}

# Mapping from otel_scope_name to instrumentors
SCOPE_TO_INSTRUMENTOR = {
    "opentelemetry.instrumentation.openai": Instrumentor.OPENAI,
    "openai": Instrumentor.OPENAI,
    "opentelemetry.instrumentation.anthropic": Instrumentor.ANTHROPIC,
    "anthropic": Instrumentor.ANTHROPIC,
    "opentelemetry.instrumentation.google_generativeai": Instrumentor.GOOGLE_GENAI,
    "opentelemetry.instrumentation.google-genai": Instrumentor.GOOGLE_GENAI,
    "google-genai": Instrumentor.GOOGLE_GENAI,
    "opentelemetry.instrumentation.litellm": Instrumentor.LITELLM,
    "litellm": Instrumentor.LITELLM,
    "pydantic-ai": Instrumentor.PYDANTIC_AI,
    "pydantic_ai": Instrumentor.PYDANTIC_AI,
}


def detect_instrumentor(span: dict[str, Any]) -> Instrumentor:
    """Detect the instrumentor from Logfire span attributes.

    Detection priority:
    1. Check attributes["gen_ai.system"] or attributes["gen_ai.provider.name"]
    2. Check otel_scope_name
    3. Infer from model name patterns

    Args:
        span: Logfire span dictionary with 'attributes' and 'otel_scope_name'

    Returns:
        Detected Instrumentor enum value
    """
    attributes = span.get("attributes") or {}

    # 1. Check gen_ai.system or gen_ai.provider.name (most reliable)
    gen_ai_system = attributes.get("gen_ai.system") or attributes.get(
        "gen_ai.provider.name"
    )
    if gen_ai_system:
        system_lower = str(gen_ai_system).lower()
        if system_lower in SYSTEM_TO_INSTRUMENTOR:
            return SYSTEM_TO_INSTRUMENTOR[system_lower]

    # 2. Check otel_scope_name
    scope_name = span.get("otel_scope_name") or ""
    if scope_name:
        scope_lower = str(scope_name).lower()
        for key, instrumentor in SCOPE_TO_INSTRUMENTOR.items():
            if key.lower() in scope_lower:
                return instrumentor

    # 3. Infer from model name
    model_name = get_model_name(span)
    if model_name:
        model_lower = model_name.lower()
        if any(p in model_lower for p in ["gpt-", "o1-", "o3-", "text-davinci"]):
            return Instrumentor.OPENAI
        if "claude" in model_lower:
            return Instrumentor.ANTHROPIC
        if "gemini" in model_lower or "palm" in model_lower:
            return Instrumentor.GOOGLE_GENAI

    return Instrumentor.UNKNOWN


def get_model_name(span: dict[str, Any]) -> str | None:
    """Get the model name from span attributes.

    Checks both request and response model attributes.

    Args:
        span: Logfire span dictionary

    Returns:
        Model name or None if not found
    """
    attributes = span.get("attributes") or {}

    # Prefer response model (actual model used)
    model = attributes.get("gen_ai.response.model")
    if model:
        return str(model)

    # Fall back to request model
    model = attributes.get("gen_ai.request.model")
    if model:
        return str(model)

    return None


def is_llm_span(span: dict[str, Any]) -> bool:
    """Check if a span represents an LLM operation.

    Args:
        span: Logfire span dictionary

    Returns:
        True if this is an LLM span (chat, text_completion, generate_content)
    """
    attributes = span.get("attributes") or {}
    operation = attributes.get("gen_ai.operation.name", "")

    return operation in ("chat", "text_completion", "generate_content", "embeddings")


def is_tool_span(span: dict[str, Any]) -> bool:
    """Check if a span represents a tool execution.

    Args:
        span: Logfire span dictionary

    Returns:
        True if this is a tool execution span
    """
    attributes = span.get("attributes") or {}

    # Check for tool-related attributes
    if attributes.get("gen_ai.tool.name"):
        return True

    # Check for execute_tool operation
    operation = attributes.get("gen_ai.operation.name", "")
    return str(operation) == "execute_tool"


def is_agent_span(span: dict[str, Any]) -> bool:
    """Check if a span represents an agent operation.

    Args:
        span: Logfire span dictionary

    Returns:
        True if this is an agent span (Pydantic AI agent, invoke_agent, etc.)
    """
    attributes = span.get("attributes") or {}
    operation = attributes.get("gen_ai.operation.name", "")

    if operation in ("invoke_agent", "create_agent"):
        return True

    # Check for Pydantic AI agent spans
    span_name = span.get("span_name") or ""
    message = span.get("message") or ""

    if "agent" in span_name.lower() or "agent" in message.lower():
        return True

    return False
