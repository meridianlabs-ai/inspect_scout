"""LangSmith test configuration and fixtures.

Provides skip decorators and fixtures for LangSmith integration tests.
"""

import os
from typing import Any, Callable, TypeVar, cast

import pytest

# Test project name for LangSmith tests
LANGSMITH_TEST_PROJECT = "inspect-scout-tests-v2"

F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_langsmith(func: F) -> F:
    """Skip test if LangSmith test environment is not configured.

    Requires both:
    - LANGSMITH_RUN_TESTS=1 (explicit opt-in)
    - LANGSMITH_API_KEY (for API access)

    Args:
        func: Test function to decorate

    Returns:
        Decorated function with skip marker
    """
    run_tests = os.environ.get("LANGSMITH_RUN_TESTS", "").lower() in ("1", "true")
    api_key = os.environ.get("LANGSMITH_API_KEY")

    return cast(
        F,
        pytest.mark.api(
            pytest.mark.skipif(
                not (run_tests and api_key),
                reason="LangSmith tests require LANGSMITH_RUN_TESTS=1 and LANGSMITH_API_KEY",
            )(func)
        ),
    )


@pytest.fixture
def langsmith_project() -> str:
    """Return the test project name for LangSmith tests.

    Returns:
        The test project name
    """
    return os.environ.get("LANGSMITH_PROJECT", LANGSMITH_TEST_PROJECT)


@pytest.fixture
def langsmith_client() -> Any:
    """Create a LangSmith client for testing.

    Returns:
        LangSmith client instance

    Raises:
        pytest.skip: If LangSmith package is not installed or API key not set
    """
    try:
        from langsmith import Client
    except ImportError:
        pytest.skip("langsmith package not installed")

    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        pytest.skip("LANGSMITH_API_KEY not set")

    return Client(api_key=api_key)
