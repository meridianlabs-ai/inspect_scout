"""Tests for CLI option resolution functions (resolve_scan_option, resolve_scan_option_multi)."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from click.core import ParameterSource
from inspect_scout._cli.scan import resolve_scan_option, resolve_scan_option_multi
from inspect_scout._util.constants import DEFAULT_SCANS_DIR


@pytest.fixture
def mock_ctx() -> MagicMock:
    """Create a mock Click context with configurable parameter sources."""
    ctx = MagicMock()
    parameter_sources: dict[str, ParameterSource] = {}

    def get_parameter_source(option: str) -> ParameterSource | None:
        return parameter_sources.get(option)

    def set_parameter_source(option: str, source: ParameterSource) -> None:
        parameter_sources[option] = source

    ctx.get_parameter_source = get_parameter_source
    ctx.set_parameter_source = set_parameter_source
    return ctx


def set_source(ctx: MagicMock, option: str, source: ParameterSource) -> None:
    """Helper to set the parameter source for an option."""
    ctx.set_parameter_source(option, source)


# =============================================================================
# Tests for resolve_scan_option
# =============================================================================


class TestResolveScanOption:
    """Tests for the resolve_scan_option function."""

    def test_cli_takes_priority_over_scanjob(self, mock_ctx: MagicMock) -> None:
        """CLI argument should take priority over scanjob value."""
        set_source(mock_ctx, "model", ParameterSource.COMMANDLINE)

        result = resolve_scan_option(
            mock_ctx,
            "model",
            option_value="cli-model",
            scan_job_value="scanjob-model",
        )

        assert result == "cli-model"

    def test_scanjob_takes_priority_over_env(self, mock_ctx: MagicMock) -> None:
        """Scanjob value should take priority over environment variable."""
        set_source(mock_ctx, "model", ParameterSource.ENVIRONMENT)

        result = resolve_scan_option(
            mock_ctx,
            "model",
            option_value="env-model",
            scan_job_value="scanjob-model",
        )

        assert result == "scanjob-model"

    def test_scanjob_takes_priority_over_default(self, mock_ctx: MagicMock) -> None:
        """Scanjob value should take priority over default value."""
        set_source(mock_ctx, "results", ParameterSource.DEFAULT)

        result = resolve_scan_option(
            mock_ctx,
            "results",
            option_value=DEFAULT_SCANS_DIR,  # default value
            scan_job_value="./custom-results",
        )

        assert result == "./custom-results"

    def test_env_used_when_no_scanjob_value(self, mock_ctx: MagicMock) -> None:
        """Environment variable should be used when scanjob has no value."""
        set_source(mock_ctx, "model", ParameterSource.ENVIRONMENT)

        result = resolve_scan_option(
            mock_ctx,
            "model",
            option_value="env-model",
            scan_job_value=None,
        )

        assert result == "env-model"

    def test_default_used_when_no_scanjob_value(self, mock_ctx: MagicMock) -> None:
        """Default value should be used when scanjob has no value."""
        set_source(mock_ctx, "results", ParameterSource.DEFAULT)

        result = resolve_scan_option(
            mock_ctx,
            "results",
            option_value=DEFAULT_SCANS_DIR,
            scan_job_value=None,
        )

        assert result == DEFAULT_SCANS_DIR

    def test_none_when_both_none(self, mock_ctx: MagicMock) -> None:
        """Should return None when both option and scanjob values are None."""
        set_source(mock_ctx, "limit", ParameterSource.DEFAULT)

        result = resolve_scan_option(
            mock_ctx,
            "limit",
            option_value=None,
            scan_job_value=None,
        )

        assert result is None

    def test_unknown_option_uses_scanjob(self, mock_ctx: MagicMock) -> None:
        """Unknown option (get_parameter_source returns None) should use scanjob."""
        # Don't set any source - simulates unknown parameter
        result = resolve_scan_option(
            mock_ctx,
            "unknown_option",
            option_value="option-value",
            scan_job_value="scanjob-value",
        )

        # None != COMMANDLINE, so scanjob should be used
        assert result == "scanjob-value"

    def test_with_integer_values(self, mock_ctx: MagicMock) -> None:
        """Should work correctly with integer values."""
        set_source(mock_ctx, "max_transcripts", ParameterSource.COMMANDLINE)

        result = resolve_scan_option(
            mock_ctx,
            "max_transcripts",
            option_value=100,
            scan_job_value=50,
        )

        assert result == 100

    def test_with_float_values(self, mock_ctx: MagicMock) -> None:
        """Should work correctly with float values."""
        set_source(mock_ctx, "temperature", ParameterSource.ENVIRONMENT)

        result = resolve_scan_option(
            mock_ctx,
            "temperature",
            option_value=0.7,
            scan_job_value=0.5,
        )

        assert result == 0.5  # scanjob wins over env

    def test_with_list_values(self, mock_ctx: MagicMock) -> None:
        """Should work correctly with list values."""
        set_source(mock_ctx, "tags", ParameterSource.COMMANDLINE)

        result = resolve_scan_option(
            mock_ctx,
            "tags",
            option_value=["cli-tag"],
            scan_job_value=["scanjob-tag"],
        )

        assert result == ["cli-tag"]

    def test_with_dict_values(self, mock_ctx: MagicMock) -> None:
        """Should work correctly with dict values."""
        set_source(mock_ctx, "metadata", ParameterSource.DEFAULT)

        result = resolve_scan_option(
            mock_ctx,
            "metadata",
            option_value={"key": "default"},
            scan_job_value={"key": "scanjob"},
        )

        assert result == {"key": "scanjob"}


# =============================================================================
# Tests for resolve_scan_option_multi
# =============================================================================


class TestResolveScanOptionMulti:
    """Tests for the resolve_scan_option_multi function."""

    def test_any_cli_option_takes_priority(self, mock_ctx: MagicMock) -> None:
        """If any underlying option is from CLI, option_value should win."""
        set_source(mock_ctx, "m", ParameterSource.COMMANDLINE)
        set_source(mock_ctx, "model_config", ParameterSource.DEFAULT)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            option_value={"arg": "cli-value"},
            scan_job_value={"arg": "scanjob-value"},
        )

        assert result == {"arg": "cli-value"}

    def test_other_cli_option_takes_priority(self, mock_ctx: MagicMock) -> None:
        """If the other underlying option is from CLI, option_value should win."""
        set_source(mock_ctx, "m", ParameterSource.DEFAULT)
        set_source(mock_ctx, "model_config", ParameterSource.COMMANDLINE)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            option_value={"arg": "cli-value"},
            scan_job_value={"arg": "scanjob-value"},
        )

        assert result == {"arg": "cli-value"}

    def test_both_cli_options_take_priority(self, mock_ctx: MagicMock) -> None:
        """If both underlying options are from CLI, option_value should win."""
        set_source(mock_ctx, "m", ParameterSource.COMMANDLINE)
        set_source(mock_ctx, "model_config", ParameterSource.COMMANDLINE)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            option_value={"arg": "cli-value"},
            scan_job_value={"arg": "scanjob-value"},
        )

        assert result == {"arg": "cli-value"}

    def test_scanjob_wins_when_no_cli_options(self, mock_ctx: MagicMock) -> None:
        """If no underlying options are from CLI, scanjob should win."""
        set_source(mock_ctx, "m", ParameterSource.ENVIRONMENT)
        set_source(mock_ctx, "model_config", ParameterSource.DEFAULT)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            option_value={"arg": "env-value"},
            scan_job_value={"arg": "scanjob-value"},
        )

        assert result == {"arg": "scanjob-value"}

    def test_option_value_used_when_no_scanjob(self, mock_ctx: MagicMock) -> None:
        """If scanjob has no value, option_value should be used."""
        set_source(mock_ctx, "m", ParameterSource.ENVIRONMENT)
        set_source(mock_ctx, "model_config", ParameterSource.DEFAULT)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            option_value={"arg": "env-value"},
            scan_job_value=None,
        )

        assert result == {"arg": "env-value"}

    def test_none_when_both_none(self, mock_ctx: MagicMock) -> None:
        """Should return None when both values are None."""
        set_source(mock_ctx, "m", ParameterSource.DEFAULT)
        set_source(mock_ctx, "model_config", ParameterSource.DEFAULT)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            option_value=None,
            scan_job_value=None,
        )

        assert result is None

    def test_unknown_options_use_scanjob(self, mock_ctx: MagicMock) -> None:
        """Unknown options (get_parameter_source returns None) should use scanjob."""
        # Don't set any sources
        result = resolve_scan_option_multi(
            mock_ctx,
            ["unknown1", "unknown2"],
            option_value={"arg": "option-value"},
            scan_job_value={"arg": "scanjob-value"},
        )

        assert result == {"arg": "scanjob-value"}

    def test_single_option_list(self, mock_ctx: MagicMock) -> None:
        """Should work with a single option in the list."""
        set_source(mock_ctx, "model_role", ParameterSource.COMMANDLINE)

        result = resolve_scan_option_multi(
            mock_ctx,
            ["model_role"],
            option_value={"critic": "gpt-4"},
            scan_job_value={"critic": "claude"},
        )

        assert result == {"critic": "gpt-4"}

    def test_empty_options_list_uses_scanjob(self, mock_ctx: MagicMock) -> None:
        """Empty options list should use scanjob if present."""
        result = resolve_scan_option_multi(
            mock_ctx,
            [],
            option_value={"arg": "option-value"},
            scan_job_value={"arg": "scanjob-value"},
        )

        # any([]) is False, so scanjob should be used
        assert result == {"arg": "scanjob-value"}


# =============================================================================
# Integration-style tests with realistic scenarios
# =============================================================================


class TestOptionResolutionScenarios:
    """Integration-style tests for realistic option resolution scenarios."""

    def test_model_priority_cli_over_scanjob_over_env(
        self, mock_ctx: MagicMock
    ) -> None:
        """Test model option follows priority: CLI > scanjob > env."""
        # Scenario 1: CLI specified
        set_source(mock_ctx, "model", ParameterSource.COMMANDLINE)
        assert (
            resolve_scan_option(mock_ctx, "model", "openai/gpt-4", "anthropic/claude")
            == "openai/gpt-4"
        )

        # Scenario 2: Env specified (scanjob wins)
        set_source(mock_ctx, "model", ParameterSource.ENVIRONMENT)
        assert (
            resolve_scan_option(mock_ctx, "model", "openai/gpt-4", "anthropic/claude")
            == "anthropic/claude"
        )

        # Scenario 3: Env specified, no scanjob
        assert (
            resolve_scan_option(mock_ctx, "model", "openai/gpt-4", None)
            == "openai/gpt-4"
        )

    def test_results_with_default_value(self, mock_ctx: MagicMock) -> None:
        """Test results option with its default value of './scans'."""
        # Default value, scanjob overrides
        set_source(mock_ctx, "results", ParameterSource.DEFAULT)
        assert (
            resolve_scan_option(
                mock_ctx, "results", DEFAULT_SCANS_DIR, "./custom-output"
            )
            == "./custom-output"
        )

        # CLI specified, wins over scanjob
        set_source(mock_ctx, "results", ParameterSource.COMMANDLINE)
        assert (
            resolve_scan_option(mock_ctx, "results", "./cli-output", "./custom-output")
            == "./cli-output"
        )

    def test_model_args_derived_from_multiple_options(
        self, mock_ctx: MagicMock
    ) -> None:
        """Test model_args which is derived from -M and --model-config."""
        # Neither -M nor --model-config from CLI
        set_source(mock_ctx, "m", ParameterSource.DEFAULT)
        set_source(mock_ctx, "model_config", ParameterSource.DEFAULT)
        assert resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            {"timeout": 30},
            {"timeout": 60},
        ) == {"timeout": 60}

        # -M from CLI
        set_source(mock_ctx, "m", ParameterSource.COMMANDLINE)
        assert resolve_scan_option_multi(
            mock_ctx,
            ["m", "model_config"],
            {"timeout": 30},
            {"timeout": 60},
        ) == {"timeout": 30}

        # --model-config from env, -M from default
        set_source(mock_ctx, "m", ParameterSource.DEFAULT)
        set_source(mock_ctx, "model_config", ParameterSource.ENVIRONMENT)
        assert (
            resolve_scan_option_multi(
                mock_ctx,
                ["m", "model_config"],
                {"timeout": 30},
                {"timeout": 60},
            )
            == {"timeout": 60}  # scanjob wins because no CLI option
        )

    def test_generate_config_options(self, mock_ctx: MagicMock) -> None:
        """Test GenerateConfig options like temperature, max_tokens."""
        # Temperature from env, scanjob should win
        set_source(mock_ctx, "temperature", ParameterSource.ENVIRONMENT)
        assert resolve_scan_option(mock_ctx, "temperature", 0.7, 0.5) == 0.5

        # max_tokens from CLI, should win
        set_source(mock_ctx, "max_tokens", ParameterSource.COMMANDLINE)
        assert resolve_scan_option(mock_ctx, "max_tokens", 1000, 2000) == 1000

        # timeout from default, scanjob should win
        set_source(mock_ctx, "timeout", ParameterSource.DEFAULT)
        assert resolve_scan_option(mock_ctx, "timeout", None, 60) == 60


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for option resolution."""

    def test_falsy_but_valid_values(self, mock_ctx: MagicMock) -> None:
        """Test that falsy values (0, empty string, False) are handled correctly."""
        set_source(mock_ctx, "limit", ParameterSource.COMMANDLINE)

        # 0 is a valid value
        result_int = resolve_scan_option(mock_ctx, "limit", 0, 100)
        assert result_int == 0

        # Empty string (if valid for an option)
        set_source(mock_ctx, "tags", ParameterSource.COMMANDLINE)
        result_str = resolve_scan_option(mock_ctx, "tags", "", "default-tag")
        assert result_str == ""

    def test_scanjob_with_falsy_value(self, mock_ctx: MagicMock) -> None:
        """Test scanjob with falsy but valid values."""
        set_source(mock_ctx, "shuffle", ParameterSource.DEFAULT)

        # Scanjob value of 0 should NOT be used because it's falsy
        # This is actually a limitation of the current implementation
        # scan_job_value of 0 is falsy, so the check `if scan_job_value is not None`
        # passes, but the value 0 would be used if we checked `is not None`
        result = resolve_scan_option(mock_ctx, "shuffle", None, 0)
        # With `if scan_job_value is not None:` check, 0 IS used
        assert result == 0

    def test_default_map_source(self, mock_ctx: MagicMock) -> None:
        """Test with DEFAULT_MAP parameter source."""
        set_source(mock_ctx, "model", ParameterSource.DEFAULT_MAP)

        result = resolve_scan_option(
            mock_ctx,
            "model",
            option_value="default-map-model",
            scan_job_value="scanjob-model",
        )

        # DEFAULT_MAP != COMMANDLINE, so scanjob wins
        assert result == "scanjob-model"

    def test_type_preservation_dict(self, mock_ctx: MagicMock) -> None:
        """Test that dict types are preserved through resolution."""
        set_source(mock_ctx, "batch", ParameterSource.COMMANDLINE)

        batch_config: dict[str, Any] = {"size": 100, "enabled": True}
        result = resolve_scan_option(mock_ctx, "batch", batch_config, None)
        assert result == batch_config
        assert isinstance(result, dict)

    def test_type_preservation_bool(self, mock_ctx: MagicMock) -> None:
        """Test that bool types are preserved through resolution."""
        set_source(mock_ctx, "cache", ParameterSource.COMMANDLINE)
        result = resolve_scan_option(mock_ctx, "cache", True, False)
        assert result is True
        assert isinstance(result, bool)
