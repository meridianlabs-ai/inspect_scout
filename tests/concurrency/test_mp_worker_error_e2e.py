"""Issue #616: fatal SDK errors must remain useful in the parent display."""

import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.skipif(
    os.name == "nt", reason="Scout uses single process on Windows"
)


class ProviderDiagnosticMismatch(Exception):
    """Provider details are missing while output matches the #5399 signature."""


def _provider_details(provider: str, status_code: int) -> tuple[str, ...]:
    return (
        f"{provider}.APIStatusError",
        "scout worker failure fixture",
        "_raise_provider_error",
        str(status_code),
        "req_scout_616",
    )


def _compact(text: str) -> str:
    """Drop the wrapping Rich applies, so a phrase check holds at any width.

    The parent display is a Rich panel wrapped to the console width, so an
    expected phrase can arrive split across lines with the panel's borders
    between the halves. Where a line breaks depends on the console width and on
    the length of the absolute paths in the traceback, so both sides of every
    comparison lose their whitespace and box-drawing glyphs first.
    """
    return re.sub(r"[\s\u2500-\u257f]+", "", text)


def _missing_provider_details(
    diagnostic: str, provider: str, status_code: int
) -> list[str]:
    compact = _compact(diagnostic)
    return [
        detail
        for detail in _provider_details(provider, status_code)
        if _compact(detail) not in compact
    ]


def _has_issue_5399_signature(diagnostic: str) -> bool:
    compact = _compact(diagnostic)
    return all(
        _compact(fragment) in compact
        for fragment in (
            "RuntimeError: no running event loop",
            "inspect_ai/_util/_async.py",
            "in run_coroutine",
        )
    )


def _assert_mandatory_provider_invariants(report: dict[str, Any]) -> str:
    assert not report["complete"], report
    assert not report["persisted_complete"], report
    diagnostic = cast(str, report["parent_display"])
    assert _compact("APIStatusError.__init__()") not in _compact(diagnostic), diagnostic
    return diagnostic


def _check_sync_provider_diagnostic(
    diagnostic: str, provider: str, status_code: int
) -> None:
    missing = _missing_provider_details(diagnostic, provider, status_code)
    if not missing:
        return
    if _has_issue_5399_signature(diagnostic):
        raise ProviderDiagnosticMismatch(
            "provider details are missing and output matches the #5399 signature; "
            f"missing={missing}\n{diagnostic}"
        )
    assert not missing, (
        "provider details disappeared without the #5399 signature; "
        f"missing={missing}\n{diagnostic}"
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
    assert process.returncode == 0, f"{stdout}\n{stderr}"
    report = cast(dict[str, Any], json.loads((tmp_path / "report.json").read_text()))
    assert (
        Path(report["scout_source"]).resolve()
        == repository / "src/inspect_scout/__init__.py"
    )
    assert report["registry_restored"]
    assert report["sigint_restored"]
    assert not report["strategy_active"]
    assert not report["worker_pids_still_alive"]
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
    diagnostic = _assert_mandatory_provider_invariants(report)
    if api == "async":
        missing = _missing_provider_details(diagnostic, provider, status_code)
        assert not missing, f"missing={missing}\n{diagnostic}"


@pytest.mark.parametrize(
    "provider,status_code",
    [
        pytest.param(
            "anthropic",
            529,
            marks=pytest.mark.xfail(
                strict=False,
                raises=ProviderDiagnosticMismatch,
                reason=("https://github.com/UKGovernmentBEIS/inspect_ai/issues/5399"),
            ),
        ),
        pytest.param(
            "openai",
            429,
            marks=pytest.mark.xfail(
                strict=False,
                raises=ProviderDiagnosticMismatch,
                reason=("https://github.com/UKGovernmentBEIS/inspect_ai/issues/5399"),
            ),
        ),
    ],
)
def test_sync_fatal_provider_error_diagnostic(
    tmp_path: Path, provider: str, status_code: int
) -> None:
    report = _run_scan(
        tmp_path,
        provider=provider,
        fail_on_error=True,
        max_processes=2,
        api="sync",
    )
    diagnostic = _assert_mandatory_provider_invariants(report)
    _check_sync_provider_diagnostic(diagnostic, provider, status_code)


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
    display = _compact(cast(str, report["parent_display"]))
    assert _compact("APIStatusError") in display
    assert _compact("scout worker failure fixture") in display
    assert _compact("_raise_provider_error") in display
    assert _compact("missing 2 required keyword-only arguments") not in display


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
    display = _compact(cast(str, report["parent_display"]))
    assert _compact(type_name) in display
    assert _compact(f"{provider} worker failure fixture") in display
    assert _compact("_raise_provider_error") in display


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
    display = _compact(cast(str, report["parent_display"]))
    assert _compact("simultaneous worker failure") in display
    assert _compact("scan_transcript") in display
