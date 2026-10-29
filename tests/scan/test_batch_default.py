"""Batch transcript defaults follow the effective scan configuration."""

import os
from pathlib import Path
from typing import NamedTuple

import pytest
from inspect_ai.model import BatchConfig, GenerateConfig
from inspect_scout import (
    Result,
    ScanJob,
    Scanner,
    ScannerInput,
    Transcript,
    scan,
    scanner,
    transcripts_from,
)

LOGS_DIR = Path(__file__).resolve().parent.parent / "recorder" / "logs"
BatchValue = bool | int | BatchConfig | None


class BatchCase(NamedTuple):
    name: str
    expected_cap: int
    batch: BatchValue = None
    job_batch: BatchValue = None
    project_cap: int | None = None
    job_cap: int | None = None
    cap: int | None = None
    connections: int | None = None
    project_batch: bool | None = None


CASES = [
    BatchCase(name="ordinary", expected_cap=25),
    BatchCase(name="function-batch", expected_cap=10000, batch=True),
    BatchCase(name="batch-size", expected_cap=10000, batch=1000),
    BatchCase(name="batch-config", expected_cap=10000, batch=BatchConfig(size=1000)),
    BatchCase(name="job-batch", expected_cap=10000, job_batch=True),
    BatchCase(name="enable-job-batch", expected_cap=10000, job_batch=False, batch=True),
    BatchCase(name="disable-job-batch", expected_cap=25, job_batch=True, batch=False),
    BatchCase(name="project-cap", expected_cap=61, project_cap=61, batch=True),
    BatchCase(
        name="job-over-project",
        expected_cap=71,
        project_cap=61,
        job_cap=71,
        batch=True,
    ),
    BatchCase(
        name="function-over-job-and-project",
        expected_cap=79,
        project_cap=61,
        job_cap=71,
        cap=79,
        batch=True,
    ),
    BatchCase(
        name="explicit-connections", expected_cap=10000, batch=True, connections=7
    ),
    BatchCase(name="project-batch", expected_cap=10000, project_batch=True),
]


@scanner(name="batch_default_never_called", messages="all")
def batch_default_never_called() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        raise AssertionError("scanner must not execute during dry run")

    return scan_transcript


def _fresh_config(
    batch: BatchValue, connections: int | None = None
) -> GenerateConfig | None:
    if batch is None and connections is None:
        return None
    return GenerateConfig(
        batch=batch.model_copy(deep=True) if isinstance(batch, BatchConfig) else batch,
        max_connections=connections,
    )


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_scan_batch_default(
    case: BatchCase, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("")
    for name in list(os.environ):
        if name.startswith("SCOUT_"):
            monkeypatch.delenv(name)

    project = ""
    if case.project_cap is not None:
        project += f"max_transcripts: {case.project_cap}\n"
    if case.project_batch is not None:
        project += (
            "model: mockllm/model\ngenerate_config:\n"
            f"  batch: {str(case.project_batch).lower()}\n"
        )
    if project:
        (tmp_path / "scout.yaml").write_text(project)

    scanner_list = [batch_default_never_called()]
    scanners: list[Scanner[ScannerInput]] | ScanJob = scanner_list
    if case.job_batch is not None or case.job_cap is not None:
        scanners = ScanJob(
            scanners=scanner_list,
            generate_config=_fresh_config(case.job_batch),
            max_transcripts=case.job_cap,
        )
    results_dir = tmp_path / "scans"

    status = scan(
        scanners=scanners,
        transcripts=transcripts_from(LOGS_DIR),
        scans=str(results_dir),
        model="mockllm/model",
        model_config=_fresh_config(case.batch, case.connections),
        max_transcripts=case.cap,
        max_processes=1,
        limit=1,
        dry_run=True,
        display="none",
    )

    assert status.complete
    assert not status.errors
    assert not results_dir.exists()
    assert status.spec.options.max_transcripts == case.expected_cap
    assert status.spec.model is not None
    assert status.spec.model.config.max_connections == (
        case.connections if case.connections is not None else case.expected_cap
    )
