"""`scout scan -F` applies to transcripts from every source (issue #852)."""

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

# LOGS_DIR holds 217 transcripts: 100 'popularity', 100 'theory_of_mind', 17 other
POPULARITY = "task_set = 'popularity'"

SCANJOB = f"""
from inspect_scout import ScanJob, scanjob, transcripts_from
from broken_scanner import always_fails

@scanjob
def job() -> ScanJob:
    return ScanJob(transcripts=transcripts_from({str(LOGS_DIR)!r}), scanners=[always_fails()])
"""


@pytest.mark.parametrize(
    "project, scan_file, transcripts",
    [
        pytest.param(f"transcripts: {LOGS_DIR}\n", "scanner", [], id="project"),
        pytest.param(
            f"transcripts: {LOGS_DIR}\n"
            "filter: \"task_set in ('popularity', 'theory_of_mind')\"\n",
            "scanner",
            [],
            id="project-with-filter",
        ),
        pytest.param(None, "scanjob", [], id="scanjob"),
        pytest.param(None, "scanner", ["-T", str(LOGS_DIR)], id="cli"),
    ],
)
def test_cli_scan_filter(
    project: str | None,
    scan_file: str,
    transcripts: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(BROKEN_SCANNER.parent))
    (tmp_path / ".env").write_text("")
    for name in list(os.environ):
        if name.startswith("SCOUT_"):
            monkeypatch.delenv(name)
    if project is not None:
        (tmp_path / "scout.yaml").write_text(project)
    scanjob_file = tmp_path / "scanjob.py"
    scanjob_file.write_text(SCANJOB)

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
            str(scanjob_file if scan_file == "scanjob" else BROKEN_SCANNER),
            *transcripts,
            "-F",
            POPULARITY,
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
    assert statuses[0].spec.transcripts is not None
    assert len(statuses[0].spec.transcripts.transcript_ids) == 100
