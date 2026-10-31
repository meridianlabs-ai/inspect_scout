"""Tests for .github/workflows/npm-publish.yml.

The build job installs the ts-mono workspace, runs its checks and packs the
viewer without the publishing id-token. The publish job holds the id-token,
runs nothing from the repository, and uploads the packed tarball only after
checking its name and version.
"""

import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from typing import Any, NamedTuple

import pytest
import yaml

REPO = pathlib.Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "npm-publish.yml"
VIEWER_PACKAGE = REPO / "src" / "inspect_scout" / "_view" / "ts-mono" / "apps" / "scout"
PACKAGE_NAME = "@meridianlabs/inspect-scout-viewer"

# npm lifecycle scripts that `npm publish` from the package directory runs and
# a tarball publish (or `npm pack --ignore-scripts`) does not.
PUBLISH_LIFECYCLE_SCRIPTS = {
    "prepublish",
    "prepare",
    "prepublishOnly",
    "prepack",
    "postpack",
    "publish",
    "postpublish",
}


def workflow() -> dict[str, Any]:
    config: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text())
    return config


def job(name: str) -> dict[str, Any]:
    config: dict[str, Any] = workflow()["jobs"][name]
    return config


def job_steps(name: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = job(name)["steps"]
    return steps


def npm_upgrade_spec(job_name: str) -> str:
    upgrade = next(s for s in job_steps(job_name) if "npm-upgrade" in s.get("run", ""))
    (install,) = [
        shlex.split(line)
        for line in upgrade["run"].splitlines()
        if line.strip().startswith("npm install")
    ]
    assert "--ignore-scripts" in install
    (spec,) = [token for token in install if token.startswith("npm@")]
    return spec


def test_npm_upgrade_is_pinned_without_install_scripts() -> None:
    # The publish job holds the npm publishing id-token, so the npm it runs
    # must not float or run install scripts. The build job's dry-run uses the
    # same npm, so it applies the same publish checks.
    spec = npm_upgrade_spec("publish")
    assert re.fullmatch(r"npm@\d+\.\d+\.\d+", spec), spec
    assert npm_upgrade_spec("build") == spec


def test_only_the_publish_job_holds_the_id_token() -> None:
    assert workflow()["permissions"] == {}
    assert "permissions" not in job("notify-approval")

    build = job("build")
    assert build["permissions"] == {"contents": "read"}
    assert "environment" not in build

    publish = job("publish")
    assert publish["needs"] == "build"
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    assert publish["environment"] == "npm"


def test_build_checkout_does_not_persist_credentials() -> None:
    checkout = next(
        s
        for s in job_steps("build")
        if s.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["persist-credentials"] is False


def test_no_dependency_cache() -> None:
    # Release builds resolve every dependency from the lockfile and the
    # registry, never from a cache another workflow saved.
    for name in ("build", "publish"):
        for step in job_steps(name):
            uses = step.get("uses", "")
            assert not uses.startswith("actions/cache"), (name, uses)
            inputs = step.get("with", {})
            assert "cache" not in inputs, (name, uses)
            if uses.startswith("actions/setup-node@"):
                assert inputs["package-manager-cache"] is False, name


def test_publish_job_runs_nothing_from_the_repository() -> None:
    steps = job_steps("publish")
    actions = [s["uses"].split("@")[0] for s in steps if "uses" in s]
    assert actions == ["actions/setup-node", "actions/download-artifact"]
    for step in steps:
        assert "pnpm" not in step.get("run", "")
    publish = next(s for s in steps if s.get("name") == "Publish to NPM")
    assert publish["run"].startswith('npm publish "$TARBALL" --ignore-scripts')


def test_publish_job_publishes_only_a_checked_release() -> None:
    # A dispatch defaults to dry-run, which must stop before the publish job.
    publish_job = job("publish")
    assert publish_job["if"] == "${{ !inputs.dry-run }}"

    steps = job_steps("publish")
    # On the release event inputs are empty, so the tarball must match the tag.
    check = next(s for s in steps if s.get("id") == "package")
    assert check["env"] == {
        "TAG": "${{ github.ref_name }}",
        "PRERELEASE": "${{ inputs.prerelease }}",
    }
    publish = next(s for s in steps if s.get("name") == "Publish to NPM")
    assert publish["if"] == "${{ steps.npm-version.outputs.published != 'true' }}"
    assert "${{ inputs.prerelease && '--tag beta' || '' }}" in publish["run"]


def test_build_runs_prepublish_before_packing() -> None:
    # Publishing a tarball runs no lifecycle scripts, so the build job must run
    # prepublishOnly itself.
    runs = [s.get("run", "") for s in job_steps("build")]
    prepublish = next(i for i, r in enumerate(runs) if "run prepublishOnly" in r)
    pack = next(i for i, r in enumerate(runs) if "npm pack" in r)
    assert prepublish < pack
    assert "--ignore-scripts" in runs[pack]


@pytest.mark.skipif(
    not (VIEWER_PACKAGE / "package.json").exists(),
    # CI's py-test job checks out without submodules, so this runs locally.
    reason="ts-mono submodule not initialized",
)
def test_viewer_has_no_other_publish_lifecycle_scripts() -> None:
    # The build job runs prepublishOnly explicitly; any other publish
    # lifecycle script would be silently skipped by the tarball publish.
    scripts = json.loads((VIEWER_PACKAGE / "package.json").read_text())["scripts"]
    assert PUBLISH_LIFECYCLE_SCRIPTS & set(scripts) == {"prepublishOnly"}


class PackageCheck(NamedTuple):
    returncode: int
    stdout: str
    outputs: dict[str, str]


def run_package_check(
    tmp_path: pathlib.Path,
    version: str,
    tag: str,
    prerelease: str = "",
    name: str = PACKAGE_NAME,
    tarballs: int = 1,
) -> PackageCheck:
    """Run the publish job's "Check the package" script on packed tarballs."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "package.json").write_text(
        json.dumps({"name": name, "version": version})
    )
    (tmp_path / "npm-package").mkdir()
    for i in range(tarballs):
        with tarfile.open(tmp_path / "npm-package" / f"pkg{i}.tgz", "w:gz") as tar:
            tar.add(package, arcname="package")
    output = tmp_path / "github_output"
    output.touch()

    script = next(s for s in job_steps("publish") if s.get("id") == "package")["run"]
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "TAG": tag,
            "PRERELEASE": prerelease,
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
    return PackageCheck(result.returncode, result.stdout, outputs)


_no_package_check = sys.platform == "win32" or shutil.which("jq") is None


@pytest.mark.skipif(_no_package_check, reason="needs a POSIX shell and jq")
def test_package_check_hands_npm_an_absolute_tarball_path(
    tmp_path: pathlib.Path,
) -> None:
    # npm reads a relative `dir/file.tgz` as a GitHub `user/repo` shorthand.
    check = run_package_check(tmp_path, "0.6.2", "0.6.2")
    assert check.returncode == 0, check.stdout
    assert pathlib.Path(check.outputs["tarball"]).is_absolute()
    assert check.outputs["name"] == PACKAGE_NAME
    assert check.outputs["version"] == "0.6.2"


@pytest.mark.skipif(_no_package_check, reason="needs a POSIX shell and jq")
@pytest.mark.parametrize(
    "version,tag,prerelease,ok",
    [
        ("0.6.2", "0.6.1", "", False),
        ("0.6.2", "main", "", False),
        ("0.6.2", "main", "true", False),
        ("0.6.3-beta.1761500000", "main", "true", True),
    ],
)
def test_package_check_publishes_only_the_release_version(
    tmp_path: pathlib.Path, version: str, tag: str, prerelease: str, ok: bool
) -> None:
    check = run_package_check(tmp_path, version, tag, prerelease)
    assert (check.returncode == 0) is ok, check.stdout


@pytest.mark.skipif(_no_package_check, reason="needs a POSIX shell and jq")
@pytest.mark.parametrize(
    "name,tarballs,error",
    [
        (PACKAGE_NAME, 0, "Expected one package tarball, found 0"),
        (PACKAGE_NAME, 2, "Expected one package tarball, found 2"),
        ("scout", 1, "Unexpected package name 'scout'"),
    ],
)
def test_package_check_rejects_anything_but_one_viewer_tarball(
    tmp_path: pathlib.Path, name: str, tarballs: int, error: str
) -> None:
    check = run_package_check(tmp_path, "0.6.2", "0.6.2", name=name, tarballs=tarballs)
    assert check.returncode != 0
    assert f"::error::{error}" in check.stdout
    assert check.outputs == {}
