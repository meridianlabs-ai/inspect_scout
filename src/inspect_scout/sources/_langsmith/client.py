"""LangSmith client management and retry logic."""

from logging import getLogger
from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = getLogger(__name__)

T = TypeVar("T")

# LangSmith source type constant
LANGSMITH_SOURCE_TYPE = "langsmith"

# HTTP status codes that indicate transient errors worth retrying
RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


def get_langsmith_client(
    api_key: str | None = None,
    api_url: str | None = None,
) -> Any:
    """Get or create a LangSmith client.

    Args:
        api_key: LangSmith API key (or use LANGSMITH_API_KEY env var)
        api_url: LangSmith API URL (or use LANGSMITH_ENDPOINT env var)

    Returns:
        LangSmith client instance

    Raises:
        ImportError: If langsmith package is not installed
    """
    try:
        from langsmith import Client
    except ImportError as e:
        raise ImportError(
            "The langsmith package is required for LangSmith import. "
            "Install it with: pip install langsmith"
        ) from e

    kwargs: dict[str, Any] = {}
    if api_key:
        kwargs["api_key"] = api_key
    if api_url:
        kwargs["api_url"] = api_url

    return Client(**kwargs)


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

    return False


def retry_api_call(func: Callable[[], T]) -> T:
    """Execute a LangSmith API call with retry logic for transient errors.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s) on:
    - Network timeouts
    - Connection errors
    - Rate limits (HTTP 429)
    - Server errors (HTTP 5xx)

    Args:
        func: Zero-argument callable that makes the API call

    Returns:
        The result of the API call

    Raises:
        The original exception if all retries fail or error is not retryable
    """

    def _log_retry(retry_state: Any) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        exc_name = type(exc).__name__ if exc else "Unknown"
        sleep_time = retry_state.next_action.sleep if retry_state.next_action else 0
        logger.warning(
            f"LangSmith API call failed ({exc_name}), "
            f"retrying in {sleep_time:.1f}s... "
            f"(attempt {retry_state.attempt_number}/3)"
        )

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def _call_with_retry() -> T:
        return func()

    return _call_with_retry()
