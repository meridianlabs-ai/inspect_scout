"""Logfire test configuration and fixtures.

Provides skip decorators and fixtures for Logfire integration tests.

Authentication:
    Logfire uses browser-based authentication. Run `logfire auth` to authenticate
    and store credentials in ~/.logfire/default.toml. Then use `logfire projects use <name>`
    to select a project.
"""

import os
from typing import Any, Callable, TypeVar, cast

import pytest

# Test project name for Logfire tests
LOGFIRE_TEST_PROJECT = "scout-import-testing"

F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_logfire(func: F) -> F:
    """Skip test if Logfire test environment is not configured.

    Requires:
    - LOGFIRE_RUN_TESTS=1 (explicit opt-in)

    Authentication is handled via browser auth (`logfire auth`) which stores
    credentials in ~/.logfire/default.toml.

    Args:
        func: Test function to decorate

    Returns:
        Decorated function with skip marker
    """
    run_tests = os.environ.get("LOGFIRE_RUN_TESTS", "").lower() in ("1", "true")

    return cast(
        F,
        pytest.mark.api(
            pytest.mark.skipif(
                not run_tests,
                reason="Logfire tests require LOGFIRE_RUN_TESTS=1 (run `logfire auth` first)",
            )(func)
        ),
    )


@pytest.fixture
def logfire_project() -> str:
    """Return the test project name for Logfire tests.

    Returns:
        The test project name
    """
    return os.environ.get("LOGFIRE_PROJECT", LOGFIRE_TEST_PROJECT)


@pytest.fixture
def logfire_client() -> Any:
    """Create a Logfire query client for testing.

    Uses LOGFIRE_READ_TOKEN environment variable for authentication.

    Returns:
        AsyncLogfireQueryClient instance

    Raises:
        pytest.skip: If logfire package is not installed or token not set
    """
    try:
        from inspect_scout.sources._logfire.client import get_logfire_client
    except ImportError:
        pytest.skip("logfire package not installed")

    try:
        return get_logfire_client()
    except ValueError as e:
        pytest.skip(str(e))
