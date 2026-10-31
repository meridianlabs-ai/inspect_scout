"""Tests for the dependency cooldown in pyproject.toml and the CI jobs around it.

pyproject.toml holds back releases younger than seven days, or six hours for a
short list of packages. Dependabot applies the seven days to its uv.lock bumps
and leaves that list to uv, and every CI job installs from uv.lock. Testing
against the newest releases happens in meridianlabs-ai/canaries, outside this
repository.
"""

import importlib.util
import pathlib
import re
import tomllib
from typing import Any

import pytest
import yaml

REPO = pathlib.Path(__file__).parents[1]
GITHUB = REPO / ".github"
WORKFLOWS = GITHUB / "workflows"
LOCKED_JOBS = {
    "py-mypy": "uv sync --locked --extra dev",
    "py-test": "uv sync --locked --extra dev",
    "py-build": "uv sync --locked --extra dist --no-install-project",
    "check-schema-and-types": "uv sync --locked",
}
EXEMPT_COOLDOWN = "6 hours"
# Unlocked installs another change replaces (publish.yaml's build toolchain).
# Remove each entry once that lands.
KNOWN_UNLOCKED = {("publish.yaml:publish", "pip install --upgrade pip build")}

spec = importlib.util.spec_from_file_location(
    "inspect_ai_source", GITHUB / "scripts" / "inspect_ai_source.py"
)
assert spec and spec.loader
inspect_ai_source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspect_ai_source)


def pyproject() -> dict[str, Any]:
    return tomllib.loads((REPO / "pyproject.toml").read_text())


def uv_config() -> dict[str, Any]:
    config: dict[str, Any] = pyproject()["tool"]["uv"]
    return config


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


def workflow_run_lines() -> list[tuple[str, str]]:
    lines = [
        (f"{path.name}:{name}", line)
        for path in workflows()
        for name, job in yaml.safe_load(path.read_text())["jobs"].items()
        for line in run_lines(job)
    ]
    for path in sorted((GITHUB / "actions").glob("*/action.y*ml")):
        runs = yaml.safe_load(path.read_text())["runs"]
        lines += [(f"{path.parent.name}/{path.name}", line) for line in run_lines(runs)]
    return lines


def test_dependabot_cooldown_matches_pyproject() -> None:
    config = uv_config()
    days = re.fullmatch(r"(\d+) days", config["exclude-newer"])
    assert days, config["exclude-newer"]
    dependabot = dependabot_uv()
    cooldown = dependabot["cooldown"]
    assert cooldown["default-days"] == int(days.group(1))
    exempt = config["exclude-newer-package"]
    assert set(exempt.values()) == {EXEMPT_COOLDOWN}
    # Dependabot's cooldown counts whole days, so it leaves these to uv.
    assert sorted(cooldown["exclude"]) == sorted(exempt)
    # The exempt packages have their own group, listed before the catch-all.
    groups = dependabot["groups"]
    assert list(groups) == ["six-hour-cooldown", "python-packages"]
    assert sorted(groups["six-hour-cooldown"]["patterns"]) == sorted(exempt)
    assert groups["python-packages"]["patterns"] == ["*"]


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def test_pinned_uv_versions_meet_required_version() -> None:
    required = re.fullmatch(r">=(\d+\.\d+\.\d+)", uv_config()["required-version"])
    assert required, uv_config()["required-version"]
    setups = 0
    for path in workflows():
        workflow = yaml.safe_load(path.read_text())
        for name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                if not step.get("uses", "").startswith("astral-sh/setup-uv@"):
                    continue
                setups += 1
                assert step["with"]["version"] == "${{ env.UV_VERSION }}", name
                pin = workflow["env"]["UV_VERSION"]
                assert version(pin) >= version(required[1]), f"{path.name}: uv {pin}"
    assert setups


@pytest.mark.parametrize("name,sync", LOCKED_JOBS.items())
def test_locked_jobs_install_from_the_lockfile(name: str, sync: str) -> None:
    job = yaml.safe_load((WORKFLOWS / "build.yaml").read_text())["jobs"][name]
    syncs = [line for line in run_lines(job) if line.startswith("uv sync")]
    assert syncs == [sync]


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
    assert set(unlocked) - KNOWN_UNLOCKED == set()


def test_no_workflow_opts_out_of_the_cooldown() -> None:
    floating = [
        (where, line)
        for where, line in workflow_run_lines()
        if re.search(r"--exclude-newer(=|\s+)false", line)
    ]
    assert floating == []


def test_release_switch_round_trips_the_inspect_ai_source() -> None:
    # The release PR drops the source and the scheduled job restores it
    # (release-pin-deps.yml), so both edits must apply to pyproject.toml.
    tracking = inspect_ai_source.add_source((REPO / "pyproject.toml").read_text())
    sources = tomllib.loads(tracking)["tool"]["uv"]["sources"]
    assert sources["inspect-ai"] == {
        "git": "https://github.com/UKGovernmentBEIS/inspect_ai",
        "branch": "main",
    }
    released = inspect_ai_source.drop_source(tracking)
    assert "inspect-ai" not in tomllib.loads(released)["tool"]["uv"]["sources"]
    assert inspect_ai_source.add_source(released) == tracking
    # A source written differently fails rather than being skipped or doubled.
    reformatted = tracking.replace('", branch', '",  branch')
    with pytest.raises(ValueError, match="source to read"):
        inspect_ai_source.drop_source(reformatted)
    with pytest.raises(ValueError, match="source to read"):
        inspect_ai_source.add_source(reformatted)


def test_release_switch_raises_the_inspect_ai_floor() -> None:
    text = inspect_ai_source.set_floor((REPO / "pyproject.toml").read_text(), "99.0.0")
    assert "inspect-ai>=99.0.0" in tomllib.loads(text)["project"]["dependencies"]


def test_release_switch_requires_a_released_inspect_ai() -> None:
    lock = """
[[package]]
name = "inspect-ai"
version = "0.3.287.dev30"
source = { git = "https://github.com/UKGovernmentBEIS/inspect_ai?branch=main#abc" }
"""
    with pytest.raises(ValueError, match="not locked from PyPI"):
        inspect_ai_source.locked_inspect_ai(lock)
    released = lock.replace('version = "0.3.287.dev30"', 'version = "0.3.287"').replace(
        'git = "https://github.com/UKGovernmentBEIS/inspect_ai?branch=main#abc"',
        'registry = "https://pypi.org/simple"',
    )
    assert inspect_ai_source.locked_inspect_ai(released) == "0.3.287"
