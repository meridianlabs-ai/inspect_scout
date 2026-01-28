"""Tests for LangSmith provider format detection.

Tests detect_provider_format() and get_model_name() functions that
identify the provider (OpenAI, Anthropic, Google) from run data.
"""

from inspect_scout.sources._langsmith.detection import (
    detect_provider_format,
    get_model_name,
)

from tests.sources.langsmith_source.mocks import (
    MockRun,
    create_anthropic_llm_run,
    create_google_llm_run,
    create_openai_llm_run,
)


class TestDetectProviderFormat:
    """Tests for detect_provider_format function."""

    # =========================================================================
    # Detection by ls_provider metadata (primary method)
    # =========================================================================

    def test_detect_openai_by_ls_provider(self) -> None:
        """Detect OpenAI format from ls_provider metadata."""
        run = create_openai_llm_run()
        assert detect_provider_format(run) == "openai"

    def test_detect_anthropic_by_ls_provider(self) -> None:
        """Detect Anthropic format from ls_provider metadata."""
        run = create_anthropic_llm_run()
        assert detect_provider_format(run) == "anthropic"

    def test_detect_google_by_ls_provider(self) -> None:
        """Detect Google format from ls_provider metadata."""
        run = create_google_llm_run()
        assert detect_provider_format(run) == "google"

    def test_detect_azure_as_openai(self) -> None:
        """Azure provider should be detected as OpenAI format."""
        run = MockRun(
            inputs={"messages": [{"role": "user", "content": "Hello"}]},
            outputs={"choices": [{"message": {"content": "Hi"}}]},
            extra={"metadata": {"ls_provider": "azure"}},
        )
        assert detect_provider_format(run) == "openai"

    # =========================================================================
    # Detection by output structure (fallback)
    # =========================================================================

    def test_detect_openai_by_choices_output(self) -> None:
        """Detect OpenAI format from choices in output."""
        run = MockRun(
            inputs={},
            outputs={"choices": [{"message": {"role": "assistant", "content": "Hi"}}]},
            extra={},
        )
        assert detect_provider_format(run) == "openai"

    def test_detect_google_by_candidates_output(self) -> None:
        """Detect Google format from candidates in output."""
        run = MockRun(
            inputs={},
            outputs={
                "candidates": [
                    {"content": {"role": "model", "parts": [{"text": "Hi"}]}}
                ]
            },
            extra={},
        )
        assert detect_provider_format(run) == "google"

    def test_detect_anthropic_by_content_blocks_output(self) -> None:
        """Detect Anthropic format from content blocks in output."""
        run = MockRun(
            inputs={},
            outputs={"content": [{"type": "text", "text": "Hello"}]},
            extra={},
        )
        assert detect_provider_format(run) == "anthropic"

    def test_detect_anthropic_by_tool_use_block_output(self) -> None:
        """Detect Anthropic format from tool_use content block."""
        run = MockRun(
            inputs={},
            outputs={
                "content": [
                    {"type": "tool_use", "id": "toolu_123", "name": "get_weather"}
                ]
            },
            extra={},
        )
        assert detect_provider_format(run) == "anthropic"

    # =========================================================================
    # Detection by input structure (fallback)
    # =========================================================================

    def test_detect_google_by_contents_input(self) -> None:
        """Detect Google format from contents key in input."""
        run = MockRun(
            inputs={"contents": [{"role": "user", "parts": [{"text": "Hello"}]}]},
            outputs={},
            extra={},
        )
        assert detect_provider_format(run) == "google"

    def test_detect_anthropic_by_content_blocks_input(self) -> None:
        """Detect Anthropic format from content blocks in input messages."""
        run = MockRun(
            inputs={
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
                ]
            },
            outputs={},
            extra={},
        )
        assert detect_provider_format(run) == "anthropic"

    def test_detect_anthropic_by_tool_result_input(self) -> None:
        """Detect Anthropic format from tool_result content block."""
        run = MockRun(
            inputs={
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": "toolu_123"}
                        ],
                    }
                ]
            },
            outputs={},
            extra={},
        )
        assert detect_provider_format(run) == "anthropic"

    # =========================================================================
    # Detection by model name hints (last resort)
    # =========================================================================

    def test_detect_openai_by_gpt_model_name(self) -> None:
        """Detect OpenAI format from gpt- model name."""
        run = MockRun(
            inputs={"messages": []},
            outputs={},
            extra={"metadata": {"ls_model_name": "gpt-4o-mini"}},
        )
        assert detect_provider_format(run) == "openai"

    def test_detect_openai_by_o1_model_name(self) -> None:
        """Detect OpenAI format from o1- model name."""
        run = MockRun(
            inputs={"messages": []},
            outputs={},
            extra={"metadata": {"ls_model_name": "o1-preview"}},
        )
        assert detect_provider_format(run) == "openai"

    def test_detect_anthropic_by_claude_model_name(self) -> None:
        """Detect Anthropic format from claude model name."""
        run = MockRun(
            inputs={"messages": []},
            outputs={},
            extra={"metadata": {"ls_model_name": "claude-3-5-sonnet"}},
        )
        assert detect_provider_format(run) == "anthropic"

    def test_detect_google_by_gemini_model_name(self) -> None:
        """Detect Google format from gemini model name."""
        run = MockRun(
            inputs={"messages": []},
            outputs={},
            extra={"metadata": {"ls_model_name": "gemini-2.0-flash"}},
        )
        assert detect_provider_format(run) == "google"

    def test_detect_google_by_palm_model_name(self) -> None:
        """Detect Google format from palm model name."""
        run = MockRun(
            inputs={"messages": []},
            outputs={},
            extra={"metadata": {"ls_model_name": "palm-2"}},
        )
        assert detect_provider_format(run) == "google"

    # =========================================================================
    # Default and unknown handling
    # =========================================================================

    def test_default_to_openai_with_messages(self) -> None:
        """Default to OpenAI format when messages present but no other signals."""
        run = MockRun(
            inputs={"messages": [{"role": "user", "content": "Hello"}]},
            outputs={},
            extra={},
        )
        assert detect_provider_format(run) == "openai"

    def test_unknown_format_no_data(self) -> None:
        """Return unknown when no format signals present."""
        run = MockRun(
            inputs={},
            outputs={},
            extra={},
        )
        assert detect_provider_format(run) == "unknown"

    def test_unknown_format_none_values(self) -> None:
        """Return unknown when inputs/outputs are None."""
        run = MockRun(
            inputs=None,
            outputs=None,
            extra=None,
        )
        assert detect_provider_format(run) == "unknown"


