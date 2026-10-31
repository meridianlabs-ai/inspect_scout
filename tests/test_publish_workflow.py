"""Tests for the PyPI publish workflow (.github/workflows/publish.yaml).

Covers the build/publish job split, the hashed build toolchain and its
Dependabot entry, the release-tag check (run against a throwaway git repo)
and the dist gate (scripts/verify_dist.py, run on fabricated distributions).
"""

import io
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "publish.yaml"
REQUIREMENTS = REPO / "scripts" / "build-dist" / "requirements.txt"
VERIFY_DIST = "scripts/verify_dist.py"
PYPI_PUBLISH = "pypa/gh-action-pypi-publish@"
SHA_PIN = re.compile(r"@[0-9a-f]{40} # v\S+$")


def _load(path: Path) -> dict[Any, Any]:
    loaded = yaml.safe_load(path.read_text())
    assert isinstance(loaded, dict)
    return loaded


def _jobs() -> dict[str, Any]:
    jobs: dict[str, Any] = _load(WORKFLOW)["jobs"]
    return jobs


def _step(job: str, name: str) -> dict[str, Any]:
    step: dict[str, Any] = next(
        s for s in _jobs()[job]["steps"] if s.get("name") == name
    )
    return step


# ---------------------------------------------------------------------------
# Workflow wiring
# ---------------------------------------------------------------------------


def test_only_the_publish_job_holds_the_publish_token() -> None:
    workflow = _load(WORKFLOW)
    jobs = workflow["jobs"]
    assert workflow["permissions"] == {}
    assert set(jobs) == {"notify-approval", "build", "publish"}
    assert jobs["notify-approval"]["permissions"] == {}
    assert jobs["build"]["permissions"] == {"contents": "read"}
    assert "environment" not in jobs["build"]
    assert jobs["publish"]["permissions"] == {"contents": "read", "id-token": "write"}
    # PyPI's trusted publisher matches this workflow file and environment.
    assert jobs["publish"]["environment"]["name"] == "pypi"
    assert jobs["publish"]["needs"] == "build"


def test_dispatch_publishes_only_when_confirmed() -> None:
    workflow = _load(WORKFLOW)
    # PyYAML reads the `on` key as True.
    assert "confirm" in workflow[True]["workflow_dispatch"]["inputs"]
    assert _jobs()["publish"]["if"] == (
        "${{ github.event_name == 'release' || inputs.confirm == 'yes' }}"
    )


def test_publish_job_installs_and_builds_nothing() -> None:
    steps = _jobs()["publish"]["steps"]
    assert [s.get("uses", "").split("@")[0] or s["run"] for s in steps] == [
        "actions/checkout",
        "actions/download-artifact",
        f'python3 -I {VERIFY_DIST} "$GITHUB_REF_NAME"',
        PYPI_PUBLISH.rstrip("@"),
    ]
    checkout, download = steps[0]["with"], steps[1]["with"]
    assert checkout == {
        "sparse-checkout": VERIFY_DIST,
        "sparse-checkout-cone-mode": False,
        "persist-credentials": False,
    }
    assert download == {"name": "dist", "path": "dist/"}


def test_build_job_checks_out_the_tag_with_lfs_and_no_credentials() -> None:
    checkout = _jobs()["build"]["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"] == {
        "fetch-depth": 0,
        "lfs": True,
        "persist-credentials": False,
    }


