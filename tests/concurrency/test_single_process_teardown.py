"""Regression test for the streaming seam's refcounted-handle teardown.

`ScannerJob.on_complete` closes a shared `TranscriptHandle` once every scanner
sharing it (the lead plus its followers) has run. `single_process_strategy`'s
teardown has to run `on_complete` for every job that did not finish, or the
handle's refcount never reaches zero and it never closes.
"""

from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import partial
from typing import Literal, cast

import anyio
import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import (
    LoaderItemJob,
    ParseFunctionResult,
    ParseJob,
    ScannerJob,
)
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

    async def scan_function(job: ScannerJob) -> AsyncGenerator[LoaderItemJob, None]:
        # never pulled: nothing dispatches the lead
        no_items: list[LoaderItemJob] = []
        for item in no_items:
            yield item

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


_CancelPoint = Literal[
    "grant_wait", "active_pull", "item_scan", "on_complete", "record"
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "point,task_count",
    [
        # the only worker waits for item 0, so the owner waits for a grant
        ("grant_wait", 1),
        # item 0 scans while the owner pulls item 1
        ("active_pull", 2),
        # both items scan, and the loader is done
        ("item_scan", 4),
        ("on_complete", 4),
        ("record", 4),
    ],
)
async def test_cancel_releases_each_job_once_and_closes_loaders(
    point: _CancelPoint, task_count: int
) -> None:
    """A cancel at any point releases each job's handle share exactly once.

    The lead has two items and one follower. Each loader does every pull and
    its close in one task. In the active-pull case the loader shields its
    awaited cleanup, so the cleanup completes.
    """
    scope = anyio.CancelScope()
    on_complete_calls: dict[str, int] = {}
    pull_tasks: dict[str, set[int]] = {}
    close_tasks: dict[str, int] = {}
    cleaned_up: list[str] = []
    in_flight = 0

    async def cancel_and_wait() -> None:
        scope.cancel()
        await anyio.sleep_forever()

    def _job(name: str, followers: tuple[ScannerJob, ...] = ()) -> ScannerJob:
        async def on_complete() -> None:
            on_complete_calls[name] = on_complete_calls.get(name, 0) + 1
            if point == "on_complete" and name == "lead":
                scope.cancel()
                # shielded by the strategy, so this completes
                await anyio.sleep(0.01)

        return ScannerJob(
            union_transcript=Transcript(transcript_id="t1"),
            scanner=_noop_scanner(),
            scanner_name=name,
            followers=followers,
            on_complete=on_complete,
        )

    lead = _job("lead", (_job("follower"),))

    async def scan_item(name: str) -> ResultReport | None:
        nonlocal in_flight
        in_flight += 1
        if name == "lead":
            if point == "grant_wait":
                await cancel_and_wait()
            if point == "active_pull":
                await anyio.sleep_forever()
            if point == "item_scan" and in_flight == 2:
                await cancel_and_wait()
            if point == "item_scan":
                await anyio.sleep_forever()
        return None

    async def scan_function(job: ScannerJob) -> AsyncGenerator[LoaderItemJob, None]:
        name = job.scanner_name
        try:
            for index in range(2):
                pull_tasks.setdefault(name, set()).add(anyio.get_current_task().id)
                if point == "active_pull" and name == "lead" and index == 1:
                    await cancel_and_wait()
                yield LoaderItemJob(job, partial(scan_item, name))
        finally:
            close_tasks[name] = anyio.get_current_task().id
            if point == "active_pull":
                with anyio.CancelScope(shield=True):
                    await anyio.sleep(0.01)
                    cleaned_up.append(name)

    async def parse_jobs() -> AsyncIterator[ParseJob]:
        yield ParseJob(
            transcript_info=TranscriptInfo(transcript_id="t1"),
            scanner_indices={0, 1},
        )

    async def parse_function(
        job: ParseJob, reader: TranscriptsReader
    ) -> ParseFunctionResult:
        return True, lead

    async def record_results(
        info: TranscriptInfo, scanner_name: str, results: list[ResultReport]
    ) -> None:
        if point == "record" and scanner_name == "lead":
            await cancel_and_wait()

    with anyio.fail_after(10):
        with scope:
            await single_process_strategy(task_count=task_count)(
                parse_jobs=parse_jobs(),
                parse_function=parse_function,
                scan_function=scan_function,
                record_results=record_results,
                update_metrics=lambda _: None,
                reader_cm_factory=_reader_cm,
            )

    assert scope.cancelled_caught
    assert on_complete_calls == {"lead": 1, "follower": 1}
    # every loader that was pulled from was closed, in its pulling task
    assert close_tasks == {name: one for name, (one,) in pull_tasks.items()}
    if point == "active_pull":
        assert cleaned_up == ["lead"]
