"""Print the inspect-ai release the release PR is tested against.

The release PR's CI resolves without `[tool.uv.sources]`, so it installs the
newest inspect-ai release that clears its cooldown (.github/actions/uv-sync).
This locks inspect-ai the same way, prints the version, and puts uv.lock back.
release-pin-deps.yml runs this in a job that holds no write token, and raises
the `inspect-ai>=` floor to the printed version.

Usage:
    python3 -I .github/scripts/inspect_ai_floor.py
"""

import subprocess
import tomllib
from pathlib import Path

LOCK = Path("uv.lock")


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
            stdout=subprocess.DEVNULL,
        )
        version = locked_inspect_ai(LOCK.read_text())
    finally:
        LOCK.write_text(lock)
    print(version)


if __name__ == "__main__":
    main()
