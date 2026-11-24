"""Loader items as units of work of `single_process_strategy`.

The jobs here are stubs: each `scan_function` is an async generator that
yields `LoaderItemJob`s, as `_scan_one` does. Concurrency is proven with
barriers, not wall-clock limits. Every run is bounded by `_TIMEOUT`, so a
barrier that cannot open fails the test and does not hang it.
"""

from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import partial
from typing import cast

import anyio
import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import (
    LoaderItemJob,
    ParseFunctionResult,
    ParseJob,
    ScanMetrics,
    ScannerJob,
)
from inspect_scout._concurrency.single_process import single_process_strategy
from inspect_scout._scanner.result import Result, ResultReport
from inspect_scout._scanner.scanner import Scanner
from inspect_scout._transcript.transcripts import TranscriptsReader
from inspect_scout._transcript.types import Transcript, TranscriptInfo

_TIMEOUT = 10


@scanner(messages="all")
def _noop_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    return scan


def _report(transcript_id: str, index: int) -> ResultReport:
    return ResultReport(
        input_type="transcript",
        input_ids=[f"{transcript_id}-{index}"],
        input=Transcript(transcript_id=transcript_id),
        result=Result(value=index),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )


@dataclass
class _Run:
    """What one strategy run did."""

    log: list[tuple[str, str]] = field(default_factory=list)
    """(what, job name) in the order it happened."""
    records: dict[str, list[int]] = field(default_factory=dict)
    on_complete_calls: dict[str, int] = field(default_factory=dict)
    in_flight: int = 0
    peak: int = 0
    metrics: ScanMetrics | None = None

    def job(self, name: str, followers: tuple[ScannerJob, ...] = ()) -> ScannerJob:
        async def on_complete() -> None:
            self.on_complete_calls[name] = self.on_complete_calls.get(name, 0) + 1
            self.log.append(("on_complete", name))

        return ScannerJob(
            union_transcript=Transcript(transcript_id=name),
            scanner=_noop_scanner(),
            scanner_name=name,
            followers=followers,
            on_complete=on_complete,
        )

    async def record_results(
        self, info: TranscriptInfo, scanner_name: str, results: list[ResultReport]
    ) -> None:
        assert scanner_name not in self.records, f"{scanner_name} recorded twice"
        self.records[scanner_name] = sorted(
            cast(int, r.result.value) for r in results if r.result is not None
        )
        self.log.append(("record", scanner_name))

    def update_metrics(self, metrics: ScanMetrics) -> None:
        self.metrics = metrics


ItemWait = Callable[[_Run, str, int], Awaitable[None]]


async def _no_wait(run: _Run, name: str, index: int) -> None:
    await anyio.lowlevel.checkpoint()


def _items_scan_function(
    run: _Run,
    items: dict[str, int],
    *,
    wait: ItemWait = _no_wait,
    pull_delay: float = 0,
    end_delay: float = 0,
) -> Callable[[ScannerJob], AsyncGenerator[LoaderItemJob, None]]:
    """A loader that yields `items[name]` items for each job."""

    async def scan_item(job: ScannerJob, index: int) -> ResultReport:
        name = job.scanner_name
        run.log.append(("scan", name))
        run.in_flight += 1
        run.peak = max(run.peak, run.in_flight)
        await wait(run, name, index)
        run.in_flight -= 1
        return _report(name, index)

    async def scan_function(job: ScannerJob) -> AsyncGenerator[LoaderItemJob, None]:
        for index in range(items[job.scanner_name]):
            await anyio.sleep(pull_delay)
            yield LoaderItemJob(job, partial(scan_item, job, index))
        await anyio.sleep(end_delay)

    return scan_function


@asynccontextmanager
async def _reader_cm() -> AsyncIterator[TranscriptsReader]:
    yield cast(TranscriptsReader, None)  # never dereferenced by these tests


async def _run_strategy(
    run: _Run,
    leads: list[ScannerJob],
    scan_function: Callable[[ScannerJob], AsyncGenerator[LoaderItemJob, None]],
    *,
    task_count: int,
    parse_delay: float = 0,
) -> None:
    async def parse_jobs() -> AsyncIterator[ParseJob]:
        for lead in leads:
            yield ParseJob(transcript_info=lead.transcript_info, scanner_indices={0})

    by_id = {lead.transcript_info.transcript_id: lead for lead in leads}

    async def parse_function(
        job: ParseJob, reader: TranscriptsReader
    ) -> ParseFunctionResult:
        await anyio.sleep(parse_delay)
        return True, by_id[job.transcript_info.transcript_id]

    with anyio.fail_after(_TIMEOUT):
        await single_process_strategy(task_count=task_count)(
            parse_jobs=parse_jobs(),
            parse_function=parse_function,
            scan_function=scan_function,
            record_results=run.record_results,
            update_metrics=run.update_metrics,
            reader_cm_factory=_reader_cm,
        )


@pytest.mark.asyncio
async def test_items_of_one_job_scan_in_parallel() -> None:
    run = _Run()
    all_in_flight = anyio.Event()
    scanning_at_peak: list[int] = []

    async def wait(run: _Run, name: str, index: int) -> None:
        if run.in_flight == 8:
            assert run.metrics is not None
            scanning_at_peak.append(run.metrics.tasks_scanning)
            all_in_flight.set()
        await all_in_flight.wait()

    await _run_strategy(
        run,
        [run.job("t")],
        _items_scan_function(run, {"t": 8}, wait=wait),
        task_count=8,
    )

    assert run.peak == 8
    assert run.records == {"t": list(range(8))}
    assert run.on_complete_calls == {"t": 1}
    # every worker holds its slot while its item scans
    assert scanning_at_peak == [8]


