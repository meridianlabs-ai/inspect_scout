import os
import pathlib
import re
from typing import Any

import inspect_scout
import pytest
from inspect_ai.model import GenerateConfig

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
        scans=str(results_dir),
        limit=limit,
        dry_run=True,
        display="plain",
    )

    assert status.complete
    assert not results_dir.exists()
    assert re.match(
        rf"|\s+dry_run_never_called\s+|\s+{limit:,}", capsys.readouterr().out
    )


@pytest.mark.parametrize(
    ("config", "options", "max_connections"),
    [
        pytest.param({}, {"max_processes": 1}, 7, id="max_transcripts-by-default"),
        pytest.param(
            {"adaptive_connections": True},
            {"max_processes": 1},
            None,
            id="adaptive_connections-single-process",
        ),
        pytest.param(
            {"adaptive_connections": True},
            {"max_processes": 4},
            7,
            id="adaptive_connections-may-fork",
            marks=pytest.mark.skipif(
                os.name == "nt", reason="Windows scans are always single-process"
            ),
        ),
        pytest.param(
            {"adaptive_connections": True, "batch": True},
            {"max_processes": 1},
            7,
            id="adaptive_connections-batch",
        ),
        pytest.param(
            {"adaptive_connections": False},
            {"max_processes": 1},
            7,
            id="adaptive_connections-opt-out",
        ),
        pytest.param(
            {"adaptive_connections": True, "max_connections": 3},
            {"max_processes": 1},
            3,
            id="adaptive_connections-explicit-max_connections",
        ),
    ],
)
def test_max_connections_follows_max_transcripts_unless_adaptive_connections(
    config: dict[str, Any], options: dict[str, Any], max_connections: int | None
) -> None:
    status = inspect_scout.scan(
        scanners=[dry_run_never_called_factory()],
        transcripts=inspect_scout.transcripts_from(LOGS_DIR),
        model="mockllm/model",
        model_config=GenerateConfig(**config),
        max_transcripts=7,
        dry_run=True,
        display="none",
        **options,
    )

    assert status.spec.model is not None
    assert status.spec.model.config.max_connections == max_connections
