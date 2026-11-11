"""Options are honoured on either side of FILE in `scout scan`."""

import importlib
import os
from pathlib import Path
from typing import Any, Callable

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