@pytest.mark.asyncio
async def test_items_in_flight_limited_by_workers() -> None:
    run = _Run()
    await _run_strategy(
        run,
        [run.job("t")],
        _items_scan_function(run, {"t": 8}, wait=lambda *_: anyio.sleep(0.01)),
        task_count=3,
    )
    assert run.peak == 3
    assert run.records == {"t": list(range(8))}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "items,item_delay,end_delay",
    [
        (0, 0, 0),
        (1, 0, 0),
        # end of loader after the last report
        (3, 0, 0.05),
        # end of loader before the last report
        (3, 0.05, 0),
    ],
)
async def test_job_finishes_once(
    items: int, item_delay: float, end_delay: float
) -> None:
    run = _Run()
    await _run_strategy(
        run,
        [run.job("t")],
        _items_scan_function(
            run,
            {"t": items},
            wait=lambda *_: anyio.sleep(item_delay),
            end_delay=end_delay,
        ),
        task_count=4,
    )
    assert run.records == {"t": list(range(items))}
    assert run.on_complete_calls == {"t": 1}
    # on_complete before record, as before items were units of work
    assert [what for what, _ in run.log if what != "scan"] == [
        "on_complete",
        "record",
    ]


@pytest.mark.asyncio
async def test_followers_start_after_the_lead_finishes() -> None:
    run = _Run()
    lead = run.job("lead", followers=(run.job("f1"), run.job("f2")))
    await _run_strategy(
        run,
        [lead],
        _items_scan_function(
            run,
            {"lead": 3, "f1": 3, "f2": 3},
            wait=lambda *_: anyio.sleep(0.01),
        ),
        task_count=8,
    )

    lead_record = run.log.index(("record", "lead"))
    follower_scans = [
        i for i, (what, name) in enumerate(run.log) if what == "scan" and name != "lead"
    ]
    assert len(follower_scans) == 6
    assert min(follower_scans) > lead_record
    assert run.records == {name: [0, 1, 2] for name in ("lead", "f1", "f2")}
    assert run.on_complete_calls == {"lead": 1, "f1": 1, "f2": 1}
    assert run.metrics is not None
    assert run.metrics.completed_scans == 3


@pytest.mark.asyncio
async def test_slow_loader_while_parse_still_runs() -> None:
    """Workers that go idle while a slow loader pulls do not end the scan early."""
    run = _Run()
    names = [f"t{i}" for i in range(4)]
    await _run_strategy(
        run,
        [run.job(name) for name in names],
        _items_scan_function(run, dict.fromkeys(names, 3), pull_delay=0.03),
        task_count=2,
        parse_delay=0.02,
    )
    assert run.records == {name: [0, 1, 2] for name in names}
    assert run.on_complete_calls == dict.fromkeys(names, 1)


_loader_context: ContextVar[int | None] = ContextVar("_loader_context", default=None)


@pytest.mark.asyncio
async def test_pulls_and_close_in_one_task_and_scanner_sees_loader_context() -> None:
    """A loader may hold a context token and a cancel scope across a `yield`.

    That needs every pull and the close in one task. The scanner also sees
    the context that the loader set before it yielded the item.
    """
    run = _Run()
    pull_tasks: set[int] = set()
    close_tasks: list[int] = []
    seen: dict[int, int | None] = {}
    all_in_flight = anyio.Event()

    async def scan_item(index: int) -> ResultReport:
        seen[index] = _loader_context.get()
        run.in_flight += 1
        run.peak = max(run.peak, run.in_flight)
        if run.in_flight == 4:
            all_in_flight.set()
        await all_in_flight.wait()
        return _report("t", index)

    async def scan_function(job: ScannerJob) -> AsyncGenerator[LoaderItemJob, None]:
        try:
            with anyio.CancelScope():
                for index in range(4):
                    pull_tasks.add(anyio.get_current_task().id)
                    await anyio.sleep(0.01)
                    token = _loader_context.set(index)
                    yield LoaderItemJob(job, partial(scan_item, index))
                    # raises if this pull runs in another task than the last
                    _loader_context.reset(token)
        finally:
            close_tasks.append(anyio.get_current_task().id)

    await _run_strategy(run, [run.job("t")], scan_function, task_count=4)

    assert run.peak == 4
    assert seen == {index: index for index in range(4)}
    assert len(pull_tasks) == 1
    assert close_tasks == list(pull_tasks)
    assert run.records == {"t": [0, 1, 2, 3]}


@pytest.mark.asyncio
async def test_bare_cancelled_error_from_a_scanner_is_not_a_success() -> None:
    """A scanner that raises a bare `CancelledError` cancels the worker pool.

    AnyIO does not report that exception, so the pool ends normally. The
    strategy must still not return as if every job finished.
    """
    run = _Run()

    async def wait(run: _Run, name: str, index: int) -> None:
        if index == 1:
            raise anyio.get_cancelled_exc_class()()
        await anyio.sleep(0.05)

    with pytest.raises(RuntimeError, match="Scan interrupted"):
        await _run_strategy(
            run,
            [run.job("t")],
            _items_scan_function(run, {"t": 4}, wait=wait),
            task_count=4,
        )
    assert run.records == {}
    assert run.on_complete_calls == {"t": 1}
