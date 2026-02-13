"""Tests for Phoenix provider detection."""

from typing import Any

from inspect_scout.sources._phoenix.detection import (
    Provider,
    detect_provider,
    get_model_name,
    is_chain_span,
    is_llm_span,
    is_tool_span,
)

from .mocks import (
    create_anthropic_llm_span,
    create_chain_span,
    create_openai_llm_span,
    create_tool_span,
)


class TestDetectProvider:
    """Tests for detect_provider function."""

    def test_detect_openai_from_system(self) -> None:
        """Detect OpenAI from llm.system attribute."""
        span = create_openai_llm_span()
        assert detect_provider(span) == Provider.OPENAI

    def test_detect_anthropic_from_system(self) -> None:
        """Detect Anthropic from llm.system attribute."""
        span = create_anthropic_llm_span()
        assert detect_provider(span) == Provider.ANTHROPIC

    def test_detect_google_from_system(self) -> None:
        """Detect Google from llm.system attribute."""
        span: dict[str, Any] = {
            "attributes": {"llm.system": "google"},
        }
        assert detect_provider(span) == Provider.GOOGLE

    def test_detect_from_model_name_openai(self) -> None:
        """Detect OpenAI from model name hints."""
        span: dict[str, Any] = {
            "attributes": {"llm.model_name": "gpt-4o"},
        }
        assert detect_provider(span) == Provider.OPENAI

    def test_detect_from_model_name_anthropic(self) -> None:
        """Detect Anthropic from model name hints."""
        span: dict[str, Any] = {
            "attributes": {"llm.model_name": "claude-3-sonnet"},
        }
        assert detect_provider(span) == Provider.ANTHROPIC

    def test_detect_from_model_name_google(self) -> None:
        """Detect Google from model name hints."""
        span: dict[str, Any] = {
            "attributes": {"llm.model_name": "gemini-1.5-pro"},
        }
        assert detect_provider(span) == Provider.GOOGLE

    def test_detect_unknown(self) -> None:
        """Return UNKNOWN when no detection signals present."""
        span: dict[str, Any] = {"attributes": {}}
        assert detect_provider(span) == Provider.UNKNOWN

    def test_detect_with_google_genai(self) -> None:
        """Detect Google from google_genai system value."""
        span: dict[str, Any] = {
            "attributes": {"llm.system": "google_genai"},
        }
        assert detect_provider(span) == Provider.GOOGLE

    def test_detect_with_vertex_ai(self) -> None:
        """Detect Google from gcp.vertex_ai system value."""
        span: dict[str, Any] = {
            "attributes": {"llm.system": "gcp.vertex_ai"},
        }
        assert detect_provider(span) == Provider.GOOGLE


class TestGetModelName:
    """Tests for get_model_name function."""

    def test_get_model_from_llm_model_name(self) -> None:
        """Get model from llm.model_name attribute."""
        span = create_openai_llm_span(model="gpt-4o-mini")
        assert get_model_name(span) == "gpt-4o-mini"

    def test_get_model_from_gen_ai_response(self) -> None:
        """Get model from gen_ai.response.model when no llm.model_name."""
        span: dict[str, Any] = {
            "attributes": {
                "gen_ai.response.model": "gpt-4-0613",
            }
        }
        assert get_model_name(span) == "gpt-4-0613"

    def test_get_model_from_gen_ai_request(self) -> None:
        """Get model from gen_ai.request.model as fallback."""
        span: dict[str, Any] = {
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

    def test_llm_span_detected(self) -> None:
        """Detect LLM span from span_kind."""
        span = create_openai_llm_span()
        assert is_llm_span(span) is True

    def test_tool_span_not_llm(self) -> None:
        """Tool span is not an LLM span."""
        span = create_tool_span()
        assert is_llm_span(span) is False

    def test_chain_span_not_llm(self) -> None:
        """Chain span is not an LLM span."""
        span = create_chain_span()
        assert is_llm_span(span) is False

    def test_case_insensitive(self) -> None:
        """span_kind comparison should be case-insensitive."""
        span: dict[str, Any] = {"span_kind": "llm"}
        assert is_llm_span(span) is True


class TestIsToolSpan:
    """Tests for is_tool_span function."""

    def test_tool_span_detected(self) -> None:
        """Detect tool span from span_kind."""
        span = create_tool_span()
        assert is_tool_span(span) is True

    def test_llm_span_not_tool(self) -> None:
        """LLM span is not a tool span."""
        span = create_openai_llm_span()
        assert is_tool_span(span) is False

    def test_span_with_tool_name_attribute(self) -> None:
        """Detect tool span from tool.name attribute."""
        span: dict[str, Any] = {
            "span_kind": "UNKNOWN",
            "attributes": {"tool.name": "search"},
        }
        assert is_tool_span(span) is True


class TestIsChainSpan:
    """Tests for is_chain_span function."""

    def test_chain_span_detected(self) -> None:
        """Detect chain span from span_kind."""
        span = create_chain_span()
        assert is_chain_span(span) is True

    def test_agent_span_detected(self) -> None:
        """Detect AGENT span_kind as chain span."""
        span: dict[str, Any] = {"span_kind": "AGENT"}
        assert is_chain_span(span) is True

    def test_llm_span_not_chain(self) -> None:
        """LLM span is not a chain span."""
        span = create_openai_llm_span()
        assert is_chain_span(span) is False
