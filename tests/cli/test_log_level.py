"""Tests that CLI commands honor ``--log-level``.

``scout import``, ``scan list``, ``scan status``, ``scan complete`` and
``scan resume`` previously accepted ``--log-level`` but never applied it. These
tests pin the resolution precedence and verify, per command, that the resolved
level actually reaches logging initialization — guarding against that
regression.

Precedence (highest to lowest): CLI argument > project config > environment
variable > default.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal
from unittest.mock import MagicMock

import inspect_scout._cli.common as common
import pytest
from click.core import ParameterSource
from click.testing import CliRunner
from inspect_ai._util.constants import DEFAULT_LOG_LEVEL
from inspect_scout._cli.common import CommonOptions, resolve_log_level
from inspect_scout._cli.main import scout
from inspect_scout._project.types import ProjectConfig

LogLevel = Literal[
    "debug", "http", "sandbox", "info", "warning", "error", "critical", "notset"
]


def _common_options(log_level: str) -> CommonOptions:
    """Build a CommonOptions dict as click would supply it to a command."""
    return CommonOptions(
        display="none",
        log_level=log_level,
        debug=False,
        debug_port=5678,
        fail_on_error=False,
    )


# =============================================================================
# resolve_log_level (unit): the shared precedence logic
# =============================================================================


@pytest.fixture
def mock_ctx() -> MagicMock:
    """A Click context whose parameter sources can be configured per option."""
    ctx = MagicMock()
    sources: dict[str, ParameterSource] = {}

    def get_parameter_source(option: str) -> ParameterSource | None:
        return sources.get(option)

    def set_parameter_source(option: str, source: ParameterSource) -> None:
        sources[option] = source

    ctx.get_parameter_source = get_parameter_source
    ctx.set_parameter_source = set_parameter_source
    return ctx


def _patch_project(monkeypatch: pytest.MonkeyPatch, level: LogLevel | None) -> None:
    """Make ``read_project()`` (as seen by common.py) return ``level``."""
    monkeypatch.setattr(common, "read_project", lambda: ProjectConfig(log_level=level))


# (parameter source of --log-level, project log_level, option value, expected)
_RESOLVE_CASES: list[tuple[ParameterSource, LogLevel | None, str, str]] = [
    # an explicit command-line flag wins over everything
    (ParameterSource.COMMANDLINE, "info", "debug", "debug"),
    # otherwise the project value wins over env and default...
    (ParameterSource.DEFAULT, "info", "warning", "info"),
    (ParameterSource.ENVIRONMENT, "info", "error", "info"),
    # ...and with no project value the click value (env / default) is used
    (ParameterSource.ENVIRONMENT, None, "error", "error"),
    (ParameterSource.DEFAULT, None, "warning", "warning"),
]


@pytest.mark.parametrize(
    "source, project_level, option_value, expected",
    _RESOLVE_CASES,
)
def test_resolve_log_level(
    monkeypatch: pytest.MonkeyPatch,
    mock_ctx: MagicMock,
    source: ParameterSource,
    project_level: LogLevel | None,
    option_value: str,
    expected: str,
) -> None:
    mock_ctx.set_parameter_source("log_level", source)
    _patch_project(monkeypatch, project_level)
    assert resolve_log_level(mock_ctx, _common_options(option_value)) == expected


def test_resolve_log_level_cli_arg_skips_project(
    monkeypatch: pytest.MonkeyPatch, mock_ctx: MagicMock
) -> None:
    """An explicit ``--log-level`` must not even read the project config.

    (read_project() raises on a malformed scout.yaml; an explicit flag should
    not be hostage to that.)
    """
    mock_ctx.set_parameter_source("log_level", ParameterSource.COMMANDLINE)

    def _fail() -> ProjectConfig:
        raise AssertionError("read_project should not be called for an explicit flag")

    monkeypatch.setattr(common, "read_project", _fail)
    assert resolve_log_level(mock_ctx, _common_options("debug")) == "debug"


# =============================================================================
# end-to-end: the resolved level reaches logging initialization, per command
# =============================================================================


class _StopInit(Exception):
    """Raised by the recorder to abort a command immediately after log init."""


class _LevelRecorder:
    """Capture the level handed to ``init_log`` and abort the command.

    Every ``--log-level`` command funnels its resolved level into
    ``init_log`` via ``process_common_options``, so patching that single
    binding intercepts the value for all of them. Aborting lets commands that
    would otherwise need real data (a scan location, a scans dir) run far
    enough to resolve and apply the level, then stop.
    """

    def __init__(self) -> None:
        self.level: str | None = None
        self.called: bool = False

    def __call__(self, log_level: str | None, **kwargs: Any) -> None:
        self.level = log_level
        self.called = True
        raise _StopInit()

    def effective_level(self) -> str:
        assert self.called, "command did not initialize logging"
        return (self.level or DEFAULT_LOG_LEVEL).lower()


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _LevelRecorder:
    rec = _LevelRecorder()
    monkeypatch.setattr(common, "init_log", rec)
    return rec


def _invoke(args: list[str], env: dict[str, str] | None = None) -> None:
    # commands abort via _StopInit once the level is captured
    CliRunner().invoke(scout, args, env=env or {}, catch_exceptions=True)


# commands that previously ignored --log-level (id -> CLI args)
_COMMANDS: list[tuple[str, list[str]]] = [
    ("import", ["import", "--sources"]),
    ("scan-list", ["scan", "list"]),
    ("scan-status", ["scan", "status", "someloc"]),
    ("scan-complete", ["scan", "complete", "someloc"]),
    ("scan-resume", ["scan", "resume", "someloc"]),
]
_COMMAND_IDS = [name for name, _ in _COMMANDS]
_COMMAND_ARGS = [args for _, args in _COMMANDS]


@pytest.mark.parametrize("args", _COMMAND_ARGS, ids=_COMMAND_IDS)
def test_explicit_log_level_is_applied(
    recorder: _LevelRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
) -> None:
    """Regression: an explicit ``--log-level`` is applied by every command."""
    monkeypatch.chdir(tmp_path)
    _invoke([*args, "--log-level", "error"])
    assert recorder.effective_level() == "error"


@pytest.mark.parametrize("args", _COMMAND_ARGS, ids=_COMMAND_IDS)
def test_absent_log_level_uses_default_without_project(
    recorder: _LevelRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
) -> None:
    """With no flag and no project config, the built-in default is used."""
    monkeypatch.chdir(tmp_path)
    _invoke(args)
    assert recorder.effective_level() == DEFAULT_LOG_LEVEL.lower()


@pytest.mark.parametrize("args", _COMMAND_ARGS, ids=_COMMAND_IDS)
def test_absent_log_level_falls_back_to_project(
    recorder: _LevelRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
) -> None:
    """With no flag, the project ``log_level`` is used by every command."""
    (tmp_path / "scout.yaml").write_text("log_level: info\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    _invoke(args)
    assert recorder.effective_level() == "info"


def test_import_honors_env_var(
    recorder: _LevelRecorder, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``SCOUT_LOG_LEVEL`` is honored when there is no flag and no project."""
    monkeypatch.chdir(tmp_path)
    _invoke(["import", "--sources"], env={"SCOUT_LOG_LEVEL": "error"})
    assert recorder.effective_level() == "error"


