"""Tests for Logfire instrumentor detection."""

from typing import Any

from inspect_scout.sources._logfire.detection import (
    Instrumentor,
    detect_instrumentor,
    get_model_name,
    is_agent_span,
    is_llm_span,
    is_tool_span,
)

from .mocks import (
    create_agent_span,
    create_anthropic_llm_span,
    create_google_llm_span,
    create_openai_llm_span,
    create_pydantic_ai_agent_trace,
    create_pydantic_ai_span,
    create_tool_span,
)


class TestDetectInstrumentor:
    """Tests for detect_instrumentor function."""

    def test_detect_openai_from_system(self) -> None:
        """Detect OpenAI from gen_ai.system attribute."""
        span = create_openai_llm_span()
        assert detect_instrumentor(span) == Instrumentor.OPENAI

    def test_detect_anthropic_from_system(self) -> None:
        """Detect Anthropic from gen_ai.system attribute."""
        span = create_anthropic_llm_span()
        assert detect_instrumentor(span) == Instrumentor.ANTHROPIC

    def test_detect_google_from_system(self) -> None:
        """Detect Google GenAI from gen_ai.system attribute."""
        span = create_google_llm_span()
        assert detect_instrumentor(span) == Instrumentor.GOOGLE_GENAI

    def test_detect_pydantic_ai_from_scope(self) -> None:
        """Detect Pydantic AI from otel_scope_name."""
        span = create_pydantic_ai_span()
        # Pydantic AI uses openai as the gen_ai.system, but has pydantic-ai scope
        # The gen_ai.system takes precedence, so it should be detected as OpenAI
        assert detect_instrumentor(span) == Instrumentor.OPENAI

    def test_detect_pydantic_ai_agent_span(self) -> None:
        """Detect Pydantic AI agent spans."""
        spans = create_pydantic_ai_agent_trace()
        agent_span = spans[0]
        # Agent span should have pydantic-ai scope
        assert agent_span["otel_scope_name"] == "pydantic-ai"

    def test_detect_from_scope_name(self) -> None:
        """Detect instrumentor from otel_scope_name when no system attribute."""
        span = {
            "otel_scope_name": "opentelemetry.instrumentation.openai",
            "attributes": {},
        }
        assert detect_instrumentor(span) == Instrumentor.OPENAI

    def test_detect_from_model_name(self) -> None:
        """Detect instrumentor from model name hints."""
        span = {
            "attributes": {"gen_ai.request.model": "gpt-4o"},
        }
        assert detect_instrumentor(span) == Instrumentor.OPENAI

        span = {
            "attributes": {"gen_ai.request.model": "claude-3-sonnet"},
        }
        assert detect_instrumentor(span) == Instrumentor.ANTHROPIC

        span = {
            "attributes": {"gen_ai.request.model": "gemini-1.5-pro"},
        }
        assert detect_instrumentor(span) == Instrumentor.GOOGLE_GENAI

    def test_detect_unknown(self) -> None:
        """Return UNKNOWN when no detection signals present."""
        span: dict[str, Any] = {"attributes": {}}
        assert detect_instrumentor(span) == Instrumentor.UNKNOWN

    def test_detect_with_provider_name(self) -> None:
        """Detect from gen_ai.provider.name attribute."""
        span = {
            "attributes": {"gen_ai.provider.name": "anthropic"},
        }
        assert detect_instrumentor(span) == Instrumentor.ANTHROPIC


class TestGetModelName:
    """Tests for get_model_name function."""

    def test_get_model_from_response(self) -> None:
        """Get model from gen_ai.response.model."""
        span = {
            "attributes": {
                "gen_ai.request.model": "gpt-4",
                "gen_ai.response.model": "gpt-4-0613",
            }
        }
        # Prefer response model
        assert get_model_name(span) == "gpt-4-0613"

    def test_get_model_from_request(self) -> None:
        """Get model from gen_ai.request.model when no response model."""
        span = {
            "attributes": {
                "gen_ai.request.model": "gpt-4",
            }
        }
        assert get_model_name(span) == "gpt-4"

    def test_no_model_returns_none(self) -> None:
        """Return None when no model attributes present."""
        span: dict[str, Any] = {"attributes": {}}
        assert get_model_name(span) is None


class TestIsLLMSpan:
    """Tests for is_llm_span function."""

    def test_chat_operation(self) -> None:
        """Detect chat operation as LLM span."""
        span = create_openai_llm_span()
        assert is_llm_span(span) is True

    def test_generate_content_operation(self) -> None:
        """Detect generate_content operation as LLM span."""
        span = create_google_llm_span()
        assert is_llm_span(span) is True

    def test_tool_span_not_llm(self) -> None:
        """Tool span is not an LLM span."""
        span = create_tool_span()
        assert is_llm_span(span) is False

    def test_agent_span_not_llm(self) -> None:
        """Agent span is not an LLM span."""
        span = create_agent_span()
        assert is_llm_span(span) is False


class TestIsToolSpan:
    """Tests for is_tool_span function."""

    def test_tool_span_detected(self) -> None:
        """Detect tool execution span."""
        span = create_tool_span()
        assert is_tool_span(span) is True

    def test_llm_span_not_tool(self) -> None:
        """LLM span is not a tool span."""
        span = create_openai_llm_span()
        assert is_tool_span(span) is False

    def test_span_with_tool_name(self) -> None:
        """Detect span with gen_ai.tool.name attribute."""
        span = {
            "attributes": {"gen_ai.tool.name": "search"},
        }
        assert is_tool_span(span) is True


class TestIsAgentSpan:
    """Tests for is_agent_span function."""

    def test_agent_span_detected(self) -> None:
        """Detect agent operation span."""
        span = create_agent_span()
        assert is_agent_span(span) is True

    def test_invoke_agent_operation(self) -> None:
        """Detect invoke_agent operation."""
        span = {
            "attributes": {"gen_ai.operation.name": "invoke_agent"},
        }
        assert is_agent_span(span) is True

    def test_llm_span_not_agent(self) -> None:
        """LLM span is not an agent span."""
        span = create_openai_llm_span()
        assert is_agent_span(span) is False
