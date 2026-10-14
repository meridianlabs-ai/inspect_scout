"""A task's ViewerConfig(trust_content=...) reaches transcripts and scan results."""

from pathlib import Path

import pandas as pd
import pytest
from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.viewer import ViewerConfig
from inspect_scout import Result, Scanner, scan, scanner, transcripts_from
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript, TranscriptContent

# task name -> the trust_content its log records
TASK_TRUST: dict[str, bool | None] = {
    "untrusted": False,
    "trusted": True,
    "unset": None,
    "no_viewer": None,
}


def _viewer(name: str) -> ViewerConfig | None:
    if name == "no_viewer":
        return None
    return ViewerConfig(trust_content=TASK_TRUST[name])


@pytest.fixture(scope="module")
def log_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    log_dir = tmp_path_factory.mktemp("logs")
    tasks = [
        Task(dataset=[Sample(input="hi")], name=name, viewer=_viewer(name))
        for name in TASK_TRUST
    ]
    logs = eval(tasks, model="mockllm/model", log_dir=str(log_dir), display="none")
    assert all(log.status == "success" for log in logs)
    return log_dir


@pytest.mark.asyncio
async def test_eval_log_index_and_read_carry_trust_content(log_dir: Path) -> None:
    async with transcripts_from(str(log_dir)).reader() as reader:
        seen: dict[str, bool | None] = {}
        async for info in reader.index():
            assert info.task_set is not None
            full = await reader.read(info, TranscriptContent(messages="all"))
            assert full.trust_content is info.trust_content
            seen[info.task_set] = info.trust_content

    assert seen == TASK_TRUST


@pytest.mark.asyncio
async def test_parquet_db_carries_trust_content(log_dir: Path, tmp_path: Path) -> None:
    db = ParquetTranscriptsDB(str(tmp_path / "db"))
    await db.connect()
    try:
        await db.insert(transcripts_from(str(log_dir)))
    finally:
        await db.disconnect()

    async with transcripts_from(str(tmp_path / "db")).reader() as reader:
        seen = {info.task_set: info.trust_content async for info in reader.index()}

    assert seen == TASK_TRUST


@scanner(name="echo", messages="all")
def echo_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True, explanation="**echo**")

    return scan_transcript


def test_scan_results_record_transcript_trust_content(
    log_dir: Path, tmp_path: Path
) -> None:
    status = scan(
        scanners=[echo_scanner()],
        transcripts=transcripts_from(str(log_dir)),
        scans=str(tmp_path),
        display="none",
    )
    assert status.complete

    df = scan_results_df(status.location, scanner="echo").scanners["echo"]
    seen = {
        task_set: None if pd.isna(trust) else bool(trust)
        for task_set, trust in zip(
            df["transcript_task_set"], df["transcript_trust_content"], strict=True
        )
    }

    assert seen == TASK_TRUST
