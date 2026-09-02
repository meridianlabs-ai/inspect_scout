"""Regression test for the streaming seam's refcounted-handle teardown.

`ScannerJob.on_complete` closes a shared `TranscriptHandle` once every scanner
sharing it (the lead plus its followers) has run. `single_process_strategy`'s
teardown has to drain `scanner_job_deque` and run `on_complete` for whatever it
finds, or the handle's refcount never reaches zero and it never closes.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
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


def _lead_with_raising_followers(
    follower_names: tuple[str, ...],
) -> tuple[ScannerJob, list[str]]:
    """A lead plus its followers, all sharing one refcount, and a visit log."""
    visited: list[str] = []

    def _on_complete(name: str, raises: bool) -> Callable[[], Awaitable[None]]:
        async def on_complete() -> None:
            visited.append(name)
            if raises:
                raise RuntimeError(f"{name} on_complete boom")

        return on_complete

    transcript = Transcript(transcript_id="t1")

    def _job(name: str, followers: tuple[ScannerJob, ...] = ()) -> ScannerJob:
        return ScannerJob(
            union_transcript=transcript,
            scanner=_noop_scanner(),
            scanner_name=name,
            on_complete=_on_complete(name, name != "lead"),
            followers=followers,
        )

    lead = _job("lead", tuple(_job(name) for name in follower_names))
    return lead, visited


async def _run_until_parse_crash(lead: ScannerJob) -> None:
    """Drive the strategy until the second parse dies, leaving `lead` queued.

    Nothing dispatches the lead, so its followers are never queued either --
    they are only reachable through `job.followers`.
    """

    async def parse_jobs() -> AsyncIterator[ParseJob]:
        for _ in range(2):
            yield ParseJob(
                transcript_info=TranscriptInfo(transcript_id="t1"),
                scanner_indices={0, 1},
            )

    parses = 0

    async def parse_function(
        job: ParseJob, reader: TranscriptsReader
    ) -> ParseFunctionResult:
        nonlocal parses
        parses += 1
        if parses > 1:
            raise RuntimeError("worker crashed")
        return True, lead

    async def scan_function(job: ScannerJob) -> list[ResultReport]:
        return []

    async def record_results(
        info: TranscriptInfo, scanner_name: str, results: list[ResultReport]
    ) -> None:
        return None

    # A queue deeper than one keeps the second parse from being pre-empted by a
    # scan, which is what leaves the first lead undispatched.
    strategy = single_process_strategy(task_count=1, prefetch_multiple=10.0)

    with pytest.raises(RuntimeError, match="worker crashed"):
        await strategy(
            parse_jobs=parse_jobs(),
            parse_function=parse_function,
            scan_function=scan_function,
            record_results=record_results,
            update_metrics=lambda _: None,
            reader_cm_factory=_reader_cm,
        )


@pytest.mark.asyncio
async def test_teardown_releases_a_stranded_lead_and_all_its_followers() -> None:
    """Every share of a stranded job's refcount is released, raises included.

    Missing the followers leaves N-1 shares outstanding and the handle open;
    so does letting one job's raising `on_complete` abandon the rest of the
    drain, which is why every follower here raises.
    """
    lead, visited = _lead_with_raising_followers(("f1", "f2"))

    await _run_until_parse_crash(lead)

    assert sorted(visited) == ["f1", "f2", "lead"]
