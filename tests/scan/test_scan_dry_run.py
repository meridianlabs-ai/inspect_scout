import pathlib

import inspect_scout
import pytest

LOGS_DIR = (
    pathlib.Path(__file__).resolve().parent.parent / "recorder" / "logs"
).resolve()


@inspect_scout.scanner(name="dry_run_never_called", messages="all")
def dry_run_never_called_factory() -> inspect_scout.Scanner[inspect_scout.Transcript]:
    async def scan_transcript(
        transcript: inspect_scout.Transcript,
    ) -> inspect_scout.Result:
        raise RuntimeError("scanner should not be executed during dry_run")

    return scan_transcript


@pytest.mark.parametrize("limit", [1, 2])
def test_scan_dry_run_does_not_execute_scanners_or_create_results_dir(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str], limit: int
) -> None:
    results_dir = tmp_path / "scans"

    status = inspect_scout.scan(
        scanners=[dry_run_never_called_factory()],
        transcripts=inspect_scout.transcripts_from(LOGS_DIR),
        results=str(results_dir),
        limit=limit,
        dry_run=True,
        display="plain",
    )

    assert status.complete
    assert not results_dir.exists()
    assert f"| dry_run_never_called |     {limit:,} |" in capsys.readouterr().out
