"""Raise the inspect-ai floor to the release the release PR is tested against.

The release PR's CI resolves without `[tool.uv.sources]`, so it installs the
newest inspect-ai release that clears its cooldown (.github/actions/uv-sync).
This locks inspect-ai the same way, sets the `inspect-ai>=` floor in
pyproject.toml to that release, and puts uv.lock back. uv.lock records no
specifier for the git-sourced inspect-ai, so it stays in sync.
release-pin-deps.yml runs this in a job that holds no write token.

Usage:
    python3 -I .github/scripts/inspect_ai_floor.py
"""

import re
import subprocess
import tomllib
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
LOCK = Path("uv.lock")
FLOOR = re.compile(r'"inspect-ai>=[^"]*"')


def set_floor(pyproject: str, version: str) -> str:
    if len(FLOOR.findall(pyproject)) != 1:
        raise ValueError("expected one inspect-ai>= requirement")
    return FLOOR.sub(f'"inspect-ai>={version}"', pyproject)


def locked_inspect_ai(lock: str) -> str:
    (package,) = [
        p for p in tomllib.loads(lock)["package"] if p["name"] == "inspect-ai"
    ]
    if "registry" not in package["source"]:
        raise ValueError(f"inspect-ai is not locked from PyPI: {package['source']}")
    version: str = package["version"]
    return version


def main() -> None:
    lock = LOCK.read_text()
    try:
        subprocess.run(
            ["uv", "lock", "--no-sources", "--upgrade-package", "inspect-ai"],
            check=True,
        )
        version = locked_inspect_ai(LOCK.read_text())
    finally:
        LOCK.write_text(lock)
    PYPROJECT.write_text(set_floor(PYPROJECT.read_text(), version))
    print(f"Set the inspect-ai floor to {version}")


if __name__ == "__main__":
    main()
