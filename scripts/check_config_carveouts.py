#!/usr/bin/env python3
"""Gate for config-level checker relaxations ("carve-outs").

config_carveouts.json (the ledger) must exactly match the checker-relaxing
settings present in the repo's tool config — any add, remove, or change fails
CI until the ledger is regenerated, so every carve-out shows up as a
reviewable ledger diff in the PR. Every ledger entry must carry a reason.

This is the config-level sibling of an inline-suppression gate: an agent (or
human) who can't add `# type: ignore` unnoticed shouldn't be able to relax
the checker in pyproject.toml unnoticed either.

Scans (repo root only):
  pyproject.toml  [tool.mypy], [[tool.mypy.overrides]],
                  [tool.ruff] / [tool.ruff.lint], [tool.pyright]
  ruff.toml / .ruff.toml

Only settings that suppress or weaken diagnostics are flagged (e.g. mypy
implicit_reexport = true, disable_error_code, disallow_* = false, exclude;
ruff lint.ignore, per-file-ignores, and exclude/extend-exclude; pyright
report* = false/"none"). Formatting and other benign config is not.

Checker config the gate cannot scan (mypy.ini, [mypy] sections in setup.cfg,
pyrightconfig.json) fails the gate outright rather than being silently
ignored.

Usage:
  python3 scripts/check_config_carveouts.py            # check (CI)
  python3 scripts/check_config_carveouts.py --update   # regenerate ledger,
                                                       # preserving reasons
"""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    sys.exit("check_config_carveouts.py requires Python >= 3.11 (tomllib)")

LEDGER_NAME = "config_carveouts.json"
UPDATE_HINT = "run `python3 scripts/check_config_carveouts.py --update`"


@dataclass(frozen=True, order=True)
class Carveout:
    """One checker-relaxing setting at one config location."""

    file: str
    location: str
    setting: str
    value: str

    def __str__(self) -> str:
        return f"{self.file}: [{self.location}] {self.setting} = {self.value}"


def _render(value: object) -> str:
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def _listify(value: Any) -> list[Any]:
    # scalar-or-list settings: a bare string is one item, not its characters
    if isinstance(value, list):
        return value
    return [value] if value else []


# mypy knobs that relax checking when set to the given polarity. Everything
# else in [tool.mypy] (paths, strictness enables, plugins) is benign.
_MYPY_RELAX_WHEN_TRUE = {
    "ignore_errors",
    "ignore_missing_imports",
    "implicit_reexport",
    "implicit_optional",
    "allow_untyped_globals",
    "allow_redefinition",
}
_MYPY_RELAX_WHEN_FALSE_PREFIXES = ("disallow_", "warn_", "strict", "no_implicit_")
_MYPY_RELAX_WHEN_FALSE = {"check_untyped_defs"}


def _mypy_relaxations(table: dict[str, Any]) -> Iterator[tuple[str, str]]:
    for key, value in sorted(table.items()):
        if key == "disable_error_code":
            yield from (("disable_error_code", str(code)) for code in _listify(value))
        elif key == "exclude":
            yield from (("exclude", str(p)) for p in _listify(value))
        elif key == "follow_imports" and value in ("skip", "silent"):
            yield (key, str(value))
        elif key in _MYPY_RELAX_WHEN_TRUE and value is True:
            yield (key, "true")
        elif value is False and (
            key.startswith(_MYPY_RELAX_WHEN_FALSE_PREFIXES)
            or key in _MYPY_RELAX_WHEN_FALSE
        ):
            yield (key, "false")


def _scan_mypy(mypy: dict[str, Any], file: str) -> Iterator[Carveout]:
    yield from (
        Carveout(file, "tool.mypy", key, value)
        for key, value in _mypy_relaxations(mypy)
    )
    for override in mypy.get("overrides", []):
        modules = override.get("module", [])
        modules = [modules] if isinstance(modules, str) else modules
        # sorted so reordering the module list doesn't churn the identity
        location = f"tool.mypy.overrides[{','.join(sorted(modules))}]"
        yield from (
            Carveout(file, location, key, value)
            for key, value in _mypy_relaxations(override)
        )


def _scan_ruff_lint(
    lint: dict[str, Any], location: str, file: str
) -> Iterator[Carveout]:
    for key in ("ignore", "extend-ignore"):
        yield from (
            Carveout(file, location, key, str(code)) for code in _listify(lint.get(key))
        )
    # excluding a path silences all lint for it — same relaxation channel as
    # an ignore code, aimed at paths instead of rules
    for key in ("exclude", "extend-exclude"):
        yield from (
            Carveout(file, location, key, str(path)) for path in _listify(lint.get(key))
        )
    for key in ("per-file-ignores", "extend-per-file-ignores"):
        for glob, codes in lint.get(key, {}).items():
            yield from (
                Carveout(file, f"{location}.{key}", str(glob), str(code))
                for code in _listify(codes)
            )


def _scan_pyright(table: dict[str, Any], file: str) -> Iterator[Carveout]:
    for key, value in sorted(table.items()):
        if key.startswith("report") and (value is False or value == "none"):
            yield Carveout(file, "tool.pyright", key, _render(value))
        elif key == "typeCheckingMode" and value in ("off", "basic"):
            yield Carveout(file, "tool.pyright", key, str(value))


