#!/usr/bin/env python3
"""Check the built distributions before they are uploaded to PyPI.

Usage:
    python3 -I scripts/verify_dist.py <version> [--dist-dir dist]

Run by both jobs of .github/workflows/publish.yaml: after the build, and again
in the publish job on the downloaded files. Stdlib only, so the publish job
installs nothing.
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path

VIEW_DIST = "inspect_scout/_view/dist/"


class DistError(Exception):
    pass


def verify_dist(dist_dir: Path, version: str) -> None:
    """Require exactly one sdist and one wheel of `version`, with the viewer.

    `version` is the release tag. hatch-vcs derives the built version from
    git, so a tag that is not on the built commit, or a dirty tree, produces
    a different version and fails here rather than on PyPI.

    Raises:
        DistError: If dist_dir holds anything else, or the wheel fails
            `verify_wheel`.
    """
    files = sorted(f.name for f in dist_dir.iterdir()) if dist_dir.is_dir() else []
    wheels = [f for f in files if f.endswith(".whl")]
    sdists = [f for f in files if f.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1 or len(files) != 2:
        raise DistError(
            f"{dist_dir}/ must contain exactly one wheel and one sdist; found {files}"
        )

    wheel, sdist = wheels[0], sdists[0]
    built = {
        wheel: wheel.split("-")[1],
        sdist: sdist.removesuffix(".tar.gz").rsplit("-", 1)[-1],
    }
    for filename, built_version in built.items():
        if built_version != version:
            raise DistError(
                f"{filename} has version {built_version}, expected {version}"
            )

    verify_wheel(dist_dir / wheel)


def verify_wheel(wheel_path: Path) -> None:
    """Require the built viewer in the wheel.

    The viewer (`src/inspect_scout/_view/dist`) is in Git LFS and is not a
    Python package, so a checkout without LFS or a broken `artifacts` entry
    in pyproject.toml would otherwise ship a wheel whose `scout view` fails.

    Raises:
        DistError: If index.html, a JS or CSS asset, or a parseable
            content-security-policy.json is missing or empty.
    """
    csp = VIEW_DIST + "content-security-policy.json"
    problems: list[str] = []
    with zipfile.ZipFile(wheel_path) as zf:
        sizes = {i.filename: i.file_size for i in zf.infolist()}
        if sizes.get(csp):
            try:
                json.loads(zf.read(csp))
            except ValueError as e:
                # A checkout without Git LFS leaves pointer files here.
                problems.append(f"{csp} is not valid JSON ({e}); is it an LFS pointer?")

    for member in [VIEW_DIST + "index.html", csp]:
        if not sizes.get(member):
            problems.append(
                f"{member} {'is empty' if member in sizes else 'is missing'}"
            )
    for suffix in [".js", ".css"]:
        if not any(
            name.startswith(VIEW_DIST + "assets/") and name.endswith(suffix) and size
            for name, size in sizes.items()
        ):
            problems.append(f"no non-empty {suffix} assets in {VIEW_DIST}assets/")

    if problems:
        raise DistError(f"{wheel_path.name}: {'; '.join(problems)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check dist/ before PyPI upload.")
    parser.add_argument("version", help="the release tag, e.g. 0.6.2")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    try:
        verify_dist(args.dist_dir, args.version)
    except DistError as e:
        print(f"::error::Distribution check failed: {e}")
        sys.exit(1)
    print(f"Distributions verified for {args.version} in {args.dist_dir}/")


if __name__ == "__main__":
    main()
