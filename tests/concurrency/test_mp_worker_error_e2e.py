"""Issue #616: fatal SDK errors must remain useful in the parent display."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.skipif(
    os.name == "nt", reason="Scout uses single process on Windows"
)


def _run_scan(
    tmp_path: Path,
    *,
    provider: str,
    fail_on_error: bool,
    max_processes: int,
    api: str = "async",
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "tests.concurrency.worker_error_scenario",
        "--root",
        str(tmp_path),
        "--provider",
        provider,
        "--max-processes",
        str(max_processes),
        "--api",
        api,
    ]
    if fail_on_error:
        command.append("--fail-on-error")
    env = dict(os.environ, SCOUT_DIAGNOSTICS="false", SCOUT_DISPLAY="plain")
    with subprocess.Popen(
        command,
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=60)
        except BaseException:
            # Also bound failure cleanup when pytest itself is interrupted.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise

    (tmp_path / "child-stdout.log").write_text(stdout)
    (tmp_path / "child-stderr.log").write_text(stderr)
    assert process.returncode == 0, f"{stdout}\n{stderr}"
    report = cast(dict[str, Any], json.loads((tmp_path / "report.json").read_text()))
    failing = next(
        item for item in report["attempts"] if item["transcript_id"] == "failing"
    )
    if max_processes == 2:
        assert failing["pid"] != report["parent_pid"]
        assert failing["start_method"] == "spawn"
    else:
        assert failing["pid"] == report["parent_pid"]
    return report


@pytest.mark.parametrize("provider,status_code", [("anthropic", 529), ("openai", 429)])
@pytest.mark.parametrize("api", ["sync", "async"])
def test_fatal_provider_error_reaches_parent(
    tmp_path: Path, provider: str, status_code: int, api: str
) -> None:
    report = _run_scan(
        tmp_path, provider=provider, fail_on_error=True, max_processes=2, api=api
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    diagnostic = report["parent_display"]
    assert "APIStatusError.__init__()" not in diagnostic, diagnostic
    for detail in (
        f"{provider}.APIStatusError",
        "scout worker failure fixture",
        "_raise_provider_error",
        str(status_code),
        "req_scout_616",
    ):
        assert detail in diagnostic, diagnostic


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_default_provider_error_records_job_and_continues(
    tmp_path: Path, provider: str
) -> None:
    report = _run_scan(
        tmp_path, provider=provider, fail_on_error=False, max_processes=2, api="sync"
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    assert len(report["errors"]) == 1
    error = report["errors"][0]
    assert error["transcript_id"] == "failing"
    assert error["error"] == "scout worker failure fixture"
    assert f"{provider}.APIStatusError" in error["traceback"]
    assert "_raise_provider_error" in error["traceback"]
    assert report["values"] == ["ok"]
    assert {item["transcript_id"] for item in report["attempts"]} == {
        "failing",
        "successful",
    }


@pytest.mark.parametrize("provider", ["anthropic", "openai"])
def test_single_process_provider_error_keeps_diagnostic(
    tmp_path: Path, provider: str
) -> None:
    report = _run_scan(tmp_path, provider=provider, fail_on_error=True, max_processes=1)
    assert not report["complete"]
    assert not report["persisted_complete"]
    assert "APIStatusError" in report["parent_display"]
    assert "scout worker failure fixture" in report["parent_display"]
    assert "_raise_provider_error" in report["parent_display"]
    assert "missing 2 required keyword-only arguments" not in report["parent_display"]
