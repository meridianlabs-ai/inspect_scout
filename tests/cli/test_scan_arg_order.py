"""Options are honoured on either side of FILE or a subcommand in `scout scan`."""

import importlib
import os
from pathlib import Path
from typing import Any, Callable

import click
import pytest
from click.testing import CliRunner
from inspect_scout import Status
from inspect_scout._cli.main import scout

LOGS_DIR = Path(__file__).resolve().parent.parent / "recorder" / "logs"
BROKEN_SCANNER = Path(__file__).parent / "broken_scanner.py"


@pytest.mark.parametrize(
    "before_file, expected_max_transcripts",
    [
        pytest.param([], 25, id="file-first"),
        pytest.param(["--dry-run"], 25, id="flag"),
        pytest.param(["--dry-run", "--fail-on-error"], 25, id="flags"),
        pytest.param(["--max-transcripts", "7"], 7, id="opt-value"),
        pytest.param(["--max-transcripts=7"], 7, id="opt-equals-value"),
    ],
)
def test_cli_scan_options_after_file_are_honoured(
    before_file: list[str],
    expected_max_transcripts: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("")
    for name in list(os.environ):
        if name.startswith("SCOUT_"):
            monkeypatch.delenv(name)

    module = importlib.import_module("inspect_scout._cli.scan")
    original_scan: Callable[..., Status] = module.scan
    statuses: list[Status] = []

    def observe_scan(*args: Any, **kwargs: Any) -> Status:
        status = original_scan(*args, **kwargs)
        statuses.append(status)
        return status

    monkeypatch.setattr(module, "scan", observe_scan)
    result = CliRunner().invoke(
        scout,
        [
            "scan",
            *before_file,
            str(BROKEN_SCANNER),
            "-T",
            str(LOGS_DIR),
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
            "--dry-run",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert len(statuses) == 1
    spec = statuses[0].spec
    assert spec.transcripts is not None
    assert spec.options.limit == 1
    assert spec.options.max_transcripts == expected_max_transcripts


@pytest.mark.parametrize(
    "args, subcommand, expected_params",
    [
        pytest.param(
            ["--dry-run", "resume", "./results", "--fail-on-error"],
            "resume",
            {"scan_location": "./results", "fail_on_error": True},
            id="flag-resume",
        ),
        pytest.param(
            ["--fail-on-error", "list", "./results", "--display", "none"],
            "list",
            {"scans_dir": "./results", "display": "none"},
            id="flag-list",
        ),
        pytest.param(
            ["--limit", "3", "list", "./results", "--display", "none"],
            "list",
            {"scans_dir": "./results", "display": "none"},
            id="opt-value-list",
        ),
    ],
)
def test_cli_scan_subcommand_options_after_group_options_are_honoured(
    args: list[str],
    subcommand: str,
    expected_params: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module(f"inspect_scout._cli.scan_{subcommand}")
    received: list[dict[str, Any]] = []

    def stop_after_parse(ctx: click.Context, *args: Any, **kwargs: Any) -> None:
        received.append(dict(ctx.params))
        ctx.exit(0)

    monkeypatch.setattr(module, "process_common_options", stop_after_parse)
    result = CliRunner().invoke(scout, ["scan", *args], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert len(received) == 1
    assert expected_params.items() <= received[0].items()


def test_cli_scan_subcommand_help_after_group_flag() -> None:
    result = CliRunner().invoke(
        scout, ["scan", "--fail-on-error", "resume", "--help"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.output
    assert "Usage: scout scan resume [OPTIONS] SCAN_LOCATION" in result.output
