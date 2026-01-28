"""Tests for Logfire client functionality."""

import os
from unittest.mock import patch

import pytest


class TestGetLogfireClient:
    """Tests for get_logfire_client function."""

    def test_missing_token_raises_error(self) -> None:
        """Raise error when no read token provided."""
        pytest.importorskip("logfire")

        from inspect_scout.sources._logfire.client import get_logfire_client

        with patch.dict(os.environ, {}, clear=True):
            # Remove LOGFIRE_READ_TOKEN if present
            if "LOGFIRE_READ_TOKEN" in os.environ:
                del os.environ["LOGFIRE_READ_TOKEN"]

            with pytest.raises(ValueError, match="read token is required"):
                get_logfire_client()

    def test_token_from_parameter(self) -> None:
        """Accept token from parameter."""
        pytest.importorskip("logfire")

        from inspect_scout.sources._logfire.client import get_logfire_client

        # Should not raise - token provided as parameter
        client = get_logfire_client(read_token="test-token")
        assert client is not None

    def test_token_from_env_var(self) -> None:
        """Accept token from environment variable."""
        pytest.importorskip("logfire")

        from inspect_scout.sources._logfire.client import get_logfire_client

        with patch.dict(os.environ, {"LOGFIRE_READ_TOKEN": "env-token"}):
            client = get_logfire_client()
            assert client is not None


class TestRetryableErrors:
    """Tests for error classification."""

    def test_rate_limit_error_detection(self) -> None:
        """Detect rate limit errors from message."""
        from inspect_scout.sources._logfire.client import _is_rate_limit_error

        class MockError(Exception):
            pass

        assert _is_rate_limit_error(MockError("rate limit exceeded"))
        assert _is_rate_limit_error(MockError("429 Too Many Requests"))
        assert not _is_rate_limit_error(MockError("connection failed"))

    def test_retryable_error_detection(self) -> None:
        """Detect retryable errors."""
        from inspect_scout.sources._logfire.client import _is_retryable_error

        class TimeoutError(Exception):
            pass

        class ConnectionError(Exception):
            pass

        class OtherError(Exception):
            pass

        assert _is_retryable_error(TimeoutError())
        assert _is_retryable_error(ConnectionError())
        # Generic error without retry signals
        assert not _is_retryable_error(OtherError("something went wrong"))
