"""Tests for LangSmith client management and retry logic.

Tests get_langsmith_client(), _is_retryable_error(), and retry_api_call()
functions that handle client setup and transient error retries.
"""

from unittest.mock import MagicMock, patch

import pytest
from inspect_scout.sources._langsmith.client import (
    RATE_LIMIT_MAX_ATTEMPTS,
    RETRYABLE_HTTP_CODES,
    _is_retryable_error,
    get_langsmith_client,
    retry_api_call,
)


class TestGetLangsmithClient:
    """Tests for get_langsmith_client function."""

    def test_import_error_when_langsmith_not_installed(self) -> None:
        """Raise ImportError when langsmith package is not installed."""
        with patch.dict("sys.modules", {"langsmith": None}):
            with pytest.raises(ImportError, match="langsmith package is required"):
                get_langsmith_client()

    def test_client_created_with_api_key(self) -> None:
        """Create client with provided API key."""
        mock_client = MagicMock()
        with patch("langsmith.Client") as mock_cls:
            mock_cls.return_value = mock_client

            result = get_langsmith_client(api_key="test-key")

            mock_cls.assert_called_once_with(api_key="test-key")
            assert result == mock_client

    def test_client_created_with_api_url(self) -> None:
        """Create client with provided API URL."""
        mock_client = MagicMock()
        with patch("langsmith.Client") as mock_cls:
            mock_cls.return_value = mock_client

            result = get_langsmith_client(api_url="https://custom.langsmith.com")

            mock_cls.assert_called_once_with(api_url="https://custom.langsmith.com")
            assert result == mock_client

    def test_client_created_with_both_params(self) -> None:
        """Create client with both API key and URL."""
        mock_client = MagicMock()
        with patch("langsmith.Client") as mock_cls:
            mock_cls.return_value = mock_client

            result = get_langsmith_client(
                api_key="test-key", api_url="https://custom.langsmith.com"
            )

            mock_cls.assert_called_once_with(
                api_key="test-key", api_url="https://custom.langsmith.com"
            )
            assert result == mock_client

    def test_client_created_with_no_params(self) -> None:
        """Create client with no params (uses env vars)."""
        mock_client = MagicMock()
        with patch("langsmith.Client") as mock_cls:
            mock_cls.return_value = mock_client

            result = get_langsmith_client()

            mock_cls.assert_called_once_with()
            assert result == mock_client


class TestIsRetryableError:
    """Tests for _is_retryable_error function."""

    def test_timeout_exception_is_retryable(self) -> None:
        """Timeout exceptions should be retryable."""

        class TimeoutException(Exception):
            pass

        assert _is_retryable_error(TimeoutException("timed out"))

    def test_connection_error_is_retryable(self) -> None:
        """Connection errors should be retryable."""

        class ConnectionError(Exception):
            pass

        assert _is_retryable_error(ConnectionError("connection failed"))

    def test_generic_exception_not_retryable(self) -> None:
        """Generic exceptions should not be retryable."""
        assert not _is_retryable_error(ValueError("bad value"))
        assert not _is_retryable_error(KeyError("missing key"))
        assert not _is_retryable_error(RuntimeError("runtime error"))

    def test_httpx_timeout_is_retryable(self) -> None:
        """Httpx TimeoutException should be retryable."""
        try:
            import httpx

            exc = httpx.TimeoutException("read timeout")
            assert _is_retryable_error(exc)
        except ImportError:
            pytest.skip("httpx not installed")

    def test_httpx_connect_error_is_retryable(self) -> None:
        """Httpx ConnectError should be retryable."""
        try:
            import httpx

            exc = httpx.ConnectError("connection refused")
            assert _is_retryable_error(exc)
        except ImportError:
            pytest.skip("httpx not installed")

    def test_retryable_http_status_codes(self) -> None:
        """HTTP 429, 500, 502, 503, 504 should be retryable."""
        try:
            import httpx

            for code in RETRYABLE_HTTP_CODES:
                response = httpx.Response(code)
                exc = httpx.HTTPStatusError(
                    f"HTTP {code}", request=MagicMock(), response=response
                )
                assert _is_retryable_error(exc), f"HTTP {code} should be retryable"
        except ImportError:
            pytest.skip("httpx not installed")

    def test_non_retryable_http_status_codes(self) -> None:
        """HTTP 400, 401, 403, 404 should not be retryable."""
        try:
            import httpx

            non_retryable_codes = [400, 401, 403, 404, 422]
            for code in non_retryable_codes:
                response = httpx.Response(code)
                exc = httpx.HTTPStatusError(
                    f"HTTP {code}", request=MagicMock(), response=response
                )
                assert not _is_retryable_error(exc), (
                    f"HTTP {code} should NOT be retryable"
                )
        except ImportError:
            pytest.skip("httpx not installed")


class TestRetryApiCall:
    """Tests for retry_api_call function."""

    def test_successful_call_returns_result(self) -> None:
        """Successful call returns result without retry."""
        func = MagicMock(return_value="success")

        result = retry_api_call(func)

        assert result == "success"
        func.assert_called_once()

    def test_retries_on_transient_error(self) -> None:
        """Retries on transient error then succeeds."""

        class TimeoutException(Exception):
            pass

        call_count = 0

        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutException("timeout")
            return "success"

        result = retry_api_call(flaky_func)

        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self) -> None:
        """Raises original exception after max retries."""

        class TimeoutException(Exception):
            pass

        call_count = 0

        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise TimeoutException("timeout")

        with pytest.raises(TimeoutException):
            retry_api_call(always_fails)

        # Should have tried RATE_LIMIT_MAX_ATTEMPTS times
        assert call_count == RATE_LIMIT_MAX_ATTEMPTS

    def test_no_retry_on_non_retryable_error(self) -> None:
        """Does not retry on non-retryable errors."""
        call_count = 0

        def fails_with_value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("bad value")

        with pytest.raises(ValueError):
            retry_api_call(fails_with_value_error)

        # Should have tried only once
        assert call_count == 1

    def test_returns_typed_result(self) -> None:
        """Returns correctly typed result."""

        def returns_list() -> list[int]:
            return [1, 2, 3]

        result = retry_api_call(returns_list)

        assert result == [1, 2, 3]
        assert isinstance(result, list)
