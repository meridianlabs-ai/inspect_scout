import importlib.util
import os
import subprocess
from typing import Any, Callable, TypeVar, cast

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--runapi", action="store_true", default=False, help="run API tests"
    )
    parser.addoption(
        "--runflaky", action="store_true", default=False, help="run flaky tests"
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "api: mark test as requiring API access")
    config.addinivalue_line("markers", "flaky: mark test as flaky/unreliable")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--runapi"):
        skip_api = pytest.mark.skip(reason="need --runapi option to run")
        for item in items:
            if "api" in item.keywords:
                item.add_marker(skip_api)

    if not config.getoption("--runflaky"):
        skip_flaky = pytest.mark.skip(reason="need --runflaky option to run")
        for item in items:
            if "flaky" in item.keywords:
                item.add_marker(skip_flaky)


def skip_if_env_var(var: str, exists: bool = True) -> pytest.MarkDecorator:
    """
    Pytest mark to skip the test if the var environment variable is not defined.

    Use in combination with `pytest.mark.api` if the environment variable in
    question corresponds to a paid API. For example, see `skip_if_no_openai`.
    """
    condition = (var in os.environ.keys()) if exists else (var not in os.environ.keys())
    return pytest.mark.skipif(
        condition,
        reason=f"Test doesn't work without {var} environment variable defined.",
    )


F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_openai(func: F) -> F:
    return cast(
        F,
        pytest.mark.api(
            pytest.mark.skipif(
                importlib.util.find_spec("openai") is None
                or os.environ.get("OPENAI_API_KEY") is None,
                reason="Test requires both OpenAI package and OPENAI_API_KEY environment variable",
            )(func)
        ),
    )


def skip_if_no_anthropic(func: F) -> F:
    return cast(
        F, pytest.mark.api(skip_if_env_var("ANTHROPIC_API_KEY", exists=False)(func))
    )


def skip_if_no_google(func: F) -> F:
    return cast(
        F, pytest.mark.api(skip_if_env_var("GOOGLE_API_KEY", exists=False)(func))
    )


def skip_if_github_action(func: F) -> F:
    return cast(F, skip_if_env_var("GITHUB_ACTIONS", exists=True)(func))


def skip_if_no_docker(func: F) -> F:
    try:
        is_docker_installed = (
            subprocess.run(
                ["docker", "--version"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).returncode
            == 0
        )
    except FileNotFoundError:
        is_docker_installed = False

    return cast(
        F,
        pytest.mark.skipif(
            not is_docker_installed,
            reason="Test doesn't work without Docker installed.",
        )(func),
    )


def skip_if_no_langfuse_project(func: F) -> F:
    proj_public = os.environ.get("LANGFUSE_PUBLIC_KEY", None)
    return cast(
        F,
        pytest.mark.skipif(
            proj_public != "pk-lf-e69093b6-f217-407c-8841-a9923ad359a5",
            reason="Test requires Langfuse test project",
        )(func),
    )
