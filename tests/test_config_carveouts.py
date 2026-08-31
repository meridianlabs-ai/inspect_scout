"""Tests for the config carve-out gate (scripts/check_config_carveouts.py)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="the gate script requires tomllib (Python >= 3.11)",
)

SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "check_config_carveouts.py"
)

SCOUT_STYLE_OVERRIDE = """\
[[tool.mypy.overrides]]
module = ["inspect_ai._cli.util"]
implicit_reexport = true
"""


def run_gate(root: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param(
            SCOUT_STYLE_OVERRIDE,
            "[tool.mypy.overrides[inspect_ai._cli.util]] implicit_reexport = true",
            id="mypy-override-implicit-reexport",
        ),
        pytest.param(
            "[tool.mypy]\ndisallow_untyped_defs = false\n",
            "[tool.mypy] disallow_untyped_defs = false",
            id="mypy-global-disallow-false",
        ),
        pytest.param(
            '[tool.mypy]\ndisable_error_code = ["union-attr"]\n',
            "[tool.mypy] disable_error_code = union-attr",
            id="mypy-disable-error-code",
        ),
        pytest.param(
            '[tool.mypy]\nfollow_imports = "skip"\n',
            "[tool.mypy] follow_imports = skip",
            id="mypy-follow-imports-skip",
        ),
        pytest.param(
            '[tool.ruff.lint]\nignore = ["E501"]\n',
            "[tool.ruff.lint] ignore = E501",
            id="ruff-lint-ignore",
        ),
        pytest.param(
            '[tool.ruff.lint.per-file-ignores]\n"tests/*" = ["D103"]\n',
            "[tool.ruff.lint.per-file-ignores] tests/* = D103",
            id="ruff-per-file-ignores",
        ),
        pytest.param(
            "[tool.pyright]\nreportMissingImports = false\n",
            "[tool.pyright] reportMissingImports = false",
            id="pyright-report-off",
        ),
        pytest.param(
            '[tool.mypy]\nexclude = ["src/legacy/"]\n',
            "[tool.mypy] exclude = src/legacy/",
            id="mypy-exclude",
        ),
        pytest.param(
            '[tool.ruff]\nextend-exclude = ["scripts"]\n',
            "[tool.ruff] extend-exclude = scripts",
            id="ruff-extend-exclude",
        ),
        pytest.param(
            '[tool.ruff.lint]\nexclude = ["scripts/*.py"]\n',
            "[tool.ruff.lint] exclude = scripts/*.py",
            id="ruff-lint-exclude",
        ),
    ],
)
def test_detects_relaxation(tmp_path: Path, config: str, expected: str) -> None:
    (tmp_path / "pyproject.toml").write_text(config)
    result = run_gate(tmp_path)
    assert result.returncode == 1
    assert "NEW:" in result.stderr
    assert expected in result.stderr


@pytest.mark.parametrize(
    "config",
    [
        pytest.param(
            '[tool.mypy]\nstrict = true\nmypy_path = "src"\nfiles = ["src"]\n',
            id="mypy-tightening-and-paths",
        ),
        pytest.param(
            '[tool.ruff]\nsrc = ["."]\n[tool.ruff.lint]\nselect = ["E", "F"]\n',
            id="ruff-select-and-paths",
        ),
    ],
)
def test_ignores_benign_config(tmp_path: Path, config: str) -> None:
    (tmp_path / "pyproject.toml").write_text(config)
    result = run_gate(tmp_path)
    assert result.returncode == 0


def test_ruff_toml_scanned(tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text('[lint]\nignore = ["E501"]\n')
    result = run_gate(tmp_path)
    assert result.returncode == 1
    assert "ruff.toml: [lint] ignore = E501" in result.stderr


def test_unscannable_checker_config_fails(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
    (tmp_path / "mypy.ini").write_text("[mypy]\n")
    result = run_gate(tmp_path)
    assert result.returncode != 0
    assert "mypy.ini" in result.stderr


def test_record_and_shrink_flow(tmp_path: Path) -> None:
    ledger_path = tmp_path / "config_carveouts.json"
    (tmp_path / "pyproject.toml").write_text(SCOUT_STYLE_OVERRIDE)

    # unrecorded carve-out fails the gate
    assert run_gate(tmp_path).returncode == 1

    # --update records it but demands a reason
    update = run_gate(tmp_path, "--update")
    assert update.returncode == 1
    assert "NEEDS REASON" in update.stderr
    entries = json.loads(ledger_path.read_text())
    assert entries[0]["setting"] == "implicit_reexport"
    assert entries[0]["reason"] == ""

    # empty reason still fails the check
    check = run_gate(tmp_path)
    assert check.returncode == 1
    assert "NO REASON" in check.stderr

    # filled reason passes
    entries[0]["reason"] = "upstream re-export quirk; tracked in #000"
    ledger_path.write_text(json.dumps(entries))
    assert run_gate(tmp_path).returncode == 0

    # removing the carve-out leaves a stale ledger entry; --update records the shrink
    (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
    stale = run_gate(tmp_path)
    assert stale.returncode == 1
    assert "REMOVED:" in stale.stderr
    assert run_gate(tmp_path, "--update").returncode == 0
    assert run_gate(tmp_path).returncode == 0


@pytest.mark.parametrize(
    "ledger_text",
    [
        pytest.param("{not json", id="invalid-json"),
        pytest.param('[{"file": "pyproject.toml"}]', id="missing-fields"),
        pytest.param(
            '[{"file": "f", "location": "l", "setting": "s",'
            ' "value": "v", "reason": null}]',
            id="non-string-reason",
        ),
    ],
)
def test_malformed_ledger_fails_cleanly(tmp_path: Path, ledger_text: str) -> None:
    (tmp_path / "pyproject.toml").write_text(SCOUT_STYLE_OVERRIDE)
    (tmp_path / "config_carveouts.json").write_text(ledger_text)
    result = run_gate(tmp_path)
    assert result.returncode == 1
    assert "malformed" in result.stderr
    assert "Traceback" not in result.stderr


def test_duplicate_ledger_entries_fail(tmp_path: Path) -> None:
    ledger_path = tmp_path / "config_carveouts.json"
    (tmp_path / "pyproject.toml").write_text(SCOUT_STYLE_OVERRIDE)
    run_gate(tmp_path, "--update")
    entries = json.loads(ledger_path.read_text())
    entries[0]["reason"] = "real reason"
    ledger_path.write_text(json.dumps(entries + [dict(entries[0], reason="")]))
    result = run_gate(tmp_path)
    assert result.returncode == 1
    assert "duplicate entry" in result.stderr


def test_override_identity_ignores_module_order(tmp_path: Path) -> None:
    def override(modules: str) -> str:
        return f"[[tool.mypy.overrides]]\nmodule = [{modules}]\nignore_errors = true\n"

    ledger_path = tmp_path / "config_carveouts.json"
    (tmp_path / "pyproject.toml").write_text(override('"b_mod", "a_mod"'))
    run_gate(tmp_path, "--update")
    entries = json.loads(ledger_path.read_text())
    entries[0]["reason"] = "shared reason"
    ledger_path.write_text(json.dumps(entries))
    assert run_gate(tmp_path).returncode == 0

    (tmp_path / "pyproject.toml").write_text(override('"a_mod", "b_mod"'))
    assert run_gate(tmp_path).returncode == 0


def test_update_preserves_existing_reasons(tmp_path: Path) -> None:
    ledger_path = tmp_path / "config_carveouts.json"
    (tmp_path / "pyproject.toml").write_text('[tool.ruff.lint]\nignore = ["E501"]\n')
    run_gate(tmp_path, "--update")
    entries = json.loads(ledger_path.read_text())
    entries[0]["reason"] = "kept reason"
    ledger_path.write_text(json.dumps(entries))

    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff.lint]\nignore = ["E501", "D10"]\n'
    )
    run_gate(tmp_path, "--update")
    reasons = {e["value"]: e["reason"] for e in json.loads(ledger_path.read_text())}
    assert reasons == {"E501": "kept reason", "D10": ""}
