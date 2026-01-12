"""LangFuse client management and retry logic."""

from logging import getLogger
from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = getLogger(__name__)

T = TypeVar("T")

# LangFuse source type constant
LANGFUSE_SOURCE_TYPE = "langfuse"

# HTTP status codes that indicate transient errors worth retrying
RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


def get_langfuse_client(
    public_key: str | None = None,
    secret_key: str | None = None,
    host: str | None = None,
) -> Any:
    """Get or create a LangFuse client.

    Args:
        public_key: LangFuse public key (or use LANGFUSE_PUBLIC_KEY env var)
        secret_key: LangFuse secret key (or use LANGFUSE_SECRET_KEY env var)
        host: LangFuse host URL (or use LANGFUSE_HOST env var)

    Returns:
        LangFuse client instance

    Raises:
        ImportError: If langfuse package is not installed
    """
    try:
        from langfuse import Langfuse
    except ImportError as e:
        raise ImportError(
            "The langfuse package is required for LangFuse import. "
            "Install it with: pip install langfuse"
        ) from e

    kwargs: dict[str, Any] = {}
    if public_key:
        kwargs["public_key"] = public_key
    if secret_key:
        kwargs["secret_key"] = secret_key
    if host:
        kwargs["host"] = host

    return Langfuse(**kwargs)


def resolve_project(langfuse_client: Any, project: str) -> tuple[str, str]:
    """Resolve a project name or ID to a project ID.

    Args:
        langfuse_client: LangFuse client instance
        project: Project name or ID

    Returns:
        Tuple of (project_id, project_name)

    Raises:
        ValueError: If the project cannot be found
    """
    # Get list of projects from API (with retry for transient errors)
    try:
        projects_response = retry_api_call(lambda: langfuse_client.api.projects.get())
        projects = getattr(projects_response, "data", [])
    except Exception as e:
        logger.warning(f"Failed to fetch projects list: {e}")
        # Fall back to using the value as-is (assume it's an ID)
        return project, project

    # First check if it matches any project ID
    for proj in projects:
        if getattr(proj, "id", None) == project:
            return project, str(getattr(proj, "name", project))

    # Then check if it matches any project name
    for proj in projects:
        if getattr(proj, "name", None) == project:
            return str(proj.id), project

    # If no match found, raise an error with available projects
    available = [
        f"{getattr(p, 'name', 'unknown')} ({getattr(p, 'id', 'unknown')})"
        for p in projects
    ]
    raise ValueError(
        f"Project '{project}' not found. Available projects: {', '.join(available)}"
    )


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
    """Execute a LangFuse API call with retry logic for transient errors.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s) on:
    - Network timeouts (httpx.TimeoutException)
    - Connection errors (httpx.ConnectError)
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
            f"LangFuse API call failed ({exc_name}), "
            f"retrying in {sleep_time:.1f}s... "
            f"(attempt {retry_state.attempt_number}/3)"
        )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
    def _call_with_retry() -> T:
        try:
            return func()
        except Exception as e:
            if _is_retryable_error(e):
                raise
            # Non-retryable errors should not be retried
            raise e from None

    return _call_with_retry()
