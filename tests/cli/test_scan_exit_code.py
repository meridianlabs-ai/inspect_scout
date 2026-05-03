"""Tests for CLI exit codes from `scout scan`."""

from pathlib import Path

from click.testing import CliRunner
from inspect_scout._cli.main import scout

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"
BROKEN_SCANNER = Path(__file__).parent / "broken_scanner.py"


def _invoke_scan(tmp_path: Path, *, fail_on_error: bool) -> int:
    scans_dir = tmp_path / "scans"

    args = [
        "scan",
        str(BROKEN_SCANNER),
        "-T",
        str(LOGS_DIR),
        "--scans",
        str(scans_dir),
        "--limit",
        "1",
        "--max-processes",
        "1",
        "--display",
        "none",
        "--model",
        "mockllm/model",
    ]
    if fail_on_error:
        args.append("--fail-on-error")

    runner = CliRunner()
    result = runner.invoke(scout, args, catch_exceptions=False)
    return result.exit_code


def test_scan_fail_on_error_exits_nonzero(tmp_path: Path) -> None:
    """`scout scan --fail-on-error` must exit non-zero when a scanner fails."""
    assert _invoke_scan(tmp_path, fail_on_error=True) != 0


def test_scan_without_fail_on_error_exits_zero_on_scanner_error(
    tmp_path: Path,
) -> None:
    """Without `--fail-on-error` scanner errors are captured into results and exit is 0."""
    assert _invoke_scan(tmp_path, fail_on_error=False) == 0
