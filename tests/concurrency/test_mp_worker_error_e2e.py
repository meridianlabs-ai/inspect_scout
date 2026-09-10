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
    mode: str = "normal",
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
        "--mode",
        mode,
    ]
    if fail_on_error:
        command.append("--fail-on-error")
    repository = Path(__file__).resolve().parents[2]
    env = dict(
        os.environ,
        SCOUT_DIAGNOSTICS="false",
        SCOUT_DISPLAY="plain",
        PYTHONPATH=str(repository / "src"),
    )
    with subprocess.Popen(
        command,
        cwd=repository,
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
    expected_exit = 130 if mode == "interrupt" and sys.version_info < (3, 11) else 0
    assert process.returncode == expected_exit, f"{stdout}\n{stderr}"
    report = cast(dict[str, Any], json.loads((tmp_path / "report.json").read_text()))
    assert report["native_interrupt"] == (expected_exit == 130)
    assert (
        Path(report["scout_source"]).resolve()
        == repository / "src/inspect_scout/__init__.py"
    )
    assert report["registry_restored"]
    assert report["sigint_restored"]
    assert not report["strategy_active"]
    assert not report["worker_pids_still_alive"]
    if mode == "collector":
        return report
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


@pytest.mark.parametrize(
    "provider,fail_on_error,type_name",
    [("generic", True, "ValueError"), ("prerequisite", False, "PrerequisiteError")],
)
def test_non_provider_fatal_errors_keep_existing_semantics(
    tmp_path: Path,
    provider: str,
    fail_on_error: bool,
    type_name: str,
) -> None:
    report = _run_scan(
        tmp_path, provider=provider, fail_on_error=fail_on_error, max_processes=2
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    assert not report["errors"]
    assert type_name in report["parent_display"]
    assert f"{provider} worker failure fixture" in report["parent_display"]
    assert "_raise_provider_error" in report["parent_display"]


@pytest.mark.parametrize("mode", ["multiple", "pressure"])
def test_simultaneous_worker_failures_finish_with_useful_diagnostic(
    tmp_path: Path,
    mode: str,
) -> None:
    report = _run_scan(
        tmp_path, provider="generic", fail_on_error=True, max_processes=2, mode=mode
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    assert len({item["pid"] for item in report["attempts"]}) == 2
    assert "simultaneous worker failure" in report["parent_display"]
    assert "scan_transcript" in report["parent_display"]


@pytest.mark.parametrize("mode", ["cancel", "interrupt"])
def test_interruption_keeps_precedence_over_cleanup_failure(
    tmp_path: Path,
    mode: str,
) -> None:
    report = _run_scan(
        tmp_path, provider="generic", fail_on_error=True, max_processes=2, mode=mode
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    assert "Aborted!" in report["parent_display"]
    assert "cleanup failure fixture" not in report["parent_display"]


@pytest.mark.parametrize("mode", ["cleanup", "primary_cleanup", "keyboard_cleanup"])
def test_shutdown_error_precedence(tmp_path: Path, mode: str) -> None:
    report = _run_scan(
        tmp_path,
        provider="anthropic",
        fail_on_error=True,
        max_processes=2,
        mode=mode,
        api="sync",
    )
    diagnostic = report["parent_display"]
    if mode == "cleanup":
        assert not report["complete"]
        assert "cleanup failure fixture" in diagnostic
    elif mode == "primary_cleanup":
        assert not report["complete"]
        assert "anthropic.APIStatusError" in diagnostic
        assert "scout worker failure fixture" in diagnostic
        assert "cleanup failure fixture" not in diagnostic
    else:
        # The strategy's existing KeyboardInterrupt handler returns normally.
        assert "cleanup failure fixture" not in diagnostic
        assert report["values"] == ["ok", "ok"]


def test_collector_read_failure_remains_fatal(tmp_path: Path) -> None:
    report = _run_scan(
        tmp_path,
        provider="generic",
        fail_on_error=True,
        max_processes=2,
        mode="collector",
        api="sync",
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    assert "OSError" in report["parent_display"]
    assert "collector read failure fixture" in report["parent_display"]
    assert "no running event loop" not in report["parent_display"]


def test_malformed_worker_type_still_reaches_parent(tmp_path: Path) -> None:
    report = _run_scan(
        tmp_path, provider="malformed_type", fail_on_error=True, max_processes=2
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    for detail in (
        "LocalError",
        "malformed type worker failure fixture",
        "_raise_provider_error",
    ):
        assert detail in report["parent_display"]


@pytest.mark.parametrize("mode", ["parent_group", "parent_context"])
def test_parent_error_group_preserves_failures_without_incidental_context(
    tmp_path: Path, mode: str
) -> None:
    report = _run_scan(
        tmp_path,
        provider="generic",
        fail_on_error=True,
        max_processes=2,
        mode=mode,
        api="sync",
    )
    assert not report["complete"]
    assert not report["persisted_complete"]
    diagnostic = report["parent_display"]
    if mode == "parent_group":
        assert "first parent failure fixture" in diagnostic
        assert "second parent failure fixture" in diagnostic
    else:
        assert "actual parent failure fixture" in diagnostic
        assert "incidental parent context fixture" not in diagnostic
        assert "actual parent failure fixture" in report["strategy_traceback"]
        assert "incidental parent context fixture" not in report["strategy_traceback"]
