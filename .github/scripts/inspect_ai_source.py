"""Switch uv.lock between inspect_ai main and the released inspect_ai.

Development and CI track inspect_ai main through pyproject.toml's
`[tool.uv.sources]`. A release must require, and be tested against, a released
inspect_ai. release-pin-deps.yml runs this in a job that holds no write token.

Usage:
    python3 -I .github/scripts/inspect_ai_source.py release
        Drop the git source, lock the newest inspect-ai release that clears
        the cooldown, and raise the inspect-ai floor in [project] to it.
    python3 -I .github/scripts/inspect_ai_source.py main
        Restore the git source, if it is missing, and lock inspect_ai main.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
LOCK = Path("uv.lock")
SOURCES_HEADER = "[tool.uv.sources]\n"
SOURCE = (
    'inspect-ai = { git = "https://github.com/UKGovernmentBEIS/inspect_ai",'
    ' branch = "main" }\n'
)
FLOOR = re.compile(r'"inspect-ai>=[^"]*"')


def drop_source(pyproject: str) -> str:
    return pyproject.replace(SOURCE, "")


def add_source(pyproject: str) -> str:
    if SOURCE in pyproject:
        return pyproject
    if pyproject.count(SOURCES_HEADER) != 1:
        raise ValueError(f"expected one {SOURCES_HEADER.strip()} table")
    return pyproject.replace(SOURCES_HEADER, SOURCES_HEADER + SOURCE)


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


def uv_lock(*args: str) -> None:
    subprocess.run(["uv", "lock", *args], check=True)


def release() -> None:
    PYPROJECT.write_text(drop_source(PYPROJECT.read_text()))
    uv_lock("--upgrade-package", "inspect-ai")
    version = locked_inspect_ai(LOCK.read_text())
    PYPROJECT.write_text(set_floor(PYPROJECT.read_text(), version))
    uv_lock()
    print(f"Locked inspect-ai {version} from PyPI and set the floor to it")


def main() -> None:
    pyproject = PYPROJECT.read_text()
    if SOURCE in pyproject:
        print("uv.lock already tracks inspect_ai main")
        return
    PYPROJECT.write_text(add_source(pyproject))
    uv_lock()
    print("Restored the inspect_ai main git source")


if __name__ == "__main__":
    commands = {"release": release, "main": main}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        sys.exit(__doc__)
    commands[sys.argv[1]]()