def test_import_project_beats_env(
    recorder: _LevelRecorder, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A project ``log_level`` takes precedence over ``SCOUT_LOG_LEVEL``."""
    (tmp_path / "scout.yaml").write_text("log_level: info\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    _invoke(["import", "--sources"], env={"SCOUT_LOG_LEVEL": "error"})
    assert recorder.effective_level() == "info"


def test_scan_list_explicit_dir_and_level_skips_project(
    recorder: _LevelRecorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``scan list <dir> --log-level X`` must not read the project config.

    With both the scans dir and the level given explicitly, a malformed
    scout.yaml (read_project() raises) must not break the command.
    """

    def _fail() -> object:
        raise AssertionError("read_project() should not be called")

    monkeypatch.setattr(common, "read_project", _fail)
    _invoke(["scan", "list", "somedir", "--log-level", "error"])
    assert recorder.effective_level() == "error"


# =============================================================================
# `scout scan`: the scanjob config *file* log_level is applied to the logger
# =============================================================================

# `scan` resolves a more specific level (from the scanjob config file) than
# process_common_options does, and installs the logging handler itself. Since
# the handler installs once per process, asserting the *applied* console level
# requires a fresh process — hence a subprocess.
_BROKEN_SCANNER = Path(__file__).parent / "broken_scanner.py"
_EXAMPLE_LOGS = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"


def _scanner_name() -> str:
    match = re.search(r"def (\w+)\(", _BROKEN_SCANNER.read_text())
    assert match is not None
    return match.group(1)


def _scan_console_level(tmp_path: Path, scanjob_log_level: str | None) -> str:
    """Run a real ``scout scan`` in a fresh process and report the console gate.

    Returns the level name (e.g. ``"DEBUG"``) of the installed logging
    handler's display level after the scan.
    """
    job = tmp_path / "job.yaml"
    config = f"scanners:\n  - name: {_scanner_name()}\n    file: {_BROKEN_SCANNER}\n"
    if scanjob_log_level is not None:
        config += f"log_level: {scanjob_log_level}\n"
    job.write_text(config, encoding="utf-8")

    args = [
        "scan",
        str(job),
        "-T",
        str(_EXAMPLE_LOGS),
        "--scans",
        str(tmp_path / "scans"),
        "--limit",
        "1",
        "--max-processes",
        "1",
        "--display",
        "none",
        "--model",
        "mockllm/model",
    ]
    snippet = (
        "import logging;"
        "from click.testing import CliRunner;"
        "from inspect_scout._cli.main import scout;"
        "import inspect_scout._util.log as logmod;"
        f"r = CliRunner().invoke(scout, {args!r}, catch_exceptions=False);"
        "assert r.exit_code == 0, r.output;"
        "h = logmod._scout_log_handler['handler'];"
        "print(logging.getLevelName(h.display_level) if h else 'NONE')"
    )
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=str(tmp_path),  # hermetic: no stray scout.yaml on the resolution path
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_scan_applies_scanjob_file_log_level(tmp_path: Path) -> None:
    """Regression: a scanjob config file's ``log_level`` reaches the logger.

    An eager logging init in ``process_common_options`` would install the
    one-shot handler at the less-specific (project/default) level before the
    scanjob file was read, silently dropping its ``log_level``.
    """
    assert _scan_console_level(tmp_path, "debug") == "DEBUG"


def test_scan_default_console_level_without_scanjob_level(tmp_path: Path) -> None:
    """Without a scanjob ``log_level`` (or project/flag), the default is used."""
    assert _scan_console_level(tmp_path, None) == DEFAULT_LOG_LEVEL.upper()