def _check_unscannable(root: Path) -> None:
    found = [
        name
        for name in ("mypy.ini", ".mypy.ini", "pyrightconfig.json")
        if (root / name).exists()
    ]
    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(setup_cfg)
        except configparser.Error as error:
            sys.exit(f"setup.cfg is malformed — {type(error).__name__}: {error}")
        if any(s == "mypy" or s.startswith("mypy-") for s in parser.sections()):
            found.append("setup.cfg ([mypy] sections)")
    if found:
        sys.exit(
            "check_config_carveouts.py only scans pyproject.toml and ruff.toml; "
            f"found checker config it cannot scan: {', '.join(found)}. "
            "Move that config into pyproject.toml or extend the gate."
        )


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as error:
        sys.exit(f"{path.name} is malformed — TOMLDecodeError: {error}")


def scan_config(root: Path) -> list[Carveout]:
    _check_unscannable(root)
    found: list[Carveout] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        tool = _load_toml(pyproject).get("tool", {})
        found += _scan_mypy(tool.get("mypy", {}), "pyproject.toml")
        ruff = tool.get("ruff", {})
        # legacy pre-0.2 layout put lint settings directly under [tool.ruff]
        found += _scan_ruff_lint(ruff, "tool.ruff", "pyproject.toml")
        found += _scan_ruff_lint(
            ruff.get("lint", {}), "tool.ruff.lint", "pyproject.toml"
        )
        found += _scan_pyright(tool.get("pyright", {}), "pyproject.toml")
    for name in ("ruff.toml", ".ruff.toml"):
        path = root / name
        if path.exists():
            data = _load_toml(path)
            found += _scan_ruff_lint(data, "ruff", name)
            found += _scan_ruff_lint(data.get("lint", {}), "lint", name)
    return sorted(set(found))


def read_ledger(root: Path) -> dict[Carveout, str]:
    # the ledger is hand-edited (reasons get filled in), so slips like invalid
    # JSON, a missing/non-string field, or a duplicated entry need a legible
    # error, not a traceback or a silent last-entry-wins collapse
    path = root / LEDGER_NAME
    if not path.exists():
        return {}
    ledger: dict[Carveout, str] = {}
    try:
        for entry in json.loads(path.read_text()):
            fields = [
                entry[key] for key in ("file", "location", "setting", "value", "reason")
            ]
            if not all(isinstance(field, str) for field in fields):
                raise TypeError(f"every field must be a string: {entry}")
            carveout = Carveout(*fields[:4])
            if carveout in ledger:
                raise ValueError(f"duplicate entry for {carveout}")
            ledger[carveout] = fields[4]
    except (KeyError, TypeError, ValueError) as error:
        sys.exit(
            f"{LEDGER_NAME} is malformed — {type(error).__name__}: {error}."
            f" Fix it by hand, or delete it and {UPDATE_HINT} to regenerate"
            " (reasons will need re-entering)."
        )
    return ledger


def write_ledger(root: Path, entries: dict[Carveout, str]) -> None:
    payload = [
        {
            "file": c.file,
            "location": c.location,
            "setting": c.setting,
            "value": c.value,
            "reason": reason,
        }
        for c, reason in sorted(entries.items())
    ]
    (root / LEDGER_NAME).write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check config-level checker relaxations against the ledger."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="regenerate the ledger from current config, preserving reasons",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repo root to scan (default: this script's repo)",
    )
    args = parser.parse_args()
    root: Path = args.root

    actual = scan_config(root)
    ledger = read_ledger(root)

    if args.update:
        merged = {c: ledger.get(c, "") for c in actual}
        write_ledger(root, merged)
        print(f"{LEDGER_NAME} updated: {len(merged)} carve-out(s).")
        missing = [c for c, reason in merged.items() if not reason.strip()]
        for c in missing:
            print(f"NEEDS REASON: {c}", file=sys.stderr)
        if missing:
            print(
                f'Fill in the empty "reason" fields in {LEDGER_NAME} before committing.',
                file=sys.stderr,
            )
            return 1
        return 0

    recorded = set(ledger)
    failures = [
        f"NEW: {c} — not recorded in {LEDGER_NAME}. Fix the root cause instead if at"
        f" all possible; a genuinely unavoidable carve-out needs a reason:"
        f" {UPDATE_HINT}, fill in the reason, and get maintainer sign-off on the"
        f" ledger diff."
        if c not in recorded
        else f"NO REASON: {c} — ledger entry has an empty reason. Add one in {LEDGER_NAME}."
        for c in actual
        if c not in recorded or not ledger[c].strip()
    ] + [
        f"REMOVED: {c} — in {LEDGER_NAME} but no longer in config."
        f" {UPDATE_HINT} to record the shrink."
        for c in sorted(recorded - set(actual))
    ]

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(
        f"config carve-out ledger matches: {len(actual)} carve-out(s)"
        f" recorded in {LEDGER_NAME}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
