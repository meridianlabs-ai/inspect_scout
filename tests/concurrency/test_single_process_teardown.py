"""Regression test for the streaming seam's refcounted-handle teardown.

`ScannerJob.on_complete` closes a shared `TranscriptHandle` once every scanner
sharing it (the lead plus its followers) has run. A follower is only queued
onto `scanner_job_deque` inside the lead's own `finally` (see
`single_process.py`'s `_perform_scan`), so a worker pool torn down right after
the lead -- crash or cancellation -- can strand a follower there with nobody
left to pop it. `single_process_strategy`'s own teardown has to drain that
deque and run `on_complete` for whatever it finds, or the handle's refcount
never reaches zero and it never closes.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import ParseFunctionResult, ParseJob, ScannerJob
from inspect_scout._concurrency.single_process import single_process_strategy
from inspect_scout._scanner.result import Result, ResultReport
from inspect_scout._scanner.scanner import Scanner
from inspect_scout._transcript.transcripts import TranscriptsReader
from inspect_scout._transcript.types import Transcript, TranscriptInfo


@scanner(messages="all")
def _noop_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    return scan


@asynccontextmanager
async def _reader_cm() -> AsyncIterator[TranscriptsReader]:
    yield cast(TranscriptsReader, None)  # never dereferenced by this test


@pytest.mark.asyncio
async def test_teardown_runs_on_complete_for_a_follower_stranded_in_the_queue() -> None:
    """A follower left in `scanner_job_deque` still gets `on_complete` run.

    Reproduces the bug directly: the lead's scan (via a fake `scan_function`
    that mirrors `_scan_one`'s own `finally`-based `on_complete` call) runs
    and queues its follower, then `record_results` raises -- simulating the
    worker pool crashing before anything pops the follower. Without draining
    `scanner_job_deque` in the strategy's teardown, `remaining` would stay at
    1 and the handle would never close.
    """
    remaining = 2
    closes = 0

    async def on_complete() -> None:
        nonlocal remaining, closes
        remaining -= 1
        if remaining == 0:
            closes += 1

    transcript = Transcript(transcript_id="t1")
    follower = ScannerJob(
        union_transcript=transcript,
        scanner=_noop_scanner(),
        scanner_name="follower",
        on_complete=on_complete,
    )
    lead = ScannerJob(
        union_transcript=transcript,
        scanner=_noop_scanner(),
        scanner_name="lead",
        followers=(follower,),
        on_complete=on_complete,
    )

    async def parse_jobs() -> AsyncIterator[ParseJob]:
        yield ParseJob(
            transcript_info=TranscriptInfo(transcript_id="t1"),
            scanner_indices={0, 1},
        )

    async def parse_function(
        job: ParseJob, reader: TranscriptsReader
    ) -> ParseFunctionResult:
        return True, lead

    async def scan_function(job: ScannerJob) -> list[ResultReport]:
        try:
            return []
        finally:
            if job.on_complete is not None:
                await job.on_complete()

    async def record_results(
        info: TranscriptInfo, scanner_name: str, results: list[ResultReport]
    ) -> None:
        if scanner_name == "lead":
            raise RuntimeError("worker crashed")

    strategy = single_process_strategy(task_count=1)

    with pytest.raises(RuntimeError, match="worker crashed"):
        await strategy(
            parse_jobs=parse_jobs(),
            parse_function=parse_function,
            scan_function=scan_function,
            record_results=record_results,
            update_metrics=lambda _: None,
            reader_cm_factory=_reader_cm,
        )

    assert remaining == 0
    assert closes == 1