class TestGetModelName:
    """Tests for get_model_name function."""

    def test_get_model_name_from_ls_metadata(self) -> None:
        """Get model name from ls_model_name metadata."""
        run = MockRun(
            extra={"metadata": {"ls_model_name": "gpt-4o-mini"}},
        )
        assert get_model_name(run) == "gpt-4o-mini"

    def test_get_model_name_from_invocation_params(self) -> None:
        """Get model name from invocation_params."""
        run = MockRun(
            extra={"invocation_params": {"model": "claude-3-opus"}},
        )
        assert get_model_name(run) == "claude-3-opus"

    def test_get_model_name_from_invocation_params_model_name(self) -> None:
        """Get model name from invocation_params.model_name."""
        run = MockRun(
            extra={"invocation_params": {"model_name": "gemini-pro"}},
        )
        assert get_model_name(run) == "gemini-pro"

    def test_get_model_name_prefers_ls_metadata(self) -> None:
        """ls_model_name takes precedence over invocation_params."""
        run = MockRun(
            extra={
                "metadata": {"ls_model_name": "gpt-4"},
                "invocation_params": {"model": "gpt-3.5-turbo"},
            },
        )
        assert get_model_name(run) == "gpt-4"

    def test_get_model_name_from_run_name_gpt(self) -> None:
        """Get model name from run name if it contains gpt."""
        run = MockRun(
            name="gpt-4o-mini",
            extra={},
        )
        assert get_model_name(run) == "gpt-4o-mini"

    def test_get_model_name_from_run_name_claude(self) -> None:
        """Get model name from run name if it contains claude."""
        run = MockRun(
            name="claude-3-haiku",
            extra={},
        )
        assert get_model_name(run) == "claude-3-haiku"

    def test_get_model_name_returns_unknown(self) -> None:
        """Return 'unknown' when no model name found."""
        run = MockRun(
            name="my-custom-chain",
            extra={},
        )
        assert get_model_name(run) == "unknown"

    def test_get_model_name_handles_none_extra(self) -> None:
        """Handle None extra gracefully."""
        run = MockRun(
            extra=None,
        )
        assert get_model_name(run) == "unknown"

    def test_get_model_name_handles_empty_metadata(self) -> None:
        """Handle empty metadata gracefully."""
        run = MockRun(
            extra={"metadata": {}},
        )
        assert get_model_name(run) == "unknown"