def test_build_job_builds_with_the_hashed_toolchain_and_gates_the_upload() -> None:
    steps = _jobs()["build"]["steps"]
    setup = next(
        s for s in steps if s.get("uses", "").startswith("actions/setup-python@")
    )
    assert setup["with"] == {"python-version": "3.11"}
    runs = [s.get("run", "").strip() for s in steps]
    assert [r for r in runs if "pip install" in r] == [
        "python -m pip install --require-hashes --only-binary :all: --no-deps "
        "-r scripts/build-dist/requirements.txt"
    ]
    build = runs.index("python -m build --no-isolation")
    verify = runs.index(f'python -I {VERIFY_DIST} "$GITHUB_REF_NAME"')
    upload = next(
        i
        for i, s in enumerate(steps)
        if s.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert build < verify < upload


def test_requirements_pin_every_package_with_hashes() -> None:
    requirements = REQUIREMENTS.read_text()
    pins = re.findall(r"^([A-Za-z0-9_.-]+)==\S+ \\$", requirements, re.MULTILINE)
    assert {"build", "hatchling", "hatch-vcs"} <= set(pins)
    requirement_lines = [
        line
        for line in requirements.splitlines()
        if line and not line.startswith(("#", " "))
    ]
    assert len(requirement_lines) == len(pins)
    assert requirements.count("--hash=sha256:") >= len(pins)
    assert '--exclude-newer "7 days"' in WORKFLOW.read_text()


def test_dependabot_updates_the_build_toolchain_with_a_cooldown() -> None:
    updates = _load(REPO / ".github" / "dependabot.yml")["updates"]
    (update,) = [u for u in updates if u["directory"] == "/scripts/build-dist"]
    assert update["package-ecosystem"] == "uv"
    assert update["cooldown"]["default-days"] == 7
    assert update["schedule"]["interval"] == "weekly"
    assert [group["patterns"] for group in update["groups"].values()] == [["*"]]


def test_actions_are_pinned_to_commit_shas() -> None:
    uses = [
        line.strip()
        for line in WORKFLOW.read_text().splitlines()
        if line.strip().startswith(("uses:", "- uses:"))
    ]
    assert uses
    for line in uses:
        assert SHA_PIN.search(line), line


# ---------------------------------------------------------------------------
# Release-tag check
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def tagged_repo(tmp_path: Path) -> Path:
    """A repo with tag 1.2.3 on origin/main and tag 1.2.4 off it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "a",
    )
    _git(repo, "tag", "1.2.3")
    _git(repo, "tag", "v1.2.3")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "b",
    )
    _git(repo, "tag", "1.2.4")
    return repo


@pytest.mark.parametrize(
    "event,ref_type,ref,release_tag,ok",
    [
        ("release", "tag", "1.2.3", "1.2.3", True),
        ("release", "branch", "main", "1.2.3", False),
        ("release", "tag", "v1.2.3", "v1.2.3", False),
        ("release", "tag", "1.2.3", "1.2.4", False),
        ("release", "tag", "1.2.4", "1.2.4", False),
        # the break-glass dispatch may publish a tag that is not on main
        ("workflow_dispatch", "tag", "1.2.4", "", True),
        ("workflow_dispatch", "branch", "main", "", False),
    ],
)
def test_build_refuses_anything_but_a_release_tag(
    tagged_repo: Path, event: str, ref_type: str, ref: str, release_tag: str, ok: bool
) -> None:
    _git(tagged_repo, "checkout", "-q", "--detach", ref)
    step = _step("build", "Check release tag")
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=tagged_repo,
        env={
            **os.environ,
            "GITHUB_REF_TYPE": ref_type,
            "GITHUB_REF_NAME": ref,
            "EVENT_NAME": event,
            "RELEASE_TAG": release_tag,
        },
        capture_output=True,
        check=False,
        text=True,
    )
    assert (result.returncode == 0) == ok, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Dist gate
# ---------------------------------------------------------------------------

VIEW = "inspect_scout/_view/dist/"
GOOD_WHEEL = {
    "inspect_scout/__init__.py": b"",
    VIEW + "index.html": b"<!doctype html>",
    VIEW + "content-security-policy.json": b'{"version": 1}',
    VIEW + "assets/index-abc.js": b"console.log(1)",
    VIEW + "assets/index-abc.css": b"body{}",
}
LFS_POINTER = b"version https://git-lfs.github.com/spec/v1\noid sha256:00\nsize 1\n"


def _write_dist(
    dist: Path, wheel_members: dict[str, bytes], version: str = "1.2.3"
) -> None:
    dist.mkdir()
    with zipfile.ZipFile(dist / f"inspect_scout-{version}-py3-none-any.whl", "w") as zf:
        for name, data in wheel_members.items():
            zf.writestr(name, data)
    with tarfile.open(dist / f"inspect_scout-{version}.tar.gz", "w:gz") as tf:
        info = tarfile.TarInfo(f"inspect_scout-{version}/PKG-INFO")
        tf.addfile(info, io.BytesIO(b""))


def _verify(dist: Path, version: str = "1.2.3") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO / VERIFY_DIST),
            version,
            "--dist-dir",
            str(dist),
        ],
        capture_output=True,
        check=False,
        text=True,
    )


def test_gate_accepts_a_complete_dist(tmp_path: Path) -> None:
    _write_dist(tmp_path / "dist", GOOD_WHEEL)
    result = _verify(tmp_path / "dist")
    assert result.returncode == 0, result.stdout


def _without(*names: str) -> dict[str, bytes]:
    return {k: v for k, v in GOOD_WHEEL.items() if k not in names}


@pytest.mark.parametrize(
    "members,error",
    [
        ({"inspect_scout/__init__.py": b""}, "index.html is missing"),
        (_without(VIEW + "index.html"), "index.html is missing"),
        ({**GOOD_WHEEL, VIEW + "index.html": b""}, "index.html is empty"),
        (_without(VIEW + "assets/index-abc.js"), "no non-empty .js assets"),
        (_without(VIEW + "assets/index-abc.css"), "no non-empty .css assets"),
        (
            _without(VIEW + "content-security-policy.json"),
            "content-security-policy.json is missing",
        ),
        (
            {**GOOD_WHEEL, VIEW + "content-security-policy.json": LFS_POINTER},
            "content-security-policy.json is not valid JSON",
        ),
    ],
)
def test_gate_rejects_a_wheel_without_the_viewer(
    tmp_path: Path, members: dict[str, bytes], error: str
) -> None:
    _write_dist(tmp_path / "dist", members)
    result = _verify(tmp_path / "dist")
    assert result.returncode == 1
    assert error in result.stdout


def test_gate_rejects_the_wrong_version(tmp_path: Path) -> None:
    _write_dist(tmp_path / "dist", GOOD_WHEEL, version="1.2.4.dev3")
    result = _verify(tmp_path / "dist")
    assert result.returncode == 1
    assert "has version 1.2.4.dev3, expected 1.2.3" in result.stdout


def test_gate_rejects_extra_or_missing_files(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_dist(dist, GOOD_WHEEL)
    (dist / "inspect_scout-1.2.3-py3-none-any.whl.metadata").write_text("")
    result = _verify(dist)
    assert result.returncode == 1
    assert "exactly one wheel and one sdist" in result.stdout

    assert _verify(tmp_path / "missing").returncode == 1
