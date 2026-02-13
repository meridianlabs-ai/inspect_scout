"""Tests for Phoenix client creation and error handling."""

import os
from unittest.mock import patch

import pytest
from inspect_scout.sources._phoenix.client import (
    PHOENIX_SOURCE_TYPE,
    _is_rate_limit_error,
    _is_retryable_error,
    get_phoenix_client,
)


class TestGetPhoenixClient:
    """Tests for get_phoenix_client function."""

    def test_missing_api_key_raises_value_error(self) -> None:
        """Raise ValueError when no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove both possible env vars
            env = {k: v for k, v in os.environ.items() if k != "PHOENIX_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="API key is required"):
                    get_phoenix_client()

    def test_api_key_from_parameter(self) -> None:
        """Create client with explicit API key."""
        client = get_phoenix_client(api_key="test-key")
        assert client is not None

    def test_api_key_from_env(self) -> None:
        """Create client with API key from environment."""
        with patch.dict(os.environ, {"PHOENIX_API_KEY": "env-key"}):
            client = get_phoenix_client()
            assert client is not None

    def test_base_url_from_parameter(self) -> None:
        """Create client with explicit base URL."""
        client = get_phoenix_client(
            api_key="test-key", base_url="https://phoenix.example.com"
        )
        assert client is not None

    def test_source_type_constant(self) -> None:
        """Verify source type constant."""
        assert PHOENIX_SOURCE_TYPE == "phoenix"


class TestRetryableErrors:
    """Tests for error classification functions."""

    def test_timeout_is_retryable(self) -> None:
        """Timeout errors should be retryable."""

        class TimeoutError(Exception):
            pass

        assert _is_retryable_error(TimeoutError("request timed out"))

    def test_connection_error_is_retryable(self) -> None:
        """Connection errors should be retryable."""

        class ConnectionError(Exception):
            pass

        assert _is_retryable_error(ConnectionError("connection refused"))

    def test_rate_limit_string_is_retryable(self) -> None:
        """Rate limit errors identified by string should be retryable."""
        assert _is_retryable_error(Exception("rate limit exceeded"))
        assert _is_retryable_error(Exception("429 Too Many Requests"))

    def test_generic_error_not_retryable(self) -> None:
        """Generic errors should not be retryable."""
        assert not _is_retryable_error(Exception("invalid input"))
        assert not _is_retryable_error(ValueError("bad value"))

    def test_rate_limit_detection(self) -> None:
        """Rate limit errors should be detected."""
        assert _is_rate_limit_error(Exception("rate limit exceeded"))
        assert _is_rate_limit_error(Exception("429"))
        assert not _is_rate_limit_error(Exception("server error"))
