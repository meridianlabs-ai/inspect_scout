"""Logfire client management and retry logic."""

import os
from logging import getLogger
from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
)

logger = getLogger(__name__)

T = TypeVar("T")

# Logfire source type constant
LOGFIRE_SOURCE_TYPE = "logfire"

# HTTP status codes that indicate transient errors worth retrying
RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})

# Rate limit specific settings
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_MIN_WAIT = 2  # seconds
RATE_LIMIT_MAX_WAIT = 60  # seconds


def get_logfire_client(
    read_token: str | None = None,
) -> Any:
    """Get or create an async Logfire query client.

    Uses credentials in this order:
    1. Explicit read_token parameter
    2. LOGFIRE_READ_TOKEN environment variable

    Args:
        read_token: Optional Logfire read token

    Returns:
        AsyncLogfireQueryClient instance

    Raises:
        ImportError: If logfire package is not installed
        ValueError: If no read token is provided or found in environment
    """
    try:
        from logfire.query_client import AsyncLogfireQueryClient
    except ImportError as e:
        raise ImportError(
            "The logfire package is required for Logfire import. "
            "Install it with: pip install logfire"
        ) from e

    token = read_token or os.environ.get("LOGFIRE_READ_TOKEN")
    if not token:
        raise ValueError(
            "Logfire read token is required. Provide read_token parameter "
            "or set LOGFIRE_READ_TOKEN environment variable. "
            "Generate a read token from the Logfire dashboard."
        )

    return AsyncLogfireQueryClient(read_token=token)


def _is_retryable_error(exception: BaseException) -> bool:
    """Check if an exception is retryable (timeout, rate limit, server error).

    Args:
        exception: The exception to check

    Returns:
        True if the error is transient and should be retried
    """
    # Import httpx types if available
    try:
        import httpx

        if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code in RETRYABLE_HTTP_CODES
    except ImportError:
        pass

    # Check for generic timeout/connection errors by name
    exc_name = type(exception).__name__
    if "Timeout" in exc_name or "ConnectionError" in exc_name:
        return True

    # Check for rate limit errors
    exc_str = str(exception).lower()
    if "rate limit" in exc_str or "429" in exc_str or "too many requests" in exc_str:
        return True

    return False


def _is_rate_limit_error(exception: BaseException) -> bool:
    """Check if an exception is specifically a rate limit error (HTTP 429).

    Args:
        exception: The exception to check

    Returns:
        True if this is a rate limit error that needs longer backoff
    """
    try:
        import httpx

        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code == 429
    except ImportError:
        pass

    # Check error message
    exc_str = str(exception).lower()
    return "rate limit" in exc_str or "429" in exc_str or "too many requests" in exc_str


def _get_retry_after(exception: BaseException) -> float | None:
    """Extract Retry-After header value from rate limit error if available.

    Args:
        exception: The exception to check

    Returns:
        Seconds to wait, or None if not available
    """
    try:
        import httpx

        if isinstance(exception, httpx.HTTPStatusError):
            retry_after = exception.response.headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
    except ImportError:
        pass
    return None


async def retry_api_call_async(func: Callable[[], Any]) -> Any:
    """Execute a Logfire API call with retry logic for transient errors.

    Uses adaptive retry strategy:
    - For rate limits (429): Up to 5 attempts with longer backoff (2-60s)
    - Respects Retry-After header when present
    - For other errors: 5 attempts with exponential backoff (1-30s)

    Args:
        func: Zero-argument async callable that makes the API call

    Returns:
        The result of the API call

    Raises:
        The original exception if all retries fail or error is not retryable
    """

    def _log_retry(retry_state: Any) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        exc_name = type(exc).__name__ if exc else "Unknown"
        sleep_time = retry_state.next_action.sleep if retry_state.next_action else 0
        is_rate_limit = _is_rate_limit_error(exc) if exc else False
        error_type = "rate limited" if is_rate_limit else "failed"
        logger.warning(
            f"Logfire API call {error_type} ({exc_name}), "
            f"retrying in {sleep_time:.1f}s... "
            f"(attempt {retry_state.attempt_number}/{RATE_LIMIT_MAX_ATTEMPTS})"
        )

    def _wait_with_rate_limit_handling(retry_state: Any) -> float:
        """Calculate wait time, respecting Retry-After for rate limits."""
        exc = retry_state.outcome.exception() if retry_state.outcome else None

        if exc and _is_rate_limit_error(exc):
            # Check for Retry-After header
            retry_after = _get_retry_after(exc)
            if retry_after:
                wait_time = min(retry_after, float(RATE_LIMIT_MAX_WAIT))
                logger.info(f"Rate limit: waiting {wait_time}s per Retry-After header")
                return wait_time
            # No Retry-After, use longer exponential backoff for rate limits
            attempt: int = retry_state.attempt_number
            wait_time = float(
                min(
                    RATE_LIMIT_MIN_WAIT * (2 ** (attempt - 1)),
                    RATE_LIMIT_MAX_WAIT,
                )
            )
            return wait_time

        # Standard exponential backoff for other errors
        attempt_num: int = retry_state.attempt_number
        return float(min(1 * (2 ** (attempt_num - 1)), 30))

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(RATE_LIMIT_MAX_ATTEMPTS),
        wait=_wait_with_rate_limit_handling,
        before_sleep=_log_retry,
        reraise=True,
    )
    async def _call_with_retry() -> Any:
        return await func()

    return await _call_with_retry()
