"""Tests for the dependency cooldown in pyproject.toml and the CI jobs around it.

pyproject.toml holds back releases younger than seven days, or six hours for
model provider SDKs. Inspect packages are ours and have no cooldown. Every
package, Inspect ones included, comes from PyPI. Dependabot applies the seven
days to its uv.lock bumps and leaves the shorter cooldowns to uv. Every CI job
installs from uv.lock. Testing against the newest releases happens in
meridianlabs-ai/canaries, outside this repository.
"""

import pathlib
import re
import tomllib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml

REPO = pathlib.Path(__file__).parents[1]
GITHUB = REPO / ".github"
WORKFLOWS = GITHUB / "workflows"
SHARED_ACTIONS = "meridianlabs-ai/actions/"
INSTALL_ACTION = SHARED_ACTIONS + "install-python-dependencies@"
MATRIX_PYTHON = "${{ matrix.python-version }}"
LOCKED_JOBS = {
    "py-ruff": {"python-version": "3.11", "project-install": "skip", "extras": "dev"},
    "py-mypy": {"python-version": MATRIX_PYTHON, "extras": "dev"},
    "py-test": {"python-version": MATRIX_PYTHON, "extras": "dev"},
    "py-build": {"python-version": MATRIX_PYTHON, "project-install": "skip"},
    "check-schema-and-types": {"python-version": "3.11"},
}
EXEMPT_COOLDOWN = "6 hours"
IN_HOUSE_COOLDOWN = False


def pyproject() -> dict[str, Any]:
    return tomllib.loads((REPO / "pyproject.toml").read_text())


def uv_config() -> dict[str, Any]:
    config: dict[str, Any] = pyproject()["tool"]["uv"]
    return config


def normalize(package: str) -> str:
    return re.sub(r"[-_.]+", "-", package).lower()


def in_house(package: str) -> bool:
    return normalize(package).startswith(("inspect-", "petri"))


def direct_dependencies() -> set[str]:
    """Packages in the pyproject.toml `dependencies` or the `dev` extra."""
    project = pyproject()["project"]
    requirements = project["dependencies"] + project["optional-dependencies"]["dev"]
    return {
        normalize(re.split(r"[^A-Za-z0-9._-]", requirement, maxsplit=1)[0])
        for requirement in requirements
    }


def cooldown_days(exclude_newer: str) -> int:
    days = re.fullmatch(r"(\d+) days", exclude_newer)
    assert days, exclude_newer
    return int(days[1])


def dependabot_uv() -> dict[str, Any]:
    config = yaml.safe_load((GITHUB / "dependabot.yml").read_text())
    updates: list[dict[str, Any]] = config["updates"]
    root = [
        u for u in updates if u["package-ecosystem"] == "uv" and u["directory"] == "/"
    ]
    assert len(root) == 1, "expected one uv entry for directory / in dependabot.yml"
    return root[0]


def workflows() -> list[pathlib.Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def run_lines(job: dict[str, Any]) -> list[str]:
    # Joins backslash continuations so a command's flags stay on one line.
    return [
        line.strip()
        for step in job.get("steps", [])
        for line in step.get("run", "").replace("\\\n", " ").splitlines()
        if line.strip()
    ]


def all_steps() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"{path.name}:{name}", step)
        for path in workflows()
        for name, job in yaml.safe_load(path.read_text())["jobs"].items()
        for step in job.get("steps", [])
    ]


def workflow_run_lines() -> list[tuple[str, str]]:
    return [
        (f"{path.name}:{name}", line)
        for path in workflows()
        for name, job in yaml.safe_load(path.read_text())["jobs"].items()
        for line in run_lines(job)
    ]


