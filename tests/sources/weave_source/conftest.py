"""W&B Weave test configuration and fixtures.

Provides skip decorators and fixtures for Weave integration tests.
"""

import os
from typing import Any, Callable, TypeVar, cast

import pytest

# Default test project name for Weave tests
_DEFAULT_WEAVE_PROJECT = "inspect-scout/scout-tests"


def get_weave_test_project() -> str:
    """Return the Weave test project, reading env at call time."""
    return os.environ.get("WEAVE_PROJECT", _DEFAULT_WEAVE_PROJECT)

F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_weave(func: F) -> F:
    """Skip test if Weave test environment is not configured.

    Requires both:
    - WEAVE_RUN_TESTS=1 (explicit opt-in)
    - WANDB_API_KEY (for API access)

    Uses runtime ``pytest.skip()`` so that environment variables loaded by
    pytest-dotenv (which runs after module import) are visible.

    Args:
        func: Test function to decorate

    Returns:
        Decorated function with skip marker and runtime check
    """
    import functools

    @pytest.mark.api
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        run_tests = os.environ.get("WEAVE_RUN_TESTS", "").lower() in ("1", "true")
        api_key = os.environ.get("WANDB_API_KEY")
        if not (run_tests and api_key):
            pytest.skip("Weave tests require WEAVE_RUN_TESTS=1 and WANDB_API_KEY")
        return await func(*args, **kwargs)

    return cast(F, wrapper)


@pytest.fixture
def weave_project() -> str:
    """Return the test project name for Weave tests.

    Returns:
        The test project name
    """
    return get_weave_test_project()


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

    project = get_weave_test_project()
    return weave.init(project)
