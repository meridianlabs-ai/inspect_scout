"""W&B Weave test configuration and fixtures.

Provides skip decorators and fixtures for Weave integration tests.
"""

import os
from typing import Any, Callable, TypeVar, cast

import pytest

# Test project name for Weave tests
WEAVE_TEST_PROJECT = os.environ.get("WEAVE_PROJECT", "inspect-scout/scout-tests")

F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_weave(func: F) -> F:
    """Skip test if Weave test environment is not configured.

    Requires both:
    - WEAVE_RUN_TESTS=1 (explicit opt-in)
    - WANDB_API_KEY (for API access)

    Args:
        func: Test function to decorate

    Returns:
        Decorated function with skip marker
    """
    run_tests = os.environ.get("WEAVE_RUN_TESTS", "").lower() in ("1", "true")
    api_key = os.environ.get("WANDB_API_KEY")

    return cast(
        F,
        pytest.mark.api(
            pytest.mark.skipif(
                not (run_tests and api_key),
                reason="Weave tests require WEAVE_RUN_TESTS=1 and WANDB_API_KEY",
            )(func)
        ),
    )


@pytest.fixture
def weave_project() -> str:
    """Return the test project name for Weave tests.

    Returns:
        The test project name
    """
    return WEAVE_TEST_PROJECT


@pytest.fixture
def weave_client() -> Any:
    """Create a Weave client for testing.

    Returns:
        Weave client instance

    Raises:
        pytest.skip: If weave package is not installed or API key not set
    """
    try:
        import weave
    except ImportError:
        pytest.skip("weave package not installed")

    api_key = os.environ.get("WANDB_API_KEY")
    if not api_key:
        pytest.skip("WANDB_API_KEY not set")

    project = os.environ.get("WEAVE_PROJECT", WEAVE_TEST_PROJECT)
    return weave.init(project)