def verify_exclude_newer_package(
    config: dict[str, Any], direct: set[str], now: datetime
) -> None:
    # Each entry is false for an in-house package, "6 hours" for any other
    # package, or a dated entry younger than the cooldown.
    max_age = timedelta(days=cooldown_days(config["exclude-newer"]))
    entries = config["exclude-newer-package"]
    for package, cooldown in entries.items():
        assert normalize(package) in direct, f"{package} is not a direct dependency"
        if cooldown is IN_HOUSE_COOLDOWN:
            assert in_house(package), f"{package} = false but is not in-house"
        elif cooldown == EXEMPT_COOLDOWN:
            assert not in_house(package), f'in-house {package} = "{cooldown}"'
        else:
            assert isinstance(cooldown, str), f"{package} = {cooldown!r}"
            age = now - datetime.fromisoformat(cooldown)
            assert timedelta(0) <= age < max_age, (
                f'dated entry {package} = "{cooldown}" is in the future or stale'
            )
    no_cooldown = {normalize(p) for p, c in entries.items() if c is IN_HOUSE_COOLDOWN}
    missing = sorted(p for p in direct if in_house(p) and p not in no_cooldown)
    assert missing == [], f"in-house packages not set to false: {missing}"


def test_exclude_newer_package_entries() -> None:
    verify_exclude_newer_package(uv_config(), direct_dependencies(), datetime.now(UTC))


def test_non_direct_entry_is_caught() -> None:
    config = uv_config()
    config["exclude-newer-package"]["certifi"] = EXEMPT_COOLDOWN
    with pytest.raises(AssertionError, match="not a direct dependency"):
        verify_exclude_newer_package(config, direct_dependencies(), datetime.now(UTC))


def test_fresh_dated_entry_passes() -> None:
    config = uv_config()
    now = datetime.now(UTC)
    config["exclude-newer-package"]["duckdb"] = (now - timedelta(days=6)).isoformat()
    verify_exclude_newer_package(config, direct_dependencies(), now)
    verify_dependabot_cooldown(config, dependabot_uv())


def test_stale_dated_entry_is_caught() -> None:
    config = uv_config()
    now = datetime.now(UTC)
    config["exclude-newer-package"]["duckdb"] = (now - timedelta(days=7)).isoformat()
    with pytest.raises(AssertionError, match="dated entry"):
        verify_exclude_newer_package(config, direct_dependencies(), now)


def test_future_dated_entry_is_caught() -> None:
    config = uv_config()
    now = datetime.now(UTC)
    config["exclude-newer-package"]["duckdb"] = (now + timedelta(days=1)).isoformat()
    with pytest.raises(AssertionError, match="dated entry"):
        verify_exclude_newer_package(config, direct_dependencies(), now)


@pytest.mark.parametrize(
    "package,cooldown",
    [
        ("duckdb", "1 day"),
        ("inspect-ai", "false"),
        ("inspect-ai", "0 hours"),
        ("inspect-ai", EXEMPT_COOLDOWN),
        ("inspect-ai", True),
        ("openai", IN_HOUSE_COOLDOWN),
        ("openai", "0 hours"),
    ],
)
def test_other_cooldown_value_is_caught(package: str, cooldown: str | bool) -> None:
    config = uv_config()
    config["exclude-newer-package"][package] = cooldown
    with pytest.raises((AssertionError, ValueError)):
        verify_exclude_newer_package(config, direct_dependencies(), datetime.now(UTC))


def test_missing_in_house_entry_is_caught() -> None:
    config = uv_config()
    del config["exclude-newer-package"]["inspect-swe"]
    with pytest.raises(AssertionError, match="not set to false"):
        verify_exclude_newer_package(config, direct_dependencies(), datetime.now(UTC))


def test_packages_come_from_pypi() -> None:
    assert "sources" not in uv_config()


