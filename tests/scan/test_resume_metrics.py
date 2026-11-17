"""Resumed metrics include retained results as well as successful retries."""

import asyncio
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_ai.scorer import mean, stderr
from inspect_scout import (
    Result,
    Scanner,
    Transcript,
    scan,
    scan_resume,
    scanner,
    transcripts_db,
    transcripts_from,
)

from tests.helpers import temp_active_scans_store

LOGS_DIR = Path(__file__).parents[2] / "examples" / "scanner" / "logs"
FIRST_ID = "MUBxLNC9YwakjPFXaFuEZ4"


@scanner(name="resume_metrics_retry", messages="all", metrics=[mean(), stderr()])
def retry_metrics(marker: str, first_value: int) -> Scanner[Transcript]:
    async def run(transcript: Transcript) -> Result:
        if transcript.transcript_id == FIRST_ID:
            return Result(value=first_value)
        if not Path(marker).exists():
            raise RuntimeError("Transient scanner failure")
        return Result(value=1 - first_value)

    return run


@scanner(name="resume_metrics_untouched", messages="all", metrics=[mean(), stderr()])
def untouched_metrics(first_value: int) -> Scanner[Transcript]:
    async def run(transcript: Transcript) -> Result:
        return Result(
            value=first_value
            if transcript.transcript_id == FIRST_ID
            else 1 - first_value
        )

    return run


@pytest.mark.parametrize(("processes", "first_value"), [(1, 0), (2, 1)])
def test_resume_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, processes: int, first_value: int
) -> None:
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "buffer"))
    marker = tmp_path / "recovered"
    with temp_active_scans_store():
        initial = scan(
            scanners=[
                retry_metrics(str(marker), first_value),
                untouched_metrics(first_value),
            ],
            transcripts=transcripts_from(LOGS_DIR),
            scans=str(tmp_path / "interrupted"),
            limit=2,
            max_processes=processes,
            display="none",
        )
        assert not initial.complete and len(initial.errors) == 1
        still_failing = scan_resume(initial.location, display="none")
        assert not still_failing.complete and len(still_failing.errors) == 1
        for name in ("resume_metrics_retry", "resume_metrics_untouched"):
            assert (
                still_failing.summary.scanners[name].metrics
                == initial.summary.scanners[name].metrics
            )
        marker.touch()
        resumed = scan_resume(initial.location, display="none")
        clean = scan(
            scanners=[
                retry_metrics(str(marker), first_value),
                untouched_metrics(first_value),
            ],
            transcripts=transcripts_from(LOGS_DIR),
            scans=str(tmp_path / "clean"),
            limit=2,
            max_processes=processes,
            display="none",
        )
    assert resumed.complete and not resumed.errors
    for name in ("resume_metrics_retry", "resume_metrics_untouched"):
        assert clean.summary.scanners[name].metrics == {
            name: {"mean": 0.5, "stderr": 0.5}
        }
        assert (
            resumed.summary.scanners[name].metrics
            == clean.summary.scanners[name].metrics
        )


@scanner(name="resume_nonfinite", messages=["user"], metrics=[mean()])
def nonfinite_metrics(marker: str) -> Scanner[ChatMessageUser]:
    async def run(message: ChatMessageUser) -> Result:
        if message.text == "retry" and not Path(marker).exists():
            raise RuntimeError("Transient scanner failure")
        return Result(value=float("nan") if message.text == "nonfinite" else 1)

    return run


def test_resume_nonfinite_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "buffer"))
    database = str(tmp_path / "transcripts")

    async def populate() -> None:
        async with transcripts_db(database) as db:
            await db.insert(
                [
                    Transcript(
                        transcript_id="retained",
                        messages=[
                            ChatMessageUser(content="nonfinite"),
                            ChatMessageUser(content="one"),
                        ],
                    ),
                    Transcript(
                        transcript_id="retry",
                        messages=[ChatMessageUser(content="retry")],
                    ),
                ]
            )

    asyncio.run(populate())
    marker = tmp_path / "recovered"
    with temp_active_scans_store():
        initial = scan(
            scanners=[nonfinite_metrics(str(marker))],
            transcripts=transcripts_from(database),
            scans=str(tmp_path / "scans"),
            max_processes=1,
            display="none",
        )
        assert not initial.complete and len(initial.errors) == 1
        marker.touch()
        resumed = scan_resume(initial.location, display="none")
    assert resumed.complete and not resumed.errors
