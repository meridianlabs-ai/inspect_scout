"""Exercise batch defaults through the real scan CLI and public scan API."""

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
    "options, expected_cap",
    [
        pytest.param([], 25, id="ordinary"),
        pytest.param(["--batch"], 10000, id="batch"),
        pytest.param(["--batch=1000"], 10000, id="batch-size"),
        pytest.param(["--batch", "--max-transcripts", "83"], 83, id="explicit-cap"),
    ],
)
def test_cli_scan_batch_default(
    options: list[str],
    expected_cap: int,
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
    results_dir = tmp_path / "scans"
    result = CliRunner().invoke(
        scout,
        [
            "scan",
            str(BROKEN_SCANNER),
            "-T",
            str(LOGS_DIR),
            "--scans",
            str(results_dir),
            "--limit",
            "1",
            "--max-processes",
            "1",
            "--display",
            "none",
            "--model",
            "mockllm/model",
            "--dry-run",
            *options,
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert len(statuses) == 1
    status = statuses[0]
    assert status.complete
    assert not status.errors
    assert not results_dir.exists()
    assert status.spec.options.max_transcripts == expected_cap
    assert status.spec.model is not None
    assert status.spec.model.config.max_connections == expected_cap