def verify_dependabot_cooldown(
    config: dict[str, Any], dependabot: dict[str, Any]
) -> None:
    cooldown = dependabot["cooldown"]
    assert cooldown["default-days"] == cooldown_days(config["exclude-newer"])
    assert not dependabot.get("ignore")
    # Dependabot's cooldown counts whole days, so it leaves the false and
    # "6 hours" entries to uv. Dated entries are locked by hand.
    exempt = sorted(
        package
        for package, cooldown in config["exclude-newer-package"].items()
        if cooldown is IN_HOUSE_COOLDOWN or cooldown == EXEMPT_COOLDOWN
    )
    assert sorted(cooldown["exclude"]) == exempt
    # The exempt packages have their own group, listed before the catch-all.
    groups = dependabot["groups"]
    assert list(groups) == ["six-hour-cooldown", "python-packages"]
    assert sorted(groups["six-hour-cooldown"]["patterns"]) == exempt
    assert groups["python-packages"]["patterns"] == ["*"]


def test_dependabot_cooldown_matches_pyproject() -> None:
    verify_dependabot_cooldown(uv_config(), dependabot_uv())


def test_uv_comes_from_the_shared_setup_uv() -> None:
    # meridianlabs-ai/actions/setup-uv holds the uv pin. One commit for every
    # shared action means one uv.
    uses = [(where, step["uses"]) for where, step in all_steps() if "uses" in step]
    assert [u for u in uses if u[1].startswith("astral-sh/setup-uv@")] == []
    refs = {
        ref.split("@")[1].split()[0]
        for _, ref in uses
        if ref.startswith(SHARED_ACTIONS + "setup-uv@")
        or ref.startswith(INSTALL_ACTION)
    }
    assert len(refs) == 1, refs
    assert re.fullmatch(r"[0-9a-f]{40}", refs.pop())


def test_ruff_runs_from_the_locked_environment() -> None:
    # ruff-action without a version installs the newest ruff release.
    uses = [
        step.get("uses", "")
        for path in workflows()
        for job in yaml.safe_load(path.read_text())["jobs"].values()
        for step in job.get("steps", [])
    ]
    assert not [u for u in uses if u.startswith("astral-sh/ruff-action@")]
    job = yaml.safe_load((WORKFLOWS / "build.yaml").read_text())["jobs"]["py-ruff"]
    runs = run_lines(job)
    assert "uv run --no-sync ruff check --output-format github" in runs
    assert "uv run --no-sync ruff format --check --output-format github" in runs


@pytest.mark.parametrize("name,inputs", LOCKED_JOBS.items())
def test_locked_jobs_install_from_the_lockfile(
    name: str, inputs: dict[str, str]
) -> None:
    job = yaml.safe_load((WORKFLOWS / "build.yaml").read_text())["jobs"][name]
    installs = [
        step.get("with", {})
        for step in job["steps"]
        if step.get("uses", "").startswith(INSTALL_ACTION)
    ]
    assert installs == [{"versions": "locked", **inputs}]
    assert not [line for line in run_lines(job) if line.startswith("uv sync")]


# A bare `uv run` or `uv sync` re-resolves an out-of-date uv.lock and installs
# the result. `uv run --no-project` ignores the project and uv.lock. `--with`
# installs unlocked packages whatever the other flags.
def test_uv_never_relocks() -> None:
    unlocked = [
        (where, line)
        for where, line in workflow_run_lines()
        if re.search(r"\buv (run|sync)\b", line)
        and (
            "--with" in line
            or not {"--locked", "--no-sync", "--no-project"} & set(line.split())
        )
    ]
    assert unlocked == []


# pip installs skip uv.lock, so they may only add local packages without their
# dependencies, or install a hashed lock (`-r` or `uv pip sync`).
def test_pip_installs_are_dependency_free_or_hashed() -> None:
    unlocked = [
        (where, line)
        for where, line in workflow_run_lines()
        if (re.search(r"\bpip3? install\b", line) and "--no-deps" not in line.split())
        or (
            re.search(r"\bpip sync\b|\bpip3? install\b.* -r\b", line)
            and "--require-hashes" not in line.split()
        )
    ]
    assert unlocked == []


def test_no_workflow_opts_out_of_the_cooldown() -> None:
    floating = [
        (where, line)
        for where, line in workflow_run_lines()
        if re.search(r"--exclude-newer(=|\s+)false", line)
    ]
    assert floating == []
