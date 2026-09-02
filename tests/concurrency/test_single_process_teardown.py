"""Regression tests for the streaming seam's refcounted-handle teardown.

`ScannerJob.on_complete` closes a shared `TranscriptHandle` once every scanner
sharing it (the lead plus its followers) has run. `single_process_strategy`'s
teardown has to drain `scanner_job_deque` and run `on_complete` for whatever it
finds, or the handle's refcount never reaches zero and it never closes. Two
shapes can be stranded there when the worker pool is torn down early:

- a follower whose lead already ran (a follower is only queued inside the
  lead's own `finally`, see `single_process.py`'s `_perform_scan`);
- a lead nobody dispatched, whose followers were therefore never released --
  which is why the drain recurses into `job.followers`.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal, cast

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
    yield cast(TranscriptsReader, None)  # never dereferenced by these tests


def _lead_with_followers(
    follower_names: tuple[str, ...],
    *,
    followers_raise: bool = False,
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
            on_complete=_on_complete(name, name != "lead" and followers_raise),
            followers=followers,
        )

    lead = _job("lead", tuple(_job(name) for name in follower_names))
    return lead, visited


async def _run_until_crash(
    lead: ScannerJob, *, crash_in: Literal["record", "parse"]
) -> None:
    """Drive the strategy until a worker dies, leaving `lead` or its followers queued.

    `crash_in="record"` lets the lead run and strands its followers.
    `crash_in="parse"` kills the second parse before anything is dispatched, so
    the lead itself is stranded with its followers still attached.
    """
    parse_job_count = 1 if crash_in == "record" else 2

    async def parse_jobs() -> AsyncIterator[ParseJob]:
        for _ in range(parse_job_count):
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
        if crash_in == "parse" and parses > 1:
            raise RuntimeError("worker crashed")
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
        if crash_in == "record":
            raise RuntimeError("worker crashed")

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
async def test_teardown_runs_on_complete_for_a_follower_stranded_in_the_queue() -> None:
    """A follower left in `scanner_job_deque` still gets `on_complete` run."""
    lead, visited = _lead_with_followers(("f1",))

    await _run_until_crash(lead, crash_in="record")

    assert sorted(visited) == ["f1", "lead"]


@pytest.mark.asyncio
async def test_teardown_drain_continues_past_a_raising_on_complete() -> None:
    """One stranded job's `on_complete` raising must not stop the drain.

    Each stranded job still holds a real share of the shared handle's
    refcount; skipping the rest because one of them raised would leak the
    handle just as surely as never draining at all. Every follower raises, so
    the guard is pinned whatever order the drain visits them in.
    """
    lead, visited = _lead_with_followers(("f1", "f2", "f3"), followers_raise=True)

    await _run_until_crash(lead, crash_in="record")

    assert sorted(visited) == ["f1", "f2", "f3", "lead"]


@pytest.mark.asyncio
async def test_teardown_releases_the_followers_of_a_stranded_lead() -> None:
    """An undispatched lead's followers were never queued -- the drain must recurse.

    Nothing ever ran `_perform_scan` for this lead, so its followers are only
    reachable through `job.followers`; missing them leaves N-1 refcount shares
    outstanding and the handle open.
    """
    lead, visited = _lead_with_followers(("f1", "f2"))

    await _run_until_crash(lead, crash_in="parse")

    assert sorted(visited) == ["f1", "f2", "lead"]
