"""Phoenix test configuration and fixtures.

Provides skip decorators and fixtures for Phoenix integration tests.

Authentication:
    Set PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT environment variables.
"""

import os
from typing import Any, Callable, TypeVar, cast

import pytest

# Test project name for Phoenix tests
PHOENIX_TEST_PROJECT = "default"

F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_phoenix(func: F) -> F:
    """Skip test if Phoenix test environment is not configured.

    Requires:
    - PHOENIX_RUN_TESTS=1 (explicit opt-in)

    Args:
        func: Test function to decorate

    Returns:
        Decorated function with skip marker
    """
    run_tests = os.environ.get("PHOENIX_RUN_TESTS", "").lower() in ("1", "true")

    return cast(
        F,
        pytest.mark.api(
            pytest.mark.skipif(
                not run_tests,
                reason="Phoenix tests require PHOENIX_RUN_TESTS=1",
            )(func)
        ),
    )


@pytest.fixture(autouse=True)
def no_fallback_warnings(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Assert no fallback warnings from extraction during integration tests.

    Monkeypatches logger.warning in both extraction and __init__ modules to
    record calls. After the test, asserts no warnings were emitted — confirming
    the native import path was used (not _simple_message_conversion).

    Yields:
        List of captured warning messages (empty if native path succeeded).
    """
    warnings: list[str] = []

    def _capture_warning(msg: str, *args: Any, **kwargs: Any) -> None:
        warnings.append(msg % args if args else msg)

    import inspect_scout.sources._phoenix as phoenix_pkg
    import inspect_scout.sources._phoenix.extraction as phoenix_extraction

    monkeypatch.setattr(phoenix_extraction.logger, "warning", _capture_warning)
    monkeypatch.setattr(phoenix_pkg.logger, "warning", _capture_warning)

    yield warnings

    assert not warnings, f"Extraction fell back to simple conversion: {warnings}"


@pytest.fixture
def phoenix_project() -> str:
    """Return the test project name for Phoenix tests.

    Returns:
        The test project name
    """
    return os.environ.get("PHOENIX_PROJECT", PHOENIX_TEST_PROJECT)


@pytest.fixture
def phoenix_client() -> Any:
    """Create a Phoenix client for testing.

    Uses PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT environment variables.

    Returns:
        Phoenix AsyncClient instance

    Raises:
        pytest.skip: If phoenix package is not installed or credentials not set
    """
    try:
        from inspect_scout.sources._phoenix.client import get_phoenix_client
    except ImportError:
        pytest.skip("arize-phoenix-client package not installed")

    try:
        return get_phoenix_client()
    except ValueError as e:
        pytest.skip(str(e))
