"""Tests that CLI commands honor ``--log-level``.

These commands (``import``, ``scan list``, ``scan status``, ``scan complete``,
``scan resume``) previously ignored ``--log-level`` entirely. Each test asserts
the level that is actually committed to logging initialization, covering the
explicit / absent / project-configured cases.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from click.core import ParameterSource
from click.testing import CliRunner
from inspect_ai._util.constants import DEFAULT_LOG_LEVEL
from inspect_scout._cli.common import CommonOptions, resolve_common_log_level
from inspect_scout._cli.main import scout

# =============================================================================
# resolve_common_log_level (unit)
# =============================================================================


def _common_options(log_level: str) -> CommonOptions:
    return CommonOptions(
        display="none",
        log_level=log_level,
        debug=False,
        debug_port=5678,
        fail_on_error=False,
    )


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


@pytest.mark.parametrize(
    "source, expected",
    [
        # only an explicit command-line flag overrides project/default config
        (ParameterSource.COMMANDLINE, "debug"),
        (ParameterSource.ENVIRONMENT, None),
        (ParameterSource.DEFAULT, None),
        (ParameterSource.DEFAULT_MAP, None),
    ],
)
def test_resolve_common_log_level(
    mock_ctx: MagicMock, source: ParameterSource, expected: str | None
) -> None:
    mock_ctx.set_parameter_source("log_level", source)
    result = resolve_common_log_level(mock_ctx, _common_options("debug"))
    assert result == expected


# =============================================================================
# end-to-end: the resolved level reaches logging initialization
# =============================================================================


class _StopInit(Exception):
    """Raised by the recorder to abort a command immediately after log init."""


class _LevelRecorder:
    def __init__(self) -> None:
        self.level: str | None = None
        self.called: bool = False

    def __call__(self, log_level: str | None, **kwargs: Any) -> None:
        self.level = log_level
        self.called = True
        raise _StopInit()

    def effective_level(self) -> str:
        """The level that would actually be applied (None => built-in default)."""
        assert self.called, "command did not initialize logging"
        return (self.level or DEFAULT_LOG_LEVEL).lower()


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _LevelRecorder:
    """Capture the log level committed to ``top_level_async_init``.

    All five commands funnel the resolved level into ``top_level_async_init``
    (defined in ``inspect_scout._init``): ``import`` imports it lazily from
    ``_init``; ``scan list``/``scan status`` bind it at import time; ``scan
    complete``/``scan resume`` reach it via ``scan_complete()``/``scan_resume()``
    in ``inspect_scout._scan``. Patch every binding a command actually reaches.
    """
    import inspect_scout._cli.scan_list as scan_list_mod
    import inspect_scout._cli.scan_status as scan_status_mod
    import inspect_scout._init as init_mod
    import inspect_scout._scan as scan_mod

    rec = _LevelRecorder()
    monkeypatch.setattr(init_mod, "top_level_async_init", rec)
    monkeypatch.setattr(scan_mod, "top_level_async_init", rec)
    monkeypatch.setattr(scan_list_mod, "top_level_async_init", rec)
    monkeypatch.setattr(scan_status_mod, "top_level_async_init", rec)
    return rec


# (id, cli args, whether the command resolves a project-configured log level)
_COMMANDS: list[tuple[str, list[str], bool]] = [
    ("import", ["import", "--sources"], False),
    ("scan-list", ["scan", "list"], True),
    ("scan-status", ["scan", "status", "someloc"], True),
    ("scan-complete", ["scan", "complete", "someloc"], True),
    ("scan-resume", ["scan", "resume", "someloc"], True),
]
_COMMAND_IDS = [command[0] for command in _COMMANDS]
_COMMAND_ARGS = [command[1] for command in _COMMANDS]
_COMMAND_ARGS_AWARE = [(command[1], command[2]) for command in _COMMANDS]


def _invoke(args: list[str]) -> None:
    # commands abort via _StopInit once the level is captured
    CliRunner().invoke(scout, args, catch_exceptions=True)


@pytest.mark.parametrize("args", _COMMAND_ARGS, ids=_COMMAND_IDS)
def test_explicit_log_level_is_applied(
    recorder: _LevelRecorder, args: list[str]
) -> None:
    """An explicit ``--log-level`` is committed to logging init for every command."""
    _invoke([*args, "--log-level", "error"])
    assert recorder.effective_level() == "error"


@pytest.mark.parametrize("args", _COMMAND_ARGS, ids=_COMMAND_IDS)
def test_absent_log_level_uses_default_without_project(
    recorder: _LevelRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
) -> None:
    """With no flag and no project config, the built-in default level is used."""
    monkeypatch.chdir(tmp_path)
    _invoke(args)
    assert recorder.effective_level() == DEFAULT_LOG_LEVEL.lower()


@pytest.mark.parametrize("args, project_aware", _COMMAND_ARGS_AWARE, ids=_COMMAND_IDS)
def test_absent_log_level_falls_back_to_project(
    recorder: _LevelRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    args: list[str],
    project_aware: bool,
) -> None:
    """With no flag, project ``log_level`` is used by project-aware commands.

    ``import`` is not project-scoped, so it keeps the default level.
    """
    (tmp_path / "scout.yaml").write_text("log_level: info\n")
    monkeypatch.chdir(tmp_path)
    _invoke(args)
    expected = "info" if project_aware else DEFAULT_LOG_LEVEL.lower()
    assert recorder.effective_level() == expected


def test_scan_list_explicit_dir_and_level_skips_project(
    recorder: _LevelRecorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`scan list <dir> --log-level X` must not read the project config.

    With both the scans dir and the log level specified there is nothing to
    resolve from scout.yaml, so a malformed scout.yaml must not break the
    command (read_project() raises on invalid config).
    """
    import inspect_scout._cli.scan_list as scan_list_mod

    def _fail() -> object:
        raise AssertionError("read_project() should not be called")

    monkeypatch.setattr(scan_list_mod, "read_project", _fail)
    _invoke(["scan", "list", "somedir", "--log-level", "error"])
    assert recorder.effective_level() == "error"
