"""Tests for W&B Weave provider detection."""

from tests.sources.weave_source.mocks import (
    MockWeaveCall,
    create_anthropic_llm_call,
    create_openai_llm_call,
)


class TestDetectProviderFormat:
    """Tests for detect_provider_format function."""

    def test_detect_openai_from_op_name(self) -> None:
        """Detect OpenAI format from op_name containing 'openai'."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = create_openai_llm_call()
        assert detect_provider_format(call) == "openai"

    def test_detect_anthropic_from_op_name(self) -> None:
        """Detect Anthropic format from op_name containing 'anthropic'."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = create_anthropic_llm_call()
        assert detect_provider_format(call) == "anthropic"

    def test_detect_google_from_op_name(self) -> None:
        """Detect Google format from op_name containing 'google' or 'gemini'."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(op_name="google.generativeai.generate_content")
        assert detect_provider_format(call) == "google"

        call2 = MockWeaveCall(op_name="gemini.chat")
        assert detect_provider_format(call2) == "google"

    def test_detect_from_attributes(self) -> None:
        """Detect format from attributes when op_name is generic."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(op_name="llm_call", attributes={"provider": "openai"})
        assert detect_provider_format(call) == "openai"

        call2 = MockWeaveCall(op_name="llm_call", attributes={"provider": "anthropic"})
        assert detect_provider_format(call2) == "anthropic"

    def test_detect_from_output_structure_openai(self) -> None:
        """Detect OpenAI format from 'choices' in output."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            output={"choices": [{"message": {"content": "Hello"}}]},
        )
        assert detect_provider_format(call) == "openai"

    def test_detect_from_output_structure_google(self) -> None:
        """Detect Google format from 'candidates' in output."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            output={"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]},
        )
        assert detect_provider_format(call) == "google"

    def test_detect_from_output_structure_anthropic(self) -> None:
        """Detect Anthropic format from content blocks in output."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            output={"content": [{"type": "text", "text": "Hello"}]},
        )
        assert detect_provider_format(call) == "anthropic"

    def test_detect_from_model_name_gpt(self) -> None:
        """Detect OpenAI format from model name containing 'gpt'."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            inputs={"model": "gpt-4o", "messages": []},
        )
        assert detect_provider_format(call) == "openai"

    def test_detect_from_model_name_claude(self) -> None:
        """Detect Anthropic format from model name containing 'claude'."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            inputs={"model": "claude-3-opus-20240229", "messages": []},
        )
        assert detect_provider_format(call) == "anthropic"

    def test_detect_from_model_name_gemini(self) -> None:
        """Detect Google format from model name containing 'gemini'."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            inputs={"model": "gemini-1.5-pro", "messages": []},
        )
        assert detect_provider_format(call) == "google"

    def test_fallback_to_openai_with_messages(self) -> None:
        """Fallback to OpenAI format when inputs have 'messages' key."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            inputs={"messages": [{"role": "user", "content": "Hello"}]},
        )
        assert detect_provider_format(call) == "openai"

    def test_unknown_format(self) -> None:
        """Return 'unknown' when format cannot be determined."""
        from inspect_scout.sources._weave.detection import detect_provider_format

        call = MockWeaveCall(
            op_name="generic_call",
            inputs={"some_data": "value"},
        )
        assert detect_provider_format(call) == "unknown"


class TestGetModelName:
    """Tests for get_model_name function."""

    def test_get_model_from_attributes(self) -> None:
        """Get model name from attributes."""
        from inspect_scout.sources._weave.detection import get_model_name

        call = MockWeaveCall(attributes={"model": "gpt-4o-mini"})
        assert get_model_name(call) == "gpt-4o-mini"

    def test_get_model_from_inputs(self) -> None:
        """Get model name from inputs."""
        from inspect_scout.sources._weave.detection import get_model_name

        call = MockWeaveCall(inputs={"model": "claude-3-haiku-20240307"})
        assert get_model_name(call) == "claude-3-haiku-20240307"

    def test_get_model_from_summary(self) -> None:
        """Get model name from summary."""
        from inspect_scout.sources._weave.detection import get_model_name

        call = MockWeaveCall(summary={"model": "gemini-1.5-flash"})
        assert get_model_name(call) == "gemini-1.5-flash"

    def test_unknown_model(self) -> None:
        """Return 'unknown' when model name cannot be found."""
        from inspect_scout.sources._weave.detection import get_model_name

        call = MockWeaveCall()
        assert get_model_name(call) == "unknown"
